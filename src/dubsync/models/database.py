"""
DubSync Database

SQLite database handler and initializer.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Any, Dict
from contextlib import contextmanager
import json

from dubsync.utils.constants import DB_VERSION


class Database:
    """
    SQLite database handler class.
    
    The project stores all data in a single file.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the database.
        
        Args:
            db_path: Path to the database file. If None, in-memory.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        
    @property
    def connection(self) -> sqlite3.Connection:
        """
        Get or create the database connection.
        """
        if self._connection is None:
            db_str = str(self.db_path) if self.db_path else ":memory:"
            self._connection = sqlite3.connect(db_str)
            self._connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection
    
    @contextmanager
    def cursor(self):
        """
        Context manager for cursor handling.
        """
        cur = self.connection.cursor()
        try:
            yield cur
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cur.close()
    
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute an SQL command.
        """
        return self.connection.execute(sql, params)
    
    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """
        Execute an SQL command with multiple parameter sets.
        """
        return self.connection.executemany(sql, params_list)
    
    def commit(self):
        """
        Commit changes.
        """
        self.connection.commit()
    
    def rollback(self):
        """
        Rollback changes.
        """
        self.connection.rollback()
    
    def close(self):
        """
        Close the connection.
        """
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Fetch a single row.
        """
        return self.execute(sql, params).fetchone()
    
    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Fetch all rows.
        """
        return self.execute(sql, params).fetchall()
    
    def get_version(self) -> int:
        """
        Get database version.
        """
        try:
            row = self.fetchone("SELECT value FROM metadata WHERE key = 'db_version'")
            return int(row["value"]) if row else 0
        except sqlite3.OperationalError:
            return 0


def init_database(db: Database) -> None:
    """
    Initialize the database schema.
    
    Creates all necessary tables and indexes.
    """
    schema = """
    -- Metadata table for version tracking and project settings
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    
    -- Project information
    CREATE TABLE IF NOT EXISTS project (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT 'New Project',
        series_title TEXT DEFAULT '',
        season TEXT DEFAULT '',
        episode TEXT DEFAULT '',
        episode_title TEXT DEFAULT '',
        translator TEXT DEFAULT '',
        editor TEXT DEFAULT '',
        video_path TEXT DEFAULT '',
        frame_rate REAL DEFAULT 25.0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Cues (subtitles/dubbing texts)
    CREATE TABLE IF NOT EXISTS cues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL DEFAULT 1,
        cue_index INTEGER NOT NULL,
        time_in_ms INTEGER NOT NULL,
        time_out_ms INTEGER NOT NULL,
        source_text TEXT NOT NULL DEFAULT '',
        translated_text TEXT DEFAULT '',
        character_name TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        sfx_notes TEXT DEFAULT '',
        status INTEGER NOT NULL DEFAULT 1,
        lip_sync_ratio REAL DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES project(id) ON DELETE CASCADE
    );
    
    -- Comments
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cue_id INTEGER NOT NULL,
        author TEXT NOT NULL DEFAULT 'User',
        content TEXT NOT NULL,
        status INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cue_id) REFERENCES cues(id) ON DELETE CASCADE
    );
    
    -- Indexes for faster searching
    CREATE INDEX IF NOT EXISTS idx_cues_project ON cues(project_id);
    CREATE INDEX IF NOT EXISTS idx_cues_time ON cues(time_in_ms);
    CREATE INDEX IF NOT EXISTS idx_cues_status ON cues(status);
    CREATE INDEX IF NOT EXISTS idx_comments_cue ON comments(cue_id);
    
    -- Triggers for updating updated_at
    CREATE TRIGGER IF NOT EXISTS update_project_timestamp 
    AFTER UPDATE ON project
    BEGIN
        UPDATE project SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
    
    CREATE TRIGGER IF NOT EXISTS update_cue_timestamp 
    AFTER UPDATE ON cues
    BEGIN
        UPDATE cues SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;
    """
    
    # Execute schema
    db.connection.executescript(schema)
    
    # Set database version
    db.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        ("db_version", str(DB_VERSION))
    )
    
    # Ensure at least one project exists
    row = db.fetchone("SELECT COUNT(*) as count FROM project")
    if row is None or row["count"] == 0:
        db.execute(
            "INSERT INTO project (title) VALUES (?)",
            ("New Project",)
        )
    
    db.commit()


def migrate_database(db: Database) -> None:
    """
    Execute database migrations if necessary.
    """
    current_version = db.get_version()
    
    if current_version < DB_VERSION:
        # Future migrations would go here
        # For now, just update the version
        db.execute(
            "UPDATE metadata SET value = ? WHERE key = 'db_version'",
            (str(DB_VERSION),)
        )
        db.commit()
