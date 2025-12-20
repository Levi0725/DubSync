"""
DubSync Project Manager

Projekt kezelő szolgáltatás.
Projekt létrehozás, megnyitás, mentés, import műveletek.
"""

from pathlib import Path
from typing import Optional, List, Tuple
import sqlite3

from dubsync.models.database import Database, init_database
from dubsync.models.project import Project
from dubsync.models.cue import Cue, CueBatch
from dubsync.services.srt_parser import parse_srt_file
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
    
    def _get_db(self) -> Database:
        """Get database, raising if not open."""
        if self.db is None:
            raise ValueError("Nincs megnyitott projekt")
        return self.db
    
    def _get_project(self) -> Project:
        """Get project, raising if not open."""
        if self.project is None:
            raise ValueError("Nincs megnyitott projekt")
        return self.project
    
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
        
        if self.project is None:
            raise ValueError("Nem sikerült létrehozni a projektet")
        
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

        db = self._get_db()
        proj = self._get_project()

        # If no path provided, use the current one
        target_path = project_path or self.project_path

        if target_path is None:
            raise ValueError("Nincs megadva mentési útvonal")

        # Save project data first
        proj.save(db)
        db.commit()

        # If the database is in memory or we're saving to a new location
        if db.db_path is None or (project_path is not None and project_path != self.project_path):
            self._extracted_from_save_project_33(target_path, db)
        self._dirty = False
        return target_path

    # TODO Rename this here and in `save_project`
    def _extracted_from_save_project_33(self, target_path, db):
        # Create new database file
        new_conn = sqlite3.connect(str(target_path))

        # Copy all data from current connection to new file
        db.connection.backup(new_conn)
        new_conn.close()

        # Close old connection and reopen from file
        db.close()
        self.db = Database(target_path)
        self.project = Project.load(self.db, 1)
        self.project_path = target_path
    
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
        
        db = self._get_db()
        proj = self._get_project()
        
        # Parse SRT
        cues, errors = parse_srt_file(srt_path, proj.id)
        
        if not cues:
            return 0, errors or ["Nem található felirat a fájlban"]
        
        # Clear existing cues if requested
        if clear_existing:
            CueBatch.delete_all(db, proj.id)
        
        # Calculate lip-sync if requested
        if calculate_lipsync:
            estimator = LipSyncEstimator()
            for cue in cues:
                estimator.update_cue_ratio(cue)
        
        # Save cues
        CueBatch.save_all(db, cues)
        
        self.mark_dirty()
        return len(cues), errors
    
    def get_cues(self) -> List[Cue]:
        """
        Összes cue lekérése a projektből.
        
        Returns:
            Cue lista
        """
        return Cue.load_all(self._get_db(), self._get_project().id) if self.is_open else []
    
    def get_cue(self, cue_id: int) -> Optional[Cue]:
        """
        Egyetlen cue lekérése.
        """
        return Cue.load_by_id(self._get_db(), cue_id) if self.is_open else None
    
    def save_cue(self, cue: Cue) -> None:
        """
        Cue mentése.
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        cue.save(self._get_db())
        self.mark_dirty()
    
    def delete_cue(self, cue_id: int) -> None:
        """
        Cue törlése azonosító alapján.
        
        Args:
            cue_id: Cue azonosító
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        db = self._get_db()
        proj = self._get_project()
        
        if cue := Cue.load_by_id(db, cue_id):
            cue.delete(db)
            CueBatch.reindex(db, proj.id)
            self.mark_dirty()
    
    def add_new_cue(self, time_in_ms: Optional[int] = None) -> Cue:
        """
        Új cue hozzáadása a lista végére.
        
        Args:
            time_in_ms: Opcionális kezdési idő (pl. videó pozícióból)
        
        Returns:
            Új Cue objektum
        """
        if not self.is_open:
            raise ValueError("Nincs megnyitott projekt")
        
        db = self._get_db()
        proj = self._get_project()
        
        cues = self.get_cues()
        next_index = len(cues) + 1
        
        # Calculate time based on parameter or last cue
        if time_in_ms is not None:
            # Check if time overlaps with existing cue
            overlapping = any(
                cue.time_in_ms <= time_in_ms < cue.time_out_ms
                for cue in cues
            )
            
            if overlapping:
                # Fall back to default behavior (after last cue)
                if cues:
                    last_cue = cues[-1]
                    time_in = last_cue.time_out_ms + 100
                    time_out = time_in + 2000
                else:
                    time_in = 0
                    time_out = 2000
            else:
                time_in = time_in_ms
                time_out = time_in + 2000  # 2 sec default
        elif cues:
            last_cue = cues[-1]
            time_in = last_cue.time_out_ms + 100
            time_out = time_in + 2000  # 2 sec default
        else:
            time_in = 0
            time_out = 2000
        
        cue = self._create_cue(proj.id, next_index, time_in, time_out)
        cue.save(db)
        self.mark_dirty()
        return cue
        
    def _create_cue(
        self,
        project_id: int,
        cue_index: int,
        time_in: int,
        time_out: int
    ) -> Cue:
        """Helper method to create a new Cue object."""
        return Cue(
            project_id=project_id,
            cue_index=cue_index,
            time_in_ms=time_in,
            time_out_ms=time_out,
            source_text="",
            translated_text="",
        )

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
        
        db = self._get_db()
        proj = self._get_project()
        
        cues = self.get_cues()
        
        # Shift indices
        for cue in cues:
            if cue.cue_index >= index:
                cue.cue_index += 1
                cue.save(db)
        
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
        
        cue = self._create_cue(proj.id, index, time_in, time_out)
        cue.save(db)
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
        
        db = self._get_db()
        proj = self._get_project()
        
        for key, value in kwargs.items():
            if hasattr(proj, key):
                setattr(proj, key, value)
        
        proj.save(db)
        self.mark_dirty()
    
    def recalculate_all_lipsync(self) -> int:
        """
        Összes cue lip-sync újraszámítása.
        
        Returns:
            Frissített cue-k száma
        """
        if not self.is_open:
            return 0
        
        db = self._get_db()
        cues = self.get_cues()
        estimator = LipSyncEstimator()
        
        for cue in cues:
            estimator.update_cue_ratio(cue)
            cue.save(db)
        
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
        
        db = self._get_db()
        proj = self._get_project()
        
        cues = self.get_cues()
        status_counts = Cue.count_by_status(db, proj.id)
        
        total = len(cues)
        translated = sum(c.has_translation() for c in cues)
        lipsync_issues = sum(
            c.lip_sync_ratio is not None and c.lip_sync_ratio > 1.05
            for c in cues
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
