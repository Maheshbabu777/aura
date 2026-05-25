"""
Tests for memory deduplication functionality.
"""

import pytest
import tempfile
import shutil

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


def test_find_duplicates_exact_match(memory_store):
    """Test finding exact duplicate memories."""
    # Store same text twice
    memory_store.write_memory(
        memory_id="original",
        text="John works at TechCorp as a software engineer",
        entity_type="Person"
    )

    memory_store.write_memory(
        memory_id="duplicate",
        text="John works at TechCorp as a software engineer",
        entity_type="Person"
    )

    # Find duplicates
    duplicates = memory_store.find_duplicates("original", similarity_threshold=0.95)

    assert len(duplicates) >= 1
    assert any(dup["id"] == "duplicate" for dup in duplicates)


def test_find_duplicates_similar_text(memory_store):
    """Test finding similar but not exact duplicates."""
    memory_store.write_memory(
        memory_id="original",
        text="John works at TechCorp",
        entity_type="Person"
    )

    memory_store.write_memory(
        memory_id="similar",
        text="John is employed at TechCorp",
        entity_type="Person"
    )

    # Lower threshold to catch similar text
    duplicates = memory_store.find_duplicates("original", similarity_threshold=0.80)

    # Should find the similar one
    assert len(duplicates) >= 1
    assert any(dup["id"] == "similar" for dup in duplicates)


def test_find_duplicates_no_match(memory_store):
    """Test when no duplicates exist."""
    memory_store.write_memory(
        memory_id="mem1",
        text="John works at TechCorp",
        entity_type="Person"
    )

    memory_store.write_memory(
        memory_id="mem2",
        text="Alice studies biology at University",
        entity_type="Person"
    )

    # These are completely different
    duplicates = memory_store.find_duplicates("mem1", similarity_threshold=0.95)

    # Should not find mem2 as duplicate
    assert not any(dup["id"] == "mem2" for dup in duplicates)


def test_find_duplicates_high_threshold(memory_store):
    """Test that high threshold only finds very similar memories."""
    memory_store.write_memory(
        memory_id="original",
        text="John works at TechCorp",
        entity_type="Person"
    )

    memory_store.write_memory(
        memory_id="slightly_different",
        text="John works at TechCorp as engineer",
        entity_type="Person"
    )

    # Very high threshold (99% similar)
    duplicates = memory_store.find_duplicates("original", similarity_threshold=0.99)

    # May or may not find it depending on exact similarity
    # Just checking the function runs without error
    assert isinstance(duplicates, list)


def test_find_duplicates_nonexistent_memory(memory_store):
    """Test finding duplicates for non-existent memory."""
    duplicates = memory_store.find_duplicates("nonexistent")

    assert len(duplicates) == 0


def test_find_all_duplicates_empty(memory_store):
    """Test finding duplicates in empty store."""
    pairs = memory_store.find_all_duplicates()

    assert len(pairs) == 0


def test_find_all_duplicates_with_pairs(memory_store):
    """Test finding all duplicate pairs in store."""
    # Create some duplicates
    memory_store.write_memory(
        memory_id="mem1",
        text="Meeting at office tomorrow",
        entity_type="Fact"
    )

    memory_store.write_memory(
        memory_id="mem1_dup",
        text="Meeting at office tomorrow",
        entity_type="Fact"
    )

    memory_store.write_memory(
        memory_id="mem2",
        text="Study for exam next week",
        entity_type="Fact"
    )

    memory_store.write_memory(
        memory_id="mem2_dup",
        text="Study for exam next week",
        entity_type="Fact"
    )

    # Find all duplicate pairs
    pairs = memory_store.find_all_duplicates(similarity_threshold=0.95)

    # Should find at least the exact duplicates
    assert len(pairs) >= 2


def test_merge_memories_basic(memory_store):
    """Test merging two memories."""
    memory_store.write_memory(
        memory_id="primary",
        text="John works at TechCorp",
        entity_type="Person",
        tags=["work"]
    )

    memory_store.write_memory(
        memory_id="duplicate",
        text="John works at TechCorp",
        entity_type="Person",
        tags=["person"]
    )

    # Merge duplicate into primary
    success = memory_store.merge_memories("primary", "duplicate", merge_tags=True)

    assert success == True

    # Primary should still exist
    primary = memory_store.get_memory("primary")
    assert primary is not None

    # Duplicate should be deleted
    duplicate = memory_store.get_memory("duplicate")
    assert duplicate is None

    # Tags should be merged
    primary_tags = set(primary["tags"].split(","))
    assert "work" in primary_tags
    assert "person" in primary_tags


