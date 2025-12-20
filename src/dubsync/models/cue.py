"""
DubSync Cue Model

Cue (subtitle/dubbing text) data model and operations.
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
    Cue (subtitle/dubbing text) data model.
    
    A cue is a unit of dubbing text between time_in and time_out.
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
    sfx_notes: str = ""  # Background sounds, SFX
    status: CueStatus = CueStatus.NEW
    lip_sync_ratio: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row) -> "Cue":
        """
        Create a Cue object from a database row.
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
        Load all cues from a project.
        
        Args:
            db: Database connection
            project_id: Project identifier
            
        Returns:
            List of cues in chronological order
        """
        rows = db.fetchall(
            "SELECT * FROM cues WHERE project_id = ? ORDER BY cue_index",
            (project_id,)
        )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def load_by_id(cls, db: "Database", cue_id: int) -> Optional["Cue"]:
        """
        Load a single cue by its identifier.
        """
        row = db.fetchone("SELECT * FROM cues WHERE id = ?", (cue_id,))
        return cls.from_row(row) if row else None
    
    @classmethod
    def find_at_time(cls, db: "Database", time_ms: int, project_id: int = 1) -> Optional["Cue"]:
        """
        Search for a cue at a given time.
        
        Args:
            db: Database connection
            time_ms: Time in milliseconds
            project_id: Project identifier
            
        Returns:
            A cue that contains the time, or None
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
        Find the next untranslated cue.
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
        Find the next lip-sync issue cue.
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
        Count cues by status.
        
        Returns:
            Dict with statuses and counts
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
        Save cue to the database.
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
        Delete cue from the database.
        """
        if self.id > 0:
            db.execute("DELETE FROM cues WHERE id = ?", (self.id,))
            db.commit()
    
    @property
    def duration_ms(self) -> int:
        """
        Cue duration in milliseconds.
        """
        return get_duration_ms(self.time_in_ms, self.time_out_ms)
    
    @property
    def duration_seconds(self) -> float:
        """
        Cue duration in seconds.
        """
        return self.duration_ms / 1000.0
    
    @property
    def time_in_timecode(self) -> str:
        """
        Start timecode in SRT format.
        """
        return ms_to_timecode(self.time_in_ms)
    
    @property
    def time_out_timecode(self) -> str:
        """
        End timecode in SRT format.
        """
        return ms_to_timecode(self.time_out_ms)
    
    @property
    def display_text(self) -> str:
        """
        Display text (translation or source).
        """
        return self.translated_text or self.source_text
    
    def get_lip_sync_status(self) -> LipSyncStatus:
        """
        Get lip-sync status.
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
        Check if the cue has a translation.
        """
        return bool(self.translated_text and self.translated_text.strip())
    
    def is_complete(self) -> bool:
        """
        Check if the cue is complete (has translation and is approved).
        """
        return self.has_translation() and self.status == CueStatus.APPROVED


@dataclass 
class CueBatch:
    """
    For batch operations on multiple cues.
    """
    cues: List[Cue] = field(default_factory=list)
    
    @classmethod
    def save_all(cls, db: "Database", cues: List[Cue]) -> None:
        """
        Save multiple cues at once (batch insert).
        """
        for cue in cues:
            cue.save(db)
    
    @classmethod
    def delete_all(cls, db: "Database", project_id: int = 1) -> None:
        """
        Delete all cues from a project.
        """
        db.execute("DELETE FROM cues WHERE project_id = ?", (project_id,))
        db.commit()
    
    @classmethod
    def reindex(cls, db: "Database", project_id: int = 1) -> None:
        """
        Reindex cue indices.
        """
        cues = Cue.load_all(db, project_id)
        for i, cue in enumerate(cues, 1):
            if cue.cue_index != i:
                cue.cue_index = i
                cue.save(db)
