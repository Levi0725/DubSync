"""
DubSync SRT Parser Tests

SRT parser tesztek.
"""

import pytest
from pathlib import Path

from dubsync.services.srt_parser import (
    SRTParser, SRTEntry, parse_srt_file, export_to_srt
)
from dubsync.models.cue import Cue
from dubsync.utils.constants import CueStatus


class TestSRTParser:
    """SRTParser osztály tesztjei."""
    
    def test_parse_basic_content(self, sample_srt_content):
        """Alapvető SRT tartalom parse-olása."""
        parser = SRTParser()
        entries = parser.parse_content(sample_srt_content)
        
        assert len(entries) == 4
        assert entries[0].index == 1
        assert entries[0].text == "Hello, how are you?"
    
    def test_parse_multiline_text(self):
        """Többsoros szöveg kezelése."""
        content = """1
00:00:00,000 --> 00:00:03,000
First line
Second line
Third line
"""
        parser = SRTParser()
        entries = parser.parse_content(content)
        
        assert len(entries) == 1
        assert "First line" in entries[0].text
        assert "Second line" in entries[0].text
        assert "Third line" in entries[0].text
    
    def test_parse_times(self, sample_srt_content):
        """Időkódok helyes parse-olása."""
        parser = SRTParser()
        entries = parser.parse_content(sample_srt_content)
        
        assert entries[0].time_in_ms == 0
        assert entries[0].time_out_ms == 2000
        assert entries[1].time_in_ms == 2500
        assert entries[1].time_out_ms == 5000
    
    def test_parse_file(self, sample_srt_file):
        """Fájl beolvasás."""
        parser = SRTParser()
        entries = parser.parse_file(sample_srt_file)
        
        assert len(entries) == 4
        assert not parser.has_errors()
    
    def test_parse_file_utf8_bom(self, temp_dir):
        """UTF-8 BOM kezelése."""
        # A BOM-ot a teljes tartalommal kell írni, nem a közepén
        content = """1
00:00:00,000 --> 00:00:01,000
Test
"""
        srt_path = temp_dir / "bom_test.srt"
        # Write with UTF-8 BOM encoding
        srt_path.write_bytes(content.encode("utf-8-sig"))
        
        parser = SRTParser()
        entries = parser.parse_file(srt_path)
        
        assert len(entries) == 1
        assert entries[0].text == "Test"
    
    def test_parse_removes_html_tags(self):
        """HTML tagek eltávolítása."""
        content = """1
00:00:00,000 --> 00:00:01,000
<i>Italic text</i> and <b>bold</b>
"""
        parser = SRTParser()
        entries = parser.parse_content(content)
        
        assert "<i>" not in entries[0].text
        assert "</i>" not in entries[0].text
        assert "Italic text" in entries[0].text
    
    def test_parse_removes_ass_codes(self):
        """ASS stílus kódok eltávolítása."""
        content = """1
00:00:00,000 --> 00:00:01,000
{\\an8}Top positioned text
"""
        parser = SRTParser()
        entries = parser.parse_content(content)
        
        assert "{\\an8}" not in entries[0].text
        assert "Top positioned text" in entries[0].text
    
    def test_to_cue_conversion(self):
        """SRTEntry -> Cue konverzió."""
        entry = SRTEntry(
            index=1,
            time_in_ms=1000,
            time_out_ms=5000,
            text="Test text"
        )
        
        cue = entry.to_cue(project_id=1)
        
        assert cue.cue_index == 1
        assert cue.time_in_ms == 1000
        assert cue.time_out_ms == 5000
        assert cue.source_text == "Test text"
        assert cue.status == CueStatus.NEW
    
    def test_get_cues(self, sample_srt_content):
        """Cue lista lekérése."""
        parser = SRTParser()
        parser.parse_content(sample_srt_content)
        cues = parser.get_cues(project_id=1)
        
        assert len(cues) == 4
        assert all(isinstance(c, Cue) for c in cues)
        assert all(c.project_id == 1 for c in cues)
    
    def test_invalid_time_format(self):
        """Érvénytelen időformátum kezelése."""
        content = """1
invalid --> time
Some text
"""
        parser = SRTParser()
        entries = parser.parse_content(content)
        
        assert len(entries) == 0
        assert parser.has_errors()


class TestParseSrtFile:
    """parse_srt_file convenience function tesztjei."""
    
    def test_returns_cues_and_errors(self, sample_srt_file):
        """Cue-k és hibák visszaadása."""
        cues, errors = parse_srt_file(sample_srt_file, project_id=1)
        
        assert len(cues) == 4
        assert len(errors) == 0
    
    def test_file_not_found(self, temp_dir):
        """Nem létező fájl."""
        with pytest.raises(FileNotFoundError):
            parse_srt_file(temp_dir / "nonexistent.srt")


class TestExportToSrt:
    """export_to_srt tesztek."""
    
    def test_export_basic(self, sample_cues):
        """Alapvető export."""
        content = export_to_srt(sample_cues, use_translated=True)
        
        assert "Szia, hogy vagy?" in content
        assert "00:00:00,000 --> 00:00:02,000" in content
    
    def test_export_uses_source_when_no_translation(self, sample_cues):
        """Forrás használata, ha nincs fordítás."""
        # Third cue has no translation
        content = export_to_srt(sample_cues, use_translated=True)
        
        assert "What are you doing today?" in content
    
    def test_export_source_only(self, sample_cues):
        """Csak forrás export."""
        content = export_to_srt(sample_cues, use_translated=False)
        
        assert "Hello, how are you?" in content
        assert "Szia, hogy vagy?" not in content
