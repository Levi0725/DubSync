"""
DubSync Models Tests

Modell osztályok (Project, Cue, Comment) tesztjei.
"""

import pytest
from datetime import datetime

from dubsync.models.database import Database, init_database
from dubsync.models.project import Project
from dubsync.models.cue import Cue
from dubsync.models.comment import Comment
from dubsync.utils.constants import CueStatus, CommentStatus


@pytest.fixture
def memory_db():
    """Memória-adatbázis létrehozása tesztekhez."""
    db = Database(None)  # Memory database
    init_database(db)  # Initialize schema
    yield db
    db.close()


@pytest.fixture
def sample_project(memory_db):
    """Minta projekt létrehozása."""
    # Load the default project created by init_database
    project = Project.load(memory_db, 1)
    assert project is not None, "Project with id 1 should exist"
    project.title = "Test Movie"
    project.series_title = "Test Series"
    project.season = "01"
    project.episode = "01"
    project.save(memory_db)
    return project


class TestProjectModel:
    """Project model tesztek."""
    
    def test_create_project(self):
        """Projekt létrehozása."""
        project = Project(
            title="Test Movie",
            series_title="Test Series",
            translator="Fordító"
        )
        
        assert project.title == "Test Movie"
        assert project.series_title == "Test Series"
        assert project.translator == "Fordító"
        assert project.id == 0
    
    def test_project_defaults(self):
        """Projekt alapértékek."""
        project = Project()
        
        assert project.title == "Új projekt"
        assert project.series_title == ""
        assert project.video_path == ""
        assert project.frame_rate == 25.0
        assert project.id == 0
    
    def test_save_project(self, memory_db):
        """Projekt mentése."""
        # Load the default project (id=1 is created by init_database)
        project = Project.load(memory_db, 1)
        assert project is not None, "Project with id 1 should exist"
        project.title = "Save Test"
        project.translator = "Test"
        project.save(memory_db)
        
        # Reload and verify
        reloaded = Project.load(memory_db, 1)
        assert reloaded is not None
        assert reloaded.title == "Save Test"
    
    def test_load_project(self, memory_db, sample_project):
        """Projekt betöltése."""
        loaded = Project.load(memory_db, sample_project.id)
        
        assert loaded is not None
        assert loaded.id == sample_project.id
        assert loaded.title == "Test Movie"
        assert loaded.series_title == "Test Series"
    
    def test_load_nonexistent(self, memory_db):
        """Nem létező projekt betöltése."""
        # id=1 exists, try loading non-existent id=9999
        loaded = Project.load(memory_db, 9999)
        assert loaded is None
    
    def test_update_project(self, memory_db, sample_project):
        """Projekt frissítése."""
        sample_project.title = "Updated Title"
        sample_project.translator = "New Translator"
        sample_project.save(memory_db)
        
        loaded = Project.load(memory_db, sample_project.id)
        assert loaded is not None, "Loaded project should not be None"
        assert loaded.title == "Updated Title"
        assert loaded.translator == "New Translator"
    
    def test_get_display_title(self):
        """Megjelenített cím generálása."""
        project = Project(
            series_title="Breaking Bad",
            season="05",
            episode="16",
            episode_title="Felina"
        )
        
        display = project.get_display_title()
        assert "Breaking Bad" in display
        assert "S05" in display
        assert "E16" in display
        assert "Felina" in display
    
    def test_get_display_title_simple(self):
        """Egyszerű cím projekt."""
        project = Project(title="Simple Movie")
        display = project.get_display_title()
        assert "Simple Movie" in display or display == "Simple Movie"
    
    def test_has_video(self, tmp_path):
        """Video path ellenőrzés."""
        # Nincs videó
        project = Project()
        assert not project.has_video()
        
        # Nem létező path
        project.video_path = "/nonexistent/path.mp4"
        assert not project.has_video()
        
        # Létező path
        video_file = tmp_path / "test.mp4"
        video_file.write_text("dummy")
        project.video_path = str(video_file)
        assert project.has_video()


