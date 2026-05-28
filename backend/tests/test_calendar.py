"""
Tests for Google Calendar API integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta

from backend.integrations.calendar import GoogleCalendarClient


@pytest.fixture
def calendar_client():
    """Create calendar client with mocked dependencies."""
    return GoogleCalendarClient(credentials_path="dummy.json", token_path="dummy_token.json")


@pytest.fixture
def sample_events_response():
    """Sample API response from Google Calendar."""
    return {
        'items': [
            {
                'id': 'event1',
                'summary': 'Team Standup',
                'description': 'Daily sync',
                'start': {'dateTime': '2026-05-28T10:00:00Z'},
                'end': {'dateTime': '2026-05-28T10:30:00Z'},
                'location': 'Zoom',
                'status': 'confirmed',
                'attendees': [{'email': 'team@company.com'}]
            },
            {
                'id': 'event2',
                'summary': 'Company Holiday',
                'start': {'date': '2026-05-28'},
                'end': {'date': '2026-05-29'},
                'status': 'confirmed'
            }
        ]
    }


def test_authenticate_success_with_existing_token(calendar_client):
    """Test successful authentication when token exists."""
    with patch("os.path.exists", return_value=True):
        with patch("backend.integrations.calendar.Credentials") as mock_creds:
            mock_creds.from_authorized_user_file.return_value.valid = True
            with patch("backend.integrations.calendar.build") as mock_build:
                
                result = calendar_client.authenticate()
                
                assert result is True
                assert calendar_client.service is not None
                mock_build.assert_called_once_with('calendar', 'v3', credentials=mock_creds.from_authorized_user_file.return_value)


def test_fetch_events_success(calendar_client, sample_events_response):
    """Test fetching and parsing events successfully."""
    # Mock authentication
    calendar_client.authenticate = Mock(return_value=True)
    
    # Mock API service chain: service.events().list().execute()
    mock_service = MagicMock()
    mock_events = MagicMock()
    mock_list = MagicMock()
    
    mock_list.execute.return_value = sample_events_response
    mock_events.list.return_value = mock_list
    mock_service.events.return_value = mock_events
    
    calendar_client.service = mock_service
    
    # Run fetch
    time_min = datetime(2026, 5, 28, tzinfo=timezone.utc)
    time_max = datetime(2026, 5, 29, tzinfo=timezone.utc)
    events = calendar_client.fetch_events(time_min, time_max)
    
    # Verify API call
    mock_events.list.assert_called_once_with(
        calendarId='primary',
        timeMin=time_min.isoformat(),
        timeMax=time_max.isoformat(),
        maxResults=20,
        singleEvents=True,
        orderBy='startTime'
    )
    
    # Verify parsing
    assert len(events) == 2
    
    # Timed event
    assert events[0]['id'] == 'event1'
    assert events[0]['summary'] == 'Team Standup'
    assert events[0]['start'] == '2026-05-28T10:00:00Z'
    assert events[0]['is_all_day'] is False
    assert 'team@company.com' in events[0]['attendees']
    
    # All-day event
    assert events[1]['id'] == 'event2'
    assert events[1]['summary'] == 'Company Holiday'
    assert events[1]['start'] == '2026-05-28'
    assert events[1]['is_all_day'] is True


def test_get_today_events(calendar_client):
    """Test getting today's events calculates time window correctly."""
    with patch.object(calendar_client, 'fetch_events') as mock_fetch:
        mock_fetch.return_value = []
        
        calendar_client.get_today_events()
        
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args[1]
        
        time_min = call_kwargs['time_min']
        time_max = call_kwargs['time_max']
        
        assert time_min.hour == 0
        assert time_min.minute == 0
        assert time_max.hour == 0
        assert time_max.minute == 0
        
        # Max should be exactly 1 day after min
        assert time_max - time_min == timedelta(days=1)
