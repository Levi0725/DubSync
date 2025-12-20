"""
DubSync Cue Model

Cue (felirat/szinkronszöveg) adatmodell és műveletek.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from dubsync.utils.constants import CueStatus, LipSyncStatus
from dubsync.utils.time_utils import ms_to_timecode, get_duration_ms

if TYPE_CHECKING:
    from dubsync.models.database import Database


@dataclass
class Cue:
    """
    Cue (felirat/szinkronszöveg) adatmodell.
    
    Egy cue egy szinkronszöveg egység a time_in és time_out között.
    """
    
    id: int = 0
    project_id: int = 1
    cue_index: int = 0
    time_in_ms: int = 0
    time_out_ms: int = 0
    source_text: str = ""
    translated_text: str = ""
    character_name: str = ""
    notes: str = ""
    sfx_notes: str = ""  # Háttérhangok, SFX
    status: CueStatus = CueStatus.NEW
    lip_sync_ratio: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row) -> "Cue":
        """
        Adatbázis sorból Cue objektum létrehozása.
        """
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            cue_index=row["cue_index"],
            time_in_ms=row["time_in_ms"],
            time_out_ms=row["time_out_ms"],
            source_text=row["source_text"] or "",
            translated_text=row["translated_text"] or "",
            character_name=row["character_name"] or "",
            notes=row["notes"] or "",
            sfx_notes=row["sfx_notes"] or "",
            status=CueStatus(row["status"]),
            lip_sync_ratio=row["lip_sync_ratio"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    @classmethod
    def load_all(cls, db: "Database", project_id: int = 1) -> List["Cue"]:
        """
        Összes cue betöltése egy projektből.
        
        Args:
            db: Adatbázis kapcsolat
            project_id: Projekt azonosító
            
        Returns:
            Cue-k listája időrendben
        """
        rows = db.fetchall(
            "SELECT * FROM cues WHERE project_id = ? ORDER BY cue_index",
            (project_id,)
        )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def load_by_id(cls, db: "Database", cue_id: int) -> Optional["Cue"]:
        """
        Egyetlen cue betöltése azonosító alapján.
        """
        row = db.fetchone("SELECT * FROM cues WHERE id = ?", (cue_id,))
        return cls.from_row(row) if row else None
    
    @classmethod
    def find_at_time(cls, db: "Database", time_ms: int, project_id: int = 1) -> Optional["Cue"]:
        """
        Cue keresése adott időpontban.
        
        Args:
            db: Adatbázis kapcsolat
            time_ms: Időpont milliszekundumban
            project_id: Projekt azonosító
            
        Returns:
            A cue, amely tartalmazza az időpontot, vagy None
        """
        row = db.fetchone(
            """
            SELECT * FROM cues 
            WHERE project_id = ? AND time_in_ms <= ? AND time_out_ms >= ?
            ORDER BY time_in_ms
            LIMIT 1
            """,
            (project_id, time_ms, time_ms)
        )
        return cls.from_row(row) if row else None
    
    @classmethod
    def find_next_empty(cls, db: "Database", from_index: int = 0, project_id: int = 1) -> Optional["Cue"]:
        """
        Következő fordítatlan cue keresése.
        """
        row = db.fetchone(
            """
            SELECT * FROM cues 
            WHERE project_id = ? AND cue_index > ? 
              AND (translated_text IS NULL OR translated_text = '')
            ORDER BY cue_index
            LIMIT 1
            """,
            (project_id, from_index)
        )
        return cls.from_row(row) if row else None
    
    @classmethod
    def find_next_lipsync_issue(cls, db: "Database", from_index: int = 0, 
                                 project_id: int = 1, threshold: float = 1.05) -> Optional["Cue"]:
        """
        Következő lip-sync problémás cue keresése.
        """
        row = db.fetchone(
            """
            SELECT * FROM cues 
            WHERE project_id = ? AND cue_index > ? 
              AND lip_sync_ratio IS NOT NULL AND lip_sync_ratio > ?
            ORDER BY cue_index
            LIMIT 1
            """,
            (project_id, from_index, threshold)
        )
        return cls.from_row(row) if row else None
    
    @classmethod
    def count_by_status(cls, db: "Database", project_id: int = 1) -> dict:
        """
        Cue-k számlálása státusz szerint.
        
        Returns:
            Dict a státuszokkal és számokkal
        """
        rows = db.fetchall(
            """
            SELECT status, COUNT(*) as count FROM cues 
            WHERE project_id = ? GROUP BY status
            """,
            (project_id,)
        )
        return {CueStatus(row["status"]): row["count"] for row in rows}
    
    def save(self, db: "Database") -> None:
        """
        Cue mentése adatbázisba.
        """
        if self.id == 0:
            cursor = db.execute(
                """
                INSERT INTO cues 
                (project_id, cue_index, time_in_ms, time_out_ms, source_text,
                 translated_text, character_name, notes, sfx_notes, status, lip_sync_ratio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.project_id,
                    self.cue_index,
                    self.time_in_ms,
                    self.time_out_ms,
                    self.source_text,
                    self.translated_text,
                    self.character_name,
                    self.notes,
                    self.sfx_notes,
                    self.status.value,
                    self.lip_sync_ratio,
                )
            )
            self.id = cursor.lastrowid or 0
        else:
            db.execute(
                """
                UPDATE cues SET
                    cue_index = ?,
                    time_in_ms = ?,
                    time_out_ms = ?,
                    source_text = ?,
                    translated_text = ?,
                    character_name = ?,
                    notes = ?,
                    sfx_notes = ?,
                    status = ?,
                    lip_sync_ratio = ?
                WHERE id = ?
                """,
                (
                    self.cue_index,
                    self.time_in_ms,
                    self.time_out_ms,
                    self.source_text,
                    self.translated_text,
                    self.character_name,
                    self.notes,
                    self.sfx_notes,
                    self.status.value,
                    self.lip_sync_ratio,
                    self.id,
                )
            )
        db.commit()
    
    def delete(self, db: "Database") -> None:
        """
        Cue törlése adatbázisból.
        """
        if self.id > 0:
            db.execute("DELETE FROM cues WHERE id = ?", (self.id,))
            db.commit()
    
    @property
    def duration_ms(self) -> int:
        """
        Cue időtartama milliszekundumban.
        """
        return get_duration_ms(self.time_in_ms, self.time_out_ms)
    
    @property
    def duration_seconds(self) -> float:
        """
        Cue időtartama másodpercben.
        """
        return self.duration_ms / 1000.0
    
    @property
    def time_in_timecode(self) -> str:
        """
        Kezdő időkód SRT formátumban.
        """
        return ms_to_timecode(self.time_in_ms)
    
    @property
    def time_out_timecode(self) -> str:
        """
        Záró időkód SRT formátumban.
        """
        return ms_to_timecode(self.time_out_ms)
    
    @property
    def display_text(self) -> str:
        """
        Megjelenítendő szöveg (fordítás vagy forrás).
        """
        return self.translated_text or self.source_text
    
    def get_lip_sync_status(self) -> LipSyncStatus:
        """
        Lip-sync állapot lekérése.
        """
        from dubsync.utils.constants import LIPSYNC_THRESHOLD_GOOD, LIPSYNC_THRESHOLD_WARNING
        
        if self.lip_sync_ratio is None:
            return LipSyncStatus.UNKNOWN
        elif self.lip_sync_ratio <= LIPSYNC_THRESHOLD_GOOD:
            return LipSyncStatus.GOOD
        elif self.lip_sync_ratio <= LIPSYNC_THRESHOLD_WARNING:
            return LipSyncStatus.WARNING
        else:
            return LipSyncStatus.TOO_LONG
    
    def has_translation(self) -> bool:
        """
        Van-e fordítás a cue-hoz.
        """
        return bool(self.translated_text and self.translated_text.strip())
    
    def is_complete(self) -> bool:
        """
        Teljes-e a cue (van fordítás és jóváhagyva).
        """
        return self.has_translation() and self.status == CueStatus.APPROVED


@dataclass 
class CueBatch:
    """
    Több cue batch műveleteihez.
    """
    cues: List[Cue] = field(default_factory=list)
    
    @classmethod
    def save_all(cls, db: "Database", cues: List[Cue]) -> None:
        """
        Több cue mentése egyszerre (batch insert).
        """
        for cue in cues:
            cue.save(db)
    
    @classmethod
    def delete_all(cls, db: "Database", project_id: int = 1) -> None:
        """
        Összes cue törlése egy projektből.
        """
        db.execute("DELETE FROM cues WHERE project_id = ?", (project_id,))
        db.commit()
    
    @classmethod
    def reindex(cls, db: "Database", project_id: int = 1) -> None:
        """
        Cue indexek újraszámozása.
        """
        cues = Cue.load_all(db, project_id)
        for i, cue in enumerate(cues, 1):
            if cue.cue_index != i:
                cue.cue_index = i
                cue.save(db)