class TestCueModel:
    """Cue model tesztek."""
    
    def test_create_cue(self):
        """Cue létrehozása."""
        cue = Cue(
            cue_index=1,
            time_in_ms=1000,
            time_out_ms=5000,
            source_text="Hello world"
        )
        
        assert cue.cue_index == 1
        assert cue.time_in_ms == 1000
        assert cue.time_out_ms == 5000
        assert cue.source_text == "Hello world"
    
    def test_cue_defaults(self):
        """Cue alapértékek."""
        cue = Cue()
        
        assert cue.id == 0
        assert cue.project_id == 1
        assert cue.source_text == ""
        assert cue.translated_text == ""
        assert cue.status == CueStatus.NEW
    
    def test_cue_duration(self):
        """Cue időtartam számítás."""
        cue = Cue(time_in_ms=1000, time_out_ms=5000)
        
        # Duration = time_out - time_in
        assert cue.time_out_ms - cue.time_in_ms == 4000
    
    def test_save_cue(self, memory_db, sample_project):
        """Cue mentése."""
        cue = Cue(
            project_id=sample_project.id,
            cue_index=1,
            time_in_ms=0,
            time_out_ms=3000,
            source_text="Test text"
        )
        
        cue.save(memory_db)
        
        assert cue.id > 0
    
    def test_load_cue(self, memory_db, sample_project):
        """Cue betöltése."""
        cue = Cue(
            project_id=sample_project.id,
            cue_index=1,
            time_in_ms=1000,
            time_out_ms=3000,
            source_text="Test"
        )
        cue.save(memory_db)
        
        loaded = Cue.load_by_id(memory_db, cue.id)
        
        assert loaded is not None
        assert loaded.id == cue.id
        assert loaded.source_text == "Test"
    
    def test_load_all_cues_for_project(self, memory_db, sample_project):
        """Összes cue betöltése projekthez."""
        # Több cue létrehozása
        for i in range(3):
            cue = Cue(
                project_id=sample_project.id,
                cue_index=i,
                time_in_ms=i * 1000,
                time_out_ms=(i + 1) * 1000,
                source_text=f"Cue {i}"
            )
            cue.save(memory_db)
        
        cues = Cue.load_all(memory_db, sample_project.id)
        
        assert len(cues) == 3
        assert cues[0].cue_index == 0
        assert cues[1].cue_index == 1
        assert cues[2].cue_index == 2
    
    def test_update_cue(self, memory_db, sample_project):
        """Cue frissítése."""
        cue = Cue(
            project_id=sample_project.id,
            cue_index=1,
            source_text="Original"
        )
        cue.save(memory_db)
        
        cue.translated_text = "Fordított"
        cue.status = CueStatus.APPROVED
        cue.save(memory_db)
        
        loaded = Cue.load_by_id(memory_db, cue.id)
        assert loaded is not None
        assert loaded.translated_text == "Fordított"
        assert loaded.status == CueStatus.APPROVED
    
    def test_delete_cue(self, memory_db, sample_project):
        """Cue törlése."""
        cue = Cue(
            project_id=sample_project.id,
            cue_index=1,
            source_text="Delete me"
        )
        cue.save(memory_db)
        cue_id = cue.id
        
        cue.delete(memory_db)
        
        loaded = Cue.load_by_id(memory_db, cue_id)
        assert loaded is None
    
    def test_find_at_time(self, memory_db, sample_project):
        """Cue keresése időpont alapján."""
        cue = Cue(
            project_id=sample_project.id,
            cue_index=1,
            time_in_ms=1000,
            time_out_ms=5000,
            source_text="Find me"
        )
        cue.save(memory_db)
        
        found = Cue.find_at_time(memory_db, 3000, sample_project.id)
        assert found is not None
        assert found.source_text == "Find me"
        
        # Időponton kívül nem talál
        not_found = Cue.find_at_time(memory_db, 6000, sample_project.id)
        assert not_found is None
    
    def test_find_next_empty(self, memory_db, sample_project):
        """Következő üres cue keresése."""
        cue1 = Cue(
            project_id=sample_project.id,
            cue_index=1,
            translated_text="Translated"
        )
        cue1.save(memory_db)
        
        cue2 = Cue(
            project_id=sample_project.id,
            cue_index=2,
            translated_text=""  # Üres
        )
        cue2.save(memory_db)
        
        found = Cue.find_next_empty(memory_db, 0, sample_project.id)
        assert found is not None
        assert found.cue_index == 2
    
    def test_count_by_status(self, memory_db, sample_project):
        """Státusz szerinti számlálás."""
        # NEW státuszú
        cue1 = Cue(project_id=sample_project.id, cue_index=1, status=CueStatus.NEW)
        cue1.save(memory_db)
        
        # APPROVED státuszú
        cue2 = Cue(project_id=sample_project.id, cue_index=2, status=CueStatus.APPROVED)
        cue2.save(memory_db)
        cue3 = Cue(project_id=sample_project.id, cue_index=3, status=CueStatus.APPROVED)
        cue3.save(memory_db)
        
        counts = Cue.count_by_status(memory_db, sample_project.id)
        
        assert counts.get(CueStatus.NEW, 0) == 1
        assert counts.get(CueStatus.APPROVED, 0) == 2


