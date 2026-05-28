from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from backend.guardrails.approval_queue import approval_queue
from backend.guardrails.audit_log import audit_log

router = APIRouter(prefix="/api/actions", tags=["Actions"])


class ActionResponse(BaseModel):
    success: bool
    message: str
    action: Dict[str, Any] = {}


@router.get("/pending")
async def get_pending_actions():
    """List all actions currently waiting for user approval."""
    try:
        actions = approval_queue.get_pending_actions()
        return {"actions": actions, "count": len(actions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/approve", response_model=ActionResponse)
async def approve_action(action_id: str):
    """
    Approve a pending action.
    NOTE: In the future, this endpoint will also trigger the execution of the action.
    For now, it just marks it as 'approved' in the database.
    """
    try:
        action = approval_queue.approve_action(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="Action not found or not pending")
            
        return ActionResponse(
            success=True,
            message="Action approved successfully",
            action=action
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/reject", response_model=ActionResponse)
async def reject_action(action_id: str):
    """Reject a pending action."""
    try:
        success = approval_queue.reject_action(action_id)
        if not success:
            raise HTTPException(status_code=404, detail="Action not found or not pending")
            
        return ActionResponse(
            success=True,
            message="Action rejected successfully",
            action={"id": action_id, "status": "rejected"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_action_history(limit: int = 50, offset: int = 0):
    """Get paginated history of all actions."""
    try:
        history = audit_log.get_action_history(limit=limit, offset=offset)
        return {"history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
