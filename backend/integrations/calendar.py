"""
Google Calendar API integration for fetching schedules and events.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger


# Calendar API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',  # Read events
]


class GoogleCalendarClient:
    """Client for interacting with Google Calendar API."""

    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Calendar client.

        Args:
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to store/load OAuth token for Calendar
        """
        # We can reuse the same credentials file as Gmail if both APIs are enabled in the GCP project
        self.credentials_path = credentials_path or os.getenv(
            'CALENDAR_CREDENTIALS_PATH',
            os.getenv('GMAIL_CREDENTIALS_PATH', './credentials/gmail_credentials.json')
        )
        # But we need a separate token file since the scopes are different
        self.token_path = token_path or os.getenv(
            'CALENDAR_TOKEN_PATH',
            './credentials/calendar_token.json'
        )

        self.service = None
        self.creds = None

    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API using OAuth 2.0.

        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Load existing token if available
            if os.path.exists(self.token_path):
                self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

            # If no valid credentials, go through OAuth flow
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    logger.info("Refreshing Calendar OAuth token")
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Calendar credentials not found at {self.credentials_path}")
                        return False

                    logger.info("Starting Calendar OAuth flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    )
                    # Increase timeout for slow networks/browsers
                    self.creds = flow.run_local_server(port=0, timeout_seconds=180)

                # Save credentials for future runs
                token_dir = Path(self.token_path).parent
                token_dir.mkdir(parents=True, exist_ok=True)

                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())

                logger.info(f"Calendar token saved to {self.token_path}")

            # Build Calendar service
            self.service = build('calendar', 'v3', credentials=self.creds)
            logger.info("Google Calendar API authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"Calendar authentication failed: {e}")
            return False

    def fetch_events(self, time_min: datetime, time_max: datetime, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch calendar events within a specific time window.

        Args:
            time_min: Start time (timezone-aware)
            time_max: End time (timezone-aware)
            max_results: Maximum number of events to fetch

        Returns:
            List of event dicts
        """
        if not self.service:
            if not self.authenticate():
                return []

        try:
            # Convert to RFC3339 format required by API
            time_min_str = time_min.isoformat()
            time_max_str = time_max.isoformat()

            logger.info(f"Fetching calendar events from {time_min_str} to {time_max_str}")

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min_str,
                timeMax=time_max_str,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            raw_events = events_result.get('items', [])
            
            parsed_events = []
            for event in raw_events:
                # Handle both datetime (specific time) and date (all-day) events
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                is_all_day = 'date' in event['start']

                parsed_events.append({
                    'id': event['id'],
                    'summary': event.get('summary', 'No Title'),
                    'description': event.get('description', ''),
                    'start': start,
                    'end': end,
                    'is_all_day': is_all_day,
                    'location': event.get('location', ''),
                    'status': event.get('status', ''),
                    'attendees': [a.get('email') for a in event.get('attendees', []) if a.get('email')]
                })

            logger.info(f"Fetched {len(parsed_events)} events")
            return parsed_events

        except HttpError as error:
            logger.error(f"Calendar API error: {error}")
            return []

    def get_today_events(self) -> List[Dict[str, Any]]:
        """
        Helper method to get all events for the current day.
        
        Returns:
            List of today's event dicts
        """
        now = datetime.now(timezone.utc)
        
        # Start of today
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # End of today
        end_of_day = start_of_day + timedelta(days=1)
        
        return self.fetch_events(time_min=start_of_day, time_max=end_of_day)

    def get_tomorrow_events(self) -> List[Dict[str, Any]]:
        """
        Helper method to get all events for tomorrow.
        
        Returns:
            List of tomorrow's event dicts
        """
        now = datetime.now(timezone.utc)
        
        # Start of tomorrow
        start_of_tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # End of tomorrow
        end_of_tomorrow = start_of_tomorrow + timedelta(days=1)
        
        return self.fetch_events(time_min=start_of_tomorrow, time_max=end_of_tomorrow)


# Singleton instance
calendar_client = GoogleCalendarClient()
