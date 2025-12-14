"""
DubSync Comment Model

Megjegyzések (kommentek) adatmodell és műveletek.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from dubsync.utils.constants import CommentStatus

if TYPE_CHECKING:
    from dubsync.models.database import Database


@dataclass
class Comment:
    """
    Megjegyzés adatmodell.
    
    A megjegyzések cue-khoz kapcsolódnak és thread-ként működnek.
    """
    
    id: int = 0
    cue_id: int = 0
    author: str = "Felhasználó"
    content: str = ""
    status: CommentStatus = CommentStatus.OPEN
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row) -> "Comment":
        """
        Adatbázis sorból Comment objektum létrehozása.
        """
        return cls(
            id=row["id"],
            cue_id=row["cue_id"],
            author=row["author"] or "Felhasználó",
            content=row["content"] or "",
            status=CommentStatus(row["status"]),
            created_at=row["created_at"],
        )
    
    @classmethod
    def load_for_cue(cls, db: "Database", cue_id: int) -> List["Comment"]:
        """
        Megjegyzések betöltése egy cue-hoz.
        
        Args:
            db: Adatbázis kapcsolat
            cue_id: Cue azonosító
            
        Returns:
            Megjegyzések listája időrendben
        """
        rows = db.fetchall(
            "SELECT * FROM comments WHERE cue_id = ? ORDER BY created_at",
            (cue_id,)
        )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def load_open_comments(cls, db: "Database", cue_id: int) -> List["Comment"]:
        """
        Nyitott megjegyzések betöltése.
        """
        rows = db.fetchall(
            "SELECT * FROM comments WHERE cue_id = ? AND status = ? ORDER BY created_at",
            (cue_id, CommentStatus.OPEN.value)
        )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def count_open_for_cue(cls, db: "Database", cue_id: int) -> int:
        """
        Nyitott megjegyzések száma egy cue-hoz.
        """
        row = db.fetchone(
            "SELECT COUNT(*) as count FROM comments WHERE cue_id = ? AND status = ?",
            (cue_id, CommentStatus.OPEN.value)
        )
        return row["count"] if row else 0
    
    @classmethod
    def count_all_open(cls, db: "Database", project_id: int = 1) -> int:
        """
        Összes nyitott megjegyzés száma a projektben.
        """
        row = db.fetchone(
            """
            SELECT COUNT(*) as count FROM comments c
            JOIN cues cu ON c.cue_id = cu.id
            WHERE cu.project_id = ? AND c.status = ?
            """,
            (project_id, CommentStatus.OPEN.value)
        )
        return row["count"] if row else 0
    
    @classmethod
    def get_cue_ids_with_comments(cls, db: "Database", project_id: int = 1) -> List[int]:
        """
        Azon cue-k azonosítói, amelyekhez van nyitott megjegyzés.
        """
        rows = db.fetchall(
            """
            SELECT DISTINCT c.cue_id FROM comments c
            JOIN cues cu ON c.cue_id = cu.id
            WHERE cu.project_id = ? AND c.status = ?
            """,
            (project_id, CommentStatus.OPEN.value)
        )
        return [row["cue_id"] for row in rows]
    
    def save(self, db: "Database") -> None:
        """
        Megjegyzés mentése adatbázisba.
        """
        if self.id == 0:
            cursor = db.execute(
                """
                INSERT INTO comments (cue_id, author, content, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    self.cue_id,
                    self.author,
                    self.content,
                    self.status.value,
                )
            )
            self.id = cursor.lastrowid
        else:
            db.execute(
                """
                UPDATE comments SET
                    author = ?,
                    content = ?,
                    status = ?
                WHERE id = ?
                """,
                (
                    self.author,
                    self.content,
                    self.status.value,
                    self.id,
                )
            )
        db.commit()
    
    def delete(self, db: "Database") -> None:
        """
        Megjegyzés törlése.
        """
        if self.id > 0:
            db.execute("DELETE FROM comments WHERE id = ?", (self.id,))
            db.commit()
    
    def resolve(self, db: "Database") -> None:
        """
        Megjegyzés lezárása.
        """
        self.status = CommentStatus.RESOLVED
        self.save(db)
    
    def reopen(self, db: "Database") -> None:
        """
        Megjegyzés újranyitása.
        """
        self.status = CommentStatus.OPEN
        self.save(db)
    
    @property
    def is_open(self) -> bool:
        """
        Nyitott-e a megjegyzés.
        """
        return self.status == CommentStatus.OPEN
    
    @property
    def is_resolved(self) -> bool:
        """
        Lezárt-e a megjegyzés.
        """
        return self.status == CommentStatus.RESOLVED
