"""
Tests for OrchestratorAgent.
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
        return orch


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


def test_route_not_implemented_agent(orchestrator):
    """Test routing to not-yet-implemented agent."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "goal_request",
            "agent": "goal_agent",
            "entities": [],
            "reasoning": "Goal tracking not implemented",
        }

        result = orchestrator.route("I want to become an ML engineer")

        assert result["success"] == False
        assert "not yet implemented" in result["message"].lower()
        assert result["agent"] == "goal_agent"


def test_route_general_chat_greeting(orchestrator):
    """Test routing simple greeting."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "general_chat",
            "agent": "none",
            "entities": [],
            "reasoning": "Simple greeting",
        }

        result = orchestrator.route("Hello")

        assert result["success"] == True
        assert result["intent"] == "general_chat"
        assert "AURA" in result["message"]


def test_route_general_chat_thanks(orchestrator):
    """Test routing thank you message."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "general_chat",
            "agent": "none",
            "entities": [],
            "reasoning": "Expressing gratitude",
        }

        result = orchestrator.route("Thank you!")

        assert result["success"] == True
        assert result["intent"] == "general_chat"
        assert "welcome" in result["message"].lower()


def test_route_general_chat_complex(orchestrator):
    """Test routing complex conversational message."""
    with patch.object(orchestrator, "classify_intent") as mock_classify:
        mock_classify.return_value = {
            "intent": "general_chat",
            "agent": "none",
            "entities": [],
            "reasoning": "General conversation",
        }

        with patch("backend.agents.orchestrator.gemini_client") as mock_gemini:
            mock_gemini.generate.return_value = "I can help you with that!"

            result = orchestrator.route("Tell me about your capabilities")

            assert result["success"] == True
            assert result["intent"] == "general_chat"
            mock_gemini.generate.called


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


def test_classify_intent_error_handling(orchestrator):
    """Test graceful error handling in classification."""
    with patch("backend.agents.orchestrator.ollama_client") as mock_ollama:
        mock_ollama.generate.side_effect = Exception("Connection error")

        result = orchestrator.classify_intent("Test message")

        assert result["intent"] == "error"
        assert result["agent"] == "none"
        assert "error" in result["reasoning"].lower()


def test_load_prompt(orchestrator):
    """Test that prompt loads correctly from file."""
    assert orchestrator.system_prompt is not None
    assert len(orchestrator.system_prompt) > 0
    assert "Orchestrator Agent" in orchestrator.system_prompt
    assert "memory_agent" in orchestrator.system_prompt


def test_complex_intents_tracking(orchestrator):
    """Test that complex intents are tracked correctly."""
    assert "goal_request" in orchestrator.complex_intents
    assert "task_request" in orchestrator.complex_intents
    assert "store_memory" not in orchestrator.complex_intents
