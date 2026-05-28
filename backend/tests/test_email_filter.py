"""
Tests for Rule-Based Email Filter.
"""

import pytest

from backend.agents.email_filter import EmailFilter


@pytest.fixture
def email_filter():
    """Create email filter with default settings."""
    return EmailFilter()


@pytest.fixture
def email_filter_with_vips():
    """Create email filter with VIP senders configured."""
    return EmailFilter(vip_senders=["boss@company.com", "@executive.com"])


# --- IGNORE: Sender pattern tests ---

def test_ignore_noreply_sender(email_filter):
    """Noreply senders should be classified as ignore."""
    email = {
        "id": "1",
        "subject": "Your order has shipped",
        "sender": "noreply@store.com",
        "snippet": "Your order #12345 has shipped",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"
    assert result["classification_source"] == "rule_engine"


def test_ignore_newsletter_sender(email_filter):
    """Newsletter senders should be classified as ignore."""
    email = {
        "id": "2",
        "subject": "This week in tech",
        "sender": "newsletter@techblog.com",
        "snippet": "Top stories this week...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"


def test_ignore_marketing_sender(email_filter):
    """Marketing senders should be classified as ignore."""
    email = {
        "id": "3",
        "subject": "Exciting new features",
        "sender": "marketing@saas-product.com",
        "snippet": "We have exciting updates...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"


def test_ignore_notifications_sender(email_filter):
    """Notification senders should be classified as ignore."""
    email = {
        "id": "4",
        "subject": "New login detected",
        "sender": "notifications@service.com",
        "snippet": "A new login was detected on your account",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"


def test_ignore_donotreply_sender(email_filter):
    """Do-not-reply senders should be classified as ignore."""
    email = {
        "id": "5",
        "subject": "Password changed",
        "sender": "do-not-reply@bank.com",
        "snippet": "Your password was changed",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"


# --- IGNORE: Subject pattern tests ---

def test_ignore_unsubscribe_subject(email_filter):
    """Subjects with unsubscribe should be classified as ignore."""
    email = {
        "id": "6",
        "subject": "Weekly digest - click to unsubscribe",
        "sender": "team@somecompany.com",
        "snippet": "Here is your weekly digest...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"


def test_ignore_newsletter_subject(email_filter):
    """Subjects mentioning newsletter should be classified as ignore."""
    email = {
        "id": "7",
        "subject": "Monthly Newsletter: Company updates",
        "sender": "hr@company.com",
        "snippet": "Read the latest updates...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"


def test_ignore_promotion_subject(email_filter):
    """Promotional subjects should be classified as ignore."""
    email = {
        "id": "8",
        "subject": "Special offer: 50% off today only",
        "sender": "deals@shop.com",
        "snippet": "Limited time offer...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "ignore"


# --- URGENT: Subject pattern tests ---

def test_urgent_deadline_subject(email_filter):
    """Subjects with deadline should be classified as urgent."""
    email = {
        "id": "9",
        "subject": "Project deadline extended to Friday",
        "sender": "manager@company.com",
        "snippet": "The deadline has been moved...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "urgent"
    assert result["classification_source"] == "rule_engine"


def test_urgent_asap_subject(email_filter):
    """Subjects with ASAP should be classified as urgent."""
    email = {
        "id": "10",
        "subject": "Need this report ASAP",
        "sender": "colleague@company.com",
        "snippet": "Can you send the report?",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "urgent"


def test_urgent_action_required_subject(email_filter):
    """Subjects with action required should be classified as urgent."""
    email = {
        "id": "11",
        "subject": "Action Required: Review access permissions",
        "sender": "admin@company.com",
        "snippet": "Your access needs review...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "urgent"


def test_urgent_meeting_tomorrow_subject(email_filter):
    """Subjects about meeting tomorrow should be classified as urgent."""
    email = {
        "id": "12",
        "subject": "Meeting tomorrow at 9 AM - agenda attached",
        "sender": "team@company.com",
        "snippet": "Please review the agenda...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "urgent"


def test_urgent_due_today_subject(email_filter):
    """Subjects with due today should be classified as urgent."""
    email = {
        "id": "13",
        "subject": "Reminder: Assignment due today",
        "sender": "professor@university.edu",
        "snippet": "Your assignment is due...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "urgent"


# --- URGENT: VIP sender tests ---

def test_urgent_vip_sender(email_filter_with_vips):
    """VIP senders should always be classified as urgent."""
    email = {
        "id": "14",
        "subject": "Quick question about the project",
        "sender": "boss@company.com",
        "snippet": "Hey, just wanted to ask...",
    }
    result = email_filter_with_vips.classify(email)
    assert result is not None
    assert result["category"] == "urgent"
    assert result["priority"] == 5  # VIP gets highest priority


def test_urgent_vip_domain_match(email_filter_with_vips):
    """VIP domain patterns should match any sender from that domain."""
    email = {
        "id": "15",
        "subject": "Budget review needed",
        "sender": "cfo@executive.com",
        "snippet": "Please review the budget...",
    }
    result = email_filter_with_vips.classify(email)
    assert result is not None
    assert result["category"] == "urgent"
    assert result["priority"] == 5


# --- AMBIGUOUS: Returns None ---

def test_ambiguous_regular_email(email_filter):
    """Regular work emails should return None (needs LLM)."""
    email = {
        "id": "16",
        "subject": "Re: Project status update",
        "sender": "colleague@company.com",
        "snippet": "Thanks for the update. I had a few questions...",
    }
    result = email_filter.classify(email)
    assert result is None


def test_ambiguous_personal_email(email_filter):
    """Personal emails without patterns should return None."""
    email = {
        "id": "17",
        "subject": "Dinner plans for Saturday?",
        "sender": "friend@gmail.com",
        "snippet": "Hey, are you free this Saturday?",
    }
    result = email_filter.classify(email)
    assert result is None


def test_ambiguous_work_question(email_filter):
    """Work questions without urgency signals should return None."""
    email = {
        "id": "18",
        "subject": "Question about API design",
        "sender": "dev@company.com",
        "snippet": "I was looking at the API and had some thoughts...",
    }
    result = email_filter.classify(email)
    assert result is None


# --- Edge cases ---

def test_empty_subject(email_filter):
    """Email with empty subject should return None (ambiguous)."""
    email = {
        "id": "19",
        "subject": "",
        "sender": "someone@company.com",
        "snippet": "Some content here",
    }
    result = email_filter.classify(email)
    assert result is None


def test_empty_sender(email_filter):
    """Email with empty sender should return None (ambiguous)."""
    email = {
        "id": "20",
        "subject": "Some subject",
        "sender": "",
        "snippet": "Some content",
    }
    result = email_filter.classify(email)
    assert result is None


def test_vip_overrides_ignore_subject(email_filter_with_vips):
    """VIP sender should override an ignore-pattern subject."""
    email = {
        "id": "21",
        "subject": "Newsletter: Team updates",
        "sender": "boss@company.com",
        "snippet": "Important team updates...",
    }
    # VIP check runs BEFORE ignore check, so boss wins
    result = email_filter_with_vips.classify(email)
    assert result is not None
    assert result["category"] == "urgent"


# --- VIP management tests ---

def test_add_vip_sender(email_filter):
    """Adding a VIP sender should make their emails urgent."""
    email = {
        "id": "22",
        "subject": "Casual question",
        "sender": "newboss@company.com",
        "snippet": "Hey...",
    }

    # Before adding VIP - should be ambiguous
    assert email_filter.classify(email) is None

    # After adding VIP - should be urgent
    email_filter.add_vip_sender("newboss@company.com")
    result = email_filter.classify(email)
    assert result is not None
    assert result["category"] == "urgent"


def test_remove_vip_sender(email_filter_with_vips):
    """Removing a VIP sender should stop flagging them as urgent."""
    email = {
        "id": "23",
        "subject": "Casual question",
        "sender": "boss@company.com",
        "snippet": "Hey...",
    }

    # Before removal - urgent
    result = email_filter_with_vips.classify(email)
    assert result["category"] == "urgent"

    # After removal - ambiguous (None)
    email_filter_with_vips.remove_vip_sender("boss@company.com")
    result = email_filter_with_vips.classify(email)
    assert result is None


def test_get_vip_senders(email_filter_with_vips):
    """Should return sorted list of VIP senders."""
    vips = email_filter_with_vips.get_vip_senders()
    assert vips == ["@executive.com", "boss@company.com"]


# --- Classification source tracking ---

def test_classification_source_is_rule_engine(email_filter):
    """All rule-engine classifications should have correct source."""
    email = {
        "id": "24",
        "subject": "Urgent: Server down",
        "sender": "alerts@monitoring.com",
        "snippet": "Production server is down",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["classification_source"] == "rule_engine"


def test_priority_urgent_keywords_is_4(email_filter):
    """Urgent keyword matches should get priority 4 (VIP gets 5)."""
    email = {
        "id": "25",
        "subject": "Deadline approaching",
        "sender": "pm@company.com",
        "snippet": "The project deadline is...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["priority"] == 4  # Keyword urgent, not VIP


def test_priority_ignore_is_1(email_filter):
    """Ignore classifications should get priority 1."""
    email = {
        "id": "26",
        "subject": "Weekly digest",
        "sender": "digest@blog.com",
        "snippet": "Your weekly summary...",
    }
    result = email_filter.classify(email)
    assert result is not None
    assert result["priority"] == 1
