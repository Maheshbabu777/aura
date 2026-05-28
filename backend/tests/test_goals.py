"""
Tests for the Goal Tracking subsystem.
"""

import pytest
import sqlite3
import os
import tempfile
from unittest.mock import patch, MagicMock

from backend.goals.models import Goal
from backend.goals.store import GoalStore
from backend.agents.goal_agent import GoalAgent


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    yield path
    
    os.unlink(path)


@pytest.fixture
def test_goal_store(temp_db):
    """Provide GoalStore connected to test DB."""
    return GoalStore(db_path=temp_db)


@pytest.fixture
def test_goal_agent(test_goal_store):
    """Provide GoalAgent connected to test Store and mock Gemini."""
    agent = GoalAgent()
    # Patch the store
    with patch("backend.agents.goal_agent.goal_store", test_goal_store):
        yield agent


def test_goal_store_init(temp_db):
    """Test that GoalStore initializes DB schema correctly."""
    store = GoalStore(db_path=temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "goals" in tables
    assert "milestones" in tables
    assert "weekly_tasks" in tables
    assert "daily_actions" in tables
    
    conn.close()


@patch("backend.agents.goal_agent.gemini_client.generate")
def test_create_goal(mock_generate, test_goal_agent):
    """Test creating and decomposing a goal using the agent."""
    
    # Mock LLM JSON response
    mock_generate.return_value = '''
    {
      "milestones": [
        {
          "title": "Phase 1: Research",
          "description": "Gather info",
          "weekly_tasks": [
            {
              "title": "Read 5 papers",
              "description": "Foundational reading"
            }
          ]
        }
      ]
    }
    '''
    
    goal = test_goal_agent.create_goal(
        title="Learn Quantum Computing",
        deadline="2026-12-31"
    )
    
    # Verify Goal model
    assert goal.title == "Learn Quantum Computing"
    assert goal.deadline == "2026-12-31"
    assert len(goal.milestones) == 1
    
    milestone = goal.milestones[0]
    assert milestone.title == "Phase 1: Research"
    assert len(milestone.weekly_tasks) == 1
    
    task = milestone.weekly_tasks[0]
    assert task.title == "Read 5 papers"
    
    # Verify it was saved to DB
    saved_goal = test_goal_agent.get_goal(goal.id)
    assert saved_goal is not None
    assert saved_goal.title == "Learn Quantum Computing"
    assert len(saved_goal.milestones) == 1
    assert saved_goal.milestones[0].title == "Phase 1: Research"


def test_list_goals(test_goal_agent, test_goal_store):
    """Test listing all goals."""
    # Insert dummy goals
    from backend.goals.models import Goal
    from datetime import datetime, timezone
    
    g1 = Goal(id="1", title="Goal A", created_at=datetime.now(timezone.utc).isoformat())
    g2 = Goal(id="2", title="Goal B", created_at=datetime.now(timezone.utc).isoformat())
    
    test_goal_store.save_goal(g1)
    test_goal_store.save_goal(g2)
    
    goals = test_goal_agent.list_goals()
    assert len(goals) == 2
    titles = [g.title for g in goals]
    assert "Goal A" in titles
    assert "Goal B" in titles
