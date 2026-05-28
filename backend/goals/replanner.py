"""
Adaptive Replanner for adjusting goal roadmaps when the user falls behind.
"""

import json
import uuid
import sqlite3
from datetime import datetime, timezone
from loguru import logger

from backend.config.settings import settings
from backend.models.cloud import gemini_client
from backend.goals.models import Goal, WeeklyTask
from backend.goals.store import goal_store


class AdaptiveReplanner:
    """Analyzes progress and uses LLM to dynamically shift uncompleted tasks."""

    def __init__(self):
        self.prompt_path = "./backend/prompts/replanner.txt"
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load Replanner prompt from {self.prompt_path}: {e}")
            return "You are a helpful AI replanner."

    def adaptive_replan(self, goal_id: str) -> Goal:
        """
        Triggers a recalculation of all pending tasks for a given goal.
        """
        logger.info(f"Triggering adaptive replan for goal {goal_id}")
        
        goal = goal_store.get_goal(goal_id)
        if not goal:
            raise ValueError(f"Goal {goal_id} not found.")

        # 1. Gather context and current state
        completed_tasks = []
        pending_tasks = []
        milestone_ids = []

        for milestone in goal.milestones:
            milestone_ids.append(f"ID: {milestone.id} | Title: {milestone.title}")
            for task in milestone.weekly_tasks:
                if task.status == "completed":
                    completed_tasks.append(f"- {task.title}: {task.description}")
                else:
                    pending_tasks.append(f"- ID: {task.id} | Title: {task.title} | Desc: {task.description}")

        if not pending_tasks:
            logger.info("No pending tasks to replan.")
            return goal

        # 2. Build the LLM Prompt
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        context_prompt = (
            f"Today's Date: {today}\n"
            f"Goal: {goal.title}\n"
            f"Deadline: {goal.deadline or 'None'}\n"
            f"Syllabus/Context: {goal.context or 'None'}\n\n"
            f"AVAILABLE MILESTONES:\n" + "\n".join(milestone_ids) + "\n\n"
            f"COMPLETED TASKS:\n" + ("\n".join(completed_tasks) if completed_tasks else "None") + "\n\n"
            f"PENDING/OVERDUE TASKS TO REPLAN:\n" + "\n".join(pending_tasks)
        )

        # 3. Call Cloud Gemini
        response_text = gemini_client.generate(
            system=self.system_prompt,
            prompt=context_prompt,
            temperature=0.3,
            max_tokens=4096,
            response_mime_type="application/json"
        )

        try:
            # Clean up markdown
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
                
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse replanner JSON: {e}\nResponse: {response_text}")
            raise ValueError("Failed to replan goal. LLM output invalid JSON.")

        # 4. Overwrite old pending tasks in database
        # Delete old pending tasks from SQLite
        conn = sqlite3.connect(settings.goal_db_path)
        cursor = conn.cursor()
        
        # We delete all pending tasks for this goal (join via milestone)
        cursor.execute('''
            DELETE FROM weekly_tasks 
            WHERE status != 'completed' 
            AND milestone_id IN (SELECT id FROM milestones WHERE goal_id = ?)
        ''', (goal.id,))
        
        # Insert the new rescheduled tasks
        for t_data in data.get("new_weekly_tasks", []):
            t_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO weekly_tasks (id, milestone_id, title, description, status, due_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                t_id, 
                t_data.get("milestone_id"), 
                t_data.get("title"), 
                t_data.get("description"), 
                "pending", 
                t_data.get("due_date")
            ))
            
        conn.commit()
        conn.close()

        logger.info(f"Successfully replanned goal {goal.id}")
        
        # Fetch the fresh goal state from DB
        return goal_store.get_goal(goal.id)


# Singleton instance
replanner = AdaptiveReplanner()
