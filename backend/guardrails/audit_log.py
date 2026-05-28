"""
Audit Log database for tracking AURA's actions.
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

from backend.config.settings import settings


class AuditLog:
    """Manages persistent logging of all actions taken by AURA."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.audit_log_path
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database schema."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS actions (
            id TEXT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            action_name TEXT NOT NULL,
            category TEXT NOT NULL,
            reasoning TEXT,
            payload TEXT,
            status TEXT NOT NULL
        )
        ''')
        
        # Index for faster retrieval of pending actions or recent history
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON actions(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON actions(timestamp DESC)')

        conn.commit()
        conn.close()

    def log_action(
        self, 
        action_name: str, 
        category: str, 
        reasoning: str, 
        payload: Dict[str, Any], 
        status: str,
        action_id: Optional[str] = None
    ) -> str:
        """
        Log a new action or update an existing one.

        Args:
            action_name: Name of the action (e.g., 'send_email')
            category: GREEN, YELLOW, or RED
            reasoning: Why this action was classified this way
            payload: Arguments for the action
            status: 'pending', 'approved', 'rejected', 'executed', 'blocked'
            action_id: Optional UUID (if updating an existing action, else generates new)

        Returns:
            The UUID of the action
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(payload)

        if action_id:
            # Update existing
            cursor.execute('''
            UPDATE actions 
            SET status = ?, timestamp = ?
            WHERE id = ?
            ''', (status, timestamp, action_id))
            
            if cursor.rowcount == 0:
                logger.warning(f"Attempted to update non-existent action ID: {action_id}")
                
        else:
            # Insert new
            action_id = str(uuid.uuid4())
            cursor.execute('''
            INSERT INTO actions (id, timestamp, action_name, category, reasoning, payload, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (action_id, timestamp, action_name, category, reasoning, payload_str, status))

        conn.commit()
        conn.close()
        return action_id

    def update_status(self, action_id: str, new_status: str) -> bool:
        """Update just the status of an existing action."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        cursor.execute('''
        UPDATE actions 
        SET status = ?, timestamp = ?
        WHERE id = ?
        ''', (new_status, timestamp, action_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific action by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM actions WHERE id = ?', (action_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            result = dict(row)
            result['payload'] = json.loads(result['payload'])
            return result
        return None

    def get_actions_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Retrieve all actions with a specific status."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM actions WHERE status = ? ORDER BY timestamp DESC', (status,))
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            action = dict(row)
            action['payload'] = json.loads(action['payload'])
            results.append(action)
            
        return results

    def get_action_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve paginated action history."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
        SELECT * FROM actions 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            action = dict(row)
            action['payload'] = json.loads(action['payload'])
            results.append(action)
            
        return results

# Singleton instance
audit_log = AuditLog()
