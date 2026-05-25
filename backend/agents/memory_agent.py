"""
Memory Agent - LangGraph agent for memory operations.

Handles smart explicit memory commands:
- Recognizes storage intent: "My name is...", "I work at...", "Remember..."
- Recognizes search intent: "What's my...", "Tell me about...", "Do I know..."
- Recognizes update intent: "Update...", "I graduated...", "Actually..."

Uses MemoryStore for persistence.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from loguru import logger

from backend.memory.store import MemoryStore


class MemoryAgentState(Dict):
    """State for MemoryAgent graph."""
    user_input: str
    intent: str  # store_memory, search_memory, update_memory, unknown
    entity_type: Optional[str]  # Person, Goal, Job, Location, Fact
    memory_text: Optional[str]
    search_query: Optional[str]
    search_results: Optional[List[Dict[str, Any]]]
    response: Optional[str]
    error: Optional[str]


class MemoryAgent:
    """
    LangGraph agent for memory operations.

    Workflow:
    1. classify_intent: Determine what user wants (store/search/update)
    2. extract_info: Extract entity type, text, or search query
    3. execute_operation: Call MemoryStore
    4. format_response: Return human-readable result
    """

    def __init__(self, memory_store: Optional[MemoryStore] = None):
        """
        Initialize MemoryAgent.

        Args:
            memory_store: MemoryStore instance (creates new if None)
        """
        self.store = memory_store or MemoryStore()
        self.graph = self._build_graph()

        logger.info("MemoryAgent initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(MemoryAgentState)

        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent)
        workflow.add_node("extract_info", self._extract_info)
        workflow.add_node("execute_store", self._execute_store)
        workflow.add_node("execute_search", self._execute_search)
        workflow.add_node("execute_update", self._execute_update)
        workflow.add_node("format_response", self._format_response)

        # Define edges
        workflow.set_entry_point("classify_intent")

        # After classification, extract info
        workflow.add_edge("classify_intent", "extract_info")

        # After extraction, route to correct operation
        workflow.add_conditional_edges(
            "extract_info",
            self._route_operation,
            {
                "store": "execute_store",
                "search": "execute_search",
                "update": "execute_update",
                "unknown": "format_response"
            }
        )

        # After execution, format response
        workflow.add_edge("execute_store", "format_response")
        workflow.add_edge("execute_search", "format_response")
        workflow.add_edge("execute_update", "format_response")

        # End after formatting
        workflow.add_edge("format_response", END)

        return workflow.compile()

    def _classify_intent(self, state: MemoryAgentState) -> MemoryAgentState:
        """
        Classify user intent using pattern matching.

        Patterns for STORE:
        - "My name is...", "I am...", "I work at..."
        - "Remember that...", "Save this...", "Store..."
        - "I want to...", "My goal is..."

        Patterns for SEARCH:
        - "What is my...", "Tell me about...", "What do I know..."
        - "Do I have...", "Show me...", "Find..."
        - "Remind me what..."

        Patterns for UPDATE:
        - "Update...", "Change...", "Actually..."
        - "I graduated...", "I moved to..."
        """
        user_input = state["user_input"].lower()

        # Store patterns
        store_patterns = [
            "my name is", "i am", "i'm", "i work at", "i live in",
            "remember", "save this", "store", "note that",
            "my goal is", "i want to", "i need to",
            "i have an", "i study at"
        ]

        # Search patterns
        search_patterns = [
            "what is my", "what's my", "tell me about", "what do i know",
            "do i have", "show me", "find", "search for",
            "remind me what", "what did i", "do you know"
        ]

        # Update patterns
        update_patterns = [
            "update", "change", "actually", "correct",
            "i graduated", "i moved", "i left", "i joined",
            "no longer", "not anymore"
        ]

        # Classify
        if any(pattern in user_input for pattern in store_patterns):
            state["intent"] = "store_memory"
            logger.debug(f"Intent classified: store_memory")
        elif any(pattern in user_input for pattern in search_patterns):
            state["intent"] = "search_memory"
            logger.debug(f"Intent classified: search_memory")
        elif any(pattern in user_input for pattern in update_patterns):
            state["intent"] = "update_memory"
            logger.debug(f"Intent classified: update_memory")
        else:
            state["intent"] = "unknown"
            logger.debug(f"Intent unclear - may not be memory operation")

        return state

    def _extract_info(self, state: MemoryAgentState) -> MemoryAgentState:
        """
        Extract entity type, memory text, or search query from user input.

        Entity type detection:
        - Person: "name", "colleague", "friend", "I am"
        - Goal: "goal", "want to", "objective", "plan to"
        - Job: "job", "work", "position", "interview", "company"
        - Location: "live in", "moved to", "located at"
        - Fact: default fallback
        """
        user_input = state["user_input"]
        intent = state["intent"]

        if intent == "store_memory":
            # Detect entity type
            user_lower = user_input.lower()

            if any(word in user_lower for word in ["name", "i am", "i'm", "colleague", "friend"]):
                state["entity_type"] = "Person"
            elif any(word in user_lower for word in ["goal", "want to", "objective", "plan to", "aim to"]):
                state["entity_type"] = "Goal"
            elif any(word in user_lower for word in ["job", "work", "position", "interview", "company"]):
                state["entity_type"] = "Job"
            elif any(word in user_lower for word in ["live in", "moved to", "located at", "address"]):
                state["entity_type"] = "Location"
            else:
                state["entity_type"] = "Fact"

            # Extract memory text (clean up command words)
            memory_text = user_input
            for prefix in ["remember that ", "remember ", "save this ", "store ", "note that "]:
                if user_lower.startswith(prefix):
                    memory_text = user_input[len(prefix):]
                    break

            state["memory_text"] = memory_text
            logger.debug(f"Extracted: entity_type={state['entity_type']}, text={memory_text[:50]}...")

        elif intent == "search_memory":
            # Extract search query (clean up question words)
            query = user_input
            for prefix in ["what is my ", "what's my ", "tell me about ", "what do i know about ",
                          "do i have ", "show me ", "find ", "remind me what "]:
                if user_input.lower().startswith(prefix):
                    query = user_input[len(prefix):]
                    break

            state["search_query"] = query
            logger.debug(f"Extracted search query: {query}")

        elif intent == "update_memory":
            # For updates, we'll search first then update
            # Extract what to search for (simple heuristic for now)
            state["search_query"] = user_input
            state["memory_text"] = user_input
            logger.debug(f"Update operation - will search and modify")

        return state

    def _route_operation(self, state: MemoryAgentState) -> str:
        """Route to correct operation node based on intent."""
        intent = state["intent"]

        if intent == "store_memory":
            return "store"
        elif intent == "search_memory":
            return "search"
        elif intent == "update_memory":
            return "update"
        else:
            return "unknown"

    def _execute_store(self, state: MemoryAgentState) -> MemoryAgentState:
        """Execute memory storage operation."""
        try:
            memory_id = f"mem_{uuid.uuid4().hex[:8]}"

            self.store.write_memory(
                memory_id=memory_id,
                text=state["memory_text"],
                entity_type=state["entity_type"],
                metadata={"source": "user_conversation"}
            )

            state["response"] = f"Remembered: {state['memory_text'][:100]}"
            logger.info(f"Memory stored: {memory_id} ({state['entity_type']})")

        except Exception as e:
            state["error"] = str(e)
            state["response"] = f"Failed to store memory: {e}"
            logger.error(f"Store error: {e}")

        return state

    def _execute_search(self, state: MemoryAgentState) -> MemoryAgentState:
        """Execute memory search operation."""
        try:
            results = self.store.search_memory(
                query=state["search_query"],
                top_k=5
            )

            state["search_results"] = results

            if results:
                response_parts = [f"Found {len(results)} memories:"]
                for i, result in enumerate(results, 1):
                    response_parts.append(f"{i}. {result['text'][:100]}")
                state["response"] = "\n".join(response_parts)
            else:
                state["response"] = "No matching memories found."

            logger.info(f"Search completed: {len(results)} results for '{state['search_query']}'")

        except Exception as e:
            state["error"] = str(e)
            state["response"] = f"Search failed: {e}"
            logger.error(f"Search error: {e}")

        return state

    def _execute_update(self, state: MemoryAgentState) -> MemoryAgentState:
        """Execute memory update operation."""
        try:
            # First, search for existing memory
            results = self.store.search_memory(
                query=state["search_query"],
                top_k=1
            )

            if results:
                memory_id = results[0]["id"]

                # Update with new text
                success = self.store.update_memory(
                    memory_id=memory_id,
                    text=state["memory_text"]
                )

                if success:
                    state["response"] = f"Updated memory: {state['memory_text'][:100]}"
                    logger.info(f"Memory updated: {memory_id}")
                else:
                    state["response"] = "Failed to update memory."
            else:
                # No existing memory found, store as new
                state["intent"] = "store_memory"
                state["entity_type"] = "Fact"
                return self._execute_store(state)

        except Exception as e:
            state["error"] = str(e)
            state["response"] = f"Update failed: {e}"
            logger.error(f"Update error: {e}")

        return state

    def _format_response(self, state: MemoryAgentState) -> MemoryAgentState:
        """Format final response for user."""
        if state["intent"] == "unknown":
            state["response"] = "I'm not sure if you want me to remember, search, or update something. Try phrases like:\n- 'My name is...'\n- 'What do I know about...'\n- 'Update: I graduated...'"

        # Response already set by execute nodes
        return state

    def process(self, user_input: str) -> str:
        """
        Process user input and perform memory operation.

        Args:
            user_input: User's message

        Returns:
            Response message
        """
        initial_state = {
            "user_input": user_input,
            "intent": None,
            "entity_type": None,
            "memory_text": None,
            "search_query": None,
            "search_results": None,
            "response": None,
            "error": None
        }

        logger.info(f"MemoryAgent processing: {user_input[:100]}")

        result = self.graph.invoke(initial_state)

        return result["response"]
