"""
SQLite database wrapper for Goal Tracking.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

from backend.config.settings import settings
from backend.goals.models import Goal, Milestone, WeeklyTask, DailyAction


class GoalStore:
    """Manages persistent storage of Goal hierarchies."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.goal_db_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database schema."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Goals table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            context TEXT,
            status TEXT NOT NULL,
            progress_pct INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            deadline DATETIME
        )
        ''')

        # Milestones table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS milestones (
            id TEXT PRIMARY KEY,
            goal_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL,
            due_date DATETIME,
            FOREIGN KEY(goal_id) REFERENCES goals(id) ON DELETE CASCADE
        )
        ''')

        # WeeklyTasks table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS weekly_tasks (
            id TEXT PRIMARY KEY,
            milestone_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL,
            due_date DATETIME,
            FOREIGN KEY(milestone_id) REFERENCES milestones(id) ON DELETE CASCADE
        )
        ''')

        # DailyActions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_actions (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            completed_at DATETIME,
            FOREIGN KEY(task_id) REFERENCES weekly_tasks(id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        conn.close()

    def save_goal(self, goal: Goal) -> None:
        """Save a full Goal hierarchy to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert Goal
        cursor.execute('''
        INSERT OR REPLACE INTO goals (id, title, description, context, status, progress_pct, created_at, deadline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (goal.id, goal.title, goal.description, goal.context, goal.status, goal.progress_pct, goal.created_at, goal.deadline))

        for milestone in goal.milestones:
            # Insert Milestone
            cursor.execute('''
            INSERT OR REPLACE INTO milestones (id, goal_id, title, description, status, due_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (milestone.id, milestone.goal_id, milestone.title, milestone.description, milestone.status, milestone.due_date))

            for task in milestone.weekly_tasks:
                # Insert WeeklyTask
                cursor.execute('''
                INSERT OR REPLACE INTO weekly_tasks (id, milestone_id, title, description, status, due_date)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (task.id, task.milestone_id, task.title, task.description, task.status, task.due_date))

                for action in task.daily_actions:
                    # Insert DailyAction
                    cursor.execute('''
                    INSERT OR REPLACE INTO daily_actions (id, task_id, title, status, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (action.id, action.task_id, action.title, action.status, action.created_at, action.completed_at))

        conn.commit()
        conn.close()

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Retrieve a full Goal hierarchy by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM goals WHERE id = ?', (goal_id,))
        goal_row = cursor.fetchone()

        if not goal_row:
            conn.close()
            return None

        goal_dict = dict(goal_row)
        goal_dict["milestones"] = []

        # Fetch Milestones
        cursor.execute('SELECT * FROM milestones WHERE goal_id = ?', (goal_id,))
        for m_row in cursor.fetchall():
            m_dict = dict(m_row)
            m_dict["weekly_tasks"] = []
            
            # Fetch WeeklyTasks
            cursor.execute('SELECT * FROM weekly_tasks WHERE milestone_id = ?', (m_dict["id"],))
            for t_row in cursor.fetchall():
                t_dict = dict(t_row)
                t_dict["daily_actions"] = []
                
                # Fetch DailyActions
                cursor.execute('SELECT * FROM daily_actions WHERE task_id = ?', (t_dict["id"],))
                for a_row in cursor.fetchall():
                    t_dict["daily_actions"].append(dict(a_row))
                    
                m_dict["weekly_tasks"].append(t_dict)
                
            goal_dict["milestones"].append(m_dict)

        conn.close()
        return Goal(**goal_dict)

    def list_goals(self) -> List[Goal]:
        """List all goals without fetching their full hierarchies (for overview)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM goals ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()

        # Returns goals with empty milestones lists
        return [Goal(**dict(row)) for row in rows]

# Singleton instance
goal_store = GoalStore()
