"""
Spellchecker Plugin

Magyar helyesírás-ellenőrző plugin a DubSync alkalmazáshoz.
"""


import contextlib
import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QLineEdit, QDockWidget, QListWidget, QListWidgetItem,
    QApplication, QGroupBox, QMessageBox, QMenu, QInputDialog,
    QSplitter, QFileDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QAction, QTextCursor, QTextCharFormat, QColor

from dubsync.plugins.base import UIPlugin, PluginInfo, PluginType, PluginDependency
from dubsync.i18n import t


class SpellcheckerEngine:
    """Helyesírás-ellenőrző motor."""
    
    def __init__(self):
        self._dictionary: Any = None
        self._available = False
        self._error_message = ""
        self._custom_words: Set[str] = set()
        self._ignored_words: Set[str] = set()
        self._load_dictionary()
    
    def _load_dictionary(self):
        """Magyar szótár betöltése."""
        try:
            from spylls.hunspell import Dictionary # type: ignore
            
            # Próbáljuk betölteni a magyar szótárt
            # A spylls automatikusan megkeresi a rendszer szótárakat
            try:
                self._dictionary = Dictionary.from_files('hu_HU')
                self._available = True
            except Exception:
                # Próbáljuk a plugin könyvtárából
                plugin_dir = Path(__file__).parent
                dict_path = plugin_dir / "dictionaries" / "hu_HU"
                
                if (dict_path.with_suffix('.dic')).exists():
                    self._dictionary = Dictionary.from_files(str(dict_path))
                    self._available = True
                else:
                    self._error_message = "Magyar szótár nem található"
                    self._available = False
                    
        except ImportError:
            self._error_message = "spylls csomag nincs telepítve (pip install spylls)"
            self._available = False
        except Exception as e:
            self._error_message = str(e)
            self._available = False
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    @property
    def error_message(self) -> str:
        return self._error_message
    
    def check_word(self, word: str) -> bool:
        """Szó ellenőrzése."""
        if not self._available:
            return True
        
        # Normalizálás
        clean_word = word.strip().lower()
        
        # Figyelmen kívül hagyott szavak
        if clean_word in self._ignored_words:
            return True
        
        # Egyéni szavak
        if clean_word in self._custom_words:
            return True
        
        # Számok és speciális karakterek
        if not clean_word or clean_word.isdigit():
            return True
        
        # Hunspell ellenőrzés
        return self._dictionary.lookup(word)
    
    def suggest(self, word: str) -> List[str]:
        """Javaslatok hibás szóhoz."""
        if not self._available:
            return []
        
        try:
            suggestions = list(self._dictionary.suggest(word))
            return suggestions[:5]  # Max 5 javaslat
        except Exception:
            return []
    
    def add_to_ignore(self, word: str):
        """Szó hozzáadása a figyelmen kívül hagyott listához."""
        self._ignored_words.add(word.lower())
    
    def remove_from_ignore(self, word: str):
        """Szó eltávolítása a figyelmen kívül hagyott listából."""
        self._ignored_words.discard(word.lower())
    
    def add_custom_word(self, word: str):
        """Egyéni szó hozzáadása."""
        self._custom_words.add(word.lower())
    
    def remove_custom_word(self, word: str):
        """Egyéni szó törlése."""
        self._custom_words.discard(word.lower())
    
    def get_ignored_words(self) -> List[str]:
        """Figyelmen kívül hagyott szavak listája."""
        return sorted(self._ignored_words)
    
    def get_custom_words(self) -> List[str]:
        """Egyéni szavak listája."""
        return sorted(self._custom_words)
    
    def save_words(self, path: Path):
        """Szavak mentése."""
        data = {
            "ignored": list(self._ignored_words),
            "custom": list(self._custom_words)
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_words(self, path: Path):
        """Szavak betöltése."""
        if not path.exists():
            return

        with contextlib.suppress(Exception):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._ignored_words = set(data.get("ignored", []))
            self._custom_words = set(data.get("custom", []))


class SpellingError:
    """Helyesírási hiba."""
    
    def __init__(self, word: str, position: int, suggestions: List[str]):
        self.word = word
        self.position = position
        self.suggestions = suggestions


class SpellcheckerWidget(QWidget):
    """Helyesírás-ellenőrző widget."""
    
    # Signal a szöveg kiemeléshez
    highlight_error = Signal(str, int)  # word, position
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = SpellcheckerEngine()
        self._errors: List[SpellingError] = []
        self._current_text = ""
        self._setup_ui()
        self._load_saved_words()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel(t("plugins.spellchecker.header"))
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)
        
        # Státusz
        if self.engine.is_available:
            self.status_label = QLabel(t("plugins.spellchecker.status_ok"))
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        else:
            self.status_label = QLabel(t("plugins.spellchecker.status_error", error=self.engine.error_message))
            self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Splitter a hibák és kivételek között
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Hibák csoport
        errors_group = QGroupBox(t("plugins.spellchecker.errors_group"))
        errors_layout = QVBoxLayout(errors_group)
        
        self.errors_list = QListWidget()
        self.errors_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.errors_list.customContextMenuRequested.connect(self._show_error_menu)
        self.errors_list.itemClicked.connect(self._on_error_clicked)
        errors_layout.addWidget(self.errors_list)
        
        # Hiba akció gombok
        error_btn_layout = QHBoxLayout()
        
        self.ignore_btn = QPushButton(t("plugins.spellchecker.ignore_btn"))
        self.ignore_btn.setToolTip(t("plugins.spellchecker.ignore_tooltip"))
        self.ignore_btn.setEnabled(False)
        self.ignore_btn.clicked.connect(self._ignore_word)
        error_btn_layout.addWidget(self.ignore_btn)
        
        self.add_word_btn = QPushButton(t("plugins.spellchecker.add_word_btn"))
        self.add_word_btn.setToolTip(t("plugins.spellchecker.add_word_tooltip"))
        self.add_word_btn.setEnabled(False)
        self.add_word_btn.clicked.connect(self._add_word_to_dict)
        error_btn_layout.addWidget(self.add_word_btn)
        
        errors_layout.addLayout(error_btn_layout)
        splitter.addWidget(errors_group)
        
        # Kivételek csoport
        ignored_group = QGroupBox(t("plugins.spellchecker.ignored_group"))
        ignored_layout = QVBoxLayout(ignored_group)
        
        self.ignored_list = QListWidget()
        self.ignored_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ignored_list.customContextMenuRequested.connect(self._show_ignored_menu)
        ignored_layout.addWidget(self.ignored_list)
        
        # Kivétel akció gombok
        ignored_btn_layout = QHBoxLayout()
        
        self.add_ignored_btn = QPushButton("➕")
        self.add_ignored_btn.setToolTip(t("plugins.spellchecker.add_ignored_tooltip"))
        self.add_ignored_btn.setMaximumWidth(40)
        self.add_ignored_btn.clicked.connect(self._add_ignored_manually)
        ignored_btn_layout.addWidget(self.add_ignored_btn)
        
        self.remove_ignored_btn = QPushButton("🗑️")
        self.remove_ignored_btn.setToolTip(t("plugins.spellchecker.remove_ignored_tooltip"))
        self.remove_ignored_btn.setMaximumWidth(40)
        self.remove_ignored_btn.setEnabled(False)
        self.remove_ignored_btn.clicked.connect(self._remove_ignored)
        ignored_btn_layout.addWidget(self.remove_ignored_btn)
        
        ignored_btn_layout.addStretch()
        ignored_layout.addLayout(ignored_btn_layout)
        splitter.addWidget(ignored_group)
        
        layout.addWidget(splitter)
        
        # Ellenőrzés gomb
        self.check_btn = QPushButton(t("plugins.spellchecker.check_btn"))
        self.check_btn.clicked.connect(self._request_check)
        layout.addWidget(self.check_btn)
        
        # Import/Export
        io_layout = QHBoxLayout()
        
        self.import_btn = QPushButton(t("plugins.spellchecker.import_btn"))
        self.import_btn.clicked.connect(self._import_words)
        io_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton(t("plugins.spellchecker.export_btn"))
        self.export_btn.clicked.connect(self._export_words)
        io_layout.addWidget(self.export_btn)
        
        layout.addLayout(io_layout)
        
        # Lista kiválasztás figyelése
        self.ignored_list.currentItemChanged.connect(
            lambda c, p: self.remove_ignored_btn.setEnabled(c is not None)
        )
        self.errors_list.currentItemChanged.connect(self._on_error_selection_changed)
        
        self._update_ignored_list()
    
    def _update_ignored_list(self):
        """Kivételek lista frissítése."""
        self.ignored_list.clear()
        for word in self.engine.get_ignored_words():
            self.ignored_list.addItem(word)
        
        # Egyéni szavak is
        for word in self.engine.get_custom_words():
            item = QListWidgetItem(f"📝 {word}")
            item.setData(Qt.ItemDataRole.UserRole, word)
            self.ignored_list.addItem(item)
    
    def _on_error_selection_changed(self, current, previous):
        """Hiba kiválasztás változott."""
        has_selection = current is not None
        self.ignore_btn.setEnabled(has_selection)
        self.add_word_btn.setEnabled(has_selection)
    
    def _on_error_clicked(self, item):
        """Hibára kattintás."""
        if error := item.data(Qt.ItemDataRole.UserRole):
            self.highlight_error.emit(error.word, error.position)
    
    def _show_error_menu(self, pos):
        """Hiba kontextus menü."""
        item = self.errors_list.itemAt(pos)
        if not item:
            return

        error = item.data(Qt.ItemDataRole.UserRole)
        if not error:
            return

        menu = QMenu(self)

        # Javaslatok
        if error.suggestions:
            for suggestion in error.suggestions:
                action = menu.addAction(f"➡️ {suggestion}")
                action.setData(("replace", suggestion))
            menu.addSeparator()

        ignore_action = menu.addAction(t("plugins.spellchecker.context_ignore"))
        ignore_action.setData(("ignore", error.word))

        add_action = menu.addAction(t("plugins.spellchecker.context_add"))
        add_action.setData(("add", error.word))

        action = menu.exec_(self.errors_list.mapToGlobal(pos))
        if action and action.data():
            cmd, word = action.data()
            if cmd == "ignore":
                self.engine.add_to_ignore(word)
                self._extracted_from__show_error_menu_31()
            elif cmd == "add":
                self.engine.add_custom_word(word)
                self._extracted_from__show_error_menu_31()

    # TODO Rename this here and in `_show_error_menu`
    def _extracted_from__show_error_menu_31(self):
        self._save_words()
        self._update_ignored_list()
        self._recheck_current()
    
    def _show_ignored_menu(self, pos):
        """Kivételek kontextus menü."""
        item = self.ignored_list.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        remove_action = menu.addAction("🗑️ Törlés")
        
        action = menu.exec_(self.ignored_list.mapToGlobal(pos))
        if action == remove_action:
            self._remove_ignored()
    
    @Slot()
    def _ignore_word(self):
        """Kiválasztott szó figyelmen kívül hagyása."""
        item = self.errors_list.currentItem()
        if not item:
            return

        if error := item.data(Qt.ItemDataRole.UserRole):
            self.engine.add_to_ignore(error.word)
            self._save_words()
            self._update_ignored_list()
            self._recheck_current()
    
    @Slot()
    def _add_word_to_dict(self):
        """Szó hozzáadása az egyéni szótárhoz."""
        item = self.errors_list.currentItem()
        if not item:
            return

        if error := item.data(Qt.ItemDataRole.UserRole):
            self.engine.add_custom_word(error.word)
            self._save_words()
            self._update_ignored_list()
            self._recheck_current()
    
    @Slot()
    def _add_ignored_manually(self):
        """Kézi kivétel hozzáadása."""
        word, ok = QInputDialog.getText(
            self, "Új kivétel",
            "Szó, amit figyelmen kívül hagyunk:"
        )
        if ok and word:
            self.engine.add_to_ignore(word.strip())
            self._save_words()
            self._update_ignored_list()
            self._recheck_current()
    
    @Slot()
    def _remove_ignored(self):
        """Kivétel törlése."""
        item = self.ignored_list.currentItem()
        if not item:
            return
        
        word = item.data(Qt.ItemDataRole.UserRole) or item.text()
        if word.startswith("📝 "):
            word = word[3:]
            self.engine.remove_custom_word(word)
        else:
            self.engine.remove_from_ignore(word)
        
        self._save_words()
        self._update_ignored_list()
        self._recheck_current()
    
    @Slot()
    def _request_check(self):
        """Ellenőrzés kérése."""
        # Ez a signal-on keresztül fog működni a main window-val
        pass
    
    def check_text(self, text: str) -> List[SpellingError]:
        """Szöveg ellenőrzése."""
        self._current_text = text
        self._errors = []
        self.errors_list.clear()
        
        if not self.engine.is_available:
            return []
        
        # Szavak kinyerése
        word_pattern = re.compile(r'\b([a-záéíóöőúüű]+)\b', re.IGNORECASE)
        
        for match in word_pattern.finditer(text):
            word = match.group(1)
            if not self.engine.check_word(word):
                suggestions = self.engine.suggest(word)
                error = SpellingError(word, match.start(), suggestions)
                self._errors.append(error)
                
                # Lista elemhez
                item_text = word
                if suggestions:
                    item_text += f" → {', '.join(suggestions[:3])}"
                item = QListWidgetItem(f"❌ {item_text}")
                item.setData(Qt.ItemDataRole.UserRole, error)
                self.errors_list.addItem(item)
        
        # Státusz frissítése
        if self._errors:
            self.status_label.setText(f"⚠️ {len(self._errors)} hiba találva")
            self.status_label.setStyleSheet("color: #ff9800; font-size: 11px;")
        else:
            self.status_label.setText("✅ Nincs helyesírási hiba")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
        
        return self._errors
    
    def _recheck_current(self):
        """Újraellenőrzés."""
        if self._current_text:
            self.check_text(self._current_text)
    
    def get_errors(self) -> List[SpellingError]:
        """Hibák visszaadása."""
        return self._errors
    
    def _get_words_path(self) -> Path:
        """Szavak mentési útvonal."""
        from dubsync.services.settings_manager import SettingsManager
        settings = SettingsManager()
        data_dir = Path(settings.get("data_dir", str(Path.home() / ".dubsync")))
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "spellcheck_words.json"
    
    def _save_words(self):
        """Szavak mentése."""
        try:
            self.engine.save_words(self._get_words_path())
        except Exception as e:
            print(f"Spellcheck words save error: {e}")
    
    def _load_saved_words(self):
        """Mentett szavak betöltése."""
        try:
            self.engine.load_words(self._get_words_path())
            self._update_ignored_list()
        except Exception as e:
            print(f"Spellcheck words load error: {e}")
    
    @Slot()
    def _import_words(self):
        """Szavak importálása."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Szavak importálása",
            "", "JSON fájlok (*.json)"
        )
        if not file_path:
            return
        
        try:
            self.engine.load_words(Path(file_path))
            self._update_ignored_list()
            self._save_words()
            QMessageBox.information(self, "Import sikeres", "Szavak importálva.")
        except Exception as e:
            QMessageBox.critical(self, "Import hiba", f"Hiba: {e}")
    
    @Slot()
    def _export_words(self):
        """Szavak exportálása."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Szavak exportálása",
            "spellcheck_words.json", "JSON fájlok (*.json)"
        )
        if not file_path:
            return
        
        try:
            self.engine.save_words(Path(file_path))
            QMessageBox.information(self, "Export sikeres", "Szavak exportálva.")
        except Exception as e:
            QMessageBox.critical(self, "Export hiba", f"Hiba: {e}")


