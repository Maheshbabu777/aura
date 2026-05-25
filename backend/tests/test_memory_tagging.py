"""
Tests for memory tagging functionality.
"""

import pytest
import tempfile
import shutil

from backend.memory.store import MemoryStore, auto_tag_from_content


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


def test_write_memory_with_tags(memory_store):
    """Test storing memory with tags."""
    memory_store.write_memory(
        memory_id="tagged_001",
        text="Meeting with John at TechCorp",
        entity_type="Job",
        tags=["work", "meeting", "important"]
    )

    memory = memory_store.get_memory("tagged_001")

    assert memory is not None
    # Check tags are present (order may vary)
    tags = set(memory["tags"].split(","))
    assert "work" in tags
    assert "meeting" in tags
    assert "important" in tags


def test_write_memory_without_tags(memory_store):
    """Test storing memory without tags."""
    memory_store.write_memory(
        memory_id="untagged_001",
        text="Random fact about Python",
        entity_type="Fact"
    )

    memory = memory_store.get_memory("untagged_001")

    assert memory is not None
    assert memory["tags"] is None or memory["tags"] == ""


def test_search_by_tags_any(memory_store):
    """Test searching memories by tags (ANY match)."""
    # Create memories with different tags
    memory_store.write_memory(
        memory_id="work_001",
        text="Work project",
        entity_type="Job",
        tags=["work", "project"]
    )

    memory_store.write_memory(
        memory_id="personal_001",
        text="Personal hobby",
        entity_type="Fact",
        tags=["personal", "hobby"]
    )

    memory_store.write_memory(
        memory_id="work_personal_001",
        text="Work-life balance goal",
        entity_type="Goal",
        tags=["work", "personal"]
    )

    # Search for work OR personal (should find all 3)
    results = memory_store.search_by_tags(["work", "personal"], match_all=False)

    assert len(results) == 3


def test_search_by_tags_all(memory_store):
    """Test searching memories by tags (ALL match)."""
    memory_store.write_memory(
        memory_id="work_urgent",
        text="Urgent work deadline",
        entity_type="Job",
        tags=["work", "urgent"]
    )

    memory_store.write_memory(
        memory_id="work_only",
        text="Regular work task",
        entity_type="Job",
        tags=["work"]
    )

    # Search for work AND urgent (should find only 1)
    results = memory_store.search_by_tags(["work", "urgent"], match_all=True)

    assert len(results) == 1
    assert results[0]["id"] == "work_urgent"


def test_add_tags_to_memory(memory_store):
    """Test adding tags to existing memory."""
    memory_store.write_memory(
        memory_id="add_tags_test",
        text="Test memory",
        entity_type="Fact",
        tags=["initial"]
    )

    # Add more tags
    success = memory_store.add_tags("add_tags_test", ["new", "tags"])

    assert success == True

    memory = memory_store.get_memory("add_tags_test")
    tags = set(memory["tags"].split(","))

    assert "initial" in tags
    assert "new" in tags
    assert "tags" in tags


def test_remove_tags_from_memory(memory_store):
    """Test removing tags from existing memory."""
    memory_store.write_memory(
        memory_id="remove_tags_test",
        text="Test memory",
        entity_type="Fact",
        tags=["tag1", "tag2", "tag3"]
    )

    # Remove some tags
    success = memory_store.remove_tags("remove_tags_test", ["tag2"])

    assert success == True

    memory = memory_store.get_memory("remove_tags_test")
    tags = set(memory["tags"].split(","))

    assert "tag1" in tags
    assert "tag2" not in tags
    assert "tag3" in tags


def test_add_tags_nonexistent_memory(memory_store):
    """Test adding tags to non-existent memory."""
    success = memory_store.add_tags("nonexistent", ["tag"])

    assert success == False


def test_remove_tags_nonexistent_memory(memory_store):
    """Test removing tags from non-existent memory."""
    success = memory_store.remove_tags("nonexistent", ["tag"])

    assert success == False


def test_auto_tag_work_content():
    """Test auto-tagging for work-related content."""
    tags = auto_tag_from_content(
        "Meeting with team at company office about project",
        entity_type="Job"
    )

    assert "work" in tags
    assert "career" in tags


def test_auto_tag_personal_content():
    """Test auto-tagging for personal content."""
    tags = auto_tag_from_content(
        "Visit family and friends this weekend",
        entity_type="Fact"
    )

    assert "personal" in tags


def test_auto_tag_urgent_content():
    """Test auto-tagging for urgent content."""
    tags = auto_tag_from_content(
        "Urgent deadline tomorrow, must complete ASAP",
        entity_type="Job"
    )

    assert "urgent" in tags
    assert "career" in tags  # Job entity type gives "career" tag


def test_auto_tag_education_content():
    """Test auto-tagging for education content."""
    tags = auto_tag_from_content(
        "Study for university exam next week",
        entity_type="Fact"
    )

    assert "education" in tags


def test_auto_tag_goal_entity():
    """Test auto-tagging for Goal entity type."""
    tags = auto_tag_from_content(
        "Want to learn Python programming",
        entity_type="Goal"
    )

    assert "goal" in tags


def test_search_by_tags_empty_results(memory_store):
    """Test searching for tags that don't exist."""
    memory_store.write_memory(
        memory_id="test_001",
        text="Test memory",
        entity_type="Fact",
        tags=["tag1"]
    )

    results = memory_store.search_by_tags(["nonexistent_tag"])

    assert len(results) == 0


def test_tags_persist_across_updates(memory_store):
    """Test that tags are preserved when updating memory text."""
    memory_store.write_memory(
        memory_id="persist_tags",
        text="Original text",
        entity_type="Fact",
        tags=["important", "work"]
    )

    # Update the text (existing update_memory doesn't change tags)
    memory_store.update_memory(
        memory_id="persist_tags",
        text="Updated text"
    )

    memory = memory_store.get_memory("persist_tags")

    # Tags should still be there
    assert "important" in memory["tags"]
    assert "work" in memory["tags"]


def test_multiple_tags_handling(memory_store):
    """Test handling memories with many tags."""
    many_tags = ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]

    memory_store.write_memory(
        memory_id="many_tags",
        text="Memory with many tags",
        entity_type="Fact",
        tags=many_tags
    )

    memory = memory_store.get_memory("many_tags")
    stored_tags = set(memory["tags"].split(","))

    assert len(stored_tags) == 6
    for tag in many_tags:
        assert tag in stored_tags
