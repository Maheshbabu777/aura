"""
Tests for OrchestratorAgent with ConversationSession.
"""

import pytest
from unittest.mock import Mock, patch

from backend.agents.orchestrator import OrchestratorAgent


@pytest.fixture
def orchestrator():
    """Create orchestrator with mocked memory agent."""
    with patch("backend.agents.orchestrator.MemoryAgent") as mock_memory:
        mock_memory_instance = Mock()
        orch = OrchestratorAgent(memory_agent=mock_memory_instance)
        # Reset session state between tests
        orch.session.reset()
        return orch


# ── Classification Parsing Tests ────────────────────────────────────────

def test_parse_classification_valid(orchestrator):
    """Test parsing valid classification response."""
    response = """
    INTENT: store_memory
    AGENT: memory_agent
    ENTITIES: TechCorp, software engineer
    REASONING: User wants to store workplace information
    """

    result = orchestrator._parse_classification(response)

    assert result["intent"] == "store_memory"
    assert result["agent"] == "memory_agent"
    assert "TechCorp" in result["entities"]
    assert "software engineer" in result["entities"]
    assert "workplace" in result["reasoning"]


def test_parse_classification_missing_fields(orchestrator):
    """Test parsing response with missing fields."""
    response = """
    INTENT: general_chat
    """

    result = orchestrator._parse_classification(response)

    assert result["intent"] == "general_chat"
    assert result["agent"] == "unknown"  # Default when missing
    assert result["entities"] == []
    assert result["reasoning"] == ""


# ── Intent Classification Tests ─────────────────────────────────────────

def test_classify_intent_local(orchestrator):
    """Test intent classification using local model."""
    with patch("backend.agents.orchestrator.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        INTENT: store_memory
        AGENT: memory_agent
        ENTITIES: John, TechCorp
        REASONING: User storing personal info
        """

        result = orchestrator.classify_intent("Remember I work at TechCorp", use_cloud=False)

        assert result["intent"] == "store_memory"
        assert result["agent"] == "memory_agent"
        assert mock_ollama.generate.called


def test_classify_intent_cloud(orchestrator):
    """Test intent classification using cloud model."""
    with patch("backend.agents.orchestrator.gemini_client") as mock_gemini:
        mock_gemini.generate.return_value = """
        INTENT: goal_request
        AGENT: goal_agent
        ENTITIES: ML engineer
        REASONING: User setting career goal
        """

        result = orchestrator.classify_intent("I want to become an ML engineer", use_cloud=True)

        assert result["intent"] == "goal_request"
        assert result["agent"] == "goal_agent"
        assert mock_gemini.generate.called


def test_classify_intent_includes_history(orchestrator):
    """Test that classify_intent includes recent conversation context."""
    # Simulate existing conversation in session
    orchestrator.session.add_user_message("What did I do today?")
    orchestrator.session.add_assistant_message("You completed 3 tasks. Options: 1) Review, 2) Plan, 3) Skip")
    orchestrator.session.add_user_message("option 2")

    with patch("backend.agents.orchestrator.ollama_client") as mock_ollama:
        mock_ollama.generate.return_value = """
        INTENT: follow_up
        AGENT: conversational
        ENTITIES: none
        REASONING: User is selecting option from previous response
        """

        result = orchestrator.classify_intent("option 2")

        # Verify context was included in the prompt
        call_args = mock_ollama.generate.call_args
        prompt = call_args.kwargs.get("prompt", "")
        assert "conversation" in prompt.lower() or "AURA" in prompt


def test_classify_intent_error_handling(orchestrator):
    """Test graceful error handling when both local and cloud fail."""
    with patch("backend.agents.orchestrator.ollama_client") as mock_ollama, \
         patch("backend.agents.orchestrator.gemini_client") as mock_gemini:
        mock_ollama.generate.side_effect = Exception("Connection error")
        mock_gemini.generate.side_effect = Exception("Cloud fallback error")

        result = orchestrator.classify_intent("Test message")

    assert result["intent"] == "general_chat"
    assert result["agent"] == "none"
    assert "fallback failed" in result["reasoning"].lower()


# ── Routing Tests ───────────────────────────────────────────────────────

def test_route_memory_store(orchestrator):
    """Test routing memory store request."""
    orchestrator.memory_agent.process = Mock(return_value="Memory stored successfully")

    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "store_memory",
            "agent": "memory_agent",
            "entities": ["TechCorp"],
            "reasoning": "User storing info",
        }

        result = orchestrator.route("Remember I work at TechCorp")

        assert result["success"] == True
        assert result["agent"] == "memory_agent"
        assert "Memory stored" in result["message"]
        orchestrator.memory_agent.process.assert_called_once()


def test_route_memory_search(orchestrator):
    """Test routing memory search request."""
    orchestrator.memory_agent.process = Mock(return_value="You work at TechCorp")

    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "search_memory",
            "agent": "memory_agent",
            "entities": ["work"],
            "reasoning": "User searching memories",
        }

        result = orchestrator.route("Where do I work?")

        assert result["success"] == True
        assert result["agent"] == "memory_agent"
        assert "TechCorp" in result["message"]


def test_route_goal_goes_conversational(orchestrator):
    """Test that goal_agent routes to conversational handler (since it's not standalone yet)."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "goal_request",
            "agent": "goal_agent",
            "entities": [],
            "reasoning": "Goal tracking",
        }

        with patch.object(orchestrator, "_handle_conversational") as mock_conv:
            mock_conv.return_value = {
                "success": True,
                "message": "Let's talk about your goals!",
                "intent": "conversational",
                "agent": "conversational",
            }

            result = orchestrator.route("I want to become an ML engineer")

            assert result["success"] == True
            mock_conv.assert_called_once()


def test_route_status_agent(orchestrator):
    """Test routing status request returns intercept marker."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "status_request",
            "agent": "status_agent",
            "entities": [],
            "reasoning": "User wants daily status",
        }

        result = orchestrator.route("What did I do today?")

        assert result["message"] == "[INTERCEPT_STATUS_REQUEST]"
        assert result["agent"] == "status_agent"


def test_route_general_chat(orchestrator):
    """Test routing general chat goes to conversational handler."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "general_chat",
            "agent": "none",
            "entities": [],
            "reasoning": "General conversation",
        }

        with patch.object(orchestrator, "_handle_conversational") as mock_conv:
            mock_conv.return_value = {
                "success": True,
                "message": "Hello! I'm AURA.",
                "intent": "conversational",
                "agent": "conversational",
            }

            result = orchestrator.route("Hello")

            assert result["success"] == True
            mock_conv.assert_called_once()


