"""
DubSync PDF Export Tests

PDF exportálás tesztjei.
"""

import pytest
from pathlib import Path

from dubsync.services.pdf_export import PDFExporter
from dubsync.models.database import Database, init_database
from dubsync.models.project import Project
from dubsync.models.cue import Cue
from dubsync.utils.constants import CueStatus


@pytest.fixture
def sample_project():
    """Minta projekt."""
    return Project(
        id=1,
        title="Test Movie",
        series_title="Test Series",
        season="01",
        episode="05",
        translator="Test Translator",
        editor="Test Editor"
    )


@pytest.fixture
def sample_cues():
    """Minta cue-k."""
    return [
        Cue(
            id=1,
            project_id=1,
            cue_index=1,
            time_in_ms=0,
            time_out_ms=2000,
            source_text="Hello, how are you?",
            translated_text="Szia, hogy vagy?",
            character_name="ANNA",
            status=CueStatus.APPROVED,
        ),
        Cue(
            id=2,
            project_id=1,
            cue_index=2,
            time_in_ms=2500,
            time_out_ms=5000,
            source_text="I'm fine, thank you.",
            translated_text="Jól vagyok, köszönöm.",
            character_name="PETER",
            status=CueStatus.APPROVED,
        ),
        Cue(
            id=3,
            project_id=1,
            cue_index=3,
            time_in_ms=5500,
            time_out_ms=8000,
            source_text="What are you doing today?",
            translated_text="Mit csinálsz ma?",
            character_name="ANNA",
            notes="Kérdő hangsúly",
            status=CueStatus.TRANSLATED,
        ),
    ]


class TestPDFExporter:
    """PDFExporter osztály tesztjei."""
    
    @pytest.fixture
    def exporter(self):
        return PDFExporter()
    
    def test_exporter_init(self, exporter):
        """Exporter inicializálás."""
        assert exporter is not None
        assert exporter.styles is not None
    
    def test_exporter_has_fonts(self, exporter):
        """Font regisztráció."""
        assert exporter.font_name is not None
        assert exporter.font_bold is not None
    
    def test_export_basic(self, exporter, sample_project, sample_cues, temp_dir):
        """Alap export teszt."""
        output_path = temp_dir / "test_export.pdf"
        
        exporter.export(
            output_path=output_path,
            project=sample_project,
            cues=sample_cues
        )
        
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    
    def test_export_empty_cues(self, exporter, sample_project, temp_dir):
        """Export üres cue listával."""
        output_path = temp_dir / "test_empty.pdf"
        
        exporter.export(
            output_path=output_path,
            project=sample_project,
            cues=[]
        )
        
        assert output_path.exists()
    
    def test_export_with_source(self, exporter, sample_project, sample_cues, temp_dir):
        """Export forrásnyelvi szöveggel."""
        output_path = temp_dir / "test_with_source.pdf"
        
        exporter.export(
            output_path=output_path,
            project=sample_project,
            cues=sample_cues,
            include_source=True
        )
        
        assert output_path.exists()
    
    def test_export_without_source(self, exporter, sample_project, sample_cues, temp_dir):
        """Export forrásnyelvi szöveg nélkül."""
        output_path = temp_dir / "test_without_source.pdf"
        
        exporter.export(
            output_path=output_path,
            project=sample_project,
            cues=sample_cues,
            include_source=False
        )
        
        assert output_path.exists()


class TestPDFContent:
    """PDF tartalom tesztek."""
    
    @pytest.fixture
    def exporter(self):
        return PDFExporter()
    
    def test_cue_with_character_name(self, exporter, sample_project, temp_dir):
        """Cue karakternévvel."""
        cues = [
            Cue(
                id=1,
                project_id=1,
                cue_index=1,
                time_in_ms=0,
                time_out_ms=2000,
                character_name="ANNA",
                translated_text="Helló!"
            )
        ]
        
        output_path = temp_dir / "test_character.pdf"
        exporter.export(output_path, sample_project, cues)
        
        assert output_path.exists()
    
    def test_cue_with_notes(self, exporter, sample_project, temp_dir):
        """Cue megjegyzéssel."""
        cues = [
            Cue(
                id=1,
                project_id=1,
                cue_index=1,
                time_in_ms=0,
                time_out_ms=2000,
                translated_text="Helló!",
                notes="Vidám hangon"
            )
        ]
        
        output_path = temp_dir / "test_notes.pdf"
        exporter.export(output_path, sample_project, cues)
        
        assert output_path.exists()
    
    def test_cue_with_sfx(self, exporter, sample_project, temp_dir):
        """Cue SFX-szel."""
        cues = [
            Cue(
                id=1,
                project_id=1,
                cue_index=1,
                time_in_ms=0,
                time_out_ms=2000,
                translated_text="",
                sfx_notes="(ajtócsapódás)"
            )
        ]
        
        output_path = temp_dir / "test_sfx.pdf"
        exporter.export(output_path, sample_project, cues)
        
        assert output_path.exists()
    
    def test_long_text_handling(self, exporter, sample_project, temp_dir):
        """Hosszú szöveg kezelése."""
        long_text = "Ez egy nagyon hosszú mondat, ami több sorba is átfolyhat, " * 5
        cues = [
            Cue(
                id=1,
                project_id=1,
                cue_index=1,
                time_in_ms=0,
                time_out_ms=10000,
                translated_text=long_text
            )
        ]
        
        output_path = temp_dir / "test_long_text.pdf"
        exporter.export(output_path, sample_project, cues)
        
        assert output_path.exists()
    
    def test_hungarian_characters(self, exporter, sample_project, temp_dir):
        """Magyar karakterek kezelése."""
        cues = [
            Cue(
                id=1,
                project_id=1,
                cue_index=1,
                time_in_ms=0,
                time_out_ms=2000,
                translated_text="Árvíztűrő tükörfúrógép ŐŰÚÓÉÁÍÖ"
            )
        ]
        
        output_path = temp_dir / "test_hungarian.pdf"
        exporter.export(output_path, sample_project, cues)
        
        assert output_path.exists()
    
    def test_many_cues(self, exporter, sample_project, temp_dir):
        """Sok cue kezelése (több oldal)."""
        cues = []
        for i in range(50):
            cues.append(Cue(
                id=i+1,
                project_id=1,
                cue_index=i+1,
                time_in_ms=i * 3000,
                time_out_ms=(i+1) * 3000,
                character_name="SPEAKER",
                translated_text=f"Ez a {i+1}. mondat a tesztben."
            ))
        
        output_path = temp_dir / "test_many_cues.pdf"
        exporter.export(output_path, sample_project, cues)
        
        assert output_path.exists()
        # Check file is reasonably large (multiple pages)
        assert output_path.stat().st_size > 5000
