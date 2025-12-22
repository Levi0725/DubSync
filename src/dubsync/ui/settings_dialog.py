"""
DubSync Settings Dialog

Application settings dialog.
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
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QFont

from dubsync.services.settings_manager import SettingsManager
from dubsync.plugins.base import PluginManager, PluginInterface
from dubsync.ui.theme import ThemeManager, ThemeType, THEMES, ThemeColors
from dubsync.utils.constants import APP_NAME, APP_VERSION
from dubsync.i18n import t
from dubsync.resources.icon_manager import get_icon_manager


class GeneralSettingsTab(QWidget):
    """General settings tab."""
    
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Language settings (at top)
        lang_group = QGroupBox(t("settings.general.language"))
        lang_layout = QFormLayout(lang_group)
        
        self.language_combo = QComboBox()
        self._populate_languages()
        lang_layout.addRow(t("settings.general.app_language"), self.language_combo)
        
        self.language_hint = QLabel(t("settings.general.language_restart_hint"))
        self.language_hint.setStyleSheet("color: #ff9800; font-size: 11px;")
        lang_layout.addRow("", self.language_hint)
        
        layout.addWidget(lang_group)
        
        # Default paths
        paths_group = QGroupBox(t("settings.general.paths"))
        paths_layout = QFormLayout(paths_group)
        
        save_path_layout = QHBoxLayout()
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setPlaceholderText(t("settings.general.save_path_placeholder"))
        save_path_layout.addWidget(self.save_path_edit)
        self.save_path_btn = QPushButton(t("buttons.browse"))
        self.save_path_btn.setMaximumWidth(30)
        self.save_path_btn.clicked.connect(self._browse_save_path)
        save_path_layout.addWidget(self.save_path_btn)
        paths_layout.addRow(t("settings.general.save_path"), save_path_layout)
        
        layout.addWidget(paths_group)
        
        # User data
        user_group = QGroupBox(t("settings.general.user_data"))
        user_layout = QFormLayout(user_group)
        
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText(t("settings.general.default_name_placeholder"))
        user_layout.addRow(t("settings.general.default_name"), self.author_edit)
        
        layout.addWidget(user_group)
        
        # Auto-save
        autosave_group = QGroupBox(t("settings.general.autosave"))
        autosave_layout = QFormLayout(autosave_group)
        
        self.autosave_check = QCheckBox(t("settings.general.autosave_enabled"))
        autosave_layout.addRow(t("settings.general.autosave") + ":", self.autosave_check)
        
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(1, 60)
        self.autosave_interval.setSuffix(t("settings.general.autosave_minutes"))
        autosave_layout.addRow(t("settings.general.autosave_interval"), self.autosave_interval)
        
        layout.addWidget(autosave_group)
        
        # Lip-sync settings
        lipsync_group = QGroupBox(t("settings.general.lipsync"))
        lipsync_layout = QFormLayout(lipsync_group)
        
        self.chars_per_sec = QDoubleSpinBox()
        self.chars_per_sec.setRange(5.0, 25.0)
        self.chars_per_sec.setDecimals(1)
        self.chars_per_sec.setSuffix(t("settings.general.chars_per_sec"))
        lipsync_layout.addRow(t("settings.general.speech_speed"), self.chars_per_sec)
        
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
            t("dialogs.project_settings.select_folder") if "dialogs.project_settings.select_folder" in dir(t) else "Select folder",
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


class AppearanceSettingsTab(QWidget):
    """Appearance settings tab - layout and display options."""
    
    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Layout settings
        layout_group = QGroupBox(t("settings.appearance.layout"))
        layout_form = QFormLayout(layout_group)
        
        # Cue list position
        self.cue_list_pos = QComboBox()
        self.cue_list_pos.addItem(t("settings.appearance.cue_list_left"), "left")
        self.cue_list_pos.addItem(t("settings.appearance.cue_list_right"), "right")
        layout_form.addRow(t("settings.appearance.cue_list_position"), self.cue_list_pos)
        
        # Timeline position
        self.timeline_pos = QComboBox()
        self.timeline_pos.addItem(t("settings.appearance.timeline_under_cue_list"), "under_cue_list")
        self.timeline_pos.addItem(t("settings.appearance.timeline_under_video"), "under_video")
        self.timeline_pos.addItem(t("settings.appearance.timeline_hidden"), "hidden")
        layout_form.addRow(t("settings.appearance.timeline_position"), self.timeline_pos)
        
        layout.addWidget(layout_group)
        
        # Video player settings
        video_group = QGroupBox(t("settings.appearance.video_player"))
        video_form = QFormLayout(video_group)
        
        self.video_height = QSpinBox()
        self.video_height.setRange(150, 800)
        self.video_height.setSuffix(t("settings.appearance.video_player_height_px"))
        video_form.addRow(t("settings.appearance.video_player_height"), self.video_height)
        
        layout.addWidget(video_group)
        
        # Cue editor settings
        editor_group = QGroupBox(t("settings.appearance.cue_editor"))
        editor_layout = QVBoxLayout(editor_group)
        
        self.start_collapsed = QCheckBox(t("settings.appearance.start_collapsed"))
        editor_layout.addWidget(self.start_collapsed)
        
        self.show_lipsync = QCheckBox(t("settings.appearance.show_lipsync"))
        editor_layout.addWidget(self.show_lipsync)
        
        self.show_notes = QCheckBox(t("settings.appearance.show_notes"))
        editor_layout.addWidget(self.show_notes)
        
        self.show_sfx = QCheckBox(t("settings.appearance.show_sfx"))
        editor_layout.addWidget(self.show_sfx)
        
        layout.addWidget(editor_group)
        
        # Font settings
        font_group = QGroupBox(t("settings.appearance.fonts"))
        font_form = QFormLayout(font_group)
        
        self.font_combo = QComboBox()
        self.font_combo.addItem(t("settings.appearance.system_default"), "")
        # Add common monospace fonts
        for font in ["Consolas", "Monaco", "Courier New", "Source Code Pro", "Fira Code"]:
            self.font_combo.addItem(font, font)
        font_form.addRow(t("settings.appearance.editor_font"), self.font_combo)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 24)
        self.font_size.setSuffix(t("settings.appearance.font_size_pt"))
        font_form.addRow(t("settings.appearance.font_size"), self.font_size)
        
        layout.addWidget(font_group)
        
        # Restart hint
        hint = QLabel(t("settings.appearance.restart_hint"))
        hint.setStyleSheet("color: #ff9800; font-size: 11px;")
        layout.addWidget(hint)
        
        layout.addStretch()
    
    def _load_settings(self):
        # Cue list position
        pos = self.settings.cue_list_position
        for i in range(self.cue_list_pos.count()):
            if self.cue_list_pos.itemData(i) == pos:
                self.cue_list_pos.setCurrentIndex(i)
                break
        
        # Timeline position
        pos = self.settings.timeline_position
        for i in range(self.timeline_pos.count()):
            if self.timeline_pos.itemData(i) == pos:
                self.timeline_pos.setCurrentIndex(i)
                break
        
        self.video_height.setValue(self.settings.video_player_height)
        self.start_collapsed.setChecked(self.settings.cue_editor_collapsed)
        self.show_lipsync.setChecked(self.settings.show_lipsync_indicator)
        self.show_notes.setChecked(self.settings.show_notes_field)
        self.show_sfx.setChecked(self.settings.show_sfx_field)
        
        # Font
        font = self.settings.editor_font_family
        for i in range(self.font_combo.count()):
            if self.font_combo.itemData(i) == font:
                self.font_combo.setCurrentIndex(i)
                break
        self.font_size.setValue(self.settings.editor_font_size)
    
    def save_settings(self):
        self.settings.cue_list_position = self.cue_list_pos.currentData()
        self.settings.timeline_position = self.timeline_pos.currentData()
        self.settings.video_player_height = self.video_height.value()
        self.settings.cue_editor_collapsed = self.start_collapsed.isChecked()
        self.settings.show_lipsync_indicator = self.show_lipsync.isChecked()
        self.settings.show_notes_field = self.show_notes.isChecked()
        self.settings.show_sfx_field = self.show_sfx.isChecked()
        self.settings.editor_font_family = self.font_combo.currentData()
        self.settings.editor_font_size = self.font_size.value()


class PluginsSettingsTab(QWidget):
    """Plugins settings tab."""
    
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
        
        # === Left side - Plugin list ===
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel(t("settings.plugins.available")))
        
        self.plugin_list = QListWidget()
        self.plugin_list.itemClicked.connect(self._on_plugin_selected)
        left_layout.addWidget(self.plugin_list)
        
        # Enable/disable buttons
        btn_layout = QHBoxLayout()
        self.enable_btn = QPushButton(t("settings.plugins.enable"))
        self.enable_btn.clicked.connect(self._on_enable_plugin)
        self.enable_btn.setEnabled(False)
        btn_layout.addWidget(self.enable_btn)
        
        self.disable_btn = QPushButton(t("settings.plugins.disable"))
        self.disable_btn.clicked.connect(self._on_disable_plugin)
        self.disable_btn.setEnabled(False)
        btn_layout.addWidget(self.disable_btn)
        left_layout.addLayout(btn_layout)
        
        layout.addWidget(left_widget, 1)
        
        # === Center - Plugin description ===
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        
        center_layout.addWidget(QLabel(t("settings.plugins.info")))
        
        self.details_stack = QStackedWidget()
        
        # Empty state
        empty_label = QLabel(t("settings.plugins.select_hint"))
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("color: #888;")
        self.details_stack.addWidget(empty_label)
        
        # Details widget
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        
        # Warning (visible only when activated)
        self.restart_warning = QLabel(t("settings.plugins.restart_warning"))
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
        
        # === Right side - Settings ===
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel(t("settings.plugins.settings")))
        
        self.settings_stack = QStackedWidget()
        
        # Empty state
        empty_settings = QLabel(t("settings.plugins.settings_hint"))
        empty_settings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_settings.setStyleSheet("color: #888;")
        self.settings_stack.addWidget(empty_settings)
        
        # Settings widget
        settings_widget = QWidget()
        self.settings_widget_layout = QVBoxLayout(settings_widget)
        self.settings_widget_layout.setContentsMargins(0, 0, 0, 0)
        
        # Panel visibility settings (for UI plugins)
        self.panel_visibility_group = QGroupBox(t("settings.plugins.panel_settings"))
        panel_layout = QVBoxLayout(self.panel_visibility_group)
        self.show_panel_on_start = QCheckBox(t("settings.plugins.show_on_start"))
        self.show_panel_on_start.setToolTip(t("settings.plugins.show_on_start_tooltip"))
        self.show_panel_on_start.stateChanged.connect(self._on_panel_visibility_changed)
        panel_layout.addWidget(self.show_panel_on_start)
        self.panel_visibility_group.setVisible(False)
        self.settings_widget_layout.addWidget(self.panel_visibility_group)
        
        # Plugin custom settings
        self.plugin_settings_group = QGroupBox(t("settings.plugins.plugin_settings"))
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
        
        icon_mgr = get_icon_manager()
        
        for plugin in self.plugin_manager.get_all_plugins():
            info = plugin.info
            item = QListWidgetItem()
            
            enabled = self.plugin_manager.is_enabled(info.id)
            status_mark = "[ON]" if enabled else "[OFF]"
            type_label = self._get_type_label(info.plugin_type)
            
            item.setText(f"{status_mark} {type_label}: {info.name}")
            item.setIcon(self._get_type_icon(info.plugin_type))
            item.setData(Qt.ItemDataRole.UserRole, info.id)
            
            self.plugin_list.addItem(item)
    
    def _get_type_label(self, plugin_type) -> str:
        """Get plugin type label."""
        from dubsync.plugins.base import PluginType
        labels = {
            PluginType.EXPORT: "Export",
            PluginType.QA: "QA",
            PluginType.IMPORT: "Import",
            PluginType.TOOL: "Tool",
            PluginType.UI: "UI",
            PluginType.SERVICE: "Service",
            PluginType.LANGUAGE: "Language",
        }
        return labels.get(plugin_type, "Plugin")
    
    def _get_type_icon(self, plugin_type):
        """Get plugin type icon."""
        from dubsync.plugins.base import PluginType
        icon_mgr = get_icon_manager()
        icons = {
            PluginType.EXPORT: "file_export",
            PluginType.QA: "qa_check",
            PluginType.IMPORT: "file_import",
            PluginType.TOOL: "settings",
            PluginType.UI: "view_fullscreen",
            PluginType.SERVICE: "sync",
            PluginType.LANGUAGE: "translate",
        }
        icon_name = icons.get(plugin_type, "plugin")
        return icon_mgr.get_icon(icon_name)
    
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
            self._replace_plugin_settings_widget(settings_widget)
        else:
            self.plugin_settings_group.setVisible(False)

        self.details_stack.setCurrentIndex(1)

    def _replace_plugin_settings_widget(self, settings_widget):
        """Replace the plugin settings widget with a new one."""
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
            self._refresh_plugin_list_and_select(plugin_id)
    
    def _on_disable_plugin(self):
        if self._current_plugin:
            plugin_id = self._current_plugin.info.id
            self.plugin_manager.disable_plugin(plugin_id)
            self._refresh_plugin_list_and_select(plugin_id)

    def _refresh_plugin_list_and_select(self, plugin_id):
        """Refresh plugin list and re-select the current plugin."""
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
    """Plugin download tab (work in progress)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._add_centered_label(
            t("settings.download.wip_title"), "font-size: 24px; color: #ff9800;", layout
        )
        self._add_centered_label(
            t("settings.download.wip_message"),
            "color: #888;",
            layout,
        )
        layout.addStretch()

    def _add_centered_label(self, text: str, style: str, layout):
        """Add a centered label to the layout."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(style)
        layout.addWidget(label)


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
        theme_group = QGroupBox(t("dialogs.theme_settings.theme"))
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t("dialogs.theme_settings.dark"), ThemeType.DARK)
        self.theme_combo.addItem(t("dialogs.theme_settings.dark_contrast"), ThemeType.DARK_CONTRAST)
        self.theme_combo.addItem(t("dialogs.theme_settings.light"), ThemeType.LIGHT)
        self.theme_combo.addItem(t("dialogs.theme_settings.custom"), ThemeType.CUSTOM)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        theme_layout.addRow(t("dialogs.theme_settings.theme"), self.theme_combo)
        
        layout.addWidget(theme_group)
        
        # Egyedi színek
        self.custom_group = QGroupBox(t("dialogs.theme_settings.custom_colors"))
        custom_layout = QFormLayout(self.custom_group)
        
        self.color_buttons = {}
        color_labels = {
            "primary": t("dialogs.theme_settings.primary"),
            "background": t("dialogs.theme_settings.background"),
            "surface": t("dialogs.theme_settings.surface"),
            "foreground": t("dialogs.theme_settings.foreground"),
        }
        
        for key, label in color_labels.items():
            btn = QPushButton(t("dialogs.theme_settings.choose"))
            btn.setProperty("color_key", key)
            btn.clicked.connect(self._on_color_click)
            self.color_buttons[key] = btn
            custom_layout.addRow(label, btn)
        
        self.custom_group.setVisible(False)
        layout.addWidget(self.custom_group)
        
        # Előnézet
        preview_group = QGroupBox(t("dialogs.theme_settings.preview"))
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel(t("dialogs.theme_settings.preview_text"))
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
        
        color = QColorDialog.getColor(QColor(current), self, t("dialogs.theme_settings.color_picker_title", color=key))
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
        name_label = QLabel(APP_NAME)
        self._add_styled_centered_widget(
            name_label, "font-size: 32px; font-weight: bold;", layout
        )
        version_label = QLabel(t("app.version", version=APP_VERSION))
        self._add_styled_centered_widget(
            version_label, "font-size: 14px; color: #888;", layout
        )
        layout.addSpacing(20)

        desc_label = QLabel(
            f"{t('app.description')}\n\n{t('app.tagline')}"
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
        self._add_styled_centered_widget(copyright_label, "color: #666;", layout)

    def _add_styled_centered_widget(self, widget, style: str, layout):
        """Add a styled and centered widget to the layout."""
        widget.setStyleSheet(style)
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(widget)


class SettingsDialog(QDialog):
    """Beállítások dialógus."""
    
    settings_saved = Signal()
    theme_changed = Signal()
    
    # Tab indexek
    TAB_GENERAL = 0
    TAB_APPEARANCE = 1
    TAB_PLUGINS = 2
    TAB_DOWNLOAD = 3
    TAB_THEME = 4
    TAB_ABOUT = 5
    
    def __init__(self, parent=None, plugin_manager: Optional[PluginManager] = None, initial_tab: Optional[str] = None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager or PluginManager()
        self.settings = SettingsManager()
        self.theme_manager = ThemeManager()
        self._initial_tab = initial_tab
        
        self.setWindowTitle(t("settings.title"))
        self.setMinimumSize(800, 800)
        
        self._setup_ui()
        self._set_initial_tab()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        icon_mgr = get_icon_manager()
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # General settings (scrollable)
        self.general_tab = GeneralSettingsTab(self.settings)
        self.tab_widget.addTab(self._make_scrollable(self.general_tab), icon_mgr.get_icon("settings"), t("settings.tabs.general"))
        
        # Appearance settings (scrollable)
        self.appearance_tab = AppearanceSettingsTab(self.settings)
        self.tab_widget.addTab(self._make_scrollable(self.appearance_tab), icon_mgr.get_icon("view_fullscreen"), t("settings.tabs.appearance"))
        
        # Plugin settings
        self.plugins_tab = PluginsSettingsTab(self.settings, self.plugin_manager)
        self.tab_widget.addTab(self.plugins_tab, icon_mgr.get_icon("plugin"), t("settings.tabs.plugins"))
        
        # Plugin download
        self.download_tab = PluginDownloadTab()
        self.tab_widget.addTab(self.download_tab, icon_mgr.get_icon("plugin_download"), t("settings.tabs.download"))
        
        # Theme settings (scrollable)
        self.theme_tab = ThemeSettingsTab(self.theme_manager)
        self.theme_tab.theme_changed.connect(self._on_theme_preview)
        self.tab_widget.addTab(self._make_scrollable(self.theme_tab), icon_mgr.get_icon("settings_theme"), t("dialogs.theme_settings.title"))
        
        # About (scrollable)
        self.about_tab = AboutTab()
        self.tab_widget.addTab(self._make_scrollable(self.about_tab), icon_mgr.get_icon("about"), t("menu.help.about"))
        
        layout.addWidget(self.tab_widget)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        # Translate standard buttons
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(t("buttons.ok"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(t("buttons.cancel"))
        buttons.button(QDialogButtonBox.StandardButton.Apply).setText(t("buttons.apply"))
        
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)
    
    def _set_initial_tab(self):
        """Set initial tab."""
        if self._initial_tab:
            tab_map = {
                "general": self.TAB_GENERAL,
                "appearance": self.TAB_APPEARANCE,
                "plugins": self.TAB_PLUGINS,
                "download": self.TAB_DOWNLOAD,
                "theme": self.TAB_THEME,
                "about": self.TAB_ABOUT,
            }
            index = tab_map.get(self._initial_tab.lower(), 0)
            self.tab_widget.setCurrentIndex(index)
    
    def _make_scrollable(self, widget: QWidget) -> QScrollArea:
        """
        Wrap a widget in a scrollable area.
        
        Args:
            widget: Widget to make scrollable
            
        Returns:
            QScrollArea containing the widget
        """
        scroll_area = QScrollArea()
        scroll_area.setWidget(widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        return scroll_area
    
    def _on_theme_preview(self):
        """Téma előnézet."""
        # Előnézet az aktuális ablakra
        pass
    
    def _on_apply(self):
        """Beállítások alkalmazása."""
        self._apply_and_emit_changes()
    
    def _on_accept(self):
        """OK button handler."""
        self._apply_and_emit_changes()
        self.accept()

    def _apply_and_emit_changes(self):
        """Save all settings and emit change signals."""
        self._save_all_settings()
        self.settings_saved.emit()
        self.theme_changed.emit()
    
    def _save_all_settings(self):
        """Összes beállítás mentése."""
        self.general_tab.save_settings()
        self.appearance_tab.save_settings()
        self.plugins_tab.save_settings()
        self.theme_tab.save_settings()
        self.settings.save_settings()
