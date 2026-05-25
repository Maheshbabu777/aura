"""
Memory Store - ChromaDB + SQLite wrapper for persistent memory.

Handles:
- Vector storage (ChromaDB) for semantic search
- Metadata storage (SQLite) for structured queries and audit
- CRUD operations for memories
"""

import os
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from loguru import logger


def auto_tag_from_content(text: str, entity_type: str) -> List[str]:
    """
    Automatically suggest tags based on content patterns.

    Args:
        text: Memory text content
        entity_type: The entity type (Person/Goal/Job/Location/Fact)

    Returns:
        List of suggested tags
    """
    tags = []
    text_lower = text.lower()

    # Work-related patterns
    work_keywords = ["work", "job", "company", "office", "meeting", "interview", "project", "colleague"]
    if any(keyword in text_lower for keyword in work_keywords):
        tags.append("work")

    # Personal patterns
    personal_keywords = ["friend", "family", "hobby", "home", "personal"]
    if any(keyword in text_lower for keyword in personal_keywords):
        tags.append("personal")

    # Urgent patterns
    urgent_keywords = ["urgent", "asap", "deadline", "tomorrow", "today", "immediately"]
    if any(keyword in text_lower for keyword in urgent_keywords):
        tags.append("urgent")

    # Important patterns
    important_keywords = ["important", "critical", "priority", "must"]
    if any(keyword in text_lower for keyword in important_keywords):
        tags.append("important")

    # Education patterns
    education_keywords = ["study", "university", "college", "course", "exam", "learn"]
    if any(keyword in text_lower for keyword in education_keywords):
        tags.append("education")

    # Entity type as default tag
    if entity_type == "Goal":
        tags.append("goal")
    elif entity_type == "Job":
        tags.append("career")

    return list(set(tags))  # Remove duplicates


