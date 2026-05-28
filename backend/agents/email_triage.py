"""
Email Triage Agent: Classifies and prioritizes emails.
"""

from typing import Dict, Any, List
from loguru import logger

from backend.integrations.gmail import gmail_client
from backend.models.cloud import gemini_client
from backend.agents.memory_agent import MemoryAgent


class EmailTriageAgent:
    """
    Triages emails by classification: urgent, normal, or ignore.
    Stores summaries in memory for context.
    """

    def __init__(self, memory_agent: MemoryAgent = None):
        self.memory_agent = memory_agent or MemoryAgent()
        self.gmail = gmail_client

    def classify_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify email as urgent, normal, or ignore using local model.

        Args:
            email: Email dict with subject, sender, snippet, body

        Returns:
            Classification dict with category, priority, reasoning, summary
        """
        prompt = f"""Classify this email as URGENT, NORMAL, or IGNORE.

Subject: {email['subject']}
From: {email['sender']}
Preview: {email['snippet']}

Provide your response in this format:
CATEGORY: <urgent/normal/ignore>
PRIORITY: <1-5, where 5 is highest>
REASONING: <why you classified it this way>
SUMMARY: <one-sentence summary of the email>

Guidelines:
- URGENT: Requires immediate attention (deadlines, time-sensitive requests, important meetings)
- NORMAL: Important but not time-sensitive (general work emails, updates, questions)
- IGNORE: Low-priority or spam (newsletters, promotions, automated notifications)
"""

        try:
            response = gemini_client.generate(
                prompt=prompt,
                temperature=0.3,  # Lower temp for consistent classification
                max_tokens=256
            )

            classification = self._parse_classification(response)
            classification['email_id'] = email['id']
            classification['subject'] = email['subject']
            classification['sender'] = email['sender']

            logger.info(
                f"Email classified: {email['subject'][:50]} -> {classification['category']} (priority: {classification['priority']})"
            )

            return classification

        except Exception as e:
            logger.error(f"Email classification failed: {e}")
            return {
                'email_id': email['id'],
                'subject': email['subject'],
                'sender': email['sender'],
                'category': 'normal',  # Default to normal on error
                'priority': 3,
                'reasoning': 'Classification error',
                'summary': email['snippet'][:100]
            }

    def _parse_classification(self, response: str) -> Dict[str, Any]:
        """Parse model response into structured classification."""
        import re

        result = {
            'category': 'normal',
            'priority': 3,
            'reasoning': '',
            'summary': ''
        }

        category_match = re.search(r'CATEGORY:\s*(.+)', response, re.IGNORECASE)
        priority_match = re.search(r'PRIORITY:\s*(\d+)', response, re.IGNORECASE)
        reasoning_match = re.search(r'REASONING:\s*(.+)', response, re.IGNORECASE)
        summary_match = re.search(r'SUMMARY:\s*(.+)', response, re.IGNORECASE)

        if category_match:
            result['category'] = category_match.group(1).strip().lower()
        if priority_match:
            result['priority'] = int(priority_match.group(1).strip())
        if reasoning_match:
            result['reasoning'] = reasoning_match.group(1).strip()
        if summary_match:
            result['summary'] = summary_match.group(1).strip()

        return result

    def triage_inbox(self, max_emails: int = 10, store_in_memory: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch and triage unread emails from inbox.

        Args:
            max_emails: Maximum number of emails to fetch
            store_in_memory: Whether to store email summaries in memory

        Returns:
            List of classified emails
        """
        logger.info(f"Starting email triage (max: {max_emails})")

        # Authenticate and fetch emails
        if not self.gmail.authenticate():
            logger.error("Gmail authentication failed")
            return []

        emails = self.gmail.fetch_unread_emails(max_results=max_emails)

        if not emails:
            logger.info("No unread emails to triage")
            return []

        # Classify each email
        classified_emails = []
        for email in emails:
            classification = self.classify_email(email)
            classified_emails.append(classification)

            # Store urgent emails in memory
            if store_in_memory and classification['category'] == 'urgent':
                self._store_in_memory(classification)

        # Summary statistics
        urgent_count = sum(1 for e in classified_emails if e['category'] == 'urgent')
        normal_count = sum(1 for e in classified_emails if e['category'] == 'normal')
        ignore_count = sum(1 for e in classified_emails if e['category'] == 'ignore')

        logger.info(
            f"Email triage complete: {urgent_count} urgent, {normal_count} normal, {ignore_count} ignore"
        )

        return classified_emails

    def _store_in_memory(self, classification: Dict[str, Any]) -> None:
        """Store urgent email summary in memory."""
        try:
            memory_text = f"Urgent email from {classification['sender']}: {classification['subject']} - {classification['summary']}"

            self.memory_agent.store.write_memory(
                memory_id=f"email_{classification['email_id']}",
                text=memory_text,
                entity_type="Fact",
                tags=["email", "urgent"],
                importance=2,  # Critical importance
                ttl_days=7  # Expire after 1 week
            )

            logger.debug(f"Stored urgent email in memory: {classification['subject'][:50]}")

        except Exception as e:
            logger.error(f"Failed to store email in memory: {e}")

    def get_urgent_emails(self) -> List[Dict[str, Any]]:
        """
        Get urgent emails from current triage.

        Returns:
            List of urgent email classifications
        """
        classified = self.triage_inbox(store_in_memory=False)
        return [e for e in classified if e['category'] == 'urgent']
