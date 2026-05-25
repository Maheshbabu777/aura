"""
Tests for MemoryStore - ChromaDB + SQLite integration.
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path

from backend.memory.store import MemoryStore


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for test memories."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Windows: give ChromaDB time to release file locks
    import time
    time.sleep(0.5)
    try:
        shutil.rmtree(temp_dir)
    except PermissionError:
        # On Windows, ChromaDB may still hold locks - ignore cleanup errors in tests
        pass


@pytest.fixture
def memory_store(temp_memory_dir):
    """Create a fresh MemoryStore for each test."""
    return MemoryStore(persist_dir=temp_memory_dir)


def test_write_memory(memory_store):
    """Test writing a memory to the store."""
    memory_id = memory_store.write_memory(
        memory_id="test_001",
        text="John is a software engineer",
        entity_type="Person"
    )

    assert memory_id == "test_001"
    assert memory_store.count_memories() == 1


def test_search_memory(memory_store):
    """Test semantic search in memory store."""
    # Store test memories
    memory_store.write_memory(
        memory_id="mem_001",
        text="John works at TechCorp as a software engineer",
        entity_type="Person"
    )
    memory_store.write_memory(
        memory_id="mem_002",
        text="Alice is studying computer science at University",
        entity_type="Person"
    )
    memory_store.write_memory(
        memory_id="mem_003",
        text="Goal: Get a job at CompanyX by September",
        entity_type="Goal"
    )

    # Search for work-related info
    results = memory_store.search_memory("job career work", top_k=2)

    assert len(results) <= 2
    assert all("id" in r and "text" in r for r in results)


def test_get_memory(memory_store):
    """Test retrieving a specific memory by ID."""
    memory_store.write_memory(
        memory_id="test_get",
        text="Test memory content",
        entity_type="Fact"
    )

    memory = memory_store.get_memory("test_get")

    assert memory is not None
    assert memory["id"] == "test_get"
    assert memory["text"] == "Test memory content"
    assert memory["entity_type"] == "Fact"


def test_update_memory(memory_store):
    """Test updating an existing memory."""
    memory_store.write_memory(
        memory_id="update_test",
        text="Original text",
        entity_type="Fact"
    )

    success = memory_store.update_memory(
        memory_id="update_test",
        text="Updated text"
    )

    assert success is True

    updated = memory_store.get_memory("update_test")
    assert updated["text"] == "Updated text"


def test_delete_memory(memory_store):
    """Test deleting a memory."""
    memory_store.write_memory(
        memory_id="delete_test",
        text="To be deleted",
        entity_type="Fact"
    )

    assert memory_store.count_memories() == 1

    success = memory_store.delete_memory("delete_test")
    assert success is True
    assert memory_store.count_memories() == 0


def test_entity_type_filter(memory_store):
    """Test filtering search results by entity type."""
    memory_store.write_memory(
        memory_id="person_001",
        text="John is a person",
        entity_type="Person"
    )
    memory_store.write_memory(
        memory_id="goal_001",
        text="Goal to achieve something",
        entity_type="Goal"
    )

    # Search only for Person entities
    results = memory_store.search_memory("John person", entity_type="Person")

    assert len(results) >= 1
    assert all(r["metadata"]["entity_type"] == "Person" for r in results)


def test_persistence_across_sessions(temp_memory_dir):
    """Test that memories persist across store instances."""
    # Create first store and add memory
    store1 = MemoryStore(persist_dir=temp_memory_dir)
    store1.write_memory(
        memory_id="persist_test",
        text="This should persist",
        entity_type="Fact"
    )

    # Create second store pointing to same directory
    store2 = MemoryStore(persist_dir=temp_memory_dir)
    memory = store2.get_memory("persist_test")

    assert memory is not None
    assert memory["text"] == "This should persist"


def test_count_memories_by_type(memory_store):
    """Test counting memories filtered by entity type."""
    memory_store.write_memory("p1", "Person 1", "Person")
    memory_store.write_memory("p2", "Person 2", "Person")
    memory_store.write_memory("g1", "Goal 1", "Goal")

    assert memory_store.count_memories() == 3
    assert memory_store.count_memories(entity_type="Person") == 2
    assert memory_store.count_memories(entity_type="Goal") == 1
