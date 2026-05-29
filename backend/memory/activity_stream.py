"""
Activity Stream: A high-performance, centralized event log for AURA.
Used to instantly retrieve exactly what happened today without heavy querying.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from backend.config.settings import settings


class ActivityStream:
    """Manages the daily_logs table for blazing-fast status retrievals."""

    def __init__(self, db_path: Optional[str] = None):
        # We store this in the sqlite memory.db
        self.db_path = db_path or settings.sqlite_db_path
        self._init_db()

    def _init_db(self):
        """Initialize the activity stream schema."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # date_only allows us to do lightning fast "WHERE date = today"
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            id TEXT PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            date_only TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            description TEXT NOT NULL
        )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_date_only ON daily_logs(date_only)')
        conn.commit()
        conn.close()

    def log(self, agent_name: str, description: str) -> str:
        """
        Log a new activity.
        
        Args:
            agent_name: Which agent did this (e.g., 'GoalAgent')
            description: Human readable summary (e.g., 'Completed task: Read Chapter 4')
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc)
        log_id = str(uuid.uuid4())
        timestamp = now.isoformat()
        date_only = now.strftime("%Y-%m-%d")

        cursor.execute('''
        INSERT INTO daily_logs (id, timestamp, date_only, agent_name, description)
        VALUES (?, ?, ?, ?, ?)
        ''', (log_id, timestamp, date_only, agent_name, description))

        conn.commit()
        conn.close()
        
        logger.debug(f"Activity logged [{agent_name}]: {description}")
        return log_id

    def get_today_logs(self) -> List[Dict[str, Any]]:
        """Retrieve all activity logs for the current day."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.get_logs_by_date(today)

    def get_logs_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Retrieve all activity logs for a specific YYYY-MM-DD."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
        SELECT agent_name, timestamp, description 
        FROM daily_logs 
        WHERE date_only = ? 
        ORDER BY timestamp ASC
        ''', (date_str,))
        
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]


# Singleton instance
activity_stream = ActivityStream()
