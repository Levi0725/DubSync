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
from dubsync.i18n import t

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from dubsync.ui.main_window import MainWindow


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
        header = QLabel(t("plugins.csv_export.header"))
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # Beállítások
        settings_group = QGroupBox(t("plugins.csv_export.settings"))
        form = QFormLayout(settings_group)

        # Elválasztó karakter
        self.delimiter_combo = QComboBox()
        self.delimiter_combo.addItem(t("plugins.csv_export.delimiter_semicolon"), ";")
        self.delimiter_combo.addItem(t("plugins.csv_export.delimiter_comma"), ",")
        self.delimiter_combo.addItem(t("plugins.csv_export.delimiter_tab"), "\t")
        form.addRow(t("plugins.csv_export.delimiter"), self.delimiter_combo)

        self.include_source_cb = self._extracted_from__setup_ui_23(
            "plugins.csv_export.include_source", form
        )
        self.include_timecodes_cb = self._extracted_from__setup_ui_23(
            "plugins.csv_export.include_timecodes", form
        )
        self.include_character_cb = self._extracted_from__setup_ui_23(
            "plugins.csv_export.include_character", form
        )
        self.include_notes_cb = self._extracted_from__setup_ui_23(
            "plugins.csv_export.include_notes", form
        )
        self.include_sfx_cb = self._extracted_from__setup_ui_23(
            "plugins.csv_export.include_sfx", form
        )
        layout.addWidget(settings_group)

        # Export gomb
        self.export_btn = QPushButton(t("plugins.csv_export.export_button"))
        self.export_btn.clicked.connect(self._on_export)
        layout.addWidget(self.export_btn)

        layout.addStretch()

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_23(self, arg0, form):
        # Tartalom beállítások
        result = QCheckBox(t(arg0))
        result.setChecked(True)
        form.addRow("", result)

        return result
    
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
        
        main_window: "MainWindow" = self.plugin._main_window  # type: ignore
        pm = main_window.project_manager
        if not pm.is_open:
            QMessageBox.warning(
                self,
                t("plugins.csv_export.no_project_title"),
                t("plugins.csv_export.no_project_message")
            )
            return
        
        # Fájl választás
        project = pm.project
        if project is None:
            return
        default_name = project.title or "export"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("plugins.csv_export.file_dialog_title"),
            f"{default_name}.csv",
            t("plugins.csv_export.file_filter")
        )
        
        if not file_path:
            return
        
        # Export
        cues = pm.get_cues()
        options = self.get_options()
        
        if self.plugin.export(Path(file_path), project, cues, options):
            QMessageBox.information(
                self,
                t("plugins.csv_export.success_title"),
                t("plugins.csv_export.success_message", path=file_path)
            )
        else:
            QMessageBox.critical(
                self,
                t("plugins.csv_export.error_title"),
                t("plugins.csv_export.error_message")
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
            id="csv_export",
            name=t("plugins.csv_export.name"),
            version="1.1.0",
            author="Levente Kulacsy",
            description=t("plugins.csv_export.description"),
            plugin_type=PluginType.EXPORT,
            icon="",
            readme_path="README.md"
        )
    
    @property
    def file_extension(self) -> str:
        return ".csv"
    
    @property
    def file_filter(self) -> str:
        return t("plugins.csv_export.file_filter")
    
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
                header = [t("plugins.csv_export.csv_headers.index")]
                if include_timecodes:
                    header.extend([
                        t("plugins.csv_export.csv_headers.start"),
                        t("plugins.csv_export.csv_headers.end")
                    ])
                if include_character:
                    header.append(t("plugins.csv_export.csv_headers.character"))
                if include_source:
                    header.append(t("plugins.csv_export.csv_headers.source"))
                header.append(t("plugins.csv_export.csv_headers.translation"))
                if include_notes:
                    header.append(t("plugins.csv_export.csv_headers.notes"))
                if include_sfx:
                    header.append(t("plugins.csv_export.csv_headers.sfx"))
                
                writer.writerow(header)
                
                # Adatok
                for cue in cues:
                    row: List[Any] = [cue.cue_index]
                    
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
        # CSV Export menüpont
        export_action = QAction(t("plugins.csv_export.menu_item"), self._main_window)
        export_action.setShortcut("Ctrl+Shift+C")
        export_action.triggered.connect(self._on_export_menu)
        return [export_action]
    
    def _on_export_menu(self):
        """Export menüből indítva."""
        if not self._main_window:
            return
        
        main_window: "MainWindow" = self._main_window  # type: ignore
        pm = main_window.project_manager
        if not pm.is_open:
            QMessageBox.warning(
                self._main_window,
                t("plugins.csv_export.no_project_title"),
                t("plugins.csv_export.no_project_message")
            )
            return
        
        # Fájl választás
        project = pm.project
        if project is None:
            return
        default_name = project.title or "export"
        file_path, _ = QFileDialog.getSaveFileName(
            self._main_window,
            t("plugins.csv_export.file_dialog_title"),
            f"{default_name}.csv",
            t("plugins.csv_export.file_filter")
        )
        
        if not file_path:
            return
        
        # Export alapértelmezett beállításokkal
        cues = pm.get_cues()
        
        if self.export(Path(file_path), project, cues):
            QMessageBox.information(
                self._main_window,
                t("plugins.csv_export.success_title"),
                t("plugins.csv_export.success_message", path=file_path)
            )
        else:
            QMessageBox.critical(
                self._main_window,
                t("plugins.csv_export.error_title"),
                t("plugins.csv_export.error_message")
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