def test_route_memory_agent_error(orchestrator):
    """Test handling memory agent error."""
    orchestrator.memory_agent.process = Mock(side_effect=Exception("Memory error"))

    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "store_memory",
            "agent": "memory_agent",
            "entities": [],
            "reasoning": "Store request",
        }

        result = orchestrator.route("Remember something")

        assert result["success"] == False
        assert "error" in result["message"].lower()


# ── Sticky Routing Tests ────────────────────────────────────────────────

def test_sticky_routing_follow_up(orchestrator):
    """Test that sticky routing sends follow-ups to conversational handler."""
    # Simulate: an agent is already active
    orchestrator.session.set_active_agent("conversational")
    orchestrator.session.add_user_message("What did I do today?")
    orchestrator.session.add_assistant_message("You completed 3 tasks.")

    with patch.object(orchestrator, "_handle_conversational") as mock_conv, \
         patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_conv.return_value = {
            "success": True,
            "message": "Option 2 is the fastest.",
            "intent": "conversational",
            "agent": "conversational",
        }

        result = orchestrator.route("Which option is fastest?")

        # Verify sticky routing bypassed the classifier
        mock_classify.assert_not_called()
        mock_conv.assert_called_once()
        assert result["success"] == True


def test_sticky_routing_timeout(orchestrator):
    """Test that sticky routing releases after timeout."""
    from datetime import datetime, timedelta

    orchestrator.session.set_active_agent("conversational")
    # Simulate timeout by setting last_activity far in the past
    orchestrator.session.last_activity = datetime.now() - timedelta(seconds=300)

    assert orchestrator.session.has_active_agent() == False
    assert orchestrator.session.active_agent is None


def test_follow_up_intent(orchestrator):
    """Test that follow_up intent routes to conversational handler."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "follow_up",
            "agent": "conversational",
            "entities": [],
            "reasoning": "User is following up on previous response",
        }

        with patch.object(orchestrator, "_handle_conversational") as mock_conv:
            mock_conv.return_value = {
                "success": True,
                "message": "Sure, option 2 it is!",
                "intent": "conversational",
                "agent": "conversational",
            }

            result = orchestrator.route("option 2")

            assert result["success"] == True
            mock_conv.assert_called_once()


# ── Session Tests ───────────────────────────────────────────────────────

def test_session_history_tracking(orchestrator):
    """Test that session tracks conversation history."""
    orchestrator.session.add_user_message("Hello")
    orchestrator.session.add_assistant_message("Hi there!")

    history = orchestrator.session.get_full_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_session_sliding_window(orchestrator):
    """Test that session trims history to max_messages."""
    # Add more messages than the max (8 turns = 16 messages)
    for i in range(20):
        orchestrator.session.add_user_message(f"User message {i}")
        orchestrator.session.add_assistant_message(f"Assistant response {i}")

    history = orchestrator.session.get_full_history()
    assert len(history) == orchestrator.session.max_messages


# ── Utility Tests ───────────────────────────────────────────────────────

def test_load_prompt(orchestrator):
    """Test that prompt loads correctly from file."""
    assert orchestrator.system_prompt is not None
    assert len(orchestrator.system_prompt) > 0
    assert "Orchestrator Agent" in orchestrator.system_prompt
    assert "memory_agent" in orchestrator.system_prompt
    assert "follow_up" in orchestrator.system_prompt


def test_complex_intents_tracking(orchestrator):
    """Test that complex intents are tracked correctly."""
    assert "goal_request" in orchestrator.complex_intents
    assert "task_request" in orchestrator.complex_intents
    assert "store_memory" not in orchestrator.complex_intents
