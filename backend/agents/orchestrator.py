"""
Orchestrator Agent: Routes user input to specialized agents.

Architecture (Production-Standard Conversation Engine):
1. Session checks sticky routing (is an agent already handling this conversation?)
2. If not, classify intent WITH conversation context
3. Route to the appropriate agent WITH full history
4. Set active_agent for follow-up handling

Key design decisions:
- Session state is managed by chat.py (the API layer), not internally
- The orchestrator reads session state but only chat.py writes to it
- Full conversation history is passed to cloud agents (Gemini)
- Compact recent context is passed to the local intent classifier (Gemma)
- Sticky routing prevents unnecessary re-classification of follow-ups
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from backend.models.local import ollama_client
from backend.models.cloud import gemini_client
from backend.agents.memory_agent import MemoryAgent
from backend.conversation.session import ConversationSession


class OrchestratorAgent:
    """
    Routes user requests to appropriate specialized agents.
    Uses ConversationSession for stateful, context-aware routing.
    """

    def __init__(self, memory_agent: Optional[MemoryAgent] = None):
        self.memory_agent = memory_agent or MemoryAgent()
        self.system_prompt = self._load_prompt()
        self.session = ConversationSession(max_turns=8, timeout_seconds=180)

        # Track which intents need cloud reasoning
        self.complex_intents = {"goal_request", "task_request"}

    def _load_prompt(self) -> str:
        """Load orchestrator system prompt from file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "orchestrator.txt"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_classification(self, response: str) -> Dict[str, str]:
        """
        Parse orchestrator response into structured data.

        Expected format:
        INTENT: <intent_name>
        AGENT: <agent_name>
        ENTITIES: <entities>
        REASONING: <reasoning>
        """
        result = {
            "intent": "unknown",
            "agent": "unknown",
            "entities": [],
            "reasoning": "",
        }

        # Extract fields using regex
        intent_match = re.search(r"INTENT:\s*(.+)", response, re.IGNORECASE)
        agent_match = re.search(r"AGENT:\s*(.+)", response, re.IGNORECASE)
        entities_match = re.search(r"ENTITIES:\s*(.+)", response, re.IGNORECASE)
        reasoning_match = re.search(r"REASONING:\s*(.+)", response, re.IGNORECASE)

        if intent_match:
            result["intent"] = intent_match.group(1).strip()
        if agent_match:
            result["agent"] = agent_match.group(1).strip()
        if entities_match:
            entities_str = entities_match.group(1).strip()
            result["entities"] = [e.strip() for e in entities_str.split(",") if e.strip()]
        if reasoning_match:
            result["reasoning"] = reasoning_match.group(1).strip()

        return result

    def classify_intent(self, user_message: str, use_cloud: bool = False) -> Dict[str, str]:
        """
        Classify user intent using local or cloud model.
        Includes recent conversation context for accurate follow-up detection.
        """
        # Build prompt with conversation context
        prompt = ""

        # Include recent conversation history (last 3 turns, excluding current message)
        # The current message was already added to session by chat.py before route() is called
        history = self.session.history
        # Get history excluding the last message (the current user message)
        context_history = history[:-1] if len(history) > 0 else []
        # Take last 6 messages (3 turns) of context
        recent = context_history[-6:] if len(context_history) >= 6 else context_history

        if recent:
            prompt += "Recent conversation:\n"
            for msg in recent:
                role = "User" if msg["role"] == "user" else "AURA"
                # Truncate long messages to keep the classifier prompt manageable
                content = msg["content"][:300]
                if len(msg["content"]) > 300:
                    content += "..."
                prompt += f"  {role}: {content}\n"
            prompt += "\n"

        prompt += f"User message: {user_message}"

        try:
            if use_cloud:
                logger.info("Using Gemini for intent classification")
                response = gemini_client.generate(
                    prompt=prompt,
                    system=self.system_prompt,
                    temperature=0.3,  # Lower temp for classification
                    max_tokens=256,
                )
            else:
                logger.debug("Using Gemma for intent classification")
                response = ollama_client.generate(
                    prompt=prompt,
                    system=self.system_prompt,
                    temperature=0.3,
                    max_tokens=256,
                )

            classification = self._parse_classification(response)
            logger.info(f"Intent classified: {classification['intent']} -> {classification['agent']}")

            return classification

        except Exception as e:
            logger.error(f"Intent classification failed with local model: {e}")
            logger.info("Attempting fallback to Cloud Gemini for intent classification...")
            try:
                # Fallback to cloud model
                response = gemini_client.generate(
                    prompt=prompt,
                    system=self.system_prompt,
                    temperature=0.0,
                    max_tokens=150,
                )
                return self._parse_classification(response)
            except Exception as cloud_e:
                logger.error(f"Intent classification fallback failed: {cloud_e}")
                return {
                    "intent": "general_chat",
                    "agent": "none",
                    "entities": [],
                    "reasoning": "Fallback failed",
                }

    def route(self, user_message: str) -> Dict[str, Any]:
        """
        Main routing function with sticky routing and full conversation context.

        Flow:
        1. Check sticky routing (active agent?) → route directly
        2. Classify intent with conversation context
        3. Route to appropriate agent
        4. Return result (chat.py handles session updates)

        NOTE: chat.py adds the user message to session BEFORE calling this method,
        and adds the assistant response AFTER. This method does NOT modify session state.
        """
        logger.info(f"Orchestrator received: {user_message[:100]}...")

        # ── Step 0: Sticky Routing ──────────────────────────────────────
        if self.session.has_active_agent():
            active = self.session.active_agent
            logger.info(f"Sticky routing → '{active}' (follow-up detected)")

            # All follow-ups go through the conversational handler
            # Gemini with full history naturally understands context
            return self._handle_conversational(user_message)

        # ── Step 1: Classify Intent ─────────────────────────────────────
        classification = self.classify_intent(user_message)
        intent = classification["intent"]
        agent = classification["agent"]

        # ── Step 1b: Handle follow_up intent ────────────────────────────
        if intent == "follow_up" or agent == "conversational":
            return self._handle_conversational(user_message)

        # ── Step 2: Handle not-implemented agents ───────────────────────
        if agent == "not_implemented":
            return {
                "success": False,
                "message": "This feature is not yet available.",
                "intent": intent,
                "agent": agent,
            }

        # ── Step 3: Route to appropriate agent ──────────────────────────
        if agent == "memory_agent":
            return self._route_to_memory_agent(user_message, intent, classification)

        elif agent in ["goal_agent", "task_agent"]:
            # Not yet implemented as standalone agents — handle conversationally
            # Gemini with full history can still discuss goals/tasks intelligently
            return self._handle_conversational(user_message)
            
        elif agent == "research_agent":
            # ResearchAgent is async — return intercept marker for chat.py
            return {
                "success": True,
                "message": "[INTERCEPT_RESEARCH_REQUEST]",
                "intent": intent,
                "agent": agent,
            }

        elif agent == "status_agent":
            # StatusAgent is async — return intercept marker for chat.py
            return {
                "success": True,
                "message": "[INTERCEPT_STATUS_REQUEST]",
                "intent": intent,
                "agent": agent,
            }

        # ── Step 4: General chat / fallback ─────────────────────────────
        elif intent == "general_chat" or agent == "none":
            return self._handle_conversational(user_message)

        else:
            return {
                "success": False,
                "message": "I understood your request, but the specific agent to handle it is not available.",
                "intent": intent,
                "agent": agent,
            }

    # ── Agent Handlers ──────────────────────────────────────────────────

    def _handle_conversational(self, user_message: str) -> Dict[str, Any]:
        """
        Handle messages conversationally using Gemini with FULL conversation history.

        This is the primary handler for:
        - Follow-up messages ("option 2", "tell me more")
        - General chat
        - Agents not yet implemented (goals, tasks, research)

        Gemini receives the entire conversation history and naturally understands context.
        """
        history = self.session.get_full_history()

        # Build messages for Gemini chat API
        messages = []

        # System context as the opening exchange
        messages.append({
            "role": "user",
            "content": (
                "You are AURA, a personal AI assistant. You help users with their "
                "daily productivity, goals, tasks, and life management. Be conversational, "
                "helpful, and concise. If the user refers to options, suggestions, or anything "
                "from a previous message, use the conversation history to understand what they mean. "
                "Always respond naturally as if you remember the entire conversation."
            ),
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I'm AURA, your personal AI assistant. I'm ready to help.",
        })

        # Add full conversation history (already includes current user message)
        messages.extend(history)

        try:
            response = gemini_client.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=512,
            )
            return {
                "success": True,
                "message": response,
                "intent": "conversational",
                "agent": "conversational",
            }
        except Exception as e:
            logger.error(f"Conversational handler failed: {e}")
            return {
                "success": False,
                "message": f"I'm sorry, I'm having trouble responding right now. Please try again.",
                "intent": "conversational",
                "agent": "conversational",
            }

    def _route_to_memory_agent(
        self, user_message: str, intent: str, classification: Dict[str, str]
    ) -> Dict[str, Any]:
        """Route memory-related requests to MemoryAgent."""
        try:
            # MemoryAgent already has intent detection built-in from Week 2
            response = self.memory_agent.process(user_message)

            return {
                "success": True,
                "message": response,
                "intent": intent,
                "agent": "memory_agent",
                "classification": classification,
            }

        except Exception as e:
            logger.error(f"MemoryAgent routing failed: {e}")
            return {
                "success": False,
                "message": f"Memory agent error: {str(e)}",
                "intent": intent,
                "agent": "memory_agent",
            }

    # Legacy compatibility — tests may still call this directly
    def _handle_general_chat(self, user_message: str, chat_history=None) -> Dict[str, Any]:
        """Legacy handler — redirects to _handle_conversational."""
        return self._handle_conversational(user_message)


# Singleton instance
orchestrator = OrchestratorAgent()
