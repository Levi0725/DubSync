"""
Glossary Plugin

Egyéni fordító szótár plugin a DubSync alkalmazáshoz.
Import/export .glossync fájlokkal.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QLineEdit, QDockWidget, QListWidget, QListWidgetItem,
    QApplication, QGroupBox, QDialog, QDialogButtonBox,
    QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QMessageBox, QAbstractItemView, QCheckBox, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction

from dubsync.plugins.base import UIPlugin, PluginInfo, PluginType


class GlossaryEntry:
    """Szótár bejegyzés."""
    
    def __init__(self, source: str, target: str, notes: str = ""):
        self.source = source
        self.target = target
        self.notes = notes
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "source": self.source,
            "target": self.target,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'GlossaryEntry':
        return cls(
            source=data.get("source", ""),
            target=data.get("target", ""),
            notes=data.get("notes", "")
        )


class GlossaryData:
    """Szótár adatok kezelése."""
    
    def __init__(self):
        self.entries: List[GlossaryEntry] = []
        self.name: str = "Új szótár"
        self.source_lang: str = "en"
        self.target_lang: str = "hu"
    
    def add_entry(self, source: str, target: str, notes: str = "") -> GlossaryEntry:
        """Új bejegyzés hozzáadása."""
        entry = GlossaryEntry(source, target, notes)
        self.entries.append(entry)
        return entry
    
    def remove_entry(self, entry: GlossaryEntry):
        """Bejegyzés törlése."""
        if entry in self.entries:
            self.entries.remove(entry)
    
    def find_translation(self, text: str) -> Optional[str]:
        """Fordítás keresése a szótárban."""
        text_lower = text.lower()
        for entry in self.entries:
            if entry.source.lower() == text_lower:
                return entry.target
        return None
    
    def search(self, query: str) -> List[GlossaryEntry]:
        """Bejegyzések keresése."""
        query_lower = query.lower()
        results = []
        for entry in self.entries:
            if (query_lower in entry.source.lower() or 
                query_lower in entry.target.lower() or
                query_lower in entry.notes.lower()):
                results.append(entry)
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "source_lang": self.source_lang,
            "target_lang": self.target_lang,
            "entries": [e.to_dict() for e in self.entries]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GlossaryData':
        glossary = cls()
        glossary.name = data.get("name", "Importált szótár")
        glossary.source_lang = data.get("source_lang", "en")
        glossary.target_lang = data.get("target_lang", "hu")
        for entry_data in data.get("entries", []):
            entry = GlossaryEntry.from_dict(entry_data)
            glossary.entries.append(entry)
        return glossary
    
    def save_to_file(self, path: Path):
        """Szótár mentése fájlba."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load_from_file(cls, path: Path) -> 'GlossaryData':
        """Szótár betöltése fájlból."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


class AddEditEntryDialog(QDialog):
    """Bejegyzés hozzáadása/szerkesztése dialógus."""
    
    def __init__(self, entry: Optional[GlossaryEntry] = None, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setWindowTitle("Bejegyzés szerkesztése" if entry else "Új bejegyzés")
        self.setMinimumWidth(400)
        self._setup_ui()
        
        if entry:
            self.source_edit.setText(entry.source)
            self.target_edit.setText(entry.target)
            self.notes_edit.setText(entry.notes)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Forrás szó
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Forrás (EN):"))
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("Angol szó vagy kifejezés...")
        source_layout.addWidget(self.source_edit)
        layout.addLayout(source_layout)
        
        # Cél szó
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Fordítás (HU):"))
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("Magyar fordítás...")
        target_layout.addWidget(self.target_edit)
        layout.addLayout(target_layout)
        
        # Megjegyzés
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel("Megjegyzés:"))
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Opcionális megjegyzés...")
        notes_layout.addWidget(self.notes_edit)
        layout.addLayout(notes_layout)
        
        # Gombok
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_entry(self) -> GlossaryEntry:
        """Visszaadja a szerkesztett bejegyzést."""
        return GlossaryEntry(
            source=self.source_edit.text().strip(),
            target=self.target_edit.text().strip(),
            notes=self.notes_edit.text().strip()
        )


class ImportExportDialog(QDialog):
    """Import/Export választó dialógus."""
    
    def __init__(self, entries: List[GlossaryEntry], is_import: bool = True, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.is_import = is_import
        self.selected_entries: List[GlossaryEntry] = []
        
        self.setWindowTitle("Bejegyzések importálása" if is_import else "Bejegyzések exportálása")
        self.setMinimumSize(500, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Fejléc
        header = QLabel(
            "Válaszd ki az importálandó bejegyzéseket:" if self.is_import 
            else "Válaszd ki az exportálandó bejegyzéseket:"
        )
        layout.addWidget(header)
        
        # Gyors kiválasztás gombok
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Összes kiválasztása")
        select_all_btn.clicked.connect(self._select_all)
        btn_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Kiválasztás törlése")
        select_none_btn.clicked.connect(self._select_none)
        btn_layout.addWidget(select_none_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Bejegyzések listája
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", "Forrás (EN)", "Fordítás (HU)", "Megjegyzés"])
        self.tree.setColumnWidth(0, 30)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 150)
        self.tree.header().setStretchLastSection(True)
        
        for entry in self.entries:
            item = QTreeWidgetItem()
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked)
            item.setText(1, entry.source)
            item.setText(2, entry.target)
            item.setText(3, entry.notes)
            item.setData(0, Qt.ItemDataRole.UserRole, entry)
            self.tree.addTopLevelItem(item)
        
        layout.addWidget(self.tree)
        
        # Számláló
        self.count_label = QLabel()
        self._update_count()
        layout.addWidget(self.count_label)
        
        # Gombok
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Változás figyelése
        self.tree.itemChanged.connect(lambda: self._update_count())
    
    def _select_all(self):
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(0, Qt.CheckState.Checked)
    
    def _select_none(self):
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(0, Qt.CheckState.Unchecked)
    
    def _update_count(self):
        checked = sum(
            1 for i in range(self.tree.topLevelItemCount())
            if self.tree.topLevelItem(i).checkState(0) == Qt.CheckState.Checked
        )
        self.count_label.setText(f"{checked} / {self.tree.topLevelItemCount()} kiválasztva")
    
    def _on_accept(self):
        self.selected_entries = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) == Qt.CheckState.Checked:
                entry = item.data(0, Qt.ItemDataRole.UserRole)
                self.selected_entries.append(entry)
        self.accept()


class GlossaryWidget(QWidget):
    """Szótár widget."""
    
    # Signal fordítás beillesztéshez
    insert_translation = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.glossary = GlossaryData()
        self._current_entry: Optional[GlossaryEntry] = None
        self._setup_ui()
        self._load_saved_glossary()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("📖 Szótár")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)
        
        # Kereső
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Keresés...")
        self.search_edit.textChanged.connect(self._filter_entries)
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)
        
        # Bejegyzések listája
        entries_group = QGroupBox("Bejegyzések")
        entries_layout = QVBoxLayout(entries_group)
        
        self.entries_list = QListWidget()
        self.entries_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entries_list.customContextMenuRequested.connect(self._show_context_menu)
        self.entries_list.itemDoubleClicked.connect(self._edit_entry)
        self.entries_list.currentItemChanged.connect(self._on_selection_changed)
        entries_layout.addWidget(self.entries_list)
        
        # Akció gombok
        action_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕")
        self.add_btn.setToolTip("Új bejegyzés")
        self.add_btn.setMaximumWidth(40)
        self.add_btn.clicked.connect(self._add_entry)
        action_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setToolTip("Szerkesztés")
        self.edit_btn.setMaximumWidth(40)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._edit_entry)
        action_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setToolTip("Törlés")
        self.delete_btn.setMaximumWidth(40)
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_entry)
        action_layout.addWidget(self.delete_btn)
        
        action_layout.addStretch()
        
        self.insert_btn = QPushButton("📥")
        self.insert_btn.setToolTip("Fordítás beillesztése")
        self.insert_btn.setMaximumWidth(40)
        self.insert_btn.setEnabled(False)
        self.insert_btn.clicked.connect(self._insert_translation)
        action_layout.addWidget(self.insert_btn)
        
        entries_layout.addLayout(action_layout)
        layout.addWidget(entries_group)
        
        # Import/Export gombok
        io_layout = QHBoxLayout()
        
        self.import_btn = QPushButton("📂 Import")
        self.import_btn.clicked.connect(self._import_glossary)
        io_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("💾 Export")
        self.export_btn.clicked.connect(self._export_glossary)
        io_layout.addWidget(self.export_btn)
        
        layout.addLayout(io_layout)
        
        # Státusz
        self.status_label = QLabel("0 bejegyzés")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def _update_list(self):
        """Lista frissítése."""
        self.entries_list.clear()
        
        search = self.search_edit.text().strip()
        entries = self.glossary.search(search) if search else self.glossary.entries
        
        for entry in entries:
            item = QListWidgetItem(f"{entry.source} → {entry.target}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            if entry.notes:
                item.setToolTip(f"Megjegyzés: {entry.notes}")
            self.entries_list.addItem(item)
        
        self._update_status()
    
    def _update_status(self):
        """Státusz frissítése."""
        total = len(self.glossary.entries)
        shown = self.entries_list.count()
        if shown < total:
            self.status_label.setText(f"{shown} / {total} bejegyzés")
        else:
            self.status_label.setText(f"{total} bejegyzés")
    
    def _filter_entries(self):
        """Szűrés keresés alapján."""
        self._update_list()
    
    def _on_selection_changed(self, current, previous):
        """Kiválasztás változott."""
        has_selection = current is not None
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.insert_btn.setEnabled(has_selection)
        
        if current:
            self._current_entry = current.data(Qt.ItemDataRole.UserRole)
        else:
            self._current_entry = None
    
    def _show_context_menu(self, pos):
        """Jobb-klikk menü."""
        item = self.entries_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        edit_action = menu.addAction("✏️ Szerkesztés")
        edit_action.triggered.connect(self._edit_entry)
        
        insert_action = menu.addAction("📥 Fordítás beillesztése")
        insert_action.triggered.connect(self._insert_translation)
        
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ Törlés")
        delete_action.triggered.connect(self._delete_entry)
        
        menu.exec_(self.entries_list.mapToGlobal(pos))
    
    @Slot()
    def _add_entry(self):
        """Új bejegyzés hozzáadása."""
        dialog = AddEditEntryDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            entry = dialog.get_entry()
            if entry.source and entry.target:
                self.glossary.add_entry(entry.source, entry.target, entry.notes)
                self._update_list()
                self._save_glossary()
    
    @Slot()
    def _edit_entry(self):
        """Bejegyzés szerkesztése."""
        item = self.entries_list.currentItem()
        if not item:
            return
        
        entry = item.data(Qt.ItemDataRole.UserRole)
        dialog = AddEditEntryDialog(entry, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_entry = dialog.get_entry()
            entry.source = new_entry.source
            entry.target = new_entry.target
            entry.notes = new_entry.notes
            self._update_list()
            self._save_glossary()
    
    @Slot()
    def _delete_entry(self):
        """Bejegyzés törlése."""
        item = self.entries_list.currentItem()
        if not item:
            return
        
        entry = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self, "Törlés megerősítése",
            f"Biztosan törölni akarod?\n\n{entry.source} → {entry.target}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.glossary.remove_entry(entry)
            self._update_list()
            self._save_glossary()
    
    @Slot()
    def _insert_translation(self):
        """Fordítás beillesztése."""
        if self._current_entry:
            self.insert_translation.emit(self._current_entry.target)
    
    @Slot()
    def _import_glossary(self):
        """Szótár importálása."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Szótár importálása",
            "", "DubSync Glossary (*.glossync);;JSON fájlok (*.json)"
        )
        if not file_path:
            return
        
        try:
            imported = GlossaryData.load_from_file(Path(file_path))
            
            if not imported.entries:
                QMessageBox.information(self, "Üres fájl", "A fájl nem tartalmaz bejegyzéseket.")
                return
            
            # Választó dialógus
            dialog = ImportExportDialog(imported.entries, is_import=True, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                added = 0
                for entry in dialog.selected_entries:
                    # Ellenőrizzük, nincs-e már ilyen
                    existing = None
                    for e in self.glossary.entries:
                        if e.source.lower() == entry.source.lower():
                            existing = e
                            break
                    
                    if existing:
                        # Frissítjük a meglévőt
                        existing.target = entry.target
                        existing.notes = entry.notes
                    else:
                        self.glossary.entries.append(entry)
                    added += 1
                
                self._update_list()
                self._save_glossary()
                QMessageBox.information(
                    self, "Import sikeres",
                    f"{added} bejegyzés importálva."
                )
        except Exception as e:
            QMessageBox.critical(self, "Import hiba", f"Hiba az importálás során:\n{e}")
    
    @Slot()
    def _export_glossary(self):
        """Szótár exportálása."""
        if not self.glossary.entries:
            QMessageBox.information(self, "Üres szótár", "Nincs mit exportálni.")
            return
        
        # Választó dialógus
        dialog = ImportExportDialog(self.glossary.entries, is_import=False, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        if not dialog.selected_entries:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Szótár exportálása",
            "glossary.glossync", "DubSync Glossary (*.glossync);;JSON fájlok (*.json)"
        )
        if not file_path:
            return
        
        try:
            export_data = GlossaryData()
            export_data.name = self.glossary.name
            export_data.source_lang = self.glossary.source_lang
            export_data.target_lang = self.glossary.target_lang
            export_data.entries = dialog.selected_entries
            export_data.save_to_file(Path(file_path))
            
            QMessageBox.information(
                self, "Export sikeres",
                f"{len(dialog.selected_entries)} bejegyzés exportálva."
            )
        except Exception as e:
            QMessageBox.critical(self, "Export hiba", f"Hiba az exportálás során:\n{e}")
    
    def _get_glossary_path(self) -> Path:
        """Szótár mentési útvonal."""
        from dubsync.services.settings_manager import SettingsManager
        settings = SettingsManager()
        data_dir = Path(settings.get("data_dir", str(Path.home() / ".dubsync")))
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "glossary.glossync"
    
    def _save_glossary(self):
        """Szótár mentése."""
        try:
            self.glossary.save_to_file(self._get_glossary_path())
        except Exception as e:
            print(f"Glossary save error: {e}")
    
    def _load_saved_glossary(self):
        """Mentett szótár betöltése."""
        try:
            path = self._get_glossary_path()
            if path.exists():
                self.glossary = GlossaryData.load_from_file(path)
                self._update_list()
        except Exception as e:
            print(f"Glossary load error: {e}")
    
    def find_translation(self, text: str) -> Optional[str]:
        """Fordítás keresése a szótárban."""
        return self.glossary.find_translation(text)
    
    def highlight_source_text(self, text: str):
        """Kiemeli ha van találat a szótárban."""
        self.search_edit.setText(text)


class GlossaryPlugin(UIPlugin):
    """Szótár plugin."""
    
    def __init__(self):
        super().__init__()
        self._dock: Optional[QDockWidget] = None
        self._widget: Optional[GlossaryWidget] = None
        self._plugin_dir = Path(__file__).parent
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="glossary",
            name="Szótár",
            version="1.0.0",
            author="Levente Kulacsy",
            description="Egyéni fordító szótár import/export .glossync fájlokkal",
            plugin_type=PluginType.UI,
            dependencies=[],
            icon="📖",
            readme_path="README.md"
        )
    
    def initialize(self) -> bool:
        """Plugin inicializálása."""
        return True
    
    def create_dock_widget(self) -> Optional[QDockWidget]:
        """Szótár dock widget létrehozása."""
        self._dock = QDockWidget("📖 Szótár", self._main_window)
        self._dock.setObjectName("glossaryDock")
        self._dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self._widget = GlossaryWidget()
        self._widget.insert_translation.connect(self._on_insert_translation)
        self._dock.setWidget(self._widget)
        
        return self._dock
    
    def create_menu_items(self) -> List[QAction]:
        """Menü elemek létrehozása."""
        actions = []
        
        action = QAction("📖 Szótár panel", self._main_window)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(self._toggle_dock)
        actions.append(action)
        
        return actions
    
    @Slot(str)
    def _on_insert_translation(self, text: str):
        """Fordítás beillesztése a cue editorba."""
        if self._main_window:
            editor = getattr(self._main_window, 'cue_editor', None)
            if editor:
                editor.insert_text(text)
    
    @Slot(bool)
    def _toggle_dock(self, checked: bool):
        """Dock ki-be kapcsolása."""
        if self._dock:
            self._dock.setVisible(checked)
    
    def on_cue_selected(self, cue) -> None:
        """Cue kiválasztás esemény."""
        if self._widget and cue and hasattr(cue, 'source_text'):
            # Keresés a forrás szövegben
            pass
    
    def get_widget(self) -> Optional[GlossaryWidget]:
        """Widget visszaadása."""
        return self._widget


# Plugin exportálása
Plugin = GlossaryPlugin
