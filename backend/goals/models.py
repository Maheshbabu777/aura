"""
Pydantic models representing the hierarchical goal structure.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class DailyAction(BaseModel):
    id: str
    task_id: str
    title: str
    status: str = Field(default="pending", description="pending, in_progress, completed")
    created_at: str
    completed_at: Optional[str] = None


class WeeklyTask(BaseModel):
    id: str
    milestone_id: str
    title: str
    description: Optional[str] = None
    status: str = Field(default="pending", description="pending, in_progress, completed")
    due_date: Optional[str] = None
    daily_actions: List[DailyAction] = Field(default_factory=list)


class Milestone(BaseModel):
    id: str
    goal_id: str
    title: str
    description: Optional[str] = None
    status: str = Field(default="pending", description="pending, in_progress, completed")
    due_date: Optional[str] = None
    weekly_tasks: List[WeeklyTask] = Field(default_factory=list)


class Goal(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    context: Optional[str] = None
    status: str = Field(default="active", description="active, completed, paused, abandoned")
    progress_pct: int = Field(default=0, ge=0, le=100)
    created_at: str
    deadline: Optional[str] = None
    milestones: List[Milestone] = Field(default_factory=list)
