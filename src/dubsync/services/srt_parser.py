"""
DubSync SRT Parser

SRT fájlok beolvasása és feldolgozása.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from dubsync.models.cue import Cue
from dubsync.utils.time_utils import timecode_to_ms


@dataclass
class SRTEntry:
    """
    Nyers SRT bejegyzés a parse-olás után.
    """
    index: int
    time_in_ms: int
    time_out_ms: int
    text: str
    
    def to_cue(self, project_id: int = 1) -> Cue:
        """
        SRT bejegyzés konvertálása Cue objektummá.
        """
        return Cue(
            project_id=project_id,
            cue_index=self.index,
            time_in_ms=self.time_in_ms,
            time_out_ms=self.time_out_ms,
            source_text=self.text,
        )


class SRTParser:
    """
    SRT fájl parser.
    
    Támogatja:
    - Standard SRT formátum
    - UTF-8 kódolás (BOM-mal és anélkül)
    - Többsoros szövegblokkok
    - Különböző sortörés formátumok (\\n, \\r\\n)
    """
    
    # SRT index pattern (number line)
    INDEX_PATTERN = re.compile(r"^\d+$")
    
    # SRT time pattern
    TIME_PATTERN = re.compile(
        r"^(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})"
    )
    
    def __init__(self):
        self.entries: List[SRTEntry] = []
        self.errors: List[str] = []
    
    def parse_file(self, file_path: Path) -> List[SRTEntry]:
        """
        SRT fájl beolvasása és feldolgozása.
        
        Args:
            file_path: SRT fájl elérési útja
            
        Returns:
            SRTEntry objektumok listája
            
        Raises:
            FileNotFoundError: Ha a fájl nem található
            UnicodeDecodeError: Ha a kódolás nem megfelelő
        """
        self.entries = []
        self.errors = []
        
        # Try UTF-8 first, then fallback to other encodings
        encodings = ["utf-8-sig", "utf-8", "cp1250", "iso-8859-2", "cp1252"]
        content = None
        
        for encoding in encodings:
            try:
                content = file_path.read_text(encoding=encoding)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        
        if content is None:
            raise UnicodeDecodeError(
                "utf-8", b"", 0, 1, 
                f"Nem sikerült beolvasni a fájlt: {file_path}"
            )
        
        return self.parse_content(content)
    
    def parse_content(self, content: str) -> List[SRTEntry]:
        """
        SRT tartalom feldolgozása stringből.
        
        Args:
            content: SRT tartalom string
            
        Returns:
            SRTEntry objektumok listája
        """
        self.entries = []
        self.errors = []
        
        # Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        
        # Split into blocks (empty line separates entries)
        blocks = re.split(r"\n\n+", content.strip())
        
        for block_num, block in enumerate(blocks, 1):
            entry = self._parse_block(block, block_num)
            if entry:
                self.entries.append(entry)
        
        return self.entries
    
    def _parse_block(self, block: str, block_num: int) -> Optional[SRTEntry]:
        """
        Egyetlen SRT blokk feldolgozása.
        
        Args:
            block: SRT blokk string
            block_num: Blokk sorszáma (hibakezeléshez)
            
        Returns:
            SRTEntry vagy None, ha hiba történt
        """
        lines = block.strip().split("\n")
        
        if len(lines) < 2:
            return None
        
        # Find index line
        index = None
        time_line_idx = 0
        
        # First line might be index
        if self.INDEX_PATTERN.match(lines[0].strip()):
            index = int(lines[0].strip())
            time_line_idx = 1
        
        if time_line_idx >= len(lines):
            self.errors.append(f"Blokk {block_num}: Hiányzó idősor")
            return None
        
        # Parse time line
        time_match = self.TIME_PATTERN.match(lines[time_line_idx].strip())
        if not time_match:
            self.errors.append(f"Blokk {block_num}: Érvénytelen időformátum")
            return None
        
        try:
            time_in_ms = timecode_to_ms(time_match.group(1))
            time_out_ms = timecode_to_ms(time_match.group(2))
        except ValueError as e:
            self.errors.append(f"Blokk {block_num}: {str(e)}")
            return None
        
        # Remaining lines are text
        text_lines = lines[time_line_idx + 1:]
        text = "\n".join(line.strip() for line in text_lines if line.strip())
        
        # Clean up common SRT artifacts
        text = self._clean_text(text)
        
        # Use block number as index if not found
        if index is None:
            index = block_num
        
        return SRTEntry(
            index=index,
            time_in_ms=time_in_ms,
            time_out_ms=time_out_ms,
            text=text
        )
    
    def _clean_text(self, text: str) -> str:
        """
        SRT szöveg tisztítása.
        
        Eltávolít:
        - HTML tag-eket (<i>, <b>, stb.)
        - ASS stílus kódokat ({\\an8}, stb.)
        - Felesleges whitespace-t
        """
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        
        # Remove ASS style codes
        text = re.sub(r"\{[^}]+\}", "", text)
        
        # Clean up whitespace
        text = " ".join(text.split())
        
        return text.strip()
    
    def get_cues(self, project_id: int = 1) -> List[Cue]:
        """
        Parse-olt bejegyzések konvertálása Cue objektumokká.
        
        Args:
            project_id: Projekt azonosító
            
        Returns:
            Cue objektumok listája
        """
        return [entry.to_cue(project_id) for entry in self.entries]
    
    def has_errors(self) -> bool:
        """
        Voltak-e hibák a parse-olás során.
        """
        return len(self.errors) > 0


def parse_srt_file(file_path: Path, project_id: int = 1) -> Tuple[List[Cue], List[str]]:
    """
    Convenience function SRT fájl parse-olásához.
    
    Args:
        file_path: SRT fájl elérési útja
        project_id: Projekt azonosító
        
    Returns:
        Tuple (Cue lista, hibalista)
    """
    parser = SRTParser()
    parser.parse_file(file_path)
    return parser.get_cues(project_id), parser.errors


def export_to_srt(cues: List[Cue], use_translated: bool = True) -> str:
    """
    Cue-k exportálása SRT formátumba.
    
    Args:
        cues: Cue objektumok listája
        use_translated: Ha True, fordított szöveget használ
        
    Returns:
        SRT tartalom string
    """
    from dubsync.utils.time_utils import ms_to_timecode
    
    lines = []
    
    for i, cue in enumerate(cues, 1):
        # Index
        lines.append(str(i))
        
        # Time codes
        time_in = ms_to_timecode(cue.time_in_ms, use_comma=True)
        time_out = ms_to_timecode(cue.time_out_ms, use_comma=True)
        lines.append(f"{time_in} --> {time_out}")
        
        # Text
        text = cue.translated_text if use_translated and cue.translated_text else cue.source_text
        lines.append(text)
        
        # Empty line
        lines.append("")
    
    return "\n".join(lines)
