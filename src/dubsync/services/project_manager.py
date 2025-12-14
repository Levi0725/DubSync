"""
DubSync Project Manager

Projekt kezelő szolgáltatás.
Projekt létrehozás, megnyitás, mentés, import műveletek.
"""

import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

from dubsync.models.database import Database, init_database
from dubsync.models.project import Project
from dubsync.models.cue import Cue, CueBatch
from dubsync.services.srt_parser import SRTParser, parse_srt_file
from dubsync.services.lip_sync import LipSyncEstimator
from dubsync.services.settings_manager import SettingsManager
from dubsync.utils.constants import PROJECT_EXTENSION


class ProjectManager:
    """
    Projekt kezelő osztály.
    
    Kezeli a projekt fájlokat és az adatbázis kapcsolatot.
    """
    
    def __init__(self):
        """
        Inicializálás.
        """
        self.db: Optional[Database] = None
        self.project_path: Optional[Path] = None
        self.project: Optional[Project] = None
        self._dirty: bool = False
    
    @property
    def is_open(self) -> bool:
        """Van-e megnyitott projekt."""
        return self.db is not None and self.project is not None
    
    @property
    def is_dirty(self) -> bool:
        """Vannak-e mentetlen változások."""
        return self._dirty
    
    def mark_dirty(self):
        """Projekt megjelölése módosítottként."""
        self._dirty = True
    
    def mark_clean(self):
        """Projekt megjelölése mentettként."""
        self._dirty = False
    
    def new_project(self, project_path: Optional[Path] = None) -> Project:
        """
        Új projekt létrehozása.
        
        Args:
            project_path: Projekt fájl elérési útja (opcionális)
            
        Returns:
            Új Project objektum
        """
        # Close existing project
        self.close()
        
        # Create database
        self.project_path = project_path
        self.db = Database(project_path)
        init_database(self.db)
        
        # Load project
        self.project = Project.load(self.db, 1)
        
        # Alapértelmezett fordító név beállítása a beállításokból
        settings = SettingsManager()
        default_name = settings.default_author_name
        if default_name and not self.project.translator:
            self.project.translator = default_name
            self.project.save(self.db)
        
        self._dirty = project_path is None  # New unsaved project is dirty
        
        return self.project
    
    def open_project(self, project_path: Path) -> Project:
        """
        Meglévő projekt megnyitása.
        
        Args:
            project_path: Projekt fájl elérési útja
            
        Returns:
            Project objektum
            
        Raises:
            FileNotFoundError: Ha a fájl nem létezik
        """
        if not project_path.exists():
            raise FileNotFoundError(f"A projekt nem található: {project_path}")
        
        # Close existing project
        self.close()
        
        # Open database
        self.project_path = project_path
        self.db = Database(project_path)
        
        # Load project
        self.project = Project.load(self.db, 1)
        if self.project is None:
            raise ValueError("Érvénytelen projekt fájl")
        
        self._dirty = False
        return self.project
    
    def save_project(self, project_path: Optional[Path] = None) -> Path:
        """
        Projekt mentése.
        
        Args:
            project_path: Új elérési út (Save As)
            
        Returns:
            Mentett fájl elérési útja
            
        Raises:
            ValueError: Ha nincs megnyitott projekt
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        # If no path provided, use the current one
        target_path = project_path or self.project_path
        
        if target_path is None:
            raise ValueError("Nincs megadva mentési útvonal")
        
        # Save project data first
        self.project.save(self.db)
        self.db.commit()
        
        # If the database is in memory or we're saving to a new location
        if self.db.db_path is None or (project_path is not None and project_path != self.project_path):
            # We need to create a new file
            # First, backup the in-memory data by creating a new file database
            import sqlite3
            
            # Create new database file
            new_conn = sqlite3.connect(str(target_path))
            
            # Copy all data from current connection to new file
            self.db.connection.backup(new_conn)
            new_conn.close()
            
            # Close old connection and reopen from file
            self.db.close()
            self.db = Database(target_path)
            self.project = Project.load(self.db, 1)
            self.project_path = target_path
        
        self._dirty = False
        return target_path
    
    def close(self):
        """
        Projekt bezárása.
        """
        if self.db:
            self.db.close()
        
        self.db = None
        self.project_path = None
        self.project = None
        self._dirty = False
    
    def import_srt(
        self,
        srt_path: Path,
        clear_existing: bool = True,
        calculate_lipsync: bool = True,
    ) -> Tuple[int, List[str]]:
        """
        SRT fájl importálása a projektbe.
        
        Args:
            srt_path: SRT fájl elérési útja
            clear_existing: Meglévő cue-k törlése
            calculate_lipsync: Lip-sync számítás
            
        Returns:
            Tuple (importált cue-k száma, hibák listája)
            
        Raises:
            ValueError: Ha nincs megnyitott projekt
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        # Parse SRT
        cues, errors = parse_srt_file(srt_path, self.project.id)
        
        if not cues:
            return 0, errors if errors else ["Nem található felirat a fájlban"]
        
        # Clear existing cues if requested
        if clear_existing:
            CueBatch.delete_all(self.db, self.project.id)
        
        # Calculate lip-sync if requested
        if calculate_lipsync:
            estimator = LipSyncEstimator()
            for cue in cues:
                estimator.update_cue_ratio(cue)
        
        # Save cues
        CueBatch.save_all(self.db, cues)
        
        self.mark_dirty()
        return len(cues), errors
    
    def get_cues(self) -> List[Cue]:
        """
        Összes cue lekérése a projektből.
        
        Returns:
            Cue lista
        """
        if not self.is_open:
            return []
        
        return Cue.load_all(self.db, self.project.id)
    
    def get_cue(self, cue_id: int) -> Optional[Cue]:
        """
        Egyetlen cue lekérése.
        """
        if not self.is_open:
            return None
        
        return Cue.load_by_id(self.db, cue_id)
    
    def save_cue(self, cue: Cue) -> None:
        """
        Cue mentése.
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        cue.save(self.db)
        self.mark_dirty()
    
    def delete_cue(self, cue_id: int) -> None:
        """
        Cue törlése azonosító alapján.
        
        Args:
            cue_id: Cue azonosító
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        cue = Cue.load_by_id(self.db, cue_id)
        if cue:
            cue.delete(self.db)
            CueBatch.reindex(self.db, self.project.id)
            self.mark_dirty()
    
    def add_new_cue(self) -> Cue:
        """
        Új cue hozzáadása a lista végére.
        
        Returns:
            Új Cue objektum
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        cues = self.get_cues()
        next_index = len(cues) + 1
        
        # Calculate time based on last cue
        if cues:
            last_cue = cues[-1]
            time_in = last_cue.time_out_ms + 100
            time_out = time_in + 2000  # 2 sec default
        else:
            time_in = 0
            time_out = 2000
        
        cue = Cue(
            project_id=self.project.id,
            cue_index=next_index,
            time_in_ms=time_in,
            time_out_ms=time_out,
            source_text="",
            translated_text="",
        )
        cue.save(self.db)
        self.mark_dirty()
        return cue
    
    def insert_cue_at(self, index: int) -> Cue:
        """
        Cue beszúrása adott pozícióba.
        
        Args:
            index: Pozíció (1-től)
            
        Returns:
            Új Cue objektum
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        cues = self.get_cues()
        
        # Shift indices
        for cue in cues:
            if cue.cue_index >= index:
                cue.cue_index += 1
                cue.save(self.db)
        
        # Calculate time based on adjacent cues
        prev_cue = None
        next_cue = None
        for cue in cues:
            if cue.cue_index == index:
                next_cue = cue
            elif cue.cue_index == index - 1:
                prev_cue = cue
        
        if prev_cue and next_cue:
            time_in = prev_cue.time_out_ms + 50
            time_out = next_cue.time_in_ms - 50
            if time_out <= time_in:
                time_out = time_in + 1000
        elif prev_cue:
            time_in = prev_cue.time_out_ms + 100
            time_out = time_in + 2000
        elif next_cue:
            time_out = next_cue.time_in_ms - 100
            time_in = max(0, time_out - 2000)
        else:
            time_in = 0
            time_out = 2000
        
        cue = Cue(
            project_id=self.project.id,
            cue_index=index,
            time_in_ms=time_in,
            time_out_ms=time_out,
            source_text="",
            translated_text="",
        )
        cue.save(self.db)
        self.mark_dirty()
        return cue
    
    def update_project(self, **kwargs) -> None:
        """
        Projekt adatok frissítése.
        
        Args:
            **kwargs: Frissítendő mezők
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        for key, value in kwargs.items():
            if hasattr(self.project, key):
                setattr(self.project, key, value)
        
        self.project.save(self.db)
        self.mark_dirty()
    
    def recalculate_all_lipsync(self) -> int:
        """
        Összes cue lip-sync újraszámítása.
        
        Returns:
            Frissített cue-k száma
        """
        if not self.is_open:
            return 0
        
        cues = self.get_cues()
        estimator = LipSyncEstimator()
        
        for cue in cues:
            estimator.update_cue_ratio(cue)
            cue.save(self.db)
        
        self.mark_dirty()
        return len(cues)
    
    def get_statistics(self) -> dict:
        """
        Projekt statisztikák lekérése.
        
        Returns:
            Dict a statisztikákkal
        """
        if not self.is_open:
            return {}
        
        cues = self.get_cues()
        status_counts = Cue.count_by_status(self.db, self.project.id)
        
        total = len(cues)
        translated = sum(1 for c in cues if c.has_translation())
        lipsync_issues = sum(
            1 for c in cues 
            if c.lip_sync_ratio and c.lip_sync_ratio > 1.05
        )
        
        return {
            "total_cues": total,
            "translated_cues": translated,
            "untranslated_cues": total - translated,
            "lipsync_issues": lipsync_issues,
            "status_counts": status_counts,
            "completion_percent": (translated / total * 100) if total > 0 else 0,
        }


def get_project_filter() -> str:
    """
    Projekt fájl szűrő dialógusokhoz.
    """
    return f"DubSync projekt (*{PROJECT_EXTENSION});;Minden fájl (*.*)"


def get_srt_filter() -> str:
    """
    SRT fájl szűrő dialógusokhoz.
    """
    return "SRT felirat (*.srt);;Minden fájl (*.*)"


def get_video_filter() -> str:
    """
    Videó fájl szűrő dialógusokhoz.
    """
    return "Videó fájlok (*.mp4 *.mkv *.avi *.mov *.webm);;Minden fájl (*.*)"
