"""
Tests for Email Triage Agent (two-stage pipeline).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.agents.email_triage import EmailTriageAgent


@pytest.fixture
def email_triage():
    """Create email triage agent with mocked dependencies."""
    with patch("backend.agents.email_triage.gmail_client") as mock_gmail:
        with patch("backend.agents.email_triage.MemoryAgent") as mock_memory:
            agent = EmailTriageAgent(memory_agent=mock_memory())
            agent.gmail = mock_gmail
            return agent


@pytest.fixture
def sample_email():
    """Sample email for testing."""
    return {
        'id': 'email_123',
        'subject': 'Urgent: Project deadline tomorrow',
        'sender': 'boss@company.com',
        'snippet': 'Please review and submit the project report by tomorrow 5 PM',
        'body': 'Hi, Please review and submit the project report by tomorrow 5 PM. This is critical for the client meeting.',
        'date': 'Mon, 26 May 2026 10:00:00 +0000',
        'thread_id': 'thread_123',
        'labels': ['INBOX', 'UNREAD']
    }


@pytest.fixture
def newsletter_email():
    """Sample newsletter email for testing rule engine."""
    return {
        'id': 'email_news_1',
        'subject': 'Weekly Newsletter: Latest updates',
        'sender': 'newsletter@techblog.com',
        'snippet': 'Check out our latest blog posts and updates',
        'body': 'Newsletter content...'
    }


@pytest.fixture
def ambiguous_email():
    """Sample ambiguous email that needs LLM classification."""
    return {
        'id': 'email_ambig_1',
        'subject': 'Re: Project status update',
        'sender': 'colleague@company.com',
        'snippet': 'Thanks for the update. I had a few questions about the timeline.',
        'body': 'Longer body content...'
    }


# --- Parse classification tests ---

def test_parse_classification(email_triage):
    """Test parsing classification response."""
    response = """
    CATEGORY: urgent
    PRIORITY: 5
    REASONING: Project deadline is tomorrow, marked as urgent
    SUMMARY: Boss requesting project report submission by tomorrow 5 PM
    """

    result = email_triage._parse_classification(response)

    assert result['category'] == 'urgent'
    assert result['priority'] == 5
    assert 'deadline' in result['reasoning'].lower()
    assert 'project report' in result['summary'].lower()


# --- Rule engine classification tests ---

def test_classify_newsletter_via_rules(email_triage, newsletter_email):
    """Newsletter emails should be classified by rule engine, no LLM call."""
    classification = email_triage.classify_email(newsletter_email)

    assert classification['category'] == 'ignore'
    assert classification['classification_source'] == 'rule_engine'
    assert classification['email_id'] == 'email_news_1'


def test_classify_urgent_keyword_via_rules(email_triage, sample_email):
    """Emails with urgent keywords should be classified by rule engine."""
    classification = email_triage.classify_email(sample_email)

    # 'Urgent' in subject should trigger rule engine
    assert classification['category'] == 'urgent'
    assert classification['classification_source'] == 'rule_engine'


def test_classify_noreply_via_rules(email_triage):
    """Noreply sender emails should be classified by rule engine."""
    email = {
        'id': 'email_auto_1',
        'subject': 'Your receipt from Store',
        'sender': 'noreply@store.com',
        'snippet': 'Thank you for your purchase',
    }

    classification = email_triage.classify_email(email)
    assert classification['category'] == 'ignore'
    assert classification['classification_source'] == 'rule_engine'


# --- LLM classification tests ---

def test_classify_ambiguous_via_llm(email_triage, ambiguous_email):
    """Ambiguous emails should fall through to local LLM."""
    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        CATEGORY: normal
        PRIORITY: 3
        REASONING: General project update, not time-sensitive
        SUMMARY: Colleague asking questions about project timeline
        """

        classification = email_triage.classify_email(ambiguous_email)

        assert classification['category'] == 'normal'
        assert classification['priority'] == 3
        assert classification['classification_source'] == 'local_llm'
        mock_ollama.generate.assert_called_once()

        # Verify the lightweight model was used
        call_kwargs = mock_ollama.generate.call_args
        assert call_kwargs[1].get('model_override') == email_triage.triage_model


