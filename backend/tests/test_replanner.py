"""
Tests for the Adaptive Replanner.
"""

import pytest
import sqlite3
import os
import tempfile
from unittest.mock import patch

from backend.goals.models import Goal, Milestone, WeeklyTask
from backend.goals.store import GoalStore
from backend.goals.replanner import AdaptiveReplanner


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def store(temp_db):
    return GoalStore(db_path=temp_db)


@pytest.fixture
def replanner_agent():
    return AdaptiveReplanner()


@patch("backend.goals.replanner.settings")
@patch("backend.goals.replanner.gemini_client.generate")
@patch("backend.goals.replanner.goal_store")
def test_adaptive_replan(mock_goal_store, mock_generate, mock_settings, temp_db, replanner_agent):
    mock_settings.goal_db_path = temp_db
    
    # Setup mock Goal
    goal = Goal(
        id="goal-1",
        title="Pass Finals",
        context="Chapter 1, 2, 3",
        created_at="2026-05-28",
        milestones=[
            Milestone(
                id="m-1",
                goal_id="goal-1",
                title="Study Phase",
                weekly_tasks=[
                    WeeklyTask(id="t-1", milestone_id="m-1", title="Chap 1", status="pending"),
                    WeeklyTask(id="t-2", milestone_id="m-1", title="Chap 2", status="completed")
                ]
            )
        ]
    )
    
    # Store returns our mock goal
    mock_goal_store.get_goal.return_value = goal
    
    # Setup test DB with the goal schema to avoid sqlite errors during delete/insert
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE goals (id TEXT PRIMARY KEY, title TEXT, description TEXT, context TEXT, status TEXT, progress_pct INTEGER, created_at DATETIME, deadline DATETIME)')
    cursor.execute('CREATE TABLE milestones (id TEXT PRIMARY KEY, goal_id TEXT, title TEXT, description TEXT, status TEXT, due_date DATETIME)')
    cursor.execute('CREATE TABLE weekly_tasks (id TEXT PRIMARY KEY, milestone_id TEXT, title TEXT, description TEXT, status TEXT, due_date DATETIME)')
    
    cursor.execute("INSERT INTO milestones (id, goal_id, title, status) VALUES ('m-1', 'goal-1', 'Study Phase', 'pending')")
    cursor.execute("INSERT INTO weekly_tasks (id, milestone_id, title, status) VALUES ('t-1', 'm-1', 'Chap 1', 'pending')")
    conn.commit()
    conn.close()
    
    # Mock LLM Response condensing Chap 1 and 3
    mock_generate.return_value = '''
    {
      "new_weekly_tasks": [
        {
          "milestone_id": "m-1",
          "title": "Condensed Chap 1 & 3 Review",
          "description": "Read both rapidly",
          "due_date": "2026-06-01"
        }
      ]
    }
    '''
    
    updated_goal = replanner_agent.adaptive_replan("goal-1")
    
    # The actual updated_goal comes from mock_goal_store.get_goal (which we mocked to return the original goal)
    # So to verify DB updates, we need to query the test DB directly
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM weekly_tasks WHERE status='pending'")
    tasks = cursor.fetchall()
    conn.close()
    
    # The replanner should have deleted the old pending task ('Chap 1') 
    # and inserted the new one ('Condensed Chap 1 & 3 Review')
    assert len(tasks) == 1
    assert tasks[0][0] == "Condensed Chap 1 & 3 Review"
