"""
Status Agent: Generates on-demand intelligent status updates.
Pulls from Activity Stream, Vector Memory, and Chat History concurrently.
"""

import json
import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

from backend.models.cloud import gemini_client
from backend.memory.activity_stream import activity_stream
from backend.memory.store import MemoryStore

class StatusAgent:
    """Agent that aggregates daily data to generate intelligent progress updates."""

    def __init__(self):
        self.prompt_path = "./backend/prompts/status_agent.txt"
        self.system_prompt = self._load_prompt()
        self.memory_store = MemoryStore()

    def _load_prompt(self) -> str:
        try:
            with open(self.prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load StatusAgent prompt: {e}")
            return "You are a helpful AI assistant."

    async def get_daily_status(self, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Concurrently fetches 3 layers of context and uses LLM to generate a status update.
        """
        logger.info("StatusAgent: Generating daily status report...")
        
        # We need generic query for core persona memory
        memory_query = "What is the user's current main focus, job, or educational goal?"

        # 1. Fire off data gathering tasks concurrently
        activity_task = asyncio.to_thread(activity_stream.get_today_logs)
        memory_task = asyncio.to_thread(self.memory_store.search_memory, memory_query, 5)

        # Wait for all fetches to finish (takes the time of the slowest single query)
        activities, memories = await asyncio.gather(activity_task, memory_task)

        # 2. Format Context Layers
        
        # Layer 1: Activity Stream
        activity_text = "No activities logged today yet."
        if activities:
            activity_text = "\n".join([f"- [{log['timestamp'][11:16]}] {log['agent_name']}: {log['description']}" for log in activities])
            
        # Layer 2: Chat History
        chat_text = "No recent chat context provided."
        if chat_history:
            # Format last 5 messages
            last_msgs = chat_history[-5:]
            chat_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in last_msgs])

        # Layer 3: Long-Term Memory
        memory_text = "No long term memories found."
        if memories:
            memory_text = "\n".join([f"- {mem['text']}" for mem in memories])

        # 3. Construct final prompt
        context_prompt = (
            f"--- LONG-TERM MEMORY ---\n{memory_text}\n\n"
            f"--- RECENT CHAT HISTORY ---\n{chat_text}\n\n"
            f"--- TODAY'S ACTIVITY STREAM ---\n{activity_text}\n"
        )

        # 4. Generate Structured Report via Cloud LLM
        try:
            # We use asyncio.to_thread because gemini_client.generate is synchronous
            response_text = await asyncio.to_thread(
                gemini_client.generate,
                system=self.system_prompt,
                prompt=context_prompt,
                temperature=0.3,
                max_tokens=1024,
                response_mime_type="application/json"
            )

            # Parse the JSON response
            return json.loads(response_text)

        except Exception as e:
            logger.error(f"StatusAgent generation failed: {e}")
            return {
                "summary_text": "I tried to generate your status update, but I ran into a technical error.",
                "suggested_actions": ["Try asking again in a few seconds."]
            }

# Singleton instance
status_agent = StatusAgent()
