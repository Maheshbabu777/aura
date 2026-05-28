"""
Morning Brief generator. Integrates Calendar, Email, and Goals into a daily summary.
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from loguru import logger
from backend.integrations.calendar import calendar_client
from backend.agents.email_triage import EmailTriageAgent
from backend.models.cloud import gemini_client
from backend.models.local import ollama_client
from backend.config.settings import settings


class MorningBriefGenerator:
    """Generates the daily morning brief."""

    def __init__(self, use_cloud: bool = False):
        """
        Initialize the generator.

        Args:
            use_cloud: If True, uses Gemini for better markdown formatting.
                       If False, uses local Ollama model.
        """
        self.use_cloud = use_cloud
        
        # Load prompt
        prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "prompts", "morning_brief.txt"
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            logger.error(f"Prompt file not found at {prompt_path}")
            self.system_prompt = "You are AURA. Summarize the following data."

    def generate(self) -> str:
        """
        Gather all data and generate the morning brief.
        
        Returns:
            Markdown string with the brief.
        """
        logger.info("Generating Morning Brief...")
        
        # 1. Gather Calendar Data
        logger.info("Fetching calendar events...")
        today_events = calendar_client.get_today_events()
        tomorrow_events = calendar_client.get_tomorrow_events()
        
        # 2. Gather Email Data
        logger.info("Fetching and triaging unread emails...")
        triage_agent = EmailTriageAgent()
        # Run triage (which also saves urgent to memory)
        classifications = triage_agent.triage_inbox(max_emails=15, store_in_memory=True)
        urgent_emails = [c for c in classifications if c['category'] == 'urgent']
        
        # 3. Format context for the LLM
        context = self._format_context(today_events, tomorrow_events, urgent_emails)
        
        # 4. Generate the brief
        logger.info(f"Sending data to LLM (use_cloud={self.use_cloud})...")
        
        try:
            if self.use_cloud:
                response = gemini_client.generate(
                    system=self.system_prompt,
                    prompt=context,
                    temperature=0.4
                )
            else:
                response = ollama_client.generate(
                    system=self.system_prompt,
                    prompt=context,
                    temperature=0.4
                )
            
            logger.info("Morning Brief generated successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error generating morning brief: {e}")
            return f"# Error Generating Brief\n\nThere was an error communicating with the LLM: {e}"
            
    def _format_context(self, today_events: List[Dict], tomorrow_events: List[Dict], urgent_emails: List[Dict]) -> str:
        """Format the gathered data into a readable string for the LLM."""
        
        lines = []
        
        lines.append(f"Current Date: {datetime.now().strftime('%Y-%m-%d')}\n")
        
        lines.append("--- TODAY'S SCHEDULE ---")
        if not today_events:
            lines.append("No events today.")
        else:
            for e in today_events:
                time_str = "All Day" if e.get('is_all_day') else e.get('start')
                lines.append(f"- [{time_str}] {e.get('summary')}")
        lines.append("")
        
        lines.append("--- TOMORROW'S SCHEDULE ---")
        if not tomorrow_events:
            lines.append("No events tomorrow.")
        else:
            for e in tomorrow_events:
                time_str = "All Day" if e.get('is_all_day') else e.get('start')
                lines.append(f"- [{time_str}] {e.get('summary')}")
        lines.append("")
        
        lines.append("--- URGENT EMAILS ---")
        if not urgent_emails:
            lines.append("No urgent emails.")
        else:
            for e in urgent_emails:
                lines.append(f"- From: {e.get('sender')}")
                lines.append(f"  Subject: {e.get('subject')}")
                lines.append(f"  Reasoning: {e.get('reasoning')}")
        lines.append("")
        
        lines.append("--- GOALS ---")
        lines.append("Goal tracking is pending Phase 3 integration.")
        
        return "\n".join(lines)
