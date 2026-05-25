"""
Tests for MemoryAgent - LangGraph agent integration.
"""

import pytest
import tempfile
import shutil

from backend.agents.memory_agent import MemoryAgent
from backend.memory.store import MemoryStore


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for test memories."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import time
    time.sleep(0.5)
    try:
        shutil.rmtree(temp_dir)
    except PermissionError:
        pass


@pytest.fixture
def memory_agent(temp_memory_dir):
    """Create a fresh MemoryAgent for each test."""
    store = MemoryStore(persist_dir=temp_memory_dir)
    return MemoryAgent(memory_store=store)


def test_store_person_intent(memory_agent):
    """Test storing person information with natural language."""
    response = memory_agent.process("My name is John")

    assert "Remembered" in response
    assert "John" in response


def test_store_goal_intent(memory_agent):
    """Test storing goal with natural language."""
    response = memory_agent.process("I want to get a job at CompanyX by September")

    assert "Remembered" in response


def test_store_with_remember_keyword(memory_agent):
    """Test explicit 'remember' command."""
    response = memory_agent.process("Remember that I study at University")

    assert "Remembered" in response
    assert "University" in response


def test_search_intent(memory_agent):
    """Test searching memories with natural language."""
    # First store something
    memory_agent.process("My name is Alice")

    # Then search
    response = memory_agent.process("What is my name?")

    assert "Found" in response or "Alice" in response


def test_search_no_results(memory_agent):
    """Test search when no memories exist."""
    response = memory_agent.process("What do I know about physics?")

    assert "No matching memories" in response or "Found 0" in response


def test_update_intent(memory_agent):
    """Test updating existing memory."""
    # Store initial memory
    memory_agent.process("I work at OldCompany")

    # Update it
    response = memory_agent.process("Update: I work at NewCompany")

    assert "Updated" in response or "Remembered" in response


def test_work_related_storage(memory_agent):
    """Test storing work-related information."""
    response = memory_agent.process("I work at TechCorp as a software engineer")

    assert "Remembered" in response


def test_location_storage(memory_agent):
    """Test storing location information."""
    response = memory_agent.process("I live in Seattle")

    assert "Remembered" in response


def test_unknown_intent(memory_agent):
    """Test handling unclear intent."""
    response = memory_agent.process("Hello there")

    assert "not sure" in response.lower() or "try phrases" in response.lower()


def test_entity_type_person(memory_agent):
    """Test that person info is correctly classified."""
    memory_agent.process("My name is Bob")

    # Search and verify it was stored
    result = memory_agent.store.search_memory("Bob", top_k=1)
    assert len(result) > 0
    assert result[0]["metadata"]["entity_type"] == "Person"


def test_entity_type_goal(memory_agent):
    """Test that goals are correctly classified."""
    memory_agent.process("My goal is to learn Python")

    result = memory_agent.store.search_memory("Python", top_k=1)
    assert len(result) > 0
    assert result[0]["metadata"]["entity_type"] == "Goal"


def test_entity_type_job(memory_agent):
    """Test that job info is correctly classified."""
    memory_agent.process("I have an interview tomorrow at CompanyX")

    result = memory_agent.store.search_memory("interview", top_k=1)
    assert len(result) > 0
    assert result[0]["metadata"]["entity_type"] == "Job"


def test_multiple_memories_search(memory_agent):
    """Test searching across multiple memories."""
    # Store multiple memories
    memory_agent.process("I work at CompanyA")
    memory_agent.process("I want to get a job at CompanyB")
    memory_agent.process("My name is Charlie")

    # Search for work-related
    response = memory_agent.process("What do I know about work?")

    assert "Found" in response
    # Should find at least the work-related memories


def test_search_variations(memory_agent):
    """Test different search phrasings."""
    memory_agent.process("My name is David")

    # Try different search phrases
    variations = [
        "What's my name?",
        "Tell me about my name",
        "Do I have a name stored?",
        "Show me my name"
    ]

    for phrase in variations:
        response = memory_agent.process(phrase)
        # Should return search results (not "not sure" error)
        assert "not sure" not in response.lower()
