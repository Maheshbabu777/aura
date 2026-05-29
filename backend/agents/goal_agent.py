"""
Goal Agent responsible for managing and decomposing long-term goals.
"""

import os
import json
import uuid
from datetime import datetime, timezone
from loguru import logger

from backend.models.cloud import gemini_client
from backend.goals.models import Goal, Milestone, WeeklyTask
from backend.goals.store import goal_store
from backend.memory.activity_stream import activity_stream


class GoalAgent:
    """Agent for creating and tracking goals."""

    def __init__(self):
        self.prompt_path = "./backend/prompts/goal_agent.txt"
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load system prompt from text file."""
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load GoalAgent prompt from {self.prompt_path}: {e}")
            return "You are a helpful AI assistant."

    def create_goal(self, title: str, description: str = "", context: str = "", deadline: str = None) -> Goal:
        """
        Takes a natural language goal and context, decomposes it using the LLM, and saves it.
        """
        logger.info(f"GoalAgent decomposing new goal: {title}")

        prompt_context = f"Goal Title: {title}\nDescription: {description}\nDeadline: {deadline or 'None'}\nContext/Syllabus: {context}"

        # We use Gemini (cloud) for this high-level reasoning task
        response_text = gemini_client.generate(
            system=self.system_prompt,
            prompt=prompt_context,
            temperature=0.3,
            max_tokens=4096,
            response_mime_type="application/json"
        )

        # Parse the JSON response
        try:
            # Clean up potential markdown formatting block if Gemini ignored the prompt
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
                
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM goal decomposition: {e}\nResponse: {response_text}")
            raise ValueError("Failed to generate goal roadmap. Please try again.")

        # Construct Pydantic models
        goal_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        
        milestones = []
        for m_data in data.get("milestones", []):
            m_id = str(uuid.uuid4())
            weekly_tasks = []
            
            for t_data in m_data.get("weekly_tasks", []):
                t_id = str(uuid.uuid4())
                task = WeeklyTask(
                    id=t_id,
                    milestone_id=m_id,
                    title=t_data.get("title", "Untitled Task"),
                    description=t_data.get("description", "")
                )
                weekly_tasks.append(task)
                
            milestone = Milestone(
                id=m_id,
                goal_id=goal_id,
                title=m_data.get("title", "Untitled Milestone"),
                description=m_data.get("description", ""),
                weekly_tasks=weekly_tasks
            )
            milestones.append(milestone)

        goal = Goal(
            id=goal_id,
            title=title,
            description=description,
            created_at=created_at,
            deadline=deadline,
            milestones=milestones
        )

        # Save to SQLite
        goal_store.save_goal(goal)
        logger.info(f"Successfully created and saved goal '{title}' with {len(milestones)} milestones.")
        
        # Log to Activity Stream
        activity_stream.log("GoalAgent", f"Created new goal: '{goal.title}' with {len(goal.milestones)} milestones.")
        
        return goal

    def get_goal(self, goal_id: str) -> Goal:
        """Retrieve a specific goal hierarchy."""
        return goal_store.get_goal(goal_id)

    def list_goals(self) -> list[Goal]:
        """List all goals."""
        return goal_store.list_goals()


# Singleton instance
goal_agent = GoalAgent()
