"""
Approval Queue for pausing and reviewing YELLOW actions.
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from backend.guardrails.audit_log import audit_log


class ApprovalQueue:
    """Manages actions that require user review before execution."""

    def enqueue_action(self, action_name: str, payload: Dict[str, Any], reasoning: str) -> str:
        """
        Add a YELLOW action to the queue for review.
        
        Args:
            action_name: The name of the action
            payload: The arguments for the action
            reasoning: Why the action was paused
            
        Returns:
            The ID of the queued action
        """
        logger.info(f"Enqueueing YELLOW action '{action_name}' for approval.")
        return audit_log.log_action(
            action_name=action_name,
            category="YELLOW",
            reasoning=reasoning,
            payload=payload,
            status="pending"
        )

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Retrieve all actions currently waiting for approval."""
        return audit_log.get_actions_by_status("pending")

    def approve_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Approve an action in the queue.
        
        Args:
            action_id: ID of the action to approve
            
        Returns:
            The action dictionary (so it can be executed), or None if not found
        """
        action = audit_log.get_action(action_id)
        if not action:
            logger.error(f"Cannot approve: Action {action_id} not found.")
            return None
            
        if action['status'] != 'pending':
            logger.warning(f"Cannot approve: Action {action_id} is already {action['status']}.")
            return None
            
        success = audit_log.update_status(action_id, "approved")
        if success:
            logger.info(f"Approved action {action_id} ({action['action_name']}).")
            action['status'] = 'approved'
            return action
        return None

    def reject_action(self, action_id: str) -> bool:
        """
        Reject an action in the queue.
        
        Args:
            action_id: ID of the action to reject
            
        Returns:
            True if successful, False otherwise
        """
        action = audit_log.get_action(action_id)
        if not action:
            logger.error(f"Cannot reject: Action {action_id} not found.")
            return False
            
        if action['status'] != 'pending':
            logger.warning(f"Cannot reject: Action {action_id} is already {action['status']}.")
            return False
            
        success = audit_log.update_status(action_id, "rejected")
        if success:
            logger.info(f"Rejected action {action_id} ({action['action_name']}).")
            return True
        return False

# Singleton instance
approval_queue = ApprovalQueue()
