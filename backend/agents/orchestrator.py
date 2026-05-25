"""
Orchestrator Agent: Routes user input to specialized agents.
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

from backend.models.local import ollama_client
from backend.models.cloud import gemini_client
from backend.agents.memory_agent import MemoryAgent


class OrchestratorAgent:
    """
    Routes user requests to appropriate specialized agents.
    Uses local model (Gemma) for simple classification,
    escalates to cloud model (Gemini) for complex reasoning.
    """

    def __init__(self, memory_agent: Optional[MemoryAgent] = None):
        self.memory_agent = memory_agent or MemoryAgent()
        self.system_prompt = self._load_prompt()

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

        Args:
            user_message: User's input text
            use_cloud: Force use of Gemini instead of Gemma

        Returns:
            Classification dict with intent, agent, entities, reasoning
        """
        prompt = f"User message: {user_message}"

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
            logger.error(f"Intent classification failed: {e}")
            return {
                "intent": "error",
                "agent": "none",
                "entities": [],
                "reasoning": f"Classification error: {str(e)}",
            }

    def route(self, user_message: str) -> Dict[str, Any]:
        """
        Main routing function: classify intent and delegate to appropriate agent.

        Args:
            user_message: User's input text

        Returns:
            Response dict with agent_response and metadata
        """
        logger.info(f"Orchestrator received: {user_message[:100]}...")

        # Step 1: Classify intent
        classification = self.classify_intent(user_message)

        intent = classification["intent"]
        agent = classification["agent"]

        # Step 2: Handle not-implemented agents
        if agent == "not_implemented":
            return {
                "success": False,
                "message": "This feature is not yet available.",
                "intent": intent,
                "agent": agent,
            }

        # Step 3: Route to appropriate agent
        if agent == "memory_agent":
            return self._route_to_memory_agent(user_message, intent, classification)

        elif agent in ["goal_agent", "task_agent", "research_agent"]:
            return {
                "success": False,
                "message": f"{agent} is not yet implemented.",
                "intent": intent,
                "agent": agent,
            }

        elif intent == "general_chat":
            return self._handle_general_chat(user_message)

        else:
            return {
                "success": False,
                "message": "Could not determine how to handle this request.",
                "intent": intent,
                "agent": agent,
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

    def _handle_general_chat(self, user_message: str) -> Dict[str, Any]:
        """Handle general conversational messages."""
        # Simple responses for common greetings
        message_lower = user_message.lower().strip()

        if any(greeting in message_lower for greeting in ["hello", "hi", "hey"]):
            response = "Hello! I'm AURA, your personal AI assistant. How can I help you today?"
        elif any(word in message_lower for word in ["thanks", "thank you"]):
            response = "You're welcome! Let me know if you need anything else."
        elif any(word in message_lower for word in ["bye", "goodbye"]):
            response = "Goodbye! Feel free to come back anytime."
        else:
            # Use Gemini for more complex conversational responses
            response = gemini_client.generate(
                prompt=user_message,
                system="You are AURA, a helpful personal AI assistant. Respond conversationally and concisely.",
                temperature=0.7,
                max_tokens=256,
            )

        return {
            "success": True,
            "message": response,
            "intent": "general_chat",
            "agent": "none",
        }
