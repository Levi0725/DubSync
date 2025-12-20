"""
DubSync Settings Dialog

Beállítások dialógus ablak.
"""

from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QPushButton, QLabel, QGroupBox, QScrollArea,
    QFileDialog, QListWidget, QListWidgetItem, QTextBrowser,
    QDialogButtonBox, QMessageBox, QFrame, QSplitter,
    QColorDialog, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from dubsync.services.settings_manager import SettingsManager
from dubsync.plugins.base import PluginManager, PluginInterface
from dubsync.ui.theme import ThemeManager, ThemeType, THEMES, ThemeColors
from dubsync.utils.constants import APP_NAME, APP_VERSION


class GeneralSettingsTab(QWidget):
    """Általános beállítások fül."""
    
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Nyelvi beállítások (legfelülre)
        lang_group = QGroupBox("Nyelv / Language")
        lang_layout = QFormLayout(lang_group)
        
        self.language_combo = QComboBox()
        self._populate_languages()
        lang_layout.addRow("Alkalmazás nyelve / App language:", self.language_combo)
        
        self.language_hint = QLabel("⚠️ A nyelvváltás az alkalmazás újraindítása után lép érvénybe.")
        self.language_hint.setStyleSheet("color: #ff9800; font-size: 11px;")
        lang_layout.addRow("", self.language_hint)
        
        layout.addWidget(lang_group)
        
        # Alapértelmezett útvonalak
        paths_group = QGroupBox("Alapértelmezett útvonalak")
        paths_layout = QFormLayout(paths_group)
        
        save_path_layout = QHBoxLayout()
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText("Dokumentumok mappa")
        save_path_layout.addWidget(self.save_path_edit)
        self.save_path_btn = QPushButton("...")
        self.save_path_btn.setMaximumWidth(30)
        self.save_path_btn.clicked.connect(self._browse_save_path)
        save_path_layout.addWidget(self.save_path_btn)
        paths_layout.addRow("Mentési hely:", save_path_layout)
        
        layout.addWidget(paths_group)
        
        # Felhasználói adatok
        user_group = QGroupBox("Felhasználói adatok")
        user_layout = QFormLayout(user_group)
        
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("A te neved...")
        user_layout.addRow("Alapértelmezett név:", self.author_edit)
        
        layout.addWidget(user_group)
        
        # Automatikus mentés
        autosave_group = QGroupBox("Automatikus mentés")
        autosave_layout = QFormLayout(autosave_group)
        
        self.autosave_check = QCheckBox("Engedélyezve")
        autosave_layout.addRow("Automatikus mentés:", self.autosave_check)
        
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(1, 60)
        self.autosave_interval.setSuffix(" perc")
        autosave_layout.addRow("Mentési időköz:", self.autosave_interval)
        
        layout.addWidget(autosave_group)
        
        # Lip-sync beállítások
        lipsync_group = QGroupBox("Lip-sync becslés")
        lipsync_layout = QFormLayout(lipsync_group)
        
        self.chars_per_sec = QDoubleSpinBox()
        self.chars_per_sec.setRange(5.0, 25.0)
        self.chars_per_sec.setDecimals(1)
        self.chars_per_sec.setSuffix(" kar/mp")
        lipsync_layout.addRow("Beszédsebesség:", self.chars_per_sec)
        
        layout.addWidget(lipsync_group)
        
        layout.addStretch()
    
    def _populate_languages(self):
        """Elérhető nyelvek betöltése a legördülő menübe."""
        try:
            from dubsync.i18n import get_available_languages
            
            languages = get_available_languages()
            for lang in languages:
                display_text = f"{lang.flag} {lang.name}" if lang.flag else lang.name
                self.language_combo.addItem(display_text, lang.code)
        except Exception as e:
            # Fallback ha az i18n még nincs inicializálva
            self.language_combo.addItem("🇬🇧 English", "en")
            self.language_combo.addItem("🇭🇺 Magyar", "hu")
    
    def _browse_save_path(self):
        if path := QFileDialog.getExistingDirectory(
            self,
            "Válassz mentési mappát",
            self.save_path_edit.text() or str(Path.home()),
        ):
            self.save_path_edit.setText(path)
    
    def _load_settings(self):
        self.save_path_edit.setText(self.settings.default_save_path)
        self.author_edit.setText(self.settings.default_author_name)
        self.autosave_check.setChecked(self.settings.auto_save_enabled)
        self.autosave_interval.setValue(self.settings.auto_save_interval)
        self.chars_per_sec.setValue(self.settings.lipsync_chars_per_second)
        
        # Nyelv beállítása
        current_lang = self.settings.language
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == current_lang:
                self.language_combo.setCurrentIndex(i)
                break
    
    def save_settings(self):
        self.settings.default_save_path = self.save_path_edit.text()
        self.settings.default_author_name = self.author_edit.text()
        self.settings.auto_save_enabled = self.autosave_check.isChecked()
        self.settings.auto_save_interval = self.autosave_interval.value()
        self.settings.lipsync_chars_per_second = self.chars_per_sec.value()
        
        # Nyelv mentése
        self.settings.language = self.language_combo.currentData()


