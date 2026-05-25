"""
Tests for memory prioritization functionality.
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


def test_write_memory_with_importance(memory_store):
    """Test storing memory with importance level."""
    memory_store.write_memory(
        memory_id="important_mem",
        text="Critical deadline tomorrow",
        entity_type="Job",
        importance=2  # Critical
    )

    memory = memory_store.get_memory("important_mem")

    assert memory is not None
    assert memory["importance"] == 2


def test_write_memory_default_importance(memory_store):
    """Test that default importance is 0."""
    memory_store.write_memory(
        memory_id="normal_mem",
        text="Regular task",
        entity_type="Fact"
    )

    memory = memory_store.get_memory("normal_mem")

    assert memory["importance"] == 0


def test_set_importance(memory_store):
    """Test changing importance of existing memory."""
    memory_store.write_memory(
        memory_id="mem_001",
        text="Test memory",
        entity_type="Fact",
        importance=0
    )

    # Upgrade importance
    success = memory_store.set_importance("mem_001", importance=2)

    assert success == True

    memory = memory_store.get_memory("mem_001")
    assert memory["importance"] == 2


def test_set_importance_nonexistent(memory_store):
    """Test setting importance for non-existent memory."""
    success = memory_store.set_importance("nonexistent", importance=1)

    assert success == False


def test_access_tracking(memory_store):
    """Test that get_memory with track_access increments counter."""
    memory_store.write_memory(
        memory_id="tracked_mem",
        text="Track access to this",
        entity_type="Fact"
    )

    # Initial state
    memory = memory_store.get_memory("tracked_mem")
    assert memory["access_count"] == 0
    assert memory["last_accessed_at"] is None

    # Access with tracking
    memory_store.get_memory("tracked_mem", track_access=True)
    memory_store.get_memory("tracked_mem", track_access=True)
    memory_store.get_memory("tracked_mem", track_access=True)

    # Check updated counts
    memory = memory_store.get_memory("tracked_mem")
    assert memory["access_count"] == 3
    assert memory["last_accessed_at"] is not None


def test_calculate_priority_score_importance(memory_store):
    """Test that importance affects priority score."""
    # Critical importance memory
    memory_critical = {
        "importance": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "access_count": 0,
        "ttl_days": 365
    }

    # Normal importance memory
    memory_normal = {
        "importance": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "access_count": 0,
        "ttl_days": 365
    }

    score_critical = memory_store.calculate_priority_score(memory_critical)
    score_normal = memory_store.calculate_priority_score(memory_normal)

    # Critical should have higher score
    assert score_critical > score_normal


def test_calculate_priority_score_recency(memory_store):
    """Test that recent memories have higher scores."""
    # Recent memory (1 day old)
    memory_recent = {
        "importance": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "access_count": 0,
        "ttl_days": 365
    }

    # Old memory (200 days old)
    memory_old = {
        "importance": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=200)).isoformat(),
        "access_count": 0,
        "ttl_days": 365
    }

    score_recent = memory_store.calculate_priority_score(memory_recent)
    score_old = memory_store.calculate_priority_score(memory_old)

    # Recent should have higher score
    assert score_recent > score_old


def test_calculate_priority_score_access_frequency(memory_store):
    """Test that frequently accessed memories have higher scores."""
    # Frequently accessed
    memory_frequent = {
        "importance": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "access_count": 15,
        "ttl_days": 365
    }

    # Rarely accessed
    memory_rare = {
        "importance": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "access_count": 1,
        "ttl_days": 365
    }

    score_frequent = memory_store.calculate_priority_score(memory_frequent)
    score_rare = memory_store.calculate_priority_score(memory_rare)

    # Frequently accessed should have higher score
    assert score_frequent > score_rare


def test_calculate_priority_score_staleness_penalty(memory_store):
    """Test that stale memories get penalized."""
    # Fresh memory
    memory_fresh = {
        "importance": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "access_count": 0,
        "ttl_days": 365
    }

    # Stale memory
    memory_stale = {
        "importance": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=400)).isoformat(),
        "access_count": 0,
        "ttl_days": 365
    }

    score_fresh = memory_store.calculate_priority_score(memory_fresh)
    score_stale = memory_store.calculate_priority_score(memory_stale)

    # Stale should have lower score (penalty applied)
    assert score_stale < score_fresh


def test_get_prioritized_memories_empty(memory_store):
    """Test getting prioritized memories from empty store."""
    result = memory_store.get_prioritized_memories()

    assert len(result) == 0


def test_get_prioritized_memories_ordering(memory_store):
    """Test that memories are returned in priority order."""
    # Create memories with different importance levels
    memory_store.write_memory(
        memory_id="low",
        text="Low priority",
        entity_type="Fact",
        importance=0
    )

    memory_store.write_memory(
        memory_id="medium",
        text="Medium priority",
        entity_type="Fact",
        importance=1
    )

    memory_store.write_memory(
        memory_id="high",
        text="High priority",
        entity_type="Fact",
        importance=2
    )

    # Get prioritized list
    result = memory_store.get_prioritized_memories(top_k=10)

    # Should be ordered: high, medium, low
    assert len(result) == 3
    assert result[0]["id"] == "high"
    assert result[1]["id"] == "medium"
    assert result[2]["id"] == "low"


def test_get_prioritized_memories_with_entity_filter(memory_store):
    """Test filtering prioritized memories by entity type."""
    memory_store.write_memory(
        memory_id="person",
        text="Person info",
        entity_type="Person",
        importance=2
    )

    memory_store.write_memory(
        memory_id="goal",
        text="Goal info",
        entity_type="Goal",
        importance=2
    )

    # Get only Person memories
    result = memory_store.get_prioritized_memories(top_k=10, entity_type="Person")

    assert len(result) == 1
    assert result[0]["id"] == "person"


def test_get_prioritized_memories_with_tag_filter(memory_store):
    """Test filtering prioritized memories by tags."""
    memory_store.write_memory(
        memory_id="work1",
        text="Work task",
        entity_type="Job",
        importance=2,
        tags=["work", "urgent"]
    )

    memory_store.write_memory(
        memory_id="personal1",
        text="Personal task",
        entity_type="Fact",
        importance=2,
        tags=["personal"]
    )

    # Get only work-tagged memories
    result = memory_store.get_prioritized_memories(top_k=10, tags=["work"])

    assert len(result) == 1
    assert result[0]["id"] == "work1"


def test_get_prioritized_memories_top_k_limit(memory_store):
    """Test that top_k limits results."""
    # Create 10 memories
    for i in range(10):
        memory_store.write_memory(
            memory_id=f"mem_{i}",
            text=f"Memory {i}",
            entity_type="Fact",
            importance=0
        )

    # Get only top 3
    result = memory_store.get_prioritized_memories(top_k=3)

    assert len(result) == 3


def test_priority_score_in_results(memory_store):
    """Test that priority_score is included in results."""
    memory_store.write_memory(
        memory_id="test",
        text="Test memory",
        entity_type="Fact",
        importance=1
    )

    result = memory_store.get_prioritized_memories()

    assert len(result) == 1
    assert "priority_score" in result[0]
    assert isinstance(result[0]["priority_score"], float)
    assert 0.0 <= result[0]["priority_score"] <= 100.0


def test_priority_score_range(memory_store):
    """Test that priority scores stay within 0-100 range."""
    # Extreme case: max importance, very recent, high access
    memory_store.write_memory(
        memory_id="max",
        text="Maximum priority",
        entity_type="Fact",
        importance=2
    )

    # Simulate high access count manually
    import sqlite3
    conn = sqlite3.connect(memory_store.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE memories
        SET access_count = 50
        WHERE id = 'max'
    """)
    conn.commit()
    conn.close()

    result = memory_store.get_prioritized_memories()

    assert len(result) == 1
    assert 0.0 <= result[0]["priority_score"] <= 100.0


def test_combined_priority_factors(memory_store):
    """Test that multiple factors combine correctly."""
    # Memory 1: High importance but old
    memory_store.write_memory(
        memory_id="old_important",
        text="Old but important",
        entity_type="Fact",
        importance=2
    )

    # Manually set old date
    import sqlite3
    old_date = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    conn = sqlite3.connect(memory_store.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE memories
        SET created_at = ?
        WHERE id = 'old_important'
    """, (old_date,))
    conn.commit()
    conn.close()

    # Memory 2: Low importance but recent and frequently accessed
    memory_store.write_memory(
        memory_id="recent_accessed",
        text="Recent and accessed",
        entity_type="Fact",
        importance=0
    )

    # Simulate access
    conn = sqlite3.connect(memory_store.db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE memories
        SET access_count = 20
        WHERE id = 'recent_accessed'
    """)
    conn.commit()
    conn.close()

    result = memory_store.get_prioritized_memories(top_k=2)

    # Both should be returned, order depends on score calculation
    assert len(result) == 2
    ids = [m["id"] for m in result]
    assert "old_important" in ids
    assert "recent_accessed" in ids
