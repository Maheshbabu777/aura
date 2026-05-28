from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.agents.goal_agent import goal_agent
from backend.goals.models import Goal

router = APIRouter(prefix="/api/goals", tags=["Goals"])


class GoalRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    deadline: Optional[str] = None


@router.post("/", response_model=Goal)
async def create_goal(request: GoalRequest):
    """
    Create a new goal.
    This will use the LLM to automatically decompose the goal into milestones and tasks.
    """
    try:
        goal = goal_agent.create_goal(
            title=request.title,
            description=request.description,
            deadline=request.deadline
        )
        return goal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Goal])
async def list_goals():
    """List all goals (without full hierarchical details)."""
    try:
        return goal_agent.list_goals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{goal_id}", response_model=Goal)
async def get_goal(goal_id: str):
    """Get a specific goal with its full hierarchy of milestones and tasks."""
    try:
        goal = goal_agent.get_goal(goal_id)
        if not goal:
            raise HTTPException(status_code=404, detail="Goal not found")
        return goal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
