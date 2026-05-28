"""
Tests for the Guardrails Approval Queue and Audit Log.
"""

import pytest
import sqlite3
import os
import tempfile
from unittest.mock import patch

from backend.guardrails.audit_log import AuditLog
from backend.guardrails.approval_queue import ApprovalQueue


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    yield path
    
    os.unlink(path)


@pytest.fixture
def test_audit_log(temp_db):
    """Provide AuditLog connected to test DB."""
    return AuditLog(db_path=temp_db)


@pytest.fixture
def test_approval_queue(test_audit_log):
    """Provide ApprovalQueue connected to test AuditLog."""
    queue = ApprovalQueue()
    # Patch the global audit_log instance imported in approval_queue
    with patch("backend.guardrails.approval_queue.audit_log", test_audit_log):
        yield queue


def test_audit_log_init(temp_db):
    """Test that AuditLog initializes DB schema correctly."""
    log = AuditLog(db_path=temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='actions'")
    assert cursor.fetchone() is not None
    conn.close()


def test_enqueue_action(test_approval_queue):
    """Test enqueueing a YELLOW action."""
    action_id = test_approval_queue.enqueue_action(
        action_name="send_email",
        payload={"to": "boss@example.com"},
        reasoning="Sending email requires approval"
    )
    
    assert action_id is not None
    
    pending = test_approval_queue.get_pending_actions()
    assert len(pending) == 1
    assert pending[0]['id'] == action_id
    assert pending[0]['action_name'] == "send_email"
    assert pending[0]['category'] == "YELLOW"
    assert pending[0]['status'] == "pending"
    assert pending[0]['payload']['to'] == "boss@example.com"


def test_approve_action(test_approval_queue):
    """Test approving a pending action."""
    action_id = test_approval_queue.enqueue_action(
        action_name="create_event",
        payload={"title": "Meeting"},
        reasoning="Modifying schedule"
    )
    
    # Approve it
    approved_action = test_approval_queue.approve_action(action_id)
    
    assert approved_action is not None
    assert approved_action['status'] == 'approved'
    
    # Should no longer be pending
    pending = test_approval_queue.get_pending_actions()
    assert len(pending) == 0


def test_reject_action(test_approval_queue):
    """Test rejecting a pending action."""
    action_id = test_approval_queue.enqueue_action(
        action_name="delete_event",
        payload={"event_id": "123"},
        reasoning="Destructive action"
    )
    
    # Reject it
    success = test_approval_queue.reject_action(action_id)
    assert success is True
    
    # Should no longer be pending
    pending = test_approval_queue.get_pending_actions()
    assert len(pending) == 0


def test_cannot_approve_non_pending(test_approval_queue):
    """Test approving an action that is already approved."""
    action_id = test_approval_queue.enqueue_action(
        action_name="test",
        payload={},
        reasoning="test"
    )
    
    test_approval_queue.approve_action(action_id)
    
    # Second approval should fail (return None)
    result = test_approval_queue.approve_action(action_id)
    assert result is None
