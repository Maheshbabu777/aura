"""
Gmail API integration for reading and triaging emails.
"""

import os
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger


# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Read emails
    'https://www.googleapis.com/auth/gmail.modify',    # Modify labels
]


class GmailClient:
    """Client for interacting with Gmail API."""

    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialize Gmail client.

        Args:
            credentials_path: Path to OAuth credentials JSON (from Google Cloud Console)
            token_path: Path to store/load OAuth token
        """
        self.credentials_path = credentials_path or os.getenv(
            'GMAIL_CREDENTIALS_PATH',
            './credentials/gmail_credentials.json'
        )
        self.token_path = token_path or os.getenv(
            'GMAIL_TOKEN_PATH',
            './credentials/gmail_token.json'
        )

        self.service = None
        self.creds = None

    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API using OAuth 2.0.

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
                    logger.info("Refreshing Gmail OAuth token")
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logger.error(f"Gmail credentials not found at {self.credentials_path}")
                        return False

                    logger.info("Starting Gmail OAuth flow")
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

                logger.info(f"Gmail token saved to {self.token_path}")

            # Build Gmail service
            self.service = build('gmail', 'v1', credentials=self.creds)
            logger.info("Gmail API authenticated successfully")
            return True

        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False

    def fetch_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch unread emails from inbox.

        Args:
            max_results: Maximum number of emails to fetch

        Returns:
            List of email dicts with id, subject, sender, snippet, body, date
        """
        if not self.service:
            if not self.authenticate():
                return []

        try:
            # Fetch unread messages
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            if not messages:
                logger.info("No unread emails found")
                return []

            emails = []
            for msg in messages:
                email_data = self._get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)

            logger.info(f"Fetched {len(emails)} unread emails")
            return emails

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []

    def _get_email_details(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific email.

        Args:
            msg_id: Gmail message ID

        Returns:
            Dict with email details or None if error
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id,
                format='full'
            ).execute()

            headers = message['payload']['headers']

            # Extract key headers
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')

            # Get email body
            body = self._get_email_body(message['payload'])

            # Get snippet (preview text)
            snippet = message.get('snippet', '')

            return {
                'id': msg_id,
                'subject': subject,
                'sender': sender,
                'date': date_str,
                'snippet': snippet,
                'body': body,
                'thread_id': message.get('threadId'),
                'labels': message.get('labelIds', []),
            }

        except HttpError as error:
            logger.error(f"Error fetching email {msg_id}: {error}")
            return None

    def _get_email_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract email body from payload.

        Args:
            payload: Email payload from Gmail API

        Returns:
            Email body text
        """
        body = ""

        if 'parts' in payload:
            # Multipart email
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html':
                    # Fallback to HTML if no plain text
                    if 'data' in part['body'] and not body:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        else:
            # Simple email
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        return body[:1000]  # Truncate to first 1000 chars

    def mark_as_read(self, msg_id: str) -> bool:
        """
        Mark an email as read.

        Args:
            msg_id: Gmail message ID

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            if not self.authenticate():
                return False

        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            logger.debug(f"Marked email {msg_id} as read")
            return True

        except HttpError as error:
            logger.error(f"Error marking email as read: {error}")
            return False

    def add_label(self, msg_id: str, label: str) -> bool:
        """
        Add a label to an email.

        Args:
            msg_id: Gmail message ID
            label: Label to add (e.g., 'IMPORTANT', 'STARRED')

        Returns:
            True if successful, False otherwise
        """
        if not self.service:
            if not self.authenticate():
                return False

        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': [label]}
            ).execute()

            logger.debug(f"Added label {label} to email {msg_id}")
            return True

        except HttpError as error:
            logger.error(f"Error adding label: {error}")
            return False


# Singleton instance
gmail_client = GmailClient()
