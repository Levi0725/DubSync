"""
DubSync Comment Model

Comment data model and operations.
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
    Comment data model.
    
    Comments are associated with cues and function as threads.
    """
    
    id: int = 0
    cue_id: int = 0
    author: str = "User"
    content: str = ""
    status: CommentStatus = CommentStatus.OPEN
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row) -> "Comment":
        """
        Create a Comment object from a database row.
        """
        return cls(
            id=row["id"],
            cue_id=row["cue_id"],
            author=row["author"] or "User",
            content=row["content"] or "",
            status=CommentStatus(row["status"]),
            created_at=row["created_at"],
        )
    
    @classmethod
    def load_for_cue(cls, db: "Database", cue_id: int) -> List["Comment"]:
        """
        Load comments for a cue.
        
        Args:
            db: Database connection
            cue_id: Cue identifier
            
        Returns:
            List of comments in chronological order
        """
        rows = db.fetchall(
            "SELECT * FROM comments WHERE cue_id = ? ORDER BY created_at",
            (cue_id,)
        )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def load_open_comments(cls, db: "Database", cue_id: int) -> List["Comment"]:
        """
        Load open comments.
        """
        rows = db.fetchall(
            "SELECT * FROM comments WHERE cue_id = ? AND status = ? ORDER BY created_at",
            (cue_id, CommentStatus.OPEN.value)
        )
        return [cls.from_row(row) for row in rows]
    
    @classmethod
    def count_open_for_cue(cls, db: "Database", cue_id: int) -> int:
        """
        Count of open comments for a cue.
        """
        row = db.fetchone(
            "SELECT COUNT(*) as count FROM comments WHERE cue_id = ? AND status = ?",
            (cue_id, CommentStatus.OPEN.value)
        )
        return row["count"] if row else 0
    
    @classmethod
    def count_all_open(cls, db: "Database", project_id: int = 1) -> int:
        """
        Count of all open comments in the project.
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
        Cue IDs that have open comments.
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
        Save comment to the database.
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
            self.id = cursor.lastrowid or 0
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
        Delete comment.
        """
        if self.id > 0:
            db.execute("DELETE FROM comments WHERE id = ?", (self.id,))
            db.commit()
    
    def resolve(self, db: "Database") -> None:
        """
        Resolve comment.
        """
        self.status = CommentStatus.RESOLVED
        self.save(db)
    
    def reopen(self, db: "Database") -> None:
        """
        Reopen comment.
        """
        self.status = CommentStatus.OPEN
        self.save(db)
    
    @property
    def is_open(self) -> bool:
        """
        Is the comment open?
        """
        return self.status == CommentStatus.OPEN
    
    @property
    def is_resolved(self) -> bool:
        """
        Is the comment resolved?
        """
        return self.status == CommentStatus.RESOLVED
