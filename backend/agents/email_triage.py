"""
Email Triage Agent: Two-stage privacy-first email classification.

Stage 1: Rule-based pre-filter (instant, no model, handles ~60-70% of emails)
Stage 2: Local LLM via Ollama (gemma3:1b, ~1-2s per email, 100% private)

Cloud Gemini is available as an opt-in fallback via settings.
"""

from typing import Dict, Any, List
from loguru import logger

from backend.integrations.gmail import gmail_client
from backend.agents.email_filter import EmailFilter
from backend.agents.memory_agent import MemoryAgent
from backend.models.local import ollama_client
from backend.config.settings import settings


class EmailTriageAgent:
    """
    Triages emails by classification: urgent, normal, or ignore.

    Uses a two-stage pipeline:
    1. Rule engine: pattern matching for obvious emails (instant)
    2. Local LLM: lightweight model for ambiguous emails (1-2s each)

    Stores summaries of urgent emails in memory for context.
    """

    def __init__(self, memory_agent: MemoryAgent = None, vip_senders: List[str] = None):
        self.memory_agent = memory_agent or MemoryAgent()
        self.gmail = gmail_client
        self.email_filter = EmailFilter(vip_senders=vip_senders)
        self.triage_model = settings.email_triage_model
        self.use_cloud = settings.email_triage_use_cloud

    def classify_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify email using two-stage pipeline.

        Stage 1: Try rule-based filter (instant, no model)
        Stage 2: Fall back to local LLM for ambiguous emails

        Args:
            email: Email dict with subject, sender, snippet, body

        Returns:
            Classification dict with category, priority, reasoning, summary,
            classification_source
        """
        # Stage 1: Rule-based pre-filter
        rule_result = self.email_filter.classify(email)
        if rule_result is not None:
            # Fill in summary from snippet since rules don't generate summaries
            rule_result['summary'] = rule_result['summary'] or email.get('snippet', '')[:100]
            rule_result['email_id'] = email['id']
            rule_result['subject'] = email['subject']
            rule_result['sender'] = email['sender']

            logger.info(
                f"Email classified (rule engine): {email['subject'][:50]} "
                f"-> {rule_result['category']} (priority: {rule_result['priority']})"
            )
            return rule_result

        # Stage 2: LLM classification for ambiguous emails
        return self._classify_with_llm(email)

    def _classify_with_llm(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify ambiguous email using LLM (local by default, cloud if configured).

        Args:
            email: Email dict with subject, sender, snippet

        Returns:
            Classification dict
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
            if self.use_cloud:
                # Cloud fallback (opt-in, not default)
                from backend.models.cloud import gemini_client
                response = gemini_client.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=256
                )
                source = "cloud_llm"
            else:
                # Local LLM with lightweight model (default, privacy-preserving)
                response = ollama_client.generate(
                    prompt=prompt,
                    temperature=0.3,
                    max_tokens=256,
                    model_override=self.triage_model,
                )
                source = "local_llm"

            classification = self._parse_classification(response)
            classification['classification_source'] = source
            classification['email_id'] = email['id']
            classification['subject'] = email['subject']
            classification['sender'] = email['sender']

            logger.info(
                f"Email classified ({source}): {email['subject'][:50]} "
                f"-> {classification['category']} (priority: {classification['priority']})"
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
                'summary': email['snippet'][:100],
                'classification_source': 'fallback',
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

        # Classify each email through the two-stage pipeline
        classified_emails = []
        rule_count = 0
        llm_count = 0

        for email in emails:
            classification = self.classify_email(email)
            classified_emails.append(classification)

            # Track classification source for logging
            if classification.get('classification_source') == 'rule_engine':
                rule_count += 1
            else:
                llm_count += 1

            # Store urgent emails in memory
            if store_in_memory and classification['category'] == 'urgent':
                self._store_in_memory(classification)

        # Summary statistics
        urgent_count = sum(1 for e in classified_emails if e['category'] == 'urgent')
        normal_count = sum(1 for e in classified_emails if e['category'] == 'normal')
        ignore_count = sum(1 for e in classified_emails if e['category'] == 'ignore')

        logger.info(
            f"Email triage complete: {urgent_count} urgent, {normal_count} normal, "
            f"{ignore_count} ignore | Sources: {rule_count} rule engine, {llm_count} LLM"
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
