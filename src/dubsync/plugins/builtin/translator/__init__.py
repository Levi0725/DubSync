"""
Argos Translator Plugin

Offline fordító plugin a DubSync alkalmazáshoz.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QComboBox, QDockWidget, QFormLayout, QSpinBox,
    QFrame, QApplication, QGroupBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QThread, QTimer
from PySide6.QtGui import QAction

from dubsync.plugins.base import (
    UIPlugin, TranslationPlugin, PluginInfo, PluginType, PluginDependency
)


class TranslatorWorker(QThread):
    """Háttérszál a fordításhoz."""
    
    translation_done = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, text: str, source_lang: str, target_lang: str):
        super().__init__()
        self.text = text
        self.source_lang = source_lang
        self.target_lang = target_lang
    
    def run(self):
        try:
            import argostranslate.translate
            
            translated = argostranslate.translate.translate(
                self.text,
                self.source_lang,
                self.target_lang
            )
            self.translation_done.emit(translated)
        except Exception as e:
            self.error_occurred.emit(str(e))


class TranslatorWidget(QWidget):
    """Fordító widget."""
    
    insert_translation = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[TranslatorWorker] = None
        self._translate_timer = QTimer()
        self._translate_timer.setSingleShot(True)
        self._translate_timer.timeout.connect(self._do_translate)
        self._delay_ms = 500
        
        self._source_lang = "en"
        self._target_lang = "hu"
        self._models_loaded = False
        
        self._setup_ui()
        self._check_models()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("🌍 Argos Fordító")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)
        
        # Státusz
        self.status_label = QLabel("Modellek ellenőrzése...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Forrás nyelv
        source_group = QGroupBox("Forrás szöveg (angol)")
        source_layout = QVBoxLayout(source_group)
        
        self.source_text = QTextEdit()
        self.source_text.setPlaceholderText("Írd ide az angol szöveget...")
        self.source_text.setMaximumHeight(120)
        self.source_text.textChanged.connect(self._on_text_changed)
        source_layout.addWidget(self.source_text)
        
        layout.addWidget(source_group)
        
        # Fordítás gomb
        btn_layout = QHBoxLayout()
        
        self.translate_btn = QPushButton("🔄 Fordítás")
        self.translate_btn.clicked.connect(self._do_translate)
        btn_layout.addWidget(self.translate_btn)
        
        btn_layout.addStretch()
        
        self.swap_btn = QPushButton("⇅")
        self.swap_btn.setMaximumWidth(40)
        self.swap_btn.setToolTip("Nyelvek felcserélése")
        self.swap_btn.clicked.connect(self._swap_languages)
        btn_layout.addWidget(self.swap_btn)
        
        layout.addLayout(btn_layout)
        
        # Cél nyelv
        target_group = QGroupBox("Fordítás (magyar)")
        target_layout = QVBoxLayout(target_group)
        
        self.target_text = QTextEdit()
        self.target_text.setPlaceholderText("A fordítás itt jelenik meg...")
        self.target_text.setReadOnly(True)
        self.target_text.setMaximumHeight(120)
        target_layout.addWidget(self.target_text)
        
        layout.addWidget(target_group)
        
        # Akció gombok
        action_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("📋 Másolás")
        self.copy_btn.clicked.connect(self._copy_translation)
        action_layout.addWidget(self.copy_btn)
        
        self.insert_btn = QPushButton("📥 Beillesztés fordításba")
        self.insert_btn.clicked.connect(self._insert_translation)
        action_layout.addWidget(self.insert_btn)
        
        layout.addLayout(action_layout)
        
        layout.addStretch()
    
    def _check_models(self):
        """Nyelvi modellek ellenőrzése."""
        try:
            import argostranslate.package
            import argostranslate.translate
            
            # Telepített nyelvek lekérése
            installed = argostranslate.translate.get_installed_languages()
            lang_codes = [lang.code for lang in installed]
            
            if "en" in lang_codes and "hu" in lang_codes:
                self._models_loaded = True
                self.status_label.setText("✅ Angol-Magyar modell betöltve")
                self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            else:
                self.status_label.setText("⚠️ Nyelvi modellek letöltése szükséges...")
                self.status_label.setStyleSheet("color: #ff9800; font-size: 11px;")
                self._download_models()
                
        except ImportError:
            self.status_label.setText("❌ argostranslate nincs telepítve")
            self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")
            self.translate_btn.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"❌ Hiba: {e}")
            self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")
    
    def _download_models(self):
        """Nyelvi modellek letöltése."""
        try:
            import argostranslate.package
            
            # Elérhető csomagok frissítése
            argostranslate.package.update_package_index()
            available = argostranslate.package.get_available_packages()
            
            # Angol-Magyar keresése
            for pkg in available:
                if pkg.from_code == "en" and pkg.to_code == "hu":
                    self.status_label.setText("⏳ Angol→Magyar modell letöltése...")
                    argostranslate.package.install_from_path(pkg.download())
                    break
            
            for pkg in available:
                if pkg.from_code == "hu" and pkg.to_code == "en":
                    self.status_label.setText("⏳ Magyar→Angol modell letöltése...")
                    argostranslate.package.install_from_path(pkg.download())
                    break
            
            self._models_loaded = True
            self.status_label.setText("✅ Modellek telepítve")
            self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            
        except Exception as e:
            self.status_label.setText(f"❌ Letöltési hiba: {e}")
            self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")
    
    def _on_text_changed(self):
        """Szöveg változott - késleltetett fordítás."""
        self._translate_timer.start(self._delay_ms)
    
    @Slot()
    def _do_translate(self):
        """Fordítás végrehajtása."""
        if not self._models_loaded:
            return
        
        text = self.source_text.toPlainText().strip()
        if not text:
            self.target_text.clear()
            return
        
        self.status_label.setText("⏳ Fordítás...")
        self.status_label.setStyleSheet("color: #2196F3; font-size: 11px;")
        
        self._worker = TranslatorWorker(text, self._source_lang, self._target_lang)
        self._worker.translation_done.connect(self._on_translation_done)
        self._worker.error_occurred.connect(self._on_translation_error)
        self._worker.start()
    
    @Slot(str)
    def _on_translation_done(self, translated: str):
        """Fordítás kész."""
        self.target_text.setPlainText(translated)
        self.status_label.setText("✅ Fordítás kész")
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
    
    @Slot(str)
    def _on_translation_error(self, error: str):
        """Fordítási hiba."""
        self.status_label.setText(f"❌ {error}")
        self.status_label.setStyleSheet("color: #f44336; font-size: 11px;")
    
    @Slot()
    def _swap_languages(self):
        """Nyelvek felcserélése."""
        self._source_lang, self._target_lang = self._target_lang, self._source_lang
        
        # Címkék frissítése
        if self._source_lang == "en":
            self.source_text.parentWidget().setTitle("Forrás szöveg (angol)")
            self.target_text.parentWidget().setTitle("Fordítás (magyar)")
        else:
            self.source_text.parentWidget().setTitle("Forrás szöveg (magyar)")
            self.target_text.parentWidget().setTitle("Fordítás (angol)")
        
        # Szövegek cseréje
        source = self.source_text.toPlainText()
        target = self.target_text.toPlainText()
        self.source_text.setPlainText(target)
        self.target_text.setPlainText(source)
    
    @Slot()
    def _copy_translation(self):
        """Fordítás másolása vágólapra."""
        text = self.target_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.status_label.setText("📋 Vágólapra másolva!")
    
    @Slot()
    def _insert_translation(self):
        """Fordítás beillesztése."""
        text = self.target_text.toPlainText()
        if text:
            self.insert_translation.emit(text)
    
    def set_source_text(self, text: str):
        """Forrás szöveg beállítása."""
        self.source_text.setPlainText(text)


class TranslatorSettingsWidget(QWidget):
    """Fordító beállítások widget."""
    
    def __init__(self, plugin: 'ArgosTranslatorPlugin', parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QFormLayout(self)
        
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(100, 2000)
        self.delay_spin.setSuffix(" ms")
        self.delay_spin.setValue(500)
        layout.addRow("Fordítás késleltetés:", self.delay_spin)


class ArgosTranslatorPlugin(UIPlugin, TranslationPlugin):
    """Argos Translate fordító plugin."""
    
    def __init__(self):
        super().__init__()
        self._dock: Optional[QDockWidget] = None
        self._widget: Optional[TranslatorWidget] = None
        self._plugin_dir = Path(__file__).parent
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="argos_translator",
            name="Argos Fordító",
            version="1.0.0",
            author="Levente Kulacsy - Argos Translate Team",
            description="Offline angol-magyar fordító az Argos Translate motorral",
            plugin_type=PluginType.UI,
            dependencies=[
                PluginDependency("argostranslate", "1.9.0"),
            ],
            icon="🌍",
            readme_path="README.md"
        )
    
    def initialize(self) -> bool:
        """Plugin inicializálása."""
        try:
            import argostranslate
            return True
        except ImportError:
            print("Argos Translate nincs telepítve. Telepítsd: pip install argostranslate")
            return True  # Engedélyezzük a betöltést, csak figyelmeztetünk
    
    def create_dock_widget(self) -> Optional[QDockWidget]:
        """Fordító dock widget létrehozása."""
        self._dock = QDockWidget("🌍 Fordító", self._main_window)
        self._dock.setObjectName("translatorDock")
        self._dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self._widget = TranslatorWidget()
        self._widget.insert_translation.connect(self._on_insert_translation)
        self._dock.setWidget(self._widget)
        
        return self._dock
    
    def create_menu_items(self) -> List[QAction]:
        """Menü elemek létrehozása."""
        actions = []
        
        action = QAction("🌍 Fordító panel", self._main_window)
        action.setCheckable(True)
        action.setChecked(True)
        action.triggered.connect(self._toggle_dock)
        actions.append(action)
        
        return actions
    
    def _toggle_dock(self, checked: bool):
        """Dock megjelenítése/elrejtése."""
        if self._dock:
            self._dock.setVisible(checked)
    
    def _on_insert_translation(self, text: str):
        """Fordítás beillesztése az editorba."""
        if self._main_window:
            editor = self._main_window.cue_editor
            if editor and hasattr(editor, 'translated_text'):
                editor.translated_text.setPlainText(text)
    
    def on_cue_selected(self, cue) -> None:
        """Cue kiválasztás - forrás szöveg betöltése."""
        if self._widget and cue and cue.source_text:
            self._widget.set_source_text(cue.source_text)
    
    def get_settings_widget(self) -> Optional[QWidget]:
        """Beállítások widget."""
        return TranslatorSettingsWidget(self)
    
    def get_long_description(self) -> str:
        """README tartalom."""
        readme_path = self._plugin_dir / "README.md"
        if readme_path.exists():
            return readme_path.read_text(encoding='utf-8')
        return self.info.description
    
    # TranslationPlugin interfész
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Szöveg fordítása."""
        try:
            import argostranslate.translate
            return argostranslate.translate.translate(text, source_lang, target_lang)
        except Exception as e:
            return f"[Fordítási hiba: {e}]"
    
    def get_supported_languages(self) -> List[tuple]:
        """Támogatott nyelvpárok."""
        return [
            ("en", "hu", "Angol → Magyar"),
            ("hu", "en", "Magyar → Angol"),
        ]
    
    def is_available(self) -> bool:
        """Ellenőrzi az elérhetőséget."""
        try:
            import argostranslate
            return True
        except ImportError:
            return False


# Plugin export
Plugin = ArgosTranslatorPlugin
