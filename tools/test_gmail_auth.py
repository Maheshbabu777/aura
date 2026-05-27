"""
Test Gmail authentication and basic email fetching.
Run this to verify OAuth flow works with your test Gmail account.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.integrations.gmail import GmailClient
from loguru import logger

logger.add("gmail_test.log", rotation="1 MB")


def test_gmail_connection():
    """Test Gmail OAuth and basic email fetching."""
    print("=" * 60)
    print("AURA Gmail Integration Test")
    print("=" * 60)
    print()

    # Initialize client
    print("1. Initializing Gmail client...")
    gmail = GmailClient()

    print(f"   Credentials: {gmail.credentials_path}")
    print(f"   Token will be saved to: {gmail.token_path}")
    print()

    # Authenticate
    print("2. Authenticating with Gmail...")
    print("   -> Browser will open for OAuth flow")
    print("   -> Use your SECONDARY Gmail account (not main)")
    print()

    try:
        success = gmail.authenticate()

        if not success:
            print("[FAIL] Authentication failed!")
            return False

        print("[OK] Authentication successful!")
        print()

        # Fetch unread emails
        print("3. Fetching unread emails (max 5)...")
        emails = gmail.fetch_unread_emails(max_results=5)

        if not emails:
            print("   No unread emails found (inbox is clean!)")
        else:
            print(f"   Found {len(emails)} unread email(s):")
            print()
            for i, email in enumerate(emails, 1):
                print(f"   Email {i}:")
                # Encode with error handling for Windows console
                subject = email['subject'].encode('ascii', 'ignore').decode('ascii')
                sender = email['sender'].encode('ascii', 'ignore').decode('ascii')
                snippet = email['snippet'][:80].encode('ascii', 'ignore').decode('ascii')
                print(f"      Subject: {subject}")
                print(f"      From: {sender}")
                print(f"      Date: {email['date']}")
                print(f"      Preview: {snippet}...")
                print()

        print("=" * 60)
        print("[OK] Gmail integration test PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"[FAIL] Error during test: {e}")
        logger.exception("Gmail test failed")
        return False


if __name__ == "__main__":
    success = test_gmail_connection()
    sys.exit(0 if success else 1)
