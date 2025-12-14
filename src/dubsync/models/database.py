"""
DubSync Database

SQLite adatbázis kezelő és inicializáló.
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Any, Dict
from contextlib import contextmanager
import json

from dubsync.utils.constants import DB_VERSION


class Database:
    """
    SQLite adatbázis kezelő osztály.
    
    A projekt egyetlen fájlban tárolja az összes adatot.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Adatbázis inicializálása.
        
        Args:
            db_path: Adatbázis fájl elérési útja. Ha None, memória-alapú.
        """
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        
    @property
    def connection(self) -> sqlite3.Connection:
        """
        Kapcsolat lekérése vagy létrehozása.
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
        Context manager kurzor kezeléshez.
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
        SQL parancs végrehajtása.
        """
        return self.connection.execute(sql, params)
    
    def executemany(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """
        SQL parancs végrehajtása több paramétersorral.
        """
        return self.connection.executemany(sql, params_list)
    
    def commit(self):
        """
        Változások mentése.
        """
        self.connection.commit()
    
    def rollback(self):
        """
        Változások visszavonása.
        """
        self.connection.rollback()
    
    def close(self):
        """
        Kapcsolat lezárása.
        """
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Egyetlen sor lekérése.
        """
        return self.execute(sql, params).fetchone()
    
    def fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Összes sor lekérése.
        """
        return self.execute(sql, params).fetchall()
    
    def get_version(self) -> int:
        """
        Adatbázis verzió lekérése.
        """
        try:
            row = self.fetchone("SELECT value FROM metadata WHERE key = 'db_version'")
            return int(row["value"]) if row else 0
        except sqlite3.OperationalError:
            return 0


def init_database(db: Database) -> None:
    """
    Adatbázis séma inicializálása.
    
    Létrehozza az összes szükséges táblát és indexet.
    """
    schema = """
    -- Metadata tábla verziókövetéshez és projekt beállításokhoz
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    
    -- Projekt információk
    CREATE TABLE IF NOT EXISTS project (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT 'Új projekt',
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
    
    -- Cue-k (feliratok/szinkronszövegek)
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
    
    -- Megjegyzések (kommentek)
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cue_id INTEGER NOT NULL,
        author TEXT NOT NULL DEFAULT 'Felhasználó',
        content TEXT NOT NULL,
        status INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cue_id) REFERENCES cues(id) ON DELETE CASCADE
    );
    
    -- Indexek a gyorsabb kereséshez
    CREATE INDEX IF NOT EXISTS idx_cues_project ON cues(project_id);
    CREATE INDEX IF NOT EXISTS idx_cues_time ON cues(time_in_ms);
    CREATE INDEX IF NOT EXISTS idx_cues_status ON cues(status);
    CREATE INDEX IF NOT EXISTS idx_comments_cue ON comments(cue_id);
    
    -- Triggerek az updated_at frissítéséhez
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
    if row["count"] == 0:
        db.execute(
            "INSERT INTO project (title) VALUES (?)",
            ("Új projekt",)
        )
    
    db.commit()


def migrate_database(db: Database) -> None:
    """
    Adatbázis migrációk végrehajtása, ha szükséges.
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
