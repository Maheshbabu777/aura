"""
Tests for guardrails classification rules.
"""

import pytest

from backend.guardrails.rules import (
    ActionCategory,
    classify_action,
    get_reasoning,
    is_action_allowed,
    requires_approval,
    is_action_blocked,
    get_all_green_actions,
    get_all_yellow_actions,
    get_all_red_actions,
)


def test_classify_green_action():
    """Test classifying safe auto-execute actions."""
    assert classify_action("read_email") == ActionCategory.GREEN
    assert classify_action("search_memory") == ActionCategory.GREEN
    assert classify_action("web_search") == ActionCategory.GREEN


def test_classify_yellow_action():
    """Test classifying actions requiring approval."""
    assert classify_action("draft_reply") == ActionCategory.YELLOW
    assert classify_action("create_event") == ActionCategory.YELLOW
    assert classify_action("delete_memory") == ActionCategory.YELLOW


def test_classify_red_action():
    """Test classifying blocked actions."""
    assert classify_action("send_email") == ActionCategory.RED
    assert classify_action("delete_email") == ActionCategory.RED
    assert classify_action("delete_event") == ActionCategory.RED


def test_classify_unknown_action():
    """Test that unknown actions default to YELLOW (require approval)."""
    assert classify_action("unknown_action") == ActionCategory.YELLOW
    assert classify_action("random_command") == ActionCategory.YELLOW


def test_get_reasoning_known_action():
    """Test getting reasoning for known actions."""
    reasoning = get_reasoning("send_email")
    assert "without approval" in reasoning.lower()
    assert "harm" in reasoning.lower()


def test_get_reasoning_unknown_action():
    """Test getting reasoning for unknown actions."""
    reasoning = get_reasoning("unknown_action")
    assert "unknown" in reasoning.lower()
    assert "review" in reasoning.lower()


def test_is_action_allowed():
    """Test checking if action is auto-executable."""
    assert is_action_allowed("read_email") == True
    assert is_action_allowed("draft_reply") == False
    assert is_action_allowed("send_email") == False


def test_requires_approval():
    """Test checking if action requires approval."""
    assert requires_approval("draft_reply") == True
    assert requires_approval("create_event") == True
    assert requires_approval("read_email") == False
    assert requires_approval("send_email") == False


def test_is_action_blocked():
    """Test checking if action is blocked."""
    assert is_action_blocked("send_email") == True
    assert is_action_blocked("delete_email") == True
    assert is_action_blocked("read_email") == False
    assert is_action_blocked("draft_reply") == False


def test_get_all_green_actions():
    """Test getting all GREEN actions."""
    green_actions = get_all_green_actions()

    assert len(green_actions) > 0
    assert "read_email" in green_actions
    assert "search_memory" in green_actions
    assert "send_email" not in green_actions


def test_get_all_yellow_actions():
    """Test getting all YELLOW actions."""
    yellow_actions = get_all_yellow_actions()

    assert len(yellow_actions) > 0
    assert "draft_reply" in yellow_actions
    assert "create_event" in yellow_actions
    assert "read_email" not in yellow_actions


def test_get_all_red_actions():
    """Test getting all RED actions."""
    red_actions = get_all_red_actions()

    assert len(red_actions) > 0
    assert "send_email" in red_actions
    assert "delete_email" in red_actions
    assert "read_email" not in red_actions


def test_email_actions_classification():
    """Test all email-related actions are classified correctly."""
    assert classify_action("read_email") == ActionCategory.GREEN
    assert classify_action("summarize_email") == ActionCategory.GREEN
    assert classify_action("mark_as_read") == ActionCategory.GREEN
    assert classify_action("add_label") == ActionCategory.GREEN
    assert classify_action("draft_reply") == ActionCategory.YELLOW
    assert classify_action("send_email") == ActionCategory.RED
    assert classify_action("delete_email") == ActionCategory.RED


def test_calendar_actions_classification():
    """Test all calendar-related actions are classified correctly."""
    assert classify_action("read_calendar") == ActionCategory.GREEN
    assert classify_action("create_event") == ActionCategory.YELLOW
    assert classify_action("update_event") == ActionCategory.YELLOW
    assert classify_action("delete_event") == ActionCategory.RED


def test_memory_actions_classification():
    """Test all memory-related actions are classified correctly."""
    assert classify_action("store_memory") == ActionCategory.GREEN
    assert classify_action("search_memory") == ActionCategory.GREEN
    assert classify_action("update_memory") == ActionCategory.GREEN
    assert classify_action("delete_memory") == ActionCategory.YELLOW


def test_action_category_values():
    """Test ActionCategory enum values."""
    assert ActionCategory.GREEN.value == "green"
    assert ActionCategory.YELLOW.value == "yellow"
    assert ActionCategory.RED.value == "red"
