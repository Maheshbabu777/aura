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
        ttl_days: int = 365
    ) -> str:
        """
        Store a new memory.

        Args:
            memory_id: Unique identifier for the memory
            text: The memory content
            entity_type: Type of entity (Person/Goal/Job/Location/Fact)
            metadata: Additional metadata dict
            ttl_days: Time-to-live in days before staleness

        Returns:
            The memory_id
        """
        now = datetime.now(timezone.utc).isoformat()

        # Store in ChromaDB for semantic search
        self.collection.add(
            ids=[memory_id],
            documents=[text],
            metadatas=[{
                "entity_type": entity_type,
                "created_at": now,
                "updated_at": now,
                "ttl_days": str(ttl_days)
            }]
        )

        # Store in SQLite for structured queries
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO memories (id, text, entity_type, created_at, updated_at, ttl_days, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id,
            text,
            entity_type,
            now,
            now,
            ttl_days,
            str(metadata) if metadata else None
        ))

        conn.commit()
        conn.close()

        logger.info(f"Memory stored: {memory_id} ({entity_type})")
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

        # Format results
        memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                memories.append({
                    "id": memory_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else None
                })

        logger.debug(f"Search query: '{query}' -> {len(memories)} results")
        return memories

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific memory by ID.

        Args:
            memory_id: The memory identifier

        Returns:
            Memory dict or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, text, entity_type, created_at, updated_at, ttl_days, metadata
            FROM memories WHERE id = ?
        """, (memory_id,))

        row = cursor.fetchone()
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

    def reset(self):
        """Delete all memories. Use with caution."""
        self.collection.delete(where={})

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories")
        conn.commit()
        conn.close()

        logger.warning("All memories deleted")
