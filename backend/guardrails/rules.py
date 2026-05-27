"""
Action classification rules for guardrails system.

Actions are classified as:
- GREEN: Safe to execute automatically
- YELLOW: Requires user approval before execution
- RED: Blocked, never execute
"""

from enum import Enum
from typing import Dict, List


class ActionCategory(Enum):
    """Action safety categories."""
    GREEN = "green"   # Auto-execute
    YELLOW = "yellow"  # Requires approval
    RED = "red"        # Blocked


# Action classification rules
CLASSIFICATION_RULES: Dict[str, Dict[str, any]] = {
    # Email actions
    "read_email": {
        "category": ActionCategory.GREEN,
        "reasoning": "Reading emails is read-only and safe"
    },
    "summarize_email": {
        "category": ActionCategory.GREEN,
        "reasoning": "Summarizing is read-only analysis"
    },
    "draft_reply": {
        "category": ActionCategory.YELLOW,
        "reasoning": "Draft requires review before sending"
    },
    "send_email": {
        "category": ActionCategory.RED,
        "reasoning": "Sending emails without approval could cause harm"
    },
    "delete_email": {
        "category": ActionCategory.RED,
        "reasoning": "Deleting emails is irreversible"
    },
    "mark_as_read": {
        "category": ActionCategory.GREEN,
        "reasoning": "Marking as read is reversible and low-risk"
    },
    "add_label": {
        "category": ActionCategory.GREEN,
        "reasoning": "Adding labels is reversible"
    },

    # Calendar actions
    "read_calendar": {
        "category": ActionCategory.GREEN,
        "reasoning": "Reading calendar is read-only"
    },
    "create_event": {
        "category": ActionCategory.YELLOW,
        "reasoning": "Creating events affects schedule, needs approval"
    },
    "update_event": {
        "category": ActionCategory.YELLOW,
        "reasoning": "Updating events could conflict with plans"
    },
    "delete_event": {
        "category": ActionCategory.RED,
        "reasoning": "Deleting events could miss important meetings"
    },

    # Memory actions
    "store_memory": {
        "category": ActionCategory.GREEN,
        "reasoning": "Storing information is safe"
    },
    "search_memory": {
        "category": ActionCategory.GREEN,
        "reasoning": "Searching is read-only"
    },
    "update_memory": {
        "category": ActionCategory.GREEN,
        "reasoning": "Updating memory is low-risk"
    },
    "delete_memory": {
        "category": ActionCategory.YELLOW,
        "reasoning": "Deleting memory should be reviewed"
    },

    # Web search
    "web_search": {
        "category": ActionCategory.GREEN,
        "reasoning": "Web search is read-only"
    },

    # System actions
    "generate_brief": {
        "category": ActionCategory.GREEN,
        "reasoning": "Generating summaries is safe"
    },
    "track_goal": {
        "category": ActionCategory.GREEN,
        "reasoning": "Goal tracking is internal state"
    },
}


def classify_action(action: str) -> ActionCategory:
    """
    Classify an action into GREEN/YELLOW/RED category.

    Args:
        action: Action name to classify

    Returns:
        ActionCategory enum value
    """
    rule = CLASSIFICATION_RULES.get(action)

    if rule:
        return rule["category"]

    # Default to YELLOW for unknown actions (require approval)
    return ActionCategory.YELLOW


def get_reasoning(action: str) -> str:
    """
    Get reasoning for action classification.

    Args:
        action: Action name

    Returns:
        Reasoning string
    """
    rule = CLASSIFICATION_RULES.get(action)

    if rule:
        return rule["reasoning"]

    return "Unknown action, requires manual review for safety"


def is_action_allowed(action: str) -> bool:
    """
    Check if action is allowed to auto-execute (GREEN).

    Args:
        action: Action name

    Returns:
        True if GREEN, False otherwise
    """
    return classify_action(action) == ActionCategory.GREEN


def requires_approval(action: str) -> bool:
    """
    Check if action requires user approval (YELLOW).

    Args:
        action: Action name

    Returns:
        True if YELLOW, False otherwise
    """
    return classify_action(action) == ActionCategory.YELLOW


def is_action_blocked(action: str) -> bool:
    """
    Check if action is blocked (RED).

    Args:
        action: Action name

    Returns:
        True if RED, False otherwise
    """
    return classify_action(action) == ActionCategory.RED


def get_all_green_actions() -> List[str]:
    """Get list of all GREEN (auto-execute) actions."""
    return [
        action for action, rule in CLASSIFICATION_RULES.items()
        if rule["category"] == ActionCategory.GREEN
    ]


def get_all_yellow_actions() -> List[str]:
    """Get list of all YELLOW (requires approval) actions."""
    return [
        action for action, rule in CLASSIFICATION_RULES.items()
        if rule["category"] == ActionCategory.YELLOW
    ]


def get_all_red_actions() -> List[str]:
    """Get list of all RED (blocked) actions."""
    return [
        action for action, rule in CLASSIFICATION_RULES.items()
        if rule["category"] == ActionCategory.RED
    ]
