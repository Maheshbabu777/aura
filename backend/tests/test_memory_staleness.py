"""
Tests for memory staleness detection.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timezone, timedelta

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
def memory_store(temp_memory_dir):
    """Create a fresh MemoryStore for each test."""
    return MemoryStore(persist_dir=temp_memory_dir)


def test_is_stale_fresh_memory(memory_store):
    """Test that fresh memories are not stale."""
    memory = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ttl_days": 365
    }

    assert memory_store.is_stale(memory) == False


def test_is_stale_expired_memory(memory_store):
    """Test that old memories are stale."""
    # Memory created 400 days ago with 365 day TTL
    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    memory = {
        "created_at": old_date.isoformat(),
        "ttl_days": 365
    }

    assert memory_store.is_stale(memory) == True


def test_is_stale_edge_case(memory_store):
    """Test edge case: memory exactly at TTL boundary."""
    # Memory created exactly 365 days ago with 365 day TTL
    boundary_date = datetime.now(timezone.utc) - timedelta(days=365)
    memory = {
        "created_at": boundary_date.isoformat(),
        "ttl_days": 365
    }

    # Should be stale (age > ttl, not >=)
    assert memory_store.is_stale(memory) == False


def test_is_stale_short_ttl(memory_store):
    """Test memory with short TTL (7 days)."""
    old_date = datetime.now(timezone.utc) - timedelta(days=10)
    memory = {
        "created_at": old_date.isoformat(),
        "ttl_days": 7
    }

    assert memory_store.is_stale(memory) == True


def test_get_stale_memories_empty(memory_store):
    """Test getting stale memories when none exist."""
    stale = memory_store.get_stale_memories()

    assert len(stale) == 0


def test_get_stale_memories_mixed(memory_store):
    """Test getting stale memories from mixed set."""
    now = datetime.now(timezone.utc)

    # Fresh memory
    memory_store.write_memory(
        memory_id="fresh_001",
        text="Fresh memory",
        entity_type="Fact",
        ttl_days=365
    )

    # Manually create stale memory by writing with old timestamp
    # We'll hack the database for testing
    import sqlite3
    conn = sqlite3.connect(memory_store.db_path)
    cursor = conn.cursor()

    old_date = (now - timedelta(days=400)).isoformat()
    cursor.execute("""
        INSERT INTO memories (id, text, entity_type, created_at, updated_at, ttl_days, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("stale_001", "Old memory", "Fact", old_date, old_date, 365, None))

    conn.commit()
    conn.close()

    # Also add to ChromaDB
    memory_store.collection.add(
        ids=["stale_001"],
        documents=["Old memory"],
        metadatas=[{
            "entity_type": "Fact",
            "created_at": old_date,
            "updated_at": old_date,
            "ttl_days": "365"
        }]
    )

    # Get stale memories
    stale = memory_store.get_stale_memories()

    assert len(stale) == 1
    assert stale[0]["id"] == "stale_001"


def test_get_stale_memories_by_entity_type(memory_store):
    """Test filtering stale memories by entity type."""
    now = datetime.now(timezone.utc)
    old_date = (now - timedelta(days=400)).isoformat()

    import sqlite3
    conn = sqlite3.connect(memory_store.db_path)
    cursor = conn.cursor()

    # Create stale Person memory
    cursor.execute("""
        INSERT INTO memories (id, text, entity_type, created_at, updated_at, ttl_days, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("stale_person", "Old person info", "Person", old_date, old_date, 365, None))

    # Create stale Goal memory
    cursor.execute("""
        INSERT INTO memories (id, text, entity_type, created_at, updated_at, ttl_days, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("stale_goal", "Old goal", "Goal", old_date, old_date, 365, None))

    conn.commit()
    conn.close()

    # Get only stale Person memories
    stale_persons = memory_store.get_stale_memories(entity_type="Person")

    assert len(stale_persons) == 1
    assert stale_persons[0]["id"] == "stale_person"


def test_search_includes_staleness_flag(memory_store):
    """Test that search results include is_stale flag."""
    now = datetime.now(timezone.utc)
    old_date = (now - timedelta(days=400)).isoformat()

    # Create fresh memory
    memory_store.write_memory(
        memory_id="fresh_search",
        text="John works at TechCorp",
        entity_type="Person",
        ttl_days=365
    )

    # Create stale memory manually
    import sqlite3
    conn = sqlite3.connect(memory_store.db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO memories (id, text, entity_type, created_at, updated_at, ttl_days, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("stale_search", "Alice worked at OldCompany", "Person", old_date, old_date, 365, None))

    conn.commit()
    conn.close()

    memory_store.collection.add(
        ids=["stale_search"],
        documents=["Alice worked at OldCompany"],
        metadatas=[{
            "entity_type": "Person",
            "created_at": old_date,
            "updated_at": old_date,
            "ttl_days": "365"
        }]
    )

    # Search
    results = memory_store.search_memory("work company", top_k=5)

    # Check that results have is_stale field
    assert len(results) > 0
    for result in results:
        assert "is_stale" in result
        assert isinstance(result["is_stale"], bool)

    # Verify stale memory is flagged
    stale_result = next((r for r in results if r["id"] == "stale_search"), None)
    if stale_result:
        assert stale_result["is_stale"] == True


def test_different_ttl_values(memory_store):
    """Test staleness with different TTL values."""
    now = datetime.now(timezone.utc)

    # Memory with short TTL (30 days), created 35 days ago
    short_ttl_date = (now - timedelta(days=35)).isoformat()
    short_ttl_memory = {
        "created_at": short_ttl_date,
        "ttl_days": 30
    }
    assert memory_store.is_stale(short_ttl_memory) == True

    # Memory with long TTL (1000 days), created 500 days ago
    long_ttl_date = (now - timedelta(days=500)).isoformat()
    long_ttl_memory = {
        "created_at": long_ttl_date,
        "ttl_days": 1000
    }
    assert memory_store.is_stale(long_ttl_memory) == False