class PluginsSettingsTab(QWidget):
    """Pluginok beállítások fül."""
    
    plugins_changed = Signal()
    
    def __init__(self, settings: SettingsManager, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.plugin_manager = plugin_manager
        self._current_plugin: Optional[PluginInterface] = None
        self._plugin_just_enabled = False
        self._setup_ui()
        self._load_plugins()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        
        # === Bal oldal - Plugin lista ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("Elérhető pluginok:"))
        
        self.plugin_list = QListWidget()
        self.plugin_list.itemClicked.connect(self._on_plugin_selected)
        left_layout.addWidget(self.plugin_list)
        
        # Engedélyezés gombok
        btn_layout = QHBoxLayout()
        self.enable_btn = QPushButton("Engedélyezés")
        self.enable_btn.clicked.connect(self._on_enable_plugin)
        self.enable_btn.setEnabled(False)
        btn_layout.addWidget(self.enable_btn)
        
        self.disable_btn = QPushButton("Letiltás")
        self.disable_btn.clicked.connect(self._on_disable_plugin)
        self.disable_btn.setEnabled(False)
        btn_layout.addWidget(self.disable_btn)
        left_layout.addLayout(btn_layout)
        
        layout.addWidget(left_widget, 1)
        
        # === Közép - Plugin leírás ===
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        center_layout.addWidget(QLabel("Plugin információk:"))
        
        self.details_stack = QStackedWidget()
        
        # Üres állapot
        empty_label = QLabel("Válassz ki egy plugint a részletek megtekintéséhez")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #888;")
        self.details_stack.addWidget(empty_label)
        
        # Részletek widget
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Figyelmeztetés (csak aktiváláskor látszik)
        self.restart_warning = QLabel("⚠️ A változások csak újraindítás után lépnek érvénybe!")
        self.restart_warning.setStyleSheet(
            "color: #ff9800; padding: 8px; background-color: rgba(255, 152, 0, 0.15); "
            "border-radius: 4px; margin-bottom: 8px;"
        )
        self.restart_warning.setVisible(False)
        details_layout.addWidget(self.restart_warning)
        
        self.plugin_name = QLabel()
        self.plugin_name.setStyleSheet("font-size: 16px; font-weight: bold;")
        details_layout.addWidget(self.plugin_name)
        
        self.plugin_meta = QLabel()
        self.plugin_meta.setStyleSheet("color: #888;")
        details_layout.addWidget(self.plugin_meta)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        details_layout.addWidget(line)
        
        self.plugin_description = QTextBrowser()
        self.plugin_description.setOpenExternalLinks(True)
        details_layout.addWidget(self.plugin_description)
        
        self.details_stack.addWidget(details_widget)
        
        center_layout.addWidget(self.details_stack)
        
        layout.addWidget(center_widget, 2)
        
        # === Jobb oldal - Beállítások ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("Beállítások:"))
        
        self.settings_stack = QStackedWidget()
        
        # Üres állapot
        empty_settings = QLabel("Válassz plugint a beállításokhoz")
        empty_settings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_settings.setStyleSheet("color: #888;")
        self.settings_stack.addWidget(empty_settings)
        
        # Beállítások widget
        settings_widget = QWidget()
        self.settings_widget_layout = QVBoxLayout(settings_widget)
        self.settings_widget_layout.setContentsMargins(0, 0, 0, 0)
        
        # Panel láthatóság beállítás (UI pluginokhoz)
        self.panel_visibility_group = QGroupBox("Panel megjelenés")
        panel_layout = QVBoxLayout(self.panel_visibility_group)
        self.show_panel_on_start = QCheckBox("Indulásnál megjelenjen")
        self.show_panel_on_start.setToolTip(
            "Ha bekapcsolod, a plugin panelje automatikusan megjelenik az alkalmazás indításakor"
        )
        self.show_panel_on_start.stateChanged.connect(self._on_panel_visibility_changed)
        panel_layout.addWidget(self.show_panel_on_start)
        self.panel_visibility_group.setVisible(False)
        self.settings_widget_layout.addWidget(self.panel_visibility_group)
        
        # Plugin egyedi beállítások
        self.plugin_settings_group = QGroupBox("Plugin beállítások")
        self.plugin_settings_layout = QVBoxLayout(self.plugin_settings_group)
        self.plugin_settings_container = QWidget()
        self.plugin_settings_layout.addWidget(self.plugin_settings_container)
        self.plugin_settings_group.setVisible(False)
        self.settings_widget_layout.addWidget(self.plugin_settings_group)
        
        self.settings_widget_layout.addStretch()
        
        self.settings_stack.addWidget(settings_widget)
        
        right_layout.addWidget(self.settings_stack)
        
        layout.addWidget(right_widget, 1)
    
    def _load_plugins(self):
        self.plugin_list.clear()
        
        for plugin in self.plugin_manager.get_all_plugins():
            info = plugin.info
            item = QListWidgetItem()
            
            enabled = self.plugin_manager.is_enabled(info.id)
            icon = "✅" if enabled else "⬜"
            type_icon = self._get_type_icon(info.plugin_type)
            
            item.setText(f"{icon} {type_icon} {info.name}")
            item.setData(Qt.ItemDataRole.UserRole, info.id)
            
            self.plugin_list.addItem(item)
    
    def _get_type_icon(self, plugin_type) -> str:
        from dubsync.plugins.base import PluginType
        icons = {
            PluginType.EXPORT: "📤",
            PluginType.QA: "✓",
            PluginType.IMPORT: "📥",
            PluginType.TOOL: "🔧",
            PluginType.UI: "🖼️",
            PluginType.SERVICE: "⚙️",
            PluginType.LANGUAGE: "🌐",
        }
        return icons.get(plugin_type, "📦")
    
    def _on_plugin_selected(self, item: QListWidgetItem):
        plugin_id = item.data(Qt.ItemDataRole.UserRole)
        if plugin := self.plugin_manager.get_plugin(plugin_id):
            self._current_plugin = plugin
            self._plugin_just_enabled = False
            self._show_plugin_details(plugin)

            enabled = self.plugin_manager.is_enabled(plugin_id)
            self.enable_btn.setEnabled(not enabled)
            self.disable_btn.setEnabled(enabled)
    
    def _show_plugin_details(self, plugin: PluginInterface):
        from dubsync.plugins.base import UIPlugin

        info = plugin.info

        self.plugin_name.setText(f"{info.icon} {info.name}" if info.icon else info.name)
        self.plugin_meta.setText(
            f"v{info.version} • {info.author} • {info.plugin_type.name}"
        )

        # Figyelmeztetés csak ha épp aktiváltuk
        self.restart_warning.setVisible(self._plugin_just_enabled)

        # Hosszú leírás
        long_desc = plugin.get_long_description()
        self.plugin_description.setMarkdown(long_desc)

        # Jobb oldali beállítások megjelenítése
        self.settings_stack.setCurrentIndex(1)

        # Panel láthatóság beállítás (csak UI pluginokhoz)
        if isinstance(plugin, UIPlugin) and plugin.create_dock_widget():
            self.panel_visibility_group.setVisible(True)
            # Betöltjük a jelenlegi beállítást
            visible = self.settings.get_plugin_panel_visible(info.id)
            self.show_panel_on_start.blockSignals(True)
            self.show_panel_on_start.setChecked(visible)
            self.show_panel_on_start.blockSignals(False)
        else:
            self.panel_visibility_group.setVisible(False)

        if settings_widget := plugin.get_settings_widget():
            self._extracted_from__show_plugin_details_34(settings_widget)
        else:
            self.plugin_settings_group.setVisible(False)

        self.details_stack.setCurrentIndex(1)

    # TODO Rename this here and in `_show_plugin_details`
    def _extracted_from__show_plugin_details_34(self, settings_widget):
        # Régi widget törlése
        old_widget = self.plugin_settings_container
        self.plugin_settings_layout.removeWidget(old_widget)
        old_widget.deleteLater()

        self.plugin_settings_container = settings_widget
        self.plugin_settings_layout.addWidget(settings_widget)
        self.plugin_settings_group.setVisible(True)
    
    def _on_panel_visibility_changed(self, state):
        """Panel indulási láthatóság változott."""
        if self._current_plugin:
            visible = state == Qt.CheckState.Checked.value
            self.settings.set_plugin_panel_visible(self._current_plugin.info.id, visible)
    
    def _on_enable_plugin(self):
        if self._current_plugin:
            plugin_id = self._current_plugin.info.id
            self.plugin_manager.enable_plugin(plugin_id)
            self._extracted_from__on_disable_plugin_5(plugin_id)
    
    def _on_disable_plugin(self):
        if self._current_plugin:
            plugin_id = self._current_plugin.info.id
            self.plugin_manager.disable_plugin(plugin_id)
            self._extracted_from__on_disable_plugin_5(plugin_id)

    # TODO Rename this here and in `_on_enable_plugin` and `_on_disable_plugin`
    def _extracted_from__on_disable_plugin_5(self, plugin_id):
        self._plugin_just_enabled = True
        self._load_plugins()
        self.plugins_changed.emit()
        for i in range(self.plugin_list.count()):
            item = self.plugin_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == plugin_id:
                self.plugin_list.setCurrentItem(item)
                self._on_plugin_selected(item)
                self.restart_warning.setVisible(True)
                break
    
    def save_settings(self):
        # Engedélyezett pluginok mentése
        self.settings.enabled_plugins = self.plugin_manager.get_enabled_plugins()

        # Plugin saját beállítások mentése
        for plugin in self.plugin_manager.get_all_plugins():
            if settings := plugin.save_settings():
                self.settings.set_plugin_settings(plugin.info.id, settings)


class PluginDownloadTab(QWidget):
    """Plugin letöltések fül (work in progress)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._extracted_from__setup_ui_5(
            "🚧 Fejlesztés alatt 🚧", "font-size: 24px; color: #ff9800;", layout
        )
        self._extracted_from__setup_ui_5(
            "Ez a funkció hamarosan elérhető lesz!\n\n"
            "Itt fogsz tudni pluginokat böngészni és telepíteni\n"
            "egy központi GitHub repository-ból.",
            "color: #888;",
            layout,
        )
        layout.addStretch()

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_5(self, arg0, arg1, layout):
        # Work in progress jelzés
        wip_label = QLabel(arg0)
        wip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        wip_label.setStyleSheet(arg1)
        layout.addWidget(wip_label)


class ThemeSettingsTab(QWidget):
    """Téma beállítások fül."""
    
    theme_changed = Signal()
    
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Téma választó
        theme_group = QGroupBox("Téma")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("🌙 Sötét", ThemeType.DARK)
        self.theme_combo.addItem("🌑 Sötét kontrasztos", ThemeType.DARK_CONTRAST)
        self.theme_combo.addItem("☀️ Világos", ThemeType.LIGHT)
        self.theme_combo.addItem("🎨 Egyedi", ThemeType.CUSTOM)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addRow("Téma:", self.theme_combo)
        
        layout.addWidget(theme_group)
        
        # Egyedi színek
        self.custom_group = QGroupBox("Egyedi színek")
        custom_layout = QFormLayout(self.custom_group)
        
        self.color_buttons = {}
        color_labels = {
            "primary": "Elsődleges szín:",
            "background": "Háttér:",
            "surface": "Felület:",
            "foreground": "Szöveg:",
        }
        
        for key, label in color_labels.items():
            btn = QPushButton("Válassz...")
            btn.setProperty("color_key", key)
            btn.clicked.connect(self._on_color_click)
            self.color_buttons[key] = btn
            custom_layout.addRow(label, btn)
        
        self.custom_group.setVisible(False)
        layout.addWidget(self.custom_group)
        
        # Előnézet
        preview_group = QGroupBox("Előnézet")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("Így fog kinézni a szöveg...")
        self.preview_label.setStyleSheet("padding: 20px;")
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_group)
        
        layout.addStretch()
    
    def _load_settings(self):
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == self.theme_manager.current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        self._update_preview()
    
    def _on_theme_changed(self, index):
        theme_type = self.theme_combo.itemData(index)
        self.custom_group.setVisible(theme_type == ThemeType.CUSTOM)
        
        if theme_type == ThemeType.CUSTOM:
            colors = THEMES[ThemeType.DARK]
            self._update_color_buttons(colors)
        
        self._update_preview()
        self.theme_changed.emit()
    
    def _update_color_buttons(self, colors: ThemeColors):
        for key, btn in self.color_buttons.items():
            color = getattr(colors, key)
            btn.setStyleSheet(f"background-color: {color}; color: white;")
            btn.setProperty("color_value", color)
    
    def _on_color_click(self):
        btn = self.sender()
        if not isinstance(btn, QPushButton):
            return
        key = btn.property("color_key")
        current = btn.property("color_value") or "#000000"
        
        color = QColorDialog.getColor(QColor(current), self, f"{key} szín választása")
        if color.isValid():
            btn.setStyleSheet(f"background-color: {color.name()}; color: white;")
            btn.setProperty("color_value", color.name())
            self._update_preview()
    
    def _update_preview(self):
        theme_type = self.theme_combo.currentData()
        if theme_type in THEMES:
            colors = THEMES[theme_type]
            self.preview_label.setStyleSheet(
                f"background-color: {colors.background}; "
                f"color: {colors.foreground}; "
                f"padding: 20px; border-radius: 8px;"
            )
    
    def get_selected_theme(self) -> ThemeType:
        return self.theme_combo.currentData()
    
    def get_custom_colors(self) -> Optional[ThemeColors]:
        if self.get_selected_theme() != ThemeType.CUSTOM:
            return None
        
        base = THEMES[ThemeType.DARK]
        return ThemeColors(
            background=self.color_buttons.get("background", {}).property("color_value") or base.background,
            background_alt=base.background_alt,
            foreground=self.color_buttons.get("foreground", {}).property("color_value") or base.foreground,
            foreground_muted=base.foreground_muted,
            surface=self.color_buttons.get("surface", {}).property("color_value") or base.surface,
            surface_hover=base.surface_hover,
            surface_selected=base.surface_selected,
            border=base.border,
            primary=self.color_buttons.get("primary", {}).property("color_value") or base.primary,
            primary_hover=base.primary_hover,
            secondary=base.secondary,
            success=base.success,
            warning=base.warning,
            error=base.error,
            info=base.info,
            lipsync_good=base.lipsync_good,
            lipsync_warning=base.lipsync_warning,
            lipsync_error=base.lipsync_error,
            input_background=base.input_background,
            input_border=base.input_border,
            scrollbar=base.scrollbar,
            scrollbar_hover=base.scrollbar_hover,
        )
    
    def save_settings(self):
        theme_type = self.get_selected_theme()
        if theme_type == ThemeType.CUSTOM:
            if custom_colors := self.get_custom_colors():
                self.theme_manager.set_custom_colors(custom_colors)
        else:
            self.theme_manager.set_theme(theme_type)


class AboutTab(QWidget):
    """Névjegy fül."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo/Név
        name_label = QLabel(f"🎬 {APP_NAME}")
        self._extracted_from__setup_ui_7(
            name_label, "font-size: 32px; font-weight: bold;", layout
        )
        version_label = QLabel(f"Verzió {APP_VERSION}")
        self._extracted_from__setup_ui_7(
            version_label, "font-size: 14px; color: #888;", layout
        )
        layout.addSpacing(20)

        desc_label = QLabel(
            "Professzionális Szinkronfordítói Editor\n\n"
            "Magyar szinkronfordítók és szinkronrendezők számára készült\n"
            "professzionális eszköz szinkronszövegek készítéséhez."
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addSpacing(20)

        # Linkek
        links_label = QLabel(
            '<a href="https://github.com/Levi0725/DubSync">GitHub Repository</a>'
        )
        links_label.setOpenExternalLinks(True)
        links_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(links_label)

        layout.addSpacing(30)

        layout.addStretch()

        # Copyright
        copyright_label = QLabel("© 2025 Levente Kulacsy - MIT License")
        self._extracted_from__setup_ui_7(copyright_label, "color: #666;", layout)

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_7(self, arg0, arg1, layout):
        arg0.setStyleSheet(arg1)
        arg0.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(arg0)


class SettingsDialog(QDialog):
    """Beállítások dialógus."""
    
    settings_saved = Signal()
    theme_changed = Signal()
    
    # Tab indexek
    TAB_GENERAL = 0
    TAB_PLUGINS = 1
    TAB_DOWNLOAD = 2
    TAB_THEME = 3
    TAB_ABOUT = 4
    
    def __init__(self, parent=None, plugin_manager: Optional[PluginManager] = None, initial_tab: Optional[str] = None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager or PluginManager()
        self.settings = SettingsManager()
        self.theme_manager = ThemeManager()
        self._initial_tab = initial_tab
        
        self.setWindowTitle("Beállítások")
        self.setMinimumSize(800, 800)
        
        self._setup_ui()
        self._set_initial_tab()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Általános beállítások
        self.general_tab = GeneralSettingsTab(self.settings)
        self.tab_widget.addTab(self.general_tab, "⚙️ Általános")
        
        # Plugin beállítások
        self.plugins_tab = PluginsSettingsTab(self.settings, self.plugin_manager)
        self.tab_widget.addTab(self.plugins_tab, "🔌 Pluginok")
        
        # Plugin letöltés
        self.download_tab = PluginDownloadTab()
        self.tab_widget.addTab(self.download_tab, "📥 Plugin letöltés")
        
        # Téma beállítások
        self.theme_tab = ThemeSettingsTab(self.theme_manager)
        self.theme_tab.theme_changed.connect(self._on_theme_preview)
        self.tab_widget.addTab(self.theme_tab, "🎨 Téma")
        
        # Névjegy
        self.about_tab = AboutTab()
        self.tab_widget.addTab(self.about_tab, "ℹ️ Névjegy")
        
        layout.addWidget(self.tab_widget)
        
        # Gombok
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)
    
    def _set_initial_tab(self):
        """Kezdő fül beállítása."""
        if self._initial_tab:
            tab_map = {
                "general": self.TAB_GENERAL,
                "plugins": self.TAB_PLUGINS,
                "download": self.TAB_DOWNLOAD,
                "theme": self.TAB_THEME,
                "about": self.TAB_ABOUT,
            }
            index = tab_map.get(self._initial_tab.lower(), 0)
            self.tab_widget.setCurrentIndex(index)
    
    def _on_theme_preview(self):
        """Téma előnézet."""
        # Előnézet az aktuális ablakra
        pass
    
    def _on_apply(self):
        """Beállítások alkalmazása."""
        self._extracted_from__on_accept_3()
    
    def _on_accept(self):
        """OK gomb."""
        self._extracted_from__on_accept_3()
        self.accept()

    # TODO Rename this here and in `_on_apply` and `_on_accept`
    def _extracted_from__on_accept_3(self):
        self._save_all_settings()
        self.settings_saved.emit()
        self.theme_changed.emit()
    
    def _save_all_settings(self):
        """Összes beállítás mentése."""
        self.general_tab.save_settings()
        self.plugins_tab.save_settings()
        self.theme_tab.save_settings()
        self.settings.save_settings()
