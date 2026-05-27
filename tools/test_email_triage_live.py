"""
Test Email Triage Agent with real Gmail emails.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agents.email_triage import EmailTriageAgent
from loguru import logger

logger.add("email_triage_test.log", rotation="1 MB")


def test_email_triage():
    """Test email triage with real Gmail account."""
    print("=" * 60)
    print("AURA Email Triage Test")
    print("=" * 60)
    print()

    # Initialize triage agent
    print("1. Initializing Email Triage Agent...")
    triage = EmailTriageAgent()
    print()

    # Triage inbox
    print("2. Triaging inbox (max 5 emails)...")
    print("   This will:")
    print("   - Fetch unread emails")
    print("   - Classify each as URGENT/NORMAL/IGNORE")
    print("   - Assign priority (1-5)")
    print("   - Store urgent emails in memory")
    print()

    try:
        classifications = triage.triage_inbox(max_emails=5, store_in_memory=False)

        if not classifications:
            print("   No emails to triage")
            return True

        print(f"   Classified {len(classifications)} emails:")
        print()

        for i, c in enumerate(classifications, 1):
            # Handle Unicode for Windows console
            subject = c['subject'].encode('ascii', 'ignore').decode('ascii')
            sender = c['sender'].encode('ascii', 'ignore').decode('ascii')
            reasoning = c['reasoning'].encode('ascii', 'ignore').decode('ascii')

            print(f"   Email {i}: {c['category'].upper()} (Priority: {c['priority']})")
            print(f"      Subject: {subject}")
            print(f"      From: {sender}")
            print(f"      Reasoning: {reasoning}")
            print()

        # Summary
        urgent = sum(1 for c in classifications if c['category'] == 'urgent')
        normal = sum(1 for c in classifications if c['category'] == 'normal')
        ignore = sum(1 for c in classifications if c['category'] == 'ignore')

        print("=" * 60)
        print(f"Summary: {urgent} urgent, {normal} normal, {ignore} ignore")
        print("[OK] Email triage test PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"[FAIL] Error during test: {e}")
        logger.exception("Email triage test failed")
        return False


if __name__ == "__main__":
    success = test_email_triage()
    sys.exit(0 if success else 1)