class TestCommentModel:
    """Comment model tesztek."""
    
    def test_create_comment(self):
        """Megjegyzés létrehozása."""
        comment = Comment(
            cue_id=1,
            author="Teszt Felhasználó",
            content="Ez egy teszt megjegyzés"
        )
        
        assert comment.cue_id == 1
        assert comment.author == "Teszt Felhasználó"
        assert comment.content == "Ez egy teszt megjegyzés"
    
    def test_comment_defaults(self):
        """Megjegyzés alapértékek."""
        comment = Comment(cue_id=1, content="Test")
        
        assert comment.id == 0
        assert comment.author == "Felhasználó"
        assert comment.status == CommentStatus.OPEN
    
    def test_save_comment(self, memory_db, sample_project):
        """Megjegyzés mentése."""
        # Először cue kell
        cue = Cue(project_id=sample_project.id, cue_index=1)
        cue.save(memory_db)
        
        comment = Comment(
            cue_id=cue.id,
            author="Tester",
            content="Test comment"
        )
        comment.save(memory_db)
        
        assert comment.id > 0
    
    def test_load_comments_for_cue(self, memory_db, sample_project):
        """Megjegyzések betöltése cue-hoz."""
        cue = Cue(project_id=sample_project.id, cue_index=1)
        cue.save(memory_db)
        
        # Több megjegyzés
        for i in range(3):
            comment = Comment(
                cue_id=cue.id,
                author=f"Author {i}",
                content=f"Comment {i}"
            )
            comment.save(memory_db)
        
        comments = Comment.load_for_cue(memory_db, cue.id)
        
        assert len(comments) == 3
    
    def test_resolve_comment(self, memory_db, sample_project):
        """Megjegyzés lezárása."""
        cue = Cue(project_id=sample_project.id, cue_index=1)
        cue.save(memory_db)
        
        comment = Comment(cue_id=cue.id, content="To resolve")
        comment.save(memory_db)
        
        assert comment.is_open
        
        comment.resolve(memory_db)
        
        assert comment.is_resolved
        assert comment.status == CommentStatus.RESOLVED
    
    def test_reopen_comment(self, memory_db, sample_project):
        """Megjegyzés újranyitása."""
        cue = Cue(project_id=sample_project.id, cue_index=1)
        cue.save(memory_db)
        
        comment = Comment(cue_id=cue.id, content="Test", status=CommentStatus.RESOLVED)
        comment.save(memory_db)
        
        assert comment.is_resolved
        
        comment.reopen(memory_db)
        
        assert comment.is_open
    
    def test_delete_comment(self, memory_db, sample_project):
        """Megjegyzés törlése."""
        cue = Cue(project_id=sample_project.id, cue_index=1)
        cue.save(memory_db)
        
        comment = Comment(cue_id=cue.id, content="Delete me")
        comment.save(memory_db)
        comment_id = comment.id
        
        comment.delete(memory_db)
        
        comments = Comment.load_for_cue(memory_db, cue.id)
        assert len(comments) == 0
    
    def test_count_open_for_cue(self, memory_db, sample_project):
        """Nyitott megjegyzések száma."""
        cue = Cue(project_id=sample_project.id, cue_index=1)
        cue.save(memory_db)
        
        # 2 nyitott
        c1 = Comment(cue_id=cue.id, content="Open 1")
        c1.save(memory_db)
        c2 = Comment(cue_id=cue.id, content="Open 2")
        c2.save(memory_db)
        
        # 1 lezárt
        c3 = Comment(cue_id=cue.id, content="Resolved", status=CommentStatus.RESOLVED)
        c3.save(memory_db)
        
        count = Comment.count_open_for_cue(memory_db, cue.id)
        assert count == 2
    
    def test_count_all_open(self, memory_db, sample_project):
        """Összes nyitott megjegyzés a projektben."""
        cue1 = Cue(project_id=sample_project.id, cue_index=1)
        cue1.save(memory_db)
        cue2 = Cue(project_id=sample_project.id, cue_index=2)
        cue2.save(memory_db)
        
        # Mindkét cue-hoz megjegyzés
        c1 = Comment(cue_id=cue1.id, content="Comment 1")
        c1.save(memory_db)
        c2 = Comment(cue_id=cue2.id, content="Comment 2")
        c2.save(memory_db)
        
        count = Comment.count_all_open(memory_db, sample_project.id)
        assert count == 2
    
    def test_get_cue_ids_with_comments(self, memory_db, sample_project):
        """Cue-k azonosítói megjegyzésekkel."""
        cue1 = Cue(project_id=sample_project.id, cue_index=1)
        cue1.save(memory_db)
        cue2 = Cue(project_id=sample_project.id, cue_index=2)
        cue2.save(memory_db)
        cue3 = Cue(project_id=sample_project.id, cue_index=3)  # Megjegyzés nélküli
        cue3.save(memory_db)
        
        c1 = Comment(cue_id=cue1.id, content="Comment 1")
        c1.save(memory_db)
        c2 = Comment(cue_id=cue2.id, content="Comment 2")
        c2.save(memory_db)
        
        ids = Comment.get_cue_ids_with_comments(memory_db, sample_project.id)
        
        assert cue1.id in ids
        assert cue2.id in ids
        assert cue3.id not in ids
