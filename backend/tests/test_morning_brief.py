"""
Tests for Morning Brief generation.
"""

import pytest
from unittest.mock import Mock, patch, mock_open

from backend.heartbeat.morning_brief import MorningBriefGenerator


@pytest.fixture
def generator():
    """Create a MorningBriefGenerator with mocked prompt file."""
    with patch("builtins.open", mock_open(read_data="MOCK_PROMPT")):
        return MorningBriefGenerator(use_cloud=True)


@pytest.fixture
def mock_calendar_events():
    """Sample calendar events."""
    return [
        {
            'summary': 'Team Standup',
            'start': '10:00 AM',
            'is_all_day': False
        },
        {
            'summary': 'Company Holiday',
            'start': '2026-05-28',
            'is_all_day': True
        }
    ]


@pytest.fixture
def mock_urgent_emails():
    """Sample urgent emails."""
    return [
        {
            'sender': 'boss@company.com',
            'subject': 'Project Update',
            'reasoning': 'VIP sender match'
        }
    ]


def test_format_context(generator, mock_calendar_events, mock_urgent_emails):
    """Test formatting of context data for the LLM."""
    
    context = generator._format_context(
        today_events=mock_calendar_events,
        tomorrow_events=[],
        urgent_emails=mock_urgent_emails
    )
    
    # Check that events are in the context
    assert 'Team Standup' in context
    assert '[10:00 AM]' in context
    assert 'Company Holiday' in context
    assert '[All Day]' in context
    
    # Check that empty schedule is handled
    assert "No events tomorrow." in context
    
    # Check that emails are in the context
    assert 'boss@company.com' in context
    assert 'Project Update' in context
    assert 'VIP sender match' in context


def test_generate_brief_success(generator):
    """Test successful brief generation pipeline."""
    # Mock data gatherers
    with patch("backend.heartbeat.morning_brief.calendar_client") as mock_cal:
        mock_cal.get_today_events.return_value = []
        mock_cal.get_tomorrow_events.return_value = []
        
        with patch("backend.heartbeat.morning_brief.EmailTriageAgent") as mock_triage_class:
            mock_triage = Mock()
            mock_triage.triage_inbox.return_value = []
            mock_triage_class.return_value = mock_triage
            
            with patch("backend.heartbeat.morning_brief.gemini_client") as mock_gemini:
                mock_gemini.generate.return_value = "# Generated Brief"
                
                # Run generator
                result = generator.generate()
                
                # Verify
                assert result == "# Generated Brief"
                mock_cal.get_today_events.assert_called_once()
                mock_cal.get_tomorrow_events.assert_called_once()
                mock_triage.triage_inbox.assert_called_once_with(max_emails=15, store_in_memory=True)
                mock_gemini.generate.assert_called_once()


def test_generate_brief_fallback_to_local(generator):
    """Test generator uses local model when use_cloud=False."""
    generator.use_cloud = False
    
    with patch("backend.heartbeat.morning_brief.calendar_client"):
        with patch("backend.heartbeat.morning_brief.EmailTriageAgent"):
            with patch("backend.heartbeat.morning_brief.ollama_client") as mock_ollama:
                mock_ollama.generate.return_value = "Local Brief"
                
                result = generator.generate()
                
                assert result == "Local Brief"
                mock_ollama.generate.assert_called_once()