def test_classify_ambiguous_uses_correct_model(email_triage, ambiguous_email):
    """LLM classification should use the email_triage_model setting."""
    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        CATEGORY: normal
        PRIORITY: 3
        REASONING: Regular update
        SUMMARY: Status update
        """

        email_triage.classify_email(ambiguous_email)

        call_kwargs = mock_ollama.generate.call_args[1]
        assert call_kwargs['model_override'] == email_triage.triage_model
        assert call_kwargs['temperature'] == 0.3


def test_classify_llm_error_defaults_to_normal(email_triage, ambiguous_email):
    """LLM errors should default to normal classification."""
    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.side_effect = Exception("Model error")

        classification = email_triage.classify_email(ambiguous_email)

        assert classification['category'] == 'normal'
        assert classification['priority'] == 3
        assert classification['classification_source'] == 'fallback'
        assert 'error' in classification['reasoning'].lower()


# --- Cloud fallback tests ---

def test_classify_cloud_fallback_when_configured(email_triage, ambiguous_email):
    """When use_cloud is True, should use Gemini instead of Ollama."""
    email_triage.use_cloud = True

    with patch("backend.agents.email_triage.ollama_client"):
        with patch("backend.models.cloud.gemini_client") as mock_gemini:
            mock_gemini.generate.return_value = """
            CATEGORY: normal
            PRIORITY: 3
            REASONING: Regular update
            SUMMARY: Status update
            """

            classification = email_triage.classify_email(ambiguous_email)

            assert classification['classification_source'] == 'cloud_llm'
            mock_gemini.generate.assert_called_once()


# --- Triage inbox tests ---

def test_triage_inbox_no_emails(email_triage):
    """Test triaging when inbox is empty."""
    email_triage.gmail.authenticate = Mock(return_value=True)
    email_triage.gmail.fetch_unread_emails = Mock(return_value=[])

    result = email_triage.triage_inbox()

    assert result == []


def test_triage_inbox_with_mixed_emails(email_triage, sample_email, newsletter_email, ambiguous_email):
    """Test triaging inbox with mix of rule-engine and LLM-classified emails."""
    email_triage.gmail.authenticate = Mock(return_value=True)
    email_triage.gmail.fetch_unread_emails = Mock(
        return_value=[sample_email, newsletter_email, ambiguous_email]
    )

    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        CATEGORY: normal
        PRIORITY: 3
        REASONING: Regular update
        SUMMARY: Colleague question about timeline
        """

        result = email_triage.triage_inbox(max_emails=10, store_in_memory=False)

        assert len(result) == 3
        # sample_email has 'Urgent' in subject -> rule engine
        assert result[0]['classification_source'] == 'rule_engine'
        # newsletter_email has newsletter sender -> rule engine
        assert result[1]['classification_source'] == 'rule_engine'
        # ambiguous_email -> LLM
        assert result[2]['classification_source'] == 'local_llm'
        # Only ambiguous email should have triggered LLM
        assert mock_ollama.generate.call_count == 1


def test_triage_inbox_auth_failure(email_triage):
    """Test handling authentication failure."""
    email_triage.gmail.authenticate = Mock(return_value=False)

    result = email_triage.triage_inbox()

    assert result == []


# --- Memory storage tests ---

def test_store_urgent_in_memory(email_triage):
    """Test storing urgent email in memory."""
    classification = {
        'email_id': 'email_123',
        'subject': 'Urgent deadline',
        'sender': 'boss@company.com',
        'category': 'urgent',
        'priority': 5,
        'reasoning': 'Deadline tomorrow',
        'summary': 'Project report due tomorrow',
        'classification_source': 'rule_engine',
    }

    email_triage.memory_agent.store = Mock()
    email_triage.memory_agent.store.write_memory = Mock()

    email_triage._store_in_memory(classification)

    email_triage.memory_agent.store.write_memory.assert_called_once()
    call_args = email_triage.memory_agent.store.write_memory.call_args
    assert call_args[1]['importance'] == 2  # Critical
    assert 'urgent' in call_args[1]['tags']


def test_triage_stores_only_urgent_emails(email_triage, sample_email, newsletter_email):
    """Only urgent emails should be stored in memory during triage."""
    email_triage.gmail.authenticate = Mock(return_value=True)
    email_triage.gmail.fetch_unread_emails = Mock(
        return_value=[sample_email, newsletter_email]
    )

    with patch.object(email_triage, '_store_in_memory') as mock_store:
        email_triage.triage_inbox(store_in_memory=True)

        # Only the urgent email (sample_email) should trigger memory storage
        assert mock_store.call_count == 1
        stored = mock_store.call_args[0][0]
        assert stored['category'] == 'urgent'


# --- Get urgent emails test ---

def test_get_urgent_emails(email_triage):
    """Test getting only urgent emails."""
    with patch.object(email_triage, 'triage_inbox') as mock_triage:
        mock_triage.return_value = [
            {'category': 'urgent', 'priority': 5},
            {'category': 'normal', 'priority': 3},
            {'category': 'urgent', 'priority': 4},
            {'category': 'ignore', 'priority': 1},
        ]

        urgent = email_triage.get_urgent_emails()

        assert len(urgent) == 2
        assert all(e['category'] == 'urgent' for e in urgent)