class MemoryStore:
    """Persistent memory storage using ChromaDB for vectors and SQLite for metadata."""

    def __init__(self, persist_dir: str = "./data/memory"):
        """
        Initialize memory store with persistent storage.

        Args:
            persist_dir: Directory for storing ChromaDB and SQLite files
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.persist_dir / "chroma"),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Use sentence-transformers for embeddings (works offline after initial download)
        sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        self.collection = self.chroma_client.get_or_create_collection(
            name="memories",
            embedding_function=sentence_transformer_ef,
            metadata={"hnsw:space": "cosine"}
        )

        # Initialize SQLite for metadata
        self.db_path = self.persist_dir / "metadata.db"
        self._init_sqlite()

        logger.info(f"MemoryStore initialized at {self.persist_dir}")

    def _init_sqlite(self):
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create memories table with FTS5 for full-text search
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                ttl_days INTEGER DEFAULT 365,
                tags TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TEXT,
                importance INTEGER DEFAULT 0,
                metadata TEXT
            )
        """)

        # Create FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(id, text, entity_type, content=memories, content_rowid=rowid)
        """)

        # Create triggers to keep FTS5 in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, id, text, entity_type)
                VALUES (new.rowid, new.id, new.text, new.entity_type);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                DELETE FROM memories_fts WHERE rowid = old.rowid;
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                DELETE FROM memories_fts WHERE rowid = old.rowid;
                INSERT INTO memories_fts(rowid, id, text, entity_type)
                VALUES (new.rowid, new.id, new.text, new.entity_type);
            END
        """)

        conn.commit()
        conn.close()

        logger.debug("SQLite schema initialized")

    def write_memory(
        self,
        memory_id: str,
        text: str,
        entity_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_days: int = 365,
        tags: Optional[List[str]] = None,
        importance: int = 0
    ) -> str:
        """
        Store a new memory.

        Args:
            memory_id: Unique identifier for the memory
            text: The memory content
            entity_type: Type of entity (Person/Goal/Job/Location/Fact)
            metadata: Additional metadata dict
            ttl_days: Time-to-live in days before staleness
            tags: Optional list of tags (e.g., ["work", "personal", "urgent"])
            importance: User-assigned importance (0=normal, 1=important, 2=critical)

        Returns:
            The memory_id
        """
        now = datetime.now(timezone.utc).isoformat()
        tags_str = ",".join(tags) if tags else None

        # Store in ChromaDB for semantic search
        self.collection.add(
            ids=[memory_id],
            documents=[text],
            metadatas=[{
                "entity_type": entity_type,
                "created_at": now,
                "updated_at": now,
                "ttl_days": str(ttl_days),
                "tags": tags_str if tags_str else ""
            }]
        )

        # Store in SQLite for structured queries
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO memories (id, text, entity_type, created_at, updated_at, ttl_days, tags, access_count, last_accessed_at, importance, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id,
            text,
            entity_type,
            now,
            now,
            ttl_days,
            tags_str,
            0,  # access_count
            None,  # last_accessed_at
            importance,
            str(metadata) if metadata else None
        ))

        conn.commit()
        conn.close()

        logger.info(f"Memory stored: {memory_id} ({entity_type}) tags={tags}")
        return memory_id

    def search_memory(
        self,
        query: str,
        top_k: int = 5,
        entity_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories by semantic similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            entity_type: Optional filter by entity type

        Returns:
            List of memory dicts with id, text, metadata, distance
        """
        # Build where clause for entity type filter
        where = {"entity_type": entity_type} if entity_type else None

        # Search ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where
        )

        # Format results with staleness check
        memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                memory = {
                    "id": memory_id,
                    "text": results["documents"][0][i],
                    "metadata": metadata,
                    "distance": results["distances"][0][i] if "distances" in results else None
                }

                # Add staleness flag
                memory["is_stale"] = self.is_stale({
                    "created_at": metadata["created_at"],
                    "ttl_days": int(metadata["ttl_days"])
                })

                memories.append(memory)

        logger.debug(f"Search query: '{query}' -> {len(memories)} results")
        return memories

    def get_memory(self, memory_id: str, track_access: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a specific memory by ID.

        Args:
            memory_id: The memory identifier
            track_access: If True, increment access count and update last_accessed_at

        Returns:
            Memory dict or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, text, entity_type, created_at, updated_at, ttl_days, tags, access_count, last_accessed_at, importance, metadata
            FROM memories WHERE id = ?
        """, (memory_id,))

        row = cursor.fetchone()

        if row and track_access:
            # Update access tracking
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                UPDATE memories
                SET access_count = access_count + 1, last_accessed_at = ?
                WHERE id = ?
            """, (now, memory_id))
            conn.commit()

        conn.close()

        if row:
            return dict(row)
        return None

    def update_memory(
        self,
        memory_id: str,
        text: Optional[str] = None,
        entity_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update an existing memory.

        Args:
            memory_id: The memory identifier
            text: New text content (optional)
            entity_type: New entity type (optional)
            metadata: New metadata (optional)

        Returns:
            True if updated, False if not found
        """
        # Get existing memory
        existing = self.get_memory(memory_id)
        if not existing:
            logger.warning(f"Memory not found: {memory_id}")
            return False

        now = datetime.now(timezone.utc).isoformat()

        # Update ChromaDB
        updated_text = text if text is not None else existing["text"]
        updated_entity_type = entity_type if entity_type is not None else existing["entity_type"]

        self.collection.update(
            ids=[memory_id],
            documents=[updated_text],
            metadatas=[{
                "entity_type": updated_entity_type,
                "created_at": existing["created_at"],
                "updated_at": now,
                "ttl_days": str(existing["ttl_days"])
            }]
        )

        # Update SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE memories
            SET text = ?, entity_type = ?, updated_at = ?, metadata = ?
            WHERE id = ?
        """, (
            updated_text,
            updated_entity_type,
            now,
            str(metadata) if metadata else existing["metadata"],
            memory_id
        ))

        conn.commit()
        conn.close()

        logger.info(f"Memory updated: {memory_id}")
        return True

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            memory_id: The memory identifier

        Returns:
            True if deleted, False if not found
        """
        try:
            # Delete from ChromaDB
            self.collection.delete(ids=[memory_id])

            # Delete from SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            conn.close()

            logger.info(f"Memory deleted: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return False

    def count_memories(self, entity_type: Optional[str] = None) -> int:
        """
        Count total memories, optionally filtered by entity type.

        Args:
            entity_type: Optional filter by entity type

        Returns:
            Count of memories
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if entity_type:
            cursor.execute("SELECT COUNT(*) FROM memories WHERE entity_type = ?", (entity_type,))
        else:
            cursor.execute("SELECT COUNT(*) FROM memories")

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def is_stale(self, memory: Dict[str, Any]) -> bool:
        """
        Check if a memory is stale based on TTL.

        Args:
            memory: Memory dict with created_at and ttl_days

        Returns:
            True if memory is past TTL, False otherwise
        """
        created_at = datetime.fromisoformat(memory["created_at"])
        ttl_days = memory.get("ttl_days", 365)
        now = datetime.now(timezone.utc)

        age_days = (now - created_at).days
        return age_days > ttl_days

    def get_stale_memories(self, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all stale memories (past their TTL).

        Args:
            entity_type: Optional filter by entity type

        Returns:
            List of stale memory dicts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if entity_type:
            cursor.execute("""
                SELECT id, text, entity_type, created_at, updated_at, ttl_days, tags, access_count, last_accessed_at, importance, metadata
                FROM memories WHERE entity_type = ?
            """, (entity_type,))
        else:
            cursor.execute("""
                SELECT id, text, entity_type, created_at, updated_at, ttl_days, tags, access_count, last_accessed_at, importance, metadata
                FROM memories
            """)

        rows = cursor.fetchall()
        conn.close()

        # Filter to only stale memories
        stale_memories = []
        for row in rows:
            memory = dict(row)
            if self.is_stale(memory):
                stale_memories.append(memory)

        logger.debug(f"Found {len(stale_memories)} stale memories")
        return stale_memories

    def search_by_tags(
        self,
        tags: List[str],
        match_all: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search memories by tags.

        Args:
            tags: List of tags to search for
            match_all: If True, memory must have ALL tags. If False, ANY tag matches.

        Returns:
            List of memory dicts matching tag criteria
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, text, entity_type, created_at, updated_at, ttl_days, tags, access_count, last_accessed_at, importance, metadata
            FROM memories
        """)

        rows = cursor.fetchall()
        conn.close()

        # Filter by tags
        matching_memories = []
        for row in rows:
            memory = dict(row)
            memory_tags = set(memory["tags"].split(",")) if memory["tags"] else set()

            if match_all:
                # Memory must have ALL requested tags
                if set(tags).issubset(memory_tags):
                    matching_memories.append(memory)
            else:
                # Memory must have ANY of the requested tags
                if any(tag in memory_tags for tag in tags):
                    matching_memories.append(memory)

        logger.debug(f"Found {len(matching_memories)} memories with tags {tags}")
        return matching_memories

    def add_tags(self, memory_id: str, new_tags: List[str]) -> bool:
        """
        Add tags to an existing memory.

        Args:
            memory_id: The memory identifier
            new_tags: List of tags to add

        Returns:
            True if successful, False if memory not found
        """
        memory = self.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return False

        # Get existing tags
        existing_tags = set(memory["tags"].split(",")) if memory.get("tags") else set()
        existing_tags.update(new_tags)
        updated_tags_str = ",".join(sorted(existing_tags))

        now = datetime.now(timezone.utc).isoformat()

        # Update ChromaDB
        self.collection.update(
            ids=[memory_id],
            metadatas=[{
                "entity_type": memory["entity_type"],
                "created_at": memory["created_at"],
                "updated_at": now,
                "ttl_days": str(memory["ttl_days"]),
                "tags": updated_tags_str
            }]
        )

        # Update SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE memories
            SET tags = ?, updated_at = ?
            WHERE id = ?
        """, (updated_tags_str, now, memory_id))

        conn.commit()
        conn.close()

        logger.info(f"Added tags to {memory_id}: {new_tags}")
        return True

    def remove_tags(self, memory_id: str, tags_to_remove: List[str]) -> bool:
        """
        Remove tags from an existing memory.

        Args:
            memory_id: The memory identifier
            tags_to_remove: List of tags to remove

        Returns:
            True if successful, False if memory not found
        """
        memory = self.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return False

        # Get existing tags and remove specified ones
        existing_tags = set(memory["tags"].split(",")) if memory.get("tags") else set()
        existing_tags.difference_update(tags_to_remove)
        updated_tags_str = ",".join(sorted(existing_tags)) if existing_tags else None

        now = datetime.now(timezone.utc).isoformat()

        # Update ChromaDB
        self.collection.update(
            ids=[memory_id],
            metadatas=[{
                "entity_type": memory["entity_type"],
                "created_at": memory["created_at"],
                "updated_at": now,
                "ttl_days": str(memory["ttl_days"]),
                "tags": updated_tags_str if updated_tags_str else ""
            }]
        )

        # Update SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE memories
            SET tags = ?, updated_at = ?
            WHERE id = ?
        """, (updated_tags_str, now, memory_id))

        conn.commit()
        conn.close()

        logger.info(f"Removed tags from {memory_id}: {tags_to_remove}")
        return True

    def find_duplicates(
        self,
        memory_id: str,
        similarity_threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Find memories that are very similar to the given memory.

        Args:
            memory_id: The memory to check for duplicates
            similarity_threshold: Cosine similarity threshold (0-1, higher = more similar)
                                Default 0.95 means 95% similar

        Returns:
            List of similar memories with similarity scores
        """
        # Get the memory
        memory = self.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return []

        # Search for similar memories using ChromaDB
        results = self.collection.query(
            query_texts=[memory["text"]],
            n_results=10  # Get top 10 most similar
        )

        # Filter by similarity threshold and exclude self
        duplicates = []
        if results["ids"] and results["ids"][0]:
            for i, found_id in enumerate(results["ids"][0]):
                if found_id == memory_id:
                    continue  # Skip self

                distance = results["distances"][0][i] if "distances" in results else 0
                # ChromaDB uses cosine distance, convert to similarity
                # similarity = 1 - distance (for normalized vectors)
                similarity = 1 - distance

                if similarity >= similarity_threshold:
                    duplicates.append({
                        "id": found_id,
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "similarity": similarity
                    })

        logger.debug(f"Found {len(duplicates)} duplicates for {memory_id}")
        return duplicates

    def find_all_duplicates(
        self,
        similarity_threshold: float = 0.95
    ) -> List[Dict[str, Any]]:
        """
        Find all duplicate pairs across the entire memory store.

        Args:
            similarity_threshold: Cosine similarity threshold

        Returns:
            List of duplicate pairs: [{"memory1": {...}, "memory2": {...}, "similarity": 0.96}, ...]
        """
        # Get all memories
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM memories")
        rows = cursor.fetchall()
        conn.close()

        memory_ids = [row["id"] for row in rows]

        # Track which pairs we've already checked
        checked_pairs = set()
        duplicate_pairs = []

        for memory_id in memory_ids:
            duplicates = self.find_duplicates(memory_id, similarity_threshold)

            for dup in duplicates:
                # Create sorted pair to avoid checking same pair twice
                pair_key = tuple(sorted([memory_id, dup["id"]]))

                if pair_key not in checked_pairs:
                    checked_pairs.add(pair_key)

                    memory1 = self.get_memory(memory_id)
                    memory2 = self.get_memory(dup["id"])

                    duplicate_pairs.append({
                        "memory1": memory1,
                        "memory2": memory2,
                        "similarity": dup["similarity"]
                    })

        logger.info(f"Found {len(duplicate_pairs)} duplicate pairs")
        return duplicate_pairs

    def merge_memories(
        self,
        primary_id: str,
        duplicate_id: str,
        merge_tags: bool = True
    ) -> bool:
        """
        Merge two similar memories by combining their info and deleting the duplicate.

        Args:
            primary_id: The memory to keep
            duplicate_id: The memory to merge into primary and then delete
            merge_tags: If True, combine tags from both memories

        Returns:
            True if successful, False otherwise
        """
        # Can't merge memory with itself
        if primary_id == duplicate_id:
            logger.warning(f"Cannot merge memory with itself: {primary_id}")
            return False

        primary = self.get_memory(primary_id)
        duplicate = self.get_memory(duplicate_id)

        if not primary or not duplicate:
            logger.warning(f"Cannot merge: memories not found")
            return False

        # Merge tags if requested
        if merge_tags:
            primary_tags = set(primary["tags"].split(",")) if primary.get("tags") else set()
            duplicate_tags = set(duplicate["tags"].split(",")) if duplicate.get("tags") else set()

            merged_tags = primary_tags.union(duplicate_tags)
            merged_tags.discard("")  # Remove empty strings

            if merged_tags:
                self.add_tags(primary_id, list(merged_tags))

        # Delete the duplicate
        success = self.delete_memory(duplicate_id)

        if success:
            logger.info(f"Merged {duplicate_id} into {primary_id}")
            return True

        return False

    def set_importance(self, memory_id: str, importance: int) -> bool:
        """
        Set the importance level of a memory.

        Args:
            memory_id: The memory identifier
            importance: Importance level (0=normal, 1=important, 2=critical)

        Returns:
            True if successful, False if not found
        """
        memory = self.get_memory(memory_id)
        if not memory:
            logger.warning(f"Memory not found: {memory_id}")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE memories
            SET importance = ?
            WHERE id = ?
        """, (importance, memory_id))

        conn.commit()
        conn.close()

        logger.info(f"Set importance for {memory_id}: {importance}")
        return True

    def calculate_priority_score(self, memory: Dict[str, Any]) -> float:
        """
        Calculate priority score for a memory based on multiple factors.

        Score components:
        - Importance: 0-40 points (user-marked: 0=0pts, 1=20pts, 2=40pts)
        - Recency: 0-30 points (newer = higher)
        - Access frequency: 0-20 points (more accessed = higher)
        - Staleness penalty: -10 points if stale

        Args:
            memory: Memory dict with all fields

        Returns:
            Priority score (0-100, higher = more important)
        """
        score = 0.0

        # Importance factor (0-40 points)
        importance = memory.get("importance", 0)
        score += importance * 20  # 0=0pts, 1=20pts, 2=40pts

        # Recency factor (0-30 points)
        created_at = datetime.fromisoformat(memory["created_at"])
        now = datetime.now(timezone.utc)
        age_days = (now - created_at).days

        if age_days < 7:
            score += 30  # Very recent
        elif age_days < 30:
            score += 20  # Recent
        elif age_days < 90:
            score += 10  # Somewhat recent
        # Else: 0 points for old memories

        # Access frequency factor (0-20 points)
        access_count = memory.get("access_count", 0)
        if access_count >= 10:
            score += 20
        elif access_count >= 5:
            score += 15
        elif access_count >= 2:
            score += 10
        elif access_count >= 1:
            score += 5

        # Staleness penalty (-10 points)
        if self.is_stale(memory):
            score -= 10

        # Ensure score stays in reasonable range
        return max(0.0, min(100.0, score))

    def get_prioritized_memories(
        self,
        top_k: int = 10,
        entity_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get memories sorted by priority score.

        Args:
            top_k: Number of top memories to return
            entity_type: Optional filter by entity type
            tags: Optional filter by tags

        Returns:
            List of memories with priority_score field, sorted highest to lowest
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with optional filters
        query = """
            SELECT id, text, entity_type, created_at, updated_at, ttl_days, tags, access_count, last_accessed_at, importance, metadata
            FROM memories
        """
        params = []

        if entity_type:
            query += " WHERE entity_type = ?"
            params.append(entity_type)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Filter by tags if specified
        memories = []
        for row in rows:
            memory = dict(row)

            if tags:
                memory_tags = set(memory["tags"].split(",")) if memory["tags"] else set()
                if not any(tag in memory_tags for tag in tags):
                    continue

            # Calculate priority score
            memory["priority_score"] = self.calculate_priority_score(memory)
            memories.append(memory)

        # Sort by priority score (highest first)
        memories.sort(key=lambda m: m["priority_score"], reverse=True)

        # Return top K
        result = memories[:top_k]
        logger.debug(f"Retrieved {len(result)} prioritized memories")
        return result

    def reset(self):
        """Delete all memories. Use with caution."""
        self.collection.delete(where={})

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()
        conn.close()

        logger.warning("All memories deleted")
