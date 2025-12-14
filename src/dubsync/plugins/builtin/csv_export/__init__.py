"""
DubSync CSV Export Plugin

CSV formátumú export plugin UI-val.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import csv

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QCheckBox, QComboBox, QLineEdit,
    QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from dubsync.plugins.base import ExportPlugin, UIPlugin, PluginInfo, PluginType
from dubsync.models.project import Project
from dubsync.models.cue import Cue
from dubsync.utils.time_utils import ms_to_timecode


class CSVExportOptionsWidget(QWidget):
    """CSV export beállítások widget."""
    
    def __init__(self, plugin: 'CSVExportPlugin', parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("📊 CSV Export")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)
        
        # Beállítások
        settings_group = QGroupBox("Beállítások")
        form = QFormLayout(settings_group)
        
        # Elválasztó karakter
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItem("Pontosvessző (;)", ";")
        self.delimiter_combo.addItem("Vessző (,)", ",")
        self.delimiter_combo.addItem("Tabulátor", "\t")
        form.addRow("Elválasztó:", self.delimiter_combo)
        
        # Tartalom beállítások
        self.include_source_cb = QCheckBox("Forrás szöveg")
        self.include_source_cb.setChecked(True)
        form.addRow("", self.include_source_cb)
        
        self.include_timecodes_cb = QCheckBox("Időkódok")
        self.include_timecodes_cb.setChecked(True)
        form.addRow("", self.include_timecodes_cb)
        
        self.include_character_cb = QCheckBox("Karakter nevek")
        self.include_character_cb.setChecked(True)
        form.addRow("", self.include_character_cb)
        
        self.include_notes_cb = QCheckBox("Megjegyzések")
        self.include_notes_cb.setChecked(True)
        form.addRow("", self.include_notes_cb)
        
        self.include_sfx_cb = QCheckBox("SFX jegyzetek")
        self.include_sfx_cb.setChecked(True)
        form.addRow("", self.include_sfx_cb)
        
        layout.addWidget(settings_group)
        
        # Export gomb
        self.export_btn = QPushButton("📊 Exportálás CSV-be...")
        self.export_btn.clicked.connect(self._on_export)
        layout.addWidget(self.export_btn)
        
        layout.addStretch()
    
    def get_options(self) -> Dict[str, Any]:
        """Beállítások lekérése."""
        return {
            "delimiter": self.delimiter_combo.currentData(),
            "include_source": self.include_source_cb.isChecked(),
            "include_timecodes": self.include_timecodes_cb.isChecked(),
            "include_character": self.include_character_cb.isChecked(),
            "include_notes": self.include_notes_cb.isChecked(),
            "include_sfx": self.include_sfx_cb.isChecked(),
        }
    
    def _on_export(self):
        """Export gomb kezelése."""
        if not self.plugin._main_window:
            return
        
        pm = self.plugin._main_window.project_manager
        if not pm.is_open:
            QMessageBox.warning(
                self,
                "Nincs projekt",
                "Nincs megnyitott projekt az exportáláshoz."
            )
            return
        
        # Fájl választás
        default_name = pm.project.title or "export"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "CSV Exportálás",
            f"{default_name}.csv",
            "CSV fájl (*.csv)"
        )
        
        if not file_path:
            return
        
        # Export
        project = pm.project
        cues = pm.get_cues()
        options = self.get_options()
        
        if self.plugin.export(Path(file_path), project, cues, options):
            QMessageBox.information(
                self,
                "Export sikeres",
                f"A fájl sikeresen exportálva:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                self,
                "Export hiba",
                "Hiba történt az exportálás során."
            )


class CSVExportPlugin(ExportPlugin, UIPlugin):
    """
    CSV export plugin UI-val.
    
    Cue-k exportálása CSV formátumba részletes beállításokkal.
    """
    
    def __init__(self):
        super().__init__()
        self._widget: Optional[CSVExportOptionsWidget] = None
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="builtin.export.csv",
            name="CSV Export",
            version="1.1.0",
            author="Levente Kulacsy",
            description="Cue-k exportálása CSV formátumba",
            plugin_type=PluginType.EXPORT,
            icon="📊",
            readme_path="README.md"
        )
    
    @property
    def file_extension(self) -> str:
        return ".csv"
    
    @property
    def file_filter(self) -> str:
        return "CSV fájl (*.csv)"
    
    def export(
        self,
        output_path: Path,
        project: Project,
        cues: List[Cue],
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """CSV export végrehajtása."""
        options = options or {}
        
        delimiter = options.get("delimiter", ";")
        include_source = options.get("include_source", True)
        include_timecodes = options.get("include_timecodes", True)
        include_character = options.get("include_character", True)
        include_notes = options.get("include_notes", True)
        include_sfx = options.get("include_sfx", True)
        
        try:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=delimiter)
                
                # Header építése
                header = ["#"]
                if include_timecodes:
                    header.extend(["Kezdés", "Vége"])
                if include_character:
                    header.append("Karakter")
                if include_source:
                    header.append("Forrás")
                header.append("Fordítás")
                if include_notes:
                    header.append("Megjegyzés")
                if include_sfx:
                    header.append("SFX")
                
                writer.writerow(header)
                
                # Adatok
                for cue in cues:
                    row = [cue.cue_index]
                    
                    if include_timecodes:
                        row.extend([
                            ms_to_timecode(cue.time_in_ms),
                            ms_to_timecode(cue.time_out_ms)
                        ])
                    
                    if include_character:
                        row.append(cue.character_name or "")
                    
                    if include_source:
                        row.append(cue.source_text or "")
                    
                    row.append(cue.translated_text or "")
                    
                    if include_notes:
                        row.append(cue.notes or "")
                    
                    if include_sfx:
                        row.append(getattr(cue, 'sfx_notes', '') or "")
                    
                    writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"CSV export hiba: {e}")
            return False
    
    # UIPlugin interfész
    
    def create_menu_items(self) -> List[QAction]:
        """Menü elemek létrehozása."""
        actions = []
        
        # CSV Export menüpont
        export_action = QAction("📊 CSV Export...", self._main_window)
        export_action.setShortcut("Ctrl+Shift+C")
        export_action.triggered.connect(self._on_export_menu)
        actions.append(export_action)
        
        return actions
    
    def _on_export_menu(self):
        """Export menüből indítva."""
        if not self._main_window:
            return
        
        pm = self._main_window.project_manager
        if not pm.is_open:
            QMessageBox.warning(
                self._main_window,
                "Nincs projekt",
                "Nincs megnyitott projekt az exportáláshoz."
            )
            return
        
        # Fájl választás
        default_name = pm.project.title or "export"
        file_path, _ = QFileDialog.getSaveFileName(
            self._main_window,
            "CSV Exportálás",
            f"{default_name}.csv",
            "CSV fájl (*.csv)"
        )
        
        if not file_path:
            return
        
        # Export alapértelmezett beállításokkal
        project = pm.project
        cues = pm.get_cues()
        
        if self.export(Path(file_path), project, cues):
            QMessageBox.information(
                self._main_window,
                "Export sikeres",
                f"A fájl sikeresen exportálva:\n{file_path}"
            )
        else:
            QMessageBox.critical(
                self._main_window,
                "Export hiba",
                "Hiba történt az exportálás során."
            )
    
    def get_settings_widget(self) -> Optional[QWidget]:
        """Beállítások widget a settings dialoghoz."""
        return CSVExportOptionsWidget(self)
    
    def get_long_description(self) -> str:
        """README tartalom."""
        from pathlib import Path
        readme_path = Path(__file__).parent / "README.md"
        if readme_path.exists():
            return readme_path.read_text(encoding='utf-8')
        return self.info.description


# Plugin export
Plugin = CSVExportPlugin
