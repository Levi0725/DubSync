"""
DubSync Project Manager Tests

ProjectManager szolgáltatás tesztjei.
"""

import pytest
from pathlib import Path

from dubsync.services.project_manager import ProjectManager
from dubsync.models.project import Project
from dubsync.models.cue import Cue


class TestProjectManager:
    """ProjectManager tesztek."""
    
    @pytest.fixture
    def manager(self):
        """ProjectManager fixture."""
        pm = ProjectManager()
        yield pm
        pm.close()
    
    @pytest.fixture
    def sample_srt_file(self, temp_dir):
        """Sample SRT fájl létrehozása."""
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello, how are you?

2
00:00:03,500 --> 00:00:06,000
I'm fine, thank you.

3
00:00:06,500 --> 00:00:09,000
What are you doing?

4
00:00:10,000 --> 00:00:12,000
Just working on a project.
"""
        srt_path = temp_dir / "sample.srt"
        srt_path.write_text(srt_content, encoding='utf-8')
        return srt_path
    
    def test_create_new_project(self, manager, temp_dir):
        """Új projekt létrehozása."""
        project_path = temp_dir / "new_project.dubsync"
        
        project = manager.new_project(project_path)
        
        assert project is not None
        assert project.id == 1
        assert manager.is_open
        assert project_path.exists()
    
    def test_create_memory_project(self, manager):
        """Memória projekt létrehozása."""
        project = manager.new_project(None)
        
        assert project is not None
        assert manager.is_open
        assert manager.is_dirty  # Memory project is dirty
    
    def test_open_project(self, manager, temp_dir):
        """Projekt megnyitása."""
        # Create first
        project_path = temp_dir / "open_test.dubsync"
        created = manager.new_project(project_path)
        created.title = "Open Test"
        manager.project.title = "Open Test"
        manager.save_project()
        manager.close()
        
        # Open
        opened = manager.open_project(project_path)
        
        assert opened is not None
        assert opened.title == "Open Test"
        assert manager.is_open
    
    def test_open_nonexistent_file(self, manager, temp_dir):
        """Nem létező fájl megnyitása."""
        invalid_path = temp_dir / "nonexistent.dubsync"
        
        with pytest.raises(FileNotFoundError):
            manager.open_project(invalid_path)
    
    def test_close_project(self, manager, temp_dir):
        """Projekt bezárása."""
        project_path = temp_dir / "close_test.dubsync"
        manager.new_project(project_path)
        
        assert manager.is_open
        
        manager.close()
        
        assert not manager.is_open
        assert manager.project is None
    
    def test_save_project(self, manager, temp_dir):
        """Projekt mentése."""
        project_path = temp_dir / "save_test.dubsync"
        project = manager.new_project(project_path)
        
        # Modify
        manager.project.title = "Modified Title"
        manager.project.translator = "Test Translator"
        manager.save_project()
        
        # Reopen and verify
        manager.close()
        reopened = manager.open_project(project_path)
        
        assert reopened.title == "Modified Title"
        assert reopened.translator == "Test Translator"
    
    def test_save_as(self, manager, temp_dir):
        """Projekt mentése új helyre."""
        original_path = temp_dir / "original.dubsync"
        new_path = temp_dir / "saved_as.dubsync"
        
        manager.new_project(original_path)
        manager.project.title = "Save As Test"
        
        # Save to new location
        manager.save_project(new_path)
        
        assert new_path.exists()
        assert manager.project_path == new_path
    
    def test_import_srt(self, manager, temp_dir, sample_srt_file):
        """SRT importálás."""
        project_path = temp_dir / "srt_import.dubsync"
        manager.new_project(project_path)
        
        count, errors = manager.import_srt(sample_srt_file)
        
        assert count == 4
        assert len(errors) == 0
    
    def test_import_srt_clears_existing(self, manager, temp_dir, sample_srt_file):
        """SRT importálás törli a meglévő cue-kat."""
        self._extracted_from_test_get_statistics_3(
            temp_dir, "srt_clear.dubsync", manager, sample_srt_file
        )
        # Second import with clear
        count, _ = manager.import_srt(sample_srt_file, clear_existing=True)

        # Should still be 4, not 8
        cues = manager.get_cues()
        assert len(cues) == 4
    
    def test_import_srt_no_project(self, manager, temp_dir, sample_srt_file):
        """SRT importálás nyitott projekt nélkül."""
        with pytest.raises(ValueError):
            manager.import_srt(sample_srt_file)
    
    def test_get_cues(self, manager, temp_dir, sample_srt_file):
        """Cue-k lekérése."""
        self._extracted_from_test_get_statistics_3(
            temp_dir, "get_cues.dubsync", manager, sample_srt_file
        )
        cues = manager.get_cues()

        assert len(cues) == 4
        assert cues[0].source_text == "Hello, how are you?"
    
    def test_update_cue(self, manager, temp_dir, sample_srt_file):
        """Cue frissítése."""
        self._extracted_from_test_get_statistics_3(
            temp_dir, "update_cue.dubsync", manager, sample_srt_file
        )
        cues = manager.get_cues()
        cue = cues[0]
        cue.translated_text = "Szia, hogy vagy?"

        manager.save_cue(cue)  # Use save_cue instead of update_cue

        # Reload and verify
        reloaded_cues = manager.get_cues()
        assert reloaded_cues[0].translated_text == "Szia, hogy vagy?"
    
    def test_update_project(self, manager, temp_dir):
        """Projekt adatok frissítése."""
        project_path = temp_dir / "update_project.dubsync"
        manager.new_project(project_path)
        
        manager.update_project(
            title="Updated Title",
            translator="Updated Translator"
        )
        
        assert manager.project.title == "Updated Title"
        assert manager.project.translator == "Updated Translator"
    
    def test_link_video(self, manager, temp_dir):
        """Videó linkelése."""
        project_path = temp_dir / "link_video.dubsync"
        manager.new_project(project_path)
        
        video_path = "/path/to/video.mp4"
        manager.update_project(video_path=video_path)
        
        assert manager.project.video_path == video_path
    
    def test_export_srt(self, manager, temp_dir, sample_srt_file):
        """SRT exportálás."""
        from dubsync.services.srt_parser import export_to_srt

        self._extracted_from_test_get_statistics_3(
            temp_dir, "export_srt.dubsync", manager, sample_srt_file
        )
        # Add translations
        cues = manager.get_cues()
        for i, cue in enumerate(cues):
            cue.translated_text = f"Fordítás {i+1}"
            manager.save_cue(cue)

        # Export using the export_to_srt helper function
        cues = manager.get_cues()
        srt_content = export_to_srt(cues, use_translated=True)

        export_path = temp_dir / "exported.srt"
        export_path.write_text(srt_content, encoding='utf-8')

        assert export_path.exists()
        content = export_path.read_text(encoding='utf-8')
        assert "Fordítás 1" in content
    
    def test_dirty_flag(self, manager, temp_dir):
        """Dirty flag működése."""
        project_path = temp_dir / "dirty_test.dubsync"
        manager.new_project(project_path)
        
        assert not manager.is_dirty
        
        manager.mark_dirty()
        assert manager.is_dirty
        
        manager.save_project()
        assert not manager.is_dirty
    
    def test_get_statistics(self, manager, temp_dir, sample_srt_file):
        """Statisztikák lekérése."""
        self._extracted_from_test_get_statistics_3(
            temp_dir, "stats.dubsync", manager, sample_srt_file
        )
        stats = manager.get_statistics()

        assert stats is not None
        assert "total_cues" in stats
        assert stats["total_cues"] == 4

    # TODO Rename this here and in `test_import_srt_clears_existing`, `test_get_cues`, `test_update_cue`, `test_export_srt` and `test_get_statistics`
    def _extracted_from_test_get_statistics_3(self, temp_dir, arg1, manager, sample_srt_file):
        project_path = temp_dir / arg1
        manager.new_project(project_path)
        manager.import_srt(sample_srt_file)


class TestProjectManagerAutoSave:
    """ProjectManager auto-save tesztek."""
    
    @pytest.fixture
    def manager(self):
        """ProjectManager fixture."""
        pm = ProjectManager()
        yield pm
        pm.close()
    
    def test_mark_dirty(self, manager, temp_dir):
        """Dirty flag beállítása."""
        project_path = temp_dir / "dirty.dubsync"
        manager.new_project(project_path)
        
        manager.mark_dirty()
        
        assert manager.is_dirty
    
    def test_mark_clean(self, manager, temp_dir):
        """Clean flag beállítása."""
        project_path = temp_dir / "clean.dubsync"
        manager.new_project(project_path)
        manager.mark_dirty()
        
        manager.mark_clean()
        
        assert not manager.is_dirty
