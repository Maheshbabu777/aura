"""
Rule-based email pre-filter for fast classification without LLM.

Handles obvious emails (newsletters, promotions, VIP senders) instantly
using pattern matching. Ambiguous emails return None and are passed to
the local LLM for classification.
"""

import re
from typing import Dict, Any, Optional, List, Set
from loguru import logger


# Sender patterns that indicate IGNORE emails
IGNORE_SENDER_PATTERNS = [
    r"noreply@",
    r"no-reply@",
    r"newsletter@",
    r"notifications?@",
    r"marketing@",
    r"promo(tions?)?@",
    r"digest@",
    r"updates?@",
    r"info@",
    r"mailer-daemon@",
    r"postmaster@",
    r"donotreply@",
    r"do-not-reply@",
    r"automated@",
    r"bounce@",
    r"feedback@.*\.noreply",
    r".*@substack\.com",
    r".*@medium\.com",
    r"news@",
]

# Subject patterns that indicate IGNORE emails
IGNORE_SUBJECT_PATTERNS = [
    r"\bunsubscribe\b",
    r"\bnewsletter\b",
    r"\bdigest\b",
    r"\bweekly roundup\b",
    r"\bdaily summary\b",
    r"\bpromotion(al)?\b",
    r"\bspecial offer\b",
    r"\bdiscount\b",
    r"\bcoupon\b",
    r"\bsale\b",
    r"\bfree trial\b",
    r"\bsponsored\b",
    r"\bad(vertisement)?\b",
    r"\bopt.?out\b",
    r"\bpreferences\b.*\bemail\b",
    r"\bnotification settings\b",
]

# Subject patterns that indicate URGENT emails
URGENT_SUBJECT_PATTERNS = [
    r"\burgent\b",
    r"\basap\b",
    r"\bdeadline\b",
    r"\bdue (today|tomorrow|tonight)\b",
    r"\baction required\b",
    r"\bimmediate(ly)?\b",
    r"\bcritical\b",
    r"\bemergency\b",
    r"\btime.?sensitive\b",
    r"\bmeeting (today|tomorrow|in \d+)\b",
    r"\binterview\b",
    r"\bfinal reminder\b",
    r"\blast chance\b",
    r"\bresponse needed\b",
    r"\breply needed\b",
    r"\bplease respond\b",
    r"\bexpir(es?|ing)\b",
]


class EmailFilter:
    """
    Rule-based email classifier for fast, privacy-preserving triage.

    Handles obvious emails instantly via pattern matching:
    - IGNORE: newsletters, promotions, automated notifications
    - URGENT: deadlines, VIP senders, time-sensitive keywords
    - None: ambiguous emails that need LLM classification
    """

    def __init__(self, vip_senders: Optional[List[str]] = None):
        """
        Args:
            vip_senders: List of sender patterns considered VIP/urgent
                         (e.g., ['boss@company.com', '@company.com'])
        """
        self.vip_senders: Set[str] = set(vip_senders or [])

        # Pre-compile regex patterns for performance
        self._ignore_sender_re = [
            re.compile(p, re.IGNORECASE) for p in IGNORE_SENDER_PATTERNS
        ]
        self._ignore_subject_re = [
            re.compile(p, re.IGNORECASE) for p in IGNORE_SUBJECT_PATTERNS
        ]
        self._urgent_subject_re = [
            re.compile(p, re.IGNORECASE) for p in URGENT_SUBJECT_PATTERNS
        ]

    def classify(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Attempt to classify an email using rules only.

        Args:
            email: Email dict with 'subject', 'sender', 'snippet'

        Returns:
            Classification dict if rules matched, None if ambiguous (needs LLM)
        """
        subject = email.get("subject", "")
        sender = email.get("sender", "")
        snippet = email.get("snippet", "")

        # Check VIP senders first (highest priority)
        vip_result = self._check_vip_senders(sender)
        if vip_result:
            logger.info(
                f"Rule engine: VIP sender match for '{subject[:50]}' -> URGENT"
            )
            return vip_result

        # Check URGENT subject patterns
        urgent_result = self._check_urgent_subject(subject)
        if urgent_result:
            logger.info(
                f"Rule engine: Urgent pattern match for '{subject[:50]}' -> URGENT"
            )
            return urgent_result

        # Check IGNORE sender patterns
        ignore_sender = self._check_ignore_sender(sender)
        if ignore_sender:
            logger.info(
                f"Rule engine: Ignore sender match for '{subject[:50]}' -> IGNORE"
            )
            return ignore_sender

        # Check IGNORE subject patterns
        ignore_subject = self._check_ignore_subject(subject)
        if ignore_subject:
            logger.info(
                f"Rule engine: Ignore subject match for '{subject[:50]}' -> IGNORE"
            )
            return ignore_subject

        # No rule matched -- email is ambiguous, needs LLM
        logger.debug(
            f"Rule engine: No match for '{subject[:50]}' -> passing to LLM"
        )
        return None

    def _check_vip_senders(self, sender: str) -> Optional[Dict[str, Any]]:
        """Check if sender matches VIP list."""
        sender_lower = sender.lower()
        for pattern in self.vip_senders:
            if pattern.lower() in sender_lower:
                return {
                    "category": "urgent",
                    "priority": 5,
                    "reasoning": f"VIP sender match: {pattern}",
                    "summary": "",
                    "classification_source": "rule_engine",
                }
        return None

    def _check_urgent_subject(self, subject: str) -> Optional[Dict[str, Any]]:
        """Check if subject contains urgent keywords."""
        for pattern in self._urgent_subject_re:
            if pattern.search(subject):
                return {
                    "category": "urgent",
                    "priority": 4,
                    "reasoning": f"Urgent keyword in subject: {pattern.pattern}",
                    "summary": "",
                    "classification_source": "rule_engine",
                }
        return None

    def _check_ignore_sender(self, sender: str) -> Optional[Dict[str, Any]]:
        """Check if sender matches ignore patterns."""
        for pattern in self._ignore_sender_re:
            if pattern.search(sender):
                return {
                    "category": "ignore",
                    "priority": 1,
                    "reasoning": f"Automated/marketing sender: {pattern.pattern}",
                    "summary": "",
                    "classification_source": "rule_engine",
                }
        return None

    def _check_ignore_subject(self, subject: str) -> Optional[Dict[str, Any]]:
        """Check if subject matches ignore patterns."""
        for pattern in self._ignore_subject_re:
            if pattern.search(subject):
                return {
                    "category": "ignore",
                    "priority": 1,
                    "reasoning": f"Low-priority keyword in subject: {pattern.pattern}",
                    "summary": "",
                    "classification_source": "rule_engine",
                }
        return None

    def add_vip_sender(self, sender_pattern: str) -> None:
        """Add a VIP sender pattern."""
        self.vip_senders.add(sender_pattern)
        logger.info(f"Added VIP sender: {sender_pattern}")

    def remove_vip_sender(self, sender_pattern: str) -> None:
        """Remove a VIP sender pattern."""
        self.vip_senders.discard(sender_pattern)
        logger.info(f"Removed VIP sender: {sender_pattern}")

    def get_vip_senders(self) -> List[str]:
        """Get current VIP sender list."""
        return sorted(self.vip_senders)
