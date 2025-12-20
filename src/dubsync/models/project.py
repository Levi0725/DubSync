"""
DubSync Project Model

Project data model and operations.
"""


import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from dubsync.models.database import Database


@dataclass
class Project:
    """
    Project data model.
    
    The project contains all metadata and settings.
    """
    
    id: int = 0
    title: str = "New Project"
    series_title: str = ""
    season: str = ""
    episode: str = ""
    episode_title: str = ""
    translator: str = ""
    editor: str = ""
    video_path: str = ""
    frame_rate: float = 25.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row) -> "Project":
        """
        Create Project object from database row.
        """
        # Handle missing episode_title column for older databases
        episode_title = ""
        with contextlib.suppress(KeyError, IndexError):
            episode_title = row["episode_title"] or ""
        return cls(
            id=row["id"],
            title=row["title"] or "",
            series_title=row["series_title"] or "",
            season=row["season"] or "",
            episode=row["episode"] or "",
            episode_title=episode_title,
            translator=row["translator"] or "",
            editor=row["editor"] or "",
            video_path=row["video_path"] or "",
            frame_rate=row["frame_rate"] or 25.0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    @classmethod
    def load(cls, db: "Database", project_id: int = 1) -> Optional["Project"]:
        """
        Load project from database.
        
        Args:
            db: Database connection
            project_id: Project ID (default: 1)
            
        Returns:
            Project object or None
        """
        row = db.fetchone(
            "SELECT * FROM project WHERE id = ?",
            (project_id,)
        )
        return cls.from_row(row) if row else None
    
    def save(self, db: "Database") -> None:
        """
        Save project to database.
        
        Args:
            db: Database connection
        """
        if self.id == 0:
            # Insert new project
            cursor = db.execute(
                """
                INSERT INTO project 
                (title, series_title, season, episode, episode_title, translator, editor, video_path, frame_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.title,
                    self.series_title,
                    self.season,
                    self.episode,
                    self.episode_title,
                    self.translator,
                    self.editor,
                    self.video_path,
                    self.frame_rate,
                )
            )
            self.id = cursor.lastrowid or 0
        else:
            # Update existing project
            db.execute(
                """
                UPDATE project SET
                    title = ?,
                    series_title = ?,
                    season = ?,
                    episode = ?,
                    episode_title = ?,
                    translator = ?,
                    editor = ?,
                    video_path = ?,
                    frame_rate = ?
                WHERE id = ?
                """,
                (
                    self.title,
                    self.series_title,
                    self.season,
                    self.episode,
                    self.episode_title,
                    self.translator,
                    self.editor,
                    self.video_path,
                    self.frame_rate,
                    self.id,
                )
            )
        db.commit()
    
    def get_display_title(self) -> str:
        """
        Generate display title.
        
        Returns:
            Formatted title with series information
        """
        parts = []
        
        if self.series_title:
            parts.append(self.series_title)
        
        if self.season or self.episode:
            season_ep = []
            if self.season:
                season_ep.append(f"S{self.season}")
            if self.episode:
                season_ep.append(f"E{self.episode}")
            if season_ep:
                parts.append("".join(season_ep))
        
        if self.episode_title:
            parts.append(f'"{self.episode_title}"')
        elif self.title and self.title != "New Project":
            parts.append(f'"{self.title}"')
        
        return " - ".join(parts) if parts else "New Project"
    
    def has_video(self) -> bool:
        """
        Check if a video is set.
        """
        return bool(self.video_path) and Path(self.video_path).exists()
