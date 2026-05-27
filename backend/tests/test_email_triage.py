"""
Tests for Email Triage Agent.
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


def test_classify_email_urgent(email_triage, sample_email):
    """Test classifying an urgent email."""
    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        CATEGORY: urgent
        PRIORITY: 5
        REASONING: Deadline tomorrow, from boss
        SUMMARY: Project report due tomorrow at 5 PM
        """

        classification = email_triage.classify_email(sample_email)

        assert classification['category'] == 'urgent'
        assert classification['priority'] == 5
        assert classification['email_id'] == 'email_123'
        assert classification['subject'] == sample_email['subject']
        mock_ollama.generate.assert_called_once()


def test_classify_email_normal(email_triage):
    """Test classifying a normal email."""
    email = {
        'id': 'email_456',
        'subject': 'Weekly team update',
        'sender': 'team@company.com',
        'snippet': 'Here is the weekly update on project progress',
        'body': 'Weekly update content...'
    }

    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        CATEGORY: normal
        PRIORITY: 3
        REASONING: Weekly update, not time-sensitive
        SUMMARY: Team weekly progress update
        """

        classification = email_triage.classify_email(email)

        assert classification['category'] == 'normal'
        assert classification['priority'] == 3


def test_classify_email_ignore(email_triage):
    """Test classifying an ignore email."""
    email = {
        'id': 'email_789',
        'subject': 'Newsletter: Latest updates',
        'sender': 'newsletter@company.com',
        'snippet': 'Check out our latest blog posts and updates',
        'body': 'Newsletter content...'
    }

    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        CATEGORY: ignore
        PRIORITY: 1
        REASONING: Newsletter, automated promotional content
        SUMMARY: Company newsletter with blog updates
        """

        classification = email_triage.classify_email(email)

        assert classification['category'] == 'ignore'
        assert classification['priority'] == 1


def test_classify_email_error_handling(email_triage, sample_email):
    """Test graceful error handling in classification."""
    with patch("backend.agents.email_triage.ollama_client") as mock_ollama:
        mock_ollama.generate.side_effect = Exception("Model error")

        classification = email_triage.classify_email(sample_email)

        # Should default to normal on error
        assert classification['category'] == 'normal'
        assert classification['priority'] == 3
        assert 'error' in classification['reasoning'].lower()


def test_triage_inbox_no_emails(email_triage):
    """Test triaging when inbox is empty."""
    email_triage.gmail.authenticate = Mock(return_value=True)
    email_triage.gmail.fetch_unread_emails = Mock(return_value=[])

    result = email_triage.triage_inbox()

    assert result == []


def test_triage_inbox_with_emails(email_triage, sample_email):
    """Test triaging inbox with multiple emails."""
    email_triage.gmail.authenticate = Mock(return_value=True)
    email_triage.gmail.fetch_unread_emails = Mock(return_value=[sample_email])

    with patch.object(email_triage, 'classify_email') as mock_classify:
        mock_classify.return_value = {
            'email_id': 'email_123',
            'subject': sample_email['subject'],
            'sender': sample_email['sender'],
            'category': 'urgent',
            'priority': 5,
            'reasoning': 'Deadline tomorrow',
            'summary': 'Project report due'
        }

        result = email_triage.triage_inbox(max_emails=10)

        assert len(result) == 1
        assert result[0]['category'] == 'urgent'
        mock_classify.assert_called_once()


def test_triage_inbox_auth_failure(email_triage):
    """Test handling authentication failure."""
    email_triage.gmail.authenticate = Mock(return_value=False)

    result = email_triage.triage_inbox()

    assert result == []


def test_store_urgent_in_memory(email_triage):
    """Test storing urgent email in memory."""
    classification = {
        'email_id': 'email_123',
        'subject': 'Urgent deadline',
        'sender': 'boss@company.com',
        'category': 'urgent',
        'priority': 5,
        'reasoning': 'Deadline tomorrow',
        'summary': 'Project report due tomorrow'
    }

    email_triage.memory_agent.store = Mock()
    email_triage.memory_agent.store.write_memory = Mock()

    email_triage._store_in_memory(classification)

    email_triage.memory_agent.store.write_memory.assert_called_once()
    call_args = email_triage.memory_agent.store.write_memory.call_args
    assert call_args[1]['importance'] == 2  # Critical
    assert 'urgent' in call_args[1]['tags']


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
