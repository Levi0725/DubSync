"""
DubSync Database Tests

Adatbázis modul tesztjei.
"""

import pytest
import sqlite3
from pathlib import Path

from dubsync.models.database import Database, init_database


class TestDatabase:
    """Database osztály tesztjei."""
    
    def test_create_memory_db(self, memory_db):
        """Memória adatbázis létrehozása."""
        assert memory_db is not None
        assert memory_db.connection is not None
    
    def test_create_file_db(self, file_db, temp_dir):
        """Fájl adatbázis létrehozása."""
        db_path = temp_dir / "test_project.dubsync"
        assert db_path.exists()
        assert file_db.connection is not None
    
    def test_schema_created(self, memory_db):
        """Séma táblák létrehozása."""
        result = memory_db.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [r["name"] for r in result]
        
        assert "metadata" in table_names
        assert "project" in table_names
        assert "cues" in table_names
        assert "comments" in table_names
    
    def test_metadata_inserted(self, memory_db):
        """Metadata rekord létrehozása."""
        result = memory_db.fetchone(
            "SELECT key, value FROM metadata WHERE key = 'db_version'"
        )
        
        assert result is not None
        assert result["key"] == "db_version"
    
    def test_execute_query(self, memory_db):
        """Query végrehajtása."""
        memory_db.execute(
            "UPDATE project SET title = ? WHERE id = 1",
            ("Test Project",)
        )
        memory_db.commit()
        
        result = memory_db.fetchone("SELECT title FROM project WHERE id = 1")
        assert result["title"] == "Test Project"
    
    def test_fetchone(self, memory_db):
        """Egy sor lekérése."""
        result = memory_db.fetchone("SELECT COUNT(*) as cnt FROM project")
        assert result is not None
        assert result["cnt"] >= 1
    
    def test_fetchall(self, memory_db):
        """Összes sor lekérése."""
        result = memory_db.fetchall("SELECT * FROM project")
        assert isinstance(result, list)
    
    def test_commit_and_rollback(self, memory_db):
        """Commit és rollback."""
        # Get initial title
        initial = memory_db.fetchone("SELECT title FROM project WHERE id = 1")
        initial_title = initial["title"]
        
        # Change title
        memory_db.execute("UPDATE project SET title = 'Changed' WHERE id = 1")
        
        # Rollback
        memory_db.rollback()
        
        # Should be back to original
        result = memory_db.fetchone("SELECT title FROM project WHERE id = 1")
        assert result["title"] == initial_title
    
    def test_close_connection(self, temp_dir):
        """Kapcsolat lezárása."""
        db_path = temp_dir / "close_test.dubsync"
        db = Database(db_path)
        init_database(db)
        
        # Force connection
        _ = db.connection
        
        db.close()
        assert db._connection is None
    
    def test_foreign_key_constraint(self, memory_db):
        """Foreign key constraint."""
        # Try to insert cue without valid project_id
        with pytest.raises(sqlite3.IntegrityError):
            memory_db.execute(
                "INSERT INTO cues (project_id, cue_index, time_in_ms, time_out_ms) "
                "VALUES (?, ?, ?, ?)",
                (999, 1, 0, 1000)
            )
            memory_db.commit()
    
    def test_get_version(self, memory_db):
        """Verzió lekérése."""
        version = memory_db.get_version()
        assert version is not None
        assert isinstance(version, int)


class TestDatabaseIntegrity:
    """Adatbázis integritás tesztek."""
    
    def test_cascade_delete_cues(self, memory_db):
        """Cue-k cascade törlése projekt törlésekor."""
        # Get existing project
        project = memory_db.fetchone("SELECT id FROM project LIMIT 1")
        project_id = project["id"]
        
        # Insert cue
        memory_db.execute(
            "INSERT INTO cues (project_id, cue_index, time_in_ms, time_out_ms, source_text) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, 1, 0, 1000, "Test")
        )
        memory_db.commit()
        
        # Verify cue exists
        cue = memory_db.fetchone("SELECT id FROM cues WHERE project_id = ?", (project_id,))
        assert cue is not None
        
        # Delete project
        memory_db.execute("DELETE FROM project WHERE id = ?", (project_id,))
        memory_db.commit()
        
        # Cue should be deleted too
        cues = memory_db.fetchall("SELECT * FROM cues WHERE project_id = ?", (project_id,))
        assert len(cues) == 0
    
    def test_cascade_delete_comments(self, memory_db):
        """Comment-ek cascade törlése cue törlésekor."""
        # Get existing project
        project = memory_db.fetchone("SELECT id FROM project LIMIT 1")
        project_id = project["id"]
        
        # Insert cue
        memory_db.execute(
            "INSERT INTO cues (project_id, cue_index, time_in_ms, time_out_ms, source_text) "
            "VALUES (?, ?, ?, ?, ?)",
            (project_id, 100, 0, 1000, "Test")
        )
        memory_db.commit()
        
        cue = memory_db.fetchone("SELECT id FROM cues WHERE cue_index = 100")
        cue_id = cue["id"]
        
        # Insert comment
        memory_db.execute(
            "INSERT INTO comments (cue_id, author, content) VALUES (?, ?, ?)",
            (cue_id, "Test Author", "Test Comment")
        )
        memory_db.commit()
        
        # Verify comment exists
        comment = memory_db.fetchone("SELECT id FROM comments WHERE cue_id = ?", (cue_id,))
        assert comment is not None
        
        # Delete cue
        memory_db.execute("DELETE FROM cues WHERE id = ?", (cue_id,))
        memory_db.commit()
        
        # Comment should be deleted too
        comments = memory_db.fetchall("SELECT * FROM comments WHERE cue_id = ?", (cue_id,))
        assert len(comments) == 0
