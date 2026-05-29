"""
ConversationSession: Manages conversation state, history, and active agent tracking.

This is the core "memory" of AURA's conversation engine. It provides:
- Full conversation history with automatic sliding window (8 turns)
- Sticky routing via active_agent tracking
- Timeout-based agent lock release (3 minutes)
- Compact context for the lightweight intent router
"""

from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger


class ConversationSession:
    """
    Stateful conversation session for a single user.

    Tracks which agent is currently handling the conversation (sticky routing),
    maintains conversation history with an automatic sliding window,
    and provides different context views for different consumers:
    - Full history for cloud agents (Gemini)
    - Compact recent context for the local intent classifier (Gemma)
    """

    def __init__(self, max_turns: int = 8, timeout_seconds: int = 180):
        """
        Args:
            max_turns: Number of conversation turns (user+assistant pairs) to keep.
            timeout_seconds: Seconds of inactivity before releasing the active agent lock.
        """
        self.active_agent: Optional[str] = None
        self.history: List[Dict[str, str]] = []
        self.last_activity: datetime = datetime.now()
        self.max_messages: int = max_turns * 2  # Each turn = user + assistant
        self.timeout_seconds: int = timeout_seconds
        logger.info(
            f"ConversationSession initialized (max_turns={max_turns}, timeout={timeout_seconds}s)"
        )

    # ── History Management ──────────────────────────────────────────────

    def add_user_message(self, content: str):
        """Add a user message and refresh the activity timer."""
        self.history.append({"role": "user", "content": content})
        self.last_activity = datetime.now()
        self._trim()

    def add_assistant_message(self, content: str):
        """Add an assistant response to the history."""
        self.history.append({"role": "assistant", "content": content})
        self._trim()

    def _trim(self):
        """Sliding window: keep only the most recent max_messages messages."""
        if len(self.history) > self.max_messages:
            self.history = self.history[-self.max_messages:]

    def get_full_history(self) -> List[Dict[str, str]]:
        """
        Get the full conversation history for cloud agents.
        Returns a copy so agents can't mutate session state.
        """
        return list(self.history)

    def get_recent_context(self, turns: int = 3) -> List[Dict[str, str]]:
        """
        Get compact recent context for the intent classifier.
        Returns the last N turns (user+assistant pairs).

        Args:
            turns: Number of recent turns to include.
        """
        count = turns * 2
        if len(self.history) >= count:
            return list(self.history[-count:])
        return list(self.history)

    # ── Sticky Routing ──────────────────────────────────────────────────

    def set_active_agent(self, agent_name: str):
        """Lock routing to this agent for follow-up messages."""
        self.active_agent = agent_name
        logger.debug(f"Session: active_agent → '{agent_name}'")

    def clear_active_agent(self):
        """Release the agent lock."""
        if self.active_agent:
            logger.debug(f"Session: cleared active_agent (was '{self.active_agent}')")
        self.active_agent = None

    def has_active_agent(self) -> bool:
        """
        Check if there's an active agent, respecting the timeout.
        Returns False (and clears the lock) if the timeout has elapsed.
        """
        if self.active_agent is None:
            return False
        elapsed = (datetime.now() - self.last_activity).total_seconds()
        if elapsed > self.timeout_seconds:
            logger.info(
                f"Session: '{self.active_agent}' timed out after {elapsed:.0f}s of inactivity"
            )
            self.clear_active_agent()
            return False
        return True

    # ── Session Lifecycle ───────────────────────────────────────────────

    def reset(self):
        """Reset the entire session (new conversation)."""
        self.active_agent = None
        self.history = []
        self.last_activity = datetime.now()
        logger.info("Session: fully reset")

    def __repr__(self) -> str:
        return (
            f"ConversationSession(active_agent={self.active_agent!r}, "
            f"history_len={len(self.history)}, "
            f"last_activity={self.last_activity.isoformat()})"
        )