class SpellcheckerPlugin(UIPlugin):
    """Helyesírás-ellenőrző plugin."""
    
    def __init__(self):
        super().__init__()
        self._dock: Optional[QDockWidget] = None
        self._widget: Optional[SpellcheckerWidget] = None
        self._plugin_dir = Path(__file__).parent
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="spellchecker",
            name=t("plugins.spellchecker.name"),
            version="1.0.0",
            author="Levente Kulacsy",
            description=t("plugins.spellchecker.description"),
            plugin_type=PluginType.UI,
            dependencies=[
                PluginDependency("spylls", "0.1.5", optional=True),
            ],
            icon="",
            readme_path="README.md"
        )
    
    def initialize(self) -> bool:
        """Plugin inicializálása."""
        return super().initialize()  # Locale fájlok betöltése
    
    def create_dock_widget(self) -> Optional[QDockWidget]:
        """Helyesírás dock widget létrehozása."""
        self._dock = QDockWidget(t("plugins.spellchecker.header"), self._main_window)
        self._dock.setObjectName("spellcheckerDock")
        self._dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self._widget = SpellcheckerWidget()
        self._widget.highlight_error.connect(self._on_highlight_error)
        self._dock.setWidget(self._widget)
        
        return self._dock
    
    def create_menu_items(self) -> List[QAction]:
        """Menü elemek létrehozása."""
        action = QAction(t("plugins.spellchecker.panel"), self._main_window)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(self._toggle_dock)
        return [action]
    
    @Slot(str, int)
    def _on_highlight_error(self, word: str, position: int):
        """Hiba kiemelése."""
        # TODO: Integráció a cue editorral
        pass
    
    @Slot(bool)
    def _toggle_dock(self, checked: bool):
        """Dock ki-be kapcsolása."""
        if self._dock:
            self._dock.setVisible(checked)
    
    def on_cue_selected(self, cue) -> None:
        """Cue kiválasztás esemény - ellenőrzés."""
        if self._widget and cue:
            if target_text := getattr(cue, 'target_text', None):
                self._widget.check_text(target_text)
            
    def get_widget(self) -> Optional[SpellcheckerWidget]:
        """Widget visszaadása."""
        return self._widget
    
    # sourcery skip: merge-nested-ifs
    def check_text(self, text: str) -> List[SpellingError]:
        """Szöveg ellenőrzése."""
        return self._widget.check_text(text) if self._widget else []


# Plugin exportálása
Plugin = SpellcheckerPlugin