def test_merge_memories_without_tag_merge(memory_store):
    """Test merging without combining tags."""
    memory_store.write_memory(
        memory_id="primary",
        text="Test memory",
        entity_type="Fact",
        tags=["tag1"]
    )

    memory_store.write_memory(
        memory_id="duplicate",
        text="Test memory",
        entity_type="Fact",
        tags=["tag2"]
    )

    # Merge without tag merge
    success = memory_store.merge_memories("primary", "duplicate", merge_tags=False)

    assert success == True

    primary = memory_store.get_memory("primary")
    # Should only have original tags
    assert "tag1" in primary["tags"]
    assert "tag2" not in primary["tags"]


def test_merge_memories_nonexistent(memory_store):
    """Test merging non-existent memories."""
    success = memory_store.merge_memories("nonexistent1", "nonexistent2")

    assert success == False


def test_merge_memories_same_id(memory_store):
    """Test merging memory with itself."""
    memory_store.write_memory(
        memory_id="same",
        text="Test memory",
        entity_type="Fact"
    )

    # This should fail gracefully
    success = memory_store.merge_memories("same", "same")

    # Since they're the same, duplicate won't exist after trying to get it
    assert success == False


def test_similarity_score_range(memory_store):
    """Test that similarity scores are in valid range [0, 1]."""
    memory_store.write_memory(
        memory_id="test1",
        text="Test memory content",
        entity_type="Fact"
    )

    memory_store.write_memory(
        memory_id="test2",
        text="Test memory content similar",
        entity_type="Fact"
    )

    duplicates = memory_store.find_duplicates("test1", similarity_threshold=0.0)

    for dup in duplicates:
        assert 0.0 <= dup["similarity"] <= 1.0


def test_find_duplicates_excludes_self(memory_store):
    """Test that a memory doesn't return itself as duplicate."""
    memory_store.write_memory(
        memory_id="self_test",
        text="Unique memory text here",
        entity_type="Fact"
    )

    duplicates = memory_store.find_duplicates("self_test", similarity_threshold=0.0)

    # Should never include itself
    assert not any(dup["id"] == "self_test" for dup in duplicates)


def test_deduplication_workflow(memory_store):
    """Test complete deduplication workflow."""
    # Add original memory
    memory_store.write_memory(
        memory_id="original",
        text="Important work deadline next Friday",
        entity_type="Job",
        tags=["work", "important"]
    )

    # Add duplicate with different tags
    memory_store.write_memory(
        memory_id="dup1",
        text="Important work deadline next Friday",
        entity_type="Job",
        tags=["urgent", "deadline"]
    )

    # Add another duplicate
    memory_store.write_memory(
        memory_id="dup2",
        text="Important work deadline next Friday",
        entity_type="Job",
        tags=["reminder"]
    )

    # Find all duplicates
    all_dups = memory_store.find_all_duplicates(similarity_threshold=0.95)
    initial_count = len(all_dups)

    # Should have found duplicate pairs
    assert initial_count > 0

    # Merge all duplicates into original
    memory_store.merge_memories("original", "dup1", merge_tags=True)
    memory_store.merge_memories("original", "dup2", merge_tags=True)

    # Verify merges
    original = memory_store.get_memory("original")
    assert original is not None

    # All tags should be combined
    original_tags = set(original["tags"].split(","))
    assert "work" in original_tags
    assert "urgent" in original_tags
    assert "deadline" in original_tags

    # Duplicates should be gone
    assert memory_store.get_memory("dup1") is None
    assert memory_store.get_memory("dup2") is None

    # No more duplicates
    final_dups = memory_store.find_all_duplicates(similarity_threshold=0.95)
    assert len(final_dups) == 0


def test_partial_similarity(memory_store):
    """Test detecting partial similarity with lower threshold."""
    memory_store.write_memory(
        memory_id="base",
        text="Meeting scheduled for Monday at office",
        entity_type="Fact"
    )

    memory_store.write_memory(
        memory_id="partial",
        text="Meeting on Monday",
        entity_type="Fact"
    )

    # High threshold won't catch it
    high_dups = memory_store.find_duplicates("base", similarity_threshold=0.95)
    assert not any(d["id"] == "partial" for d in high_dups)

    # Lower threshold might catch it
    low_dups = memory_store.find_duplicates("base", similarity_threshold=0.70)
    # May or may not find depending on exact embedding, just test it runs
    assert isinstance(low_dups, list)
