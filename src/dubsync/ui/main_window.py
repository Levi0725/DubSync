"""
DubSync Main Window

Fő alkalmazás ablak a szinkronfordító editorhoz.
"""

from pathlib import Path
from typing import Optional, cast

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QMenu, QToolBar, QFileDialog, QMessageBox,
    QLabel, QDockWidget, QApplication, QDialog,
    QFormLayout, QComboBox, QColorDialog, QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, Slot, QSettings
from PySide6.QtGui import QAction, QKeySequence, QCloseEvent, QUndoStack, QUndoCommand

from dubsync.utils.constants import APP_NAME, APP_VERSION, PROJECT_EXTENSION
from dubsync.i18n import t
from dubsync.services.project_manager import (
    ProjectManager, get_project_filter, get_srt_filter, get_video_filter
)
from dubsync.services.pdf_export import PDFExporter
from dubsync.services.settings_manager import SettingsManager
from dubsync.ui.cue_list import CueListWidget
from dubsync.ui.cue_editor import CueEditorWidget
from dubsync.ui.video_player import VideoPlayerWidget
from dubsync.ui.comments_panel import CommentsPanelWidget
from dubsync.ui.dialogs import ProjectSettingsDialog
from dubsync.ui.theme import ThemeManager, ThemeType, ThemeColors, THEMES
from dubsync.plugins.base import PluginManager


class DeleteCueCommand(QUndoCommand):
    """Undo command cue törléshez."""
    
    def __init__(self, main_window, cue_data: dict, parent=None):
        super().__init__(t("dialogs.confirm_delete.title"), parent)
        self._main_window = main_window
        self._cue_data = cue_data
        self._cue_id = cue_data.get('id')
    
    def redo(self):
        """Törlés végrehajtása."""
        if self._cue_id:
            self._main_window.project_manager.delete_cue(self._cue_id)
            self._main_window._refresh_cue_list()
            self._main_window._update_title()
            self._main_window._update_statistics()
    
    def undo(self):
        """Törlés visszavonása - cue visszaállítása."""
        from dubsync.models.cue import Cue, CueBatch
        from dubsync.utils.constants import CueStatus
        
        pm = self._main_window.project_manager
        if not pm.is_open:
            return
        
        from dubsync.models.cue import Cue as CueModel
        
        # Recreate the cue
        project_id = self._cue_data.get('project_id')
        if project_id is None:
            return
        
        cue = CueModel(
            project_id=project_id,
            cue_index=self._cue_data.get('cue_index', 1),
            time_in_ms=self._cue_data.get('time_in_ms', 0),
            time_out_ms=self._cue_data.get('time_out_ms', 2000),
            source_text=self._cue_data.get('source_text', ''),
            translated_text=self._cue_data.get('translated_text', ''),
            character_name=self._cue_data.get('character_name', ''),
            notes=self._cue_data.get('notes', ''),
            sfx_notes=self._cue_data.get('sfx_notes', ''),
            status=CueStatus(self._cue_data.get('status', 'new')),
            lip_sync_ratio=self._cue_data.get('lip_sync_ratio'),
        )
        
        cue.save(pm.db)
        self._cue_id = cue.id  # Update for next redo
        self._cue_data['id'] = cue.id
        
        # Reindex cues to ensure correct order
        CueBatch.reindex(pm.db, pm.project.id)
        
        self._main_window._refresh_cue_list()
        self._main_window._update_title()
        self._main_window._update_statistics()
        self._main_window.cue_list.select_cue(cue.id)


class ThemeSettingsDialog(QDialog):
    """Téma beállítások dialógus."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("dialogs.theme_settings.title"))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t("dialogs.theme_settings.dark"), ThemeType.DARK)
        self.theme_combo.addItem(t("dialogs.theme_settings.dark_contrast"), ThemeType.DARK_CONTRAST)
        self.theme_combo.addItem(t("dialogs.theme_settings.light"), ThemeType.LIGHT)
        self.theme_combo.addItem(t("dialogs.theme_settings.custom"), ThemeType.CUSTOM)
        form_layout.addRow(t("dialogs.theme_settings.theme"), self.theme_combo)
        
        layout.addLayout(form_layout)
        
        self.custom_group = QWidget()
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
        
        layout.addWidget(self.custom_group)
        self.custom_group.setVisible(False)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        
        theme_mgr = ThemeManager()
        settings_mgr = SettingsManager()
        
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == theme_mgr.current_theme:
                self.theme_combo.setCurrentIndex(i)
                break
        
        # Ha egyedi téma, töltsük be a mentett színeket
        if theme_mgr.current_theme == ThemeType.CUSTOM:
            if custom_colors_dict := settings_mgr.custom_theme_colors:
                for key, btn in self.color_buttons.items():
                    if key in custom_colors_dict:
                        color = custom_colors_dict[key]
                        btn.setStyleSheet(f"background-color: {color}; color: white;")
                        btn.setProperty("color_value", color)
                self.custom_group.setVisible(True)
    
    def _on_theme_changed(self, index):
        theme_type = self.theme_combo.itemData(index)
        self.custom_group.setVisible(theme_type == ThemeType.CUSTOM)
        
        if theme_type == ThemeType.CUSTOM:
            colors = THEMES[ThemeType.DARK]
            self._update_color_buttons(colors)
    
    def _update_color_buttons(self, colors: ThemeColors):
        for key, btn in self.color_buttons.items():
            color = getattr(colors, key)
            btn.setStyleSheet(f"background-color: {color}; color: white;")
            btn.setProperty("color_value", color)
    
    def _on_color_click(self):
        sender = self.sender()
        if not isinstance(sender, QPushButton):
            return
        btn = sender
        key = btn.property("color_key")
        current = btn.property("color_value") or "#000000"
        
        from PySide6.QtGui import QColor
        color = QColorDialog.getColor(QColor(current), self, f"{key} szín választása")
        if color.isValid():
            btn.setStyleSheet(f"background-color: {color.name()}; color: white;")
            btn.setProperty("color_value", color.name())
    
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


class MainWindow(QMainWindow):
    """Fő ablak a DubSync alkalmazáshoz."""
    
    project_changed = Signal()
    cue_selected = Signal(int)
    
    def __init__(self, plugin_manager: Optional[PluginManager] = None):
        super().__init__()
        
        self.project_manager = ProjectManager()
        self.settings = QSettings("DubSync", "DubSync")
        self.settings_manager = SettingsManager()
        self.theme_manager = ThemeManager()
        self.plugin_manager = plugin_manager or PluginManager()
        self._delete_mode = False
        self._plugin_docks = []
        
        # Undo stack for delete operations
        self._undo_stack = QUndoStack(self)
        
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()
        self._load_settings()
        self._apply_theme()
        self._setup_plugins()
        
        self._update_title()
        self._update_ui_state()
    
    def _setup_ui(self):
        """UI felépítése."""
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)

        layout = self._extracted_from__setup_ui_9(central, 4)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.main_splitter)

        self.cue_list = CueListWidget()
        self.main_splitter.addWidget(self.cue_list)

        center_widget = QWidget()
        center_layout = self._extracted_from__setup_ui_9(center_widget, 0)
        self.video_player = VideoPlayerWidget()
        center_layout.addWidget(self.video_player, 2)

        self.cue_editor = CueEditorWidget()
        center_layout.addWidget(self.cue_editor, 1)

        self.main_splitter.addWidget(center_widget)

        self.comments_dock = QDockWidget(t("comments_panel.title"), self)
        self.comments_dock.setObjectName("commentsDock")
        self.comments_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.comments_panel = CommentsPanelWidget()
        self.comments_dock.setWidget(self.comments_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.comments_dock)

        self.main_splitter.setSizes([350, 850])

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_9(self, arg0, arg1):
        result = QVBoxLayout(arg0)
        result.setContentsMargins(arg1, arg1, arg1, arg1)
        result.setSpacing(4)

        return result
    
    def _setup_menus(self):
        """Menük beállítása."""
        menubar = self.menuBar()
        
        # === File menu ===
        file_menu = menubar.addMenu(t("menu.file._title"))
        
        self.action_new = QAction(t("menu.file.new"), self)
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self._on_new_project)
        file_menu.addAction(self.action_new)
        
        self.action_open = QAction(t("menu.file.open"), self)
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self._on_open_project)
        file_menu.addAction(self.action_open)
        
        self.action_save = QAction(t("menu.file.save"), self)
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self._on_save_project)
        file_menu.addAction(self.action_save)
        
        self.action_save_as = QAction(t("menu.file.save_as"), self)
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_save_as.triggered.connect(self._on_save_project_as)
        file_menu.addAction(self.action_save_as)
        
        file_menu.addSeparator()
        
        import_menu = file_menu.addMenu(t("menu.file.import"))
        
        self.action_import_srt = QAction(t("menu.file.import_srt"), self)
        self.action_import_srt.triggered.connect(self._on_import_srt)
        import_menu.addAction(self.action_import_srt)
        
        self.action_import_video = QAction(t("menu.file.import_video"), self)
        self.action_import_video.triggered.connect(self._on_import_video)
        import_menu.addAction(self.action_import_video)
        
        self.export_menu = file_menu.addMenu(t("menu.file.export"))
        
        self.action_export_pdf = QAction(t("menu.file.export_pdf"), self)
        self.action_export_pdf.triggered.connect(self._on_export_pdf)
        self.export_menu.addAction(self.action_export_pdf)
        
        self.action_export_srt = QAction(t("menu.file.export_srt"), self)
        self.action_export_srt.triggered.connect(self._on_export_srt)
        self.export_menu.addAction(self.action_export_srt)
        
        # Plugin export formátumok később lesznek hozzáadva a _setup_plugins()-ban
        
        file_menu.addSeparator()
        
        self.action_settings = QAction(t("menu.file.project_settings"), self)
        self.action_settings.triggered.connect(self._on_project_settings)
        file_menu.addAction(self.action_settings)
        
        self.action_app_settings = QAction(t("menu.file.app_settings"), self)
        self.action_app_settings.setShortcut(QKeySequence("Ctrl+,"))
        self.action_app_settings.triggered.connect(self._on_app_settings)
        file_menu.addAction(self.action_app_settings)
        
        file_menu.addSeparator()
        
        self.action_exit = QAction(t("menu.file.exit"), self)
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)
        file_menu.addAction(self.action_exit)
        
        # === Edit menu ===
        edit_menu = menubar.addMenu(t("menu.edit._title"))
        
        self.action_undo = self._undo_stack.createUndoAction(self, t("menu.edit.undo"))
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(self.action_undo)
        
        self.action_redo = self._undo_stack.createRedoAction(self, t("menu.edit.redo"))
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(self.action_redo)
        
        edit_menu.addSeparator()
        
        self.action_add_cue = QAction(t("menu.edit.add_cue"), self)
        self.action_add_cue.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.action_add_cue.triggered.connect(self._on_add_cue)
        edit_menu.addAction(self.action_add_cue)
        
        self.action_insert_cue_before = QAction(t("menu.edit.insert_before"), self)
        self.action_insert_cue_before.setShortcut(QKeySequence("Ctrl+Shift+Up"))
        self.action_insert_cue_before.triggered.connect(self._on_insert_cue_before)
        edit_menu.addAction(self.action_insert_cue_before)
        
        self.action_insert_cue_after = QAction(t("menu.edit.insert_after"), self)
        self.action_insert_cue_after.setShortcut(QKeySequence("Ctrl+Shift+Down"))
        self.action_insert_cue_after.triggered.connect(self._on_insert_cue_after)
        edit_menu.addAction(self.action_insert_cue_after)
        
        self.action_delete_mode = QAction(t("menu.edit.delete_mode"), self)
        self.action_delete_mode.setShortcut(QKeySequence("Ctrl+D"))
        self.action_delete_mode.setCheckable(True)
        self.action_delete_mode.triggered.connect(self._on_toggle_delete_mode)
        edit_menu.addAction(self.action_delete_mode)
        
        self.action_delete_cue = QAction(t("menu.edit.delete_cue"), self)
        self.action_delete_cue.setShortcut(QKeySequence.StandardKey.Delete)
        self.action_delete_cue.triggered.connect(self._on_delete_cue)
        self.action_delete_cue.setEnabled(False)
        edit_menu.addAction(self.action_delete_cue)
        
        edit_menu.addSeparator()
        
        self.action_edit_timing = QAction(t("menu.edit.edit_timing"), self)
        self.action_edit_timing.setShortcut(QKeySequence("Ctrl+T"))
        self.action_edit_timing.triggered.connect(self._on_edit_timing)
        edit_menu.addAction(self.action_edit_timing)
        
        edit_menu.addSeparator()
        
        self.action_recalc_lipsync = QAction(t("menu.edit.recalc_lipsync"), self)
        self.action_recalc_lipsync.triggered.connect(self._on_recalculate_lipsync)
        edit_menu.addAction(self.action_recalc_lipsync)
        
        # === Navigate menu ===
        nav_menu = menubar.addMenu(t("menu.navigate._title"))
        
        self.action_prev_cue = QAction(t("menu.navigate.prev_cue"), self)
        self.action_prev_cue.setShortcut(QKeySequence("Ctrl+Up"))
        self.action_prev_cue.triggered.connect(self._on_goto_prev_cue)
        nav_menu.addAction(self.action_prev_cue)
        
        self.action_next_cue = QAction(t("menu.navigate.next_cue"), self)
        self.action_next_cue.setShortcut(QKeySequence("Ctrl+Down"))
        self.action_next_cue.triggered.connect(self._on_goto_next_cue)
        nav_menu.addAction(self.action_next_cue)
        
        nav_menu.addSeparator()
        
        self.action_next_empty = QAction(t("menu.navigate.next_empty"), self)
        self.action_next_empty.setShortcut(QKeySequence("Ctrl+E"))
        self.action_next_empty.triggered.connect(self._on_goto_next_empty)
        nav_menu.addAction(self.action_next_empty)
        
        self.action_next_lipsync = QAction(t("menu.navigate.next_lipsync"), self)
        self.action_next_lipsync.setShortcut(QKeySequence("Ctrl+L"))
        self.action_next_lipsync.triggered.connect(self._on_goto_next_lipsync_issue)
        nav_menu.addAction(self.action_next_lipsync)
        
        self.action_next_comment = QAction(t("menu.navigate.next_comment"), self)
        self.action_next_comment.setShortcut(QKeySequence("Ctrl+M"))
        self.action_next_comment.triggered.connect(self._on_goto_next_comment)
        nav_menu.addAction(self.action_next_comment)
        
        # === View menu ===
        self.view_menu = menubar.addMenu(t("menu.view._title"))
        
        # Panelek közvetlenül a menüben (jobb UX)
        self.view_menu.addSection(t("menu.view.panels"))
        
        self.action_toggle_comments = self.comments_dock.toggleViewAction()
        self.action_toggle_comments.setText(t("menu.view.comments_panel"))
        self.view_menu.addAction(self.action_toggle_comments)
        
        # Plugin panelek itt lesznek hozzáadva a _setup_plugins()-ban
        
        self.view_menu.addSeparator()
        
        self.action_fullscreen = QAction(t("menu.view.fullscreen"), self)
        self.action_fullscreen.setShortcut(QKeySequence("F11"))
        self.action_fullscreen.setCheckable(True)
        self.action_fullscreen.triggered.connect(self._toggle_fullscreen)
        self.view_menu.addAction(self.action_fullscreen)
        
        # === Help menu ===
        help_menu = menubar.addMenu(t("menu.help._title"))
        
        self.action_tutorial = QAction(t("menu.help.tutorial"), self)
        self.action_tutorial.setShortcut(QKeySequence("F1"))
        self.action_tutorial.triggered.connect(self._on_tutorial)
        help_menu.addAction(self.action_tutorial)
        
        help_menu.addSeparator()
        
        self.action_about = QAction(t("menu.help.about"), self)
        self.action_about.triggered.connect(self._on_about)
        help_menu.addAction(self.action_about)
    
    def _setup_toolbar(self):
        """Eszköztár beállítása."""
        toolbar = QToolBar(t("toolbar.main"))
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_import_srt)
        toolbar.addAction(self.action_export_pdf)
        toolbar.addSeparator()
        toolbar.addAction(self.action_add_cue)
        toolbar.addAction(self.action_insert_cue_before)
        toolbar.addAction(self.action_insert_cue_after)
        toolbar.addAction(self.action_delete_mode)
        toolbar.addSeparator()
        toolbar.addAction(self.action_next_empty)
        toolbar.addAction(self.action_next_lipsync)
    
    def _setup_statusbar(self):
        """Állapotsor beállítása."""
        statusbar = self.statusBar()
        
        self.delete_mode_label = QLabel("")
        self.delete_mode_label.setStyleSheet("color: #f44336; font-weight: bold;")
        statusbar.addWidget(self.delete_mode_label)
        
        self.progress_label = QLabel("")
        statusbar.addWidget(self.progress_label)
        
        self.stats_label = QLabel("")
        statusbar.addPermanentWidget(self.stats_label)
    
    def _connect_signals(self):
        """Signal-slot kapcsolatok."""
        self.cue_list.cue_selected.connect(self._on_cue_selected)
        self.cue_list.cue_double_clicked.connect(self._on_cue_double_clicked)
        self.cue_list.insert_cue_requested.connect(self._on_insert_cue_at)
        self.cue_list.delete_cue_requested.connect(self._on_delete_cue_confirmed)
        
        self.cue_editor.cue_saved.connect(self._on_cue_saved)
        self.cue_editor.status_changed.connect(self._on_cue_status_changed)
        self.cue_editor.timing_changed.connect(self._on_timing_changed)
        
        self.video_player.position_changed.connect(self._on_video_position_changed)
        
        self.comments_panel.comment_added.connect(self._on_comment_added)
    
    def _load_settings(self):
        """Beállítások betöltése."""
        if geometry := self.settings.value("geometry"):
            self.restoreGeometry(geometry)
        
        if state := self.settings.value("windowState"):
            self.restoreState(state)
        
        theme_name = self.settings.value("theme", "dark")
        try:
            theme_type = ThemeType(theme_name)
            if theme_type == ThemeType.CUSTOM:
                if custom_colors_dict := self.settings_manager.custom_theme_colors:
                    from dubsync.ui.theme import ThemeColors, THEMES
                    base = THEMES[ThemeType.DARK]
                    custom_colors = ThemeColors(
                        background=custom_colors_dict.get("background", base.background),
                        background_alt=base.background_alt,
                        foreground=custom_colors_dict.get("foreground", base.foreground),
                        foreground_muted=base.foreground_muted,
                        surface=custom_colors_dict.get("surface", base.surface),
                        surface_hover=base.surface_hover,
                        surface_selected=base.surface_selected,
                        border=base.border,
                        primary=custom_colors_dict.get("primary", base.primary),
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
                    self.theme_manager.set_custom_colors(custom_colors)
                else:
                    self.theme_manager.set_theme(ThemeType.DARK)
            else:
                self.theme_manager.set_theme(theme_type)
        except ValueError:
            self.theme_manager.set_theme(ThemeType.DARK)
    
    def _save_settings(self):
        """Beállítások mentése."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("theme", self.theme_manager.current_theme.value)
    
    def _apply_theme(self):
        """Téma alkalmazása."""
        stylesheet = self.theme_manager.get_stylesheet()
        app = QApplication.instance()
        if app is not None:
            cast(QApplication, app).setStyleSheet(stylesheet)
    
    def _setup_plugins(self):
        """Plugin UI elemek beállítása."""
        # Export pluginok hozzáadása a Fájl->Export menühöz
        for export_plugin in self.plugin_manager.get_export_plugins(enabled_only=True):
            try:
                action = QAction(f"{export_plugin.info.icon} {export_plugin.info.name}...", self)
                action.setData(export_plugin.info.id)
                action.triggered.connect(lambda checked, p=export_plugin: self._on_plugin_export(p))
                self.export_menu.addAction(action)
            except Exception as e:
                print(f"Export plugin hiba ({export_plugin.info.name}): {e}")
        
        # UI pluginok
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.set_main_window(self)
                
                if dock := plugin.create_dock_widget():
                    self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
                    self._plugin_docks.append(dock)
                    
                    # Induláskor elrejtés, hacsak nincs beállítva másképp
                    show_on_start = self.settings_manager.get_plugin_panel_visible(plugin.info.id)
                    if not show_on_start:
                        dock.hide()
                    
                    # Panel toggle hozzáadása a Nézet menühöz közvetlenül
                    toggle_action = dock.toggleViewAction()
                    toggle_action.setText(f"{plugin.info.icon} {plugin.info.name}")
                    self.view_menu.insertAction(self.action_fullscreen, toggle_action)
                
                if menu_items := plugin.create_menu_items():
                    plugins_menu = self._get_or_create_plugins_menu()
                    for action in menu_items:
                        plugins_menu.addAction(action)
                
            except Exception as e:
                print(f"Plugin UI hiba ({plugin.info.name}): {e}")
    
    def _get_or_create_plugins_menu(self) -> QMenu:
        """Pluginok menü lekérése vagy létrehozása."""
        if not hasattr(self, '_plugins_menu'):
            menubar = self.menuBar()
            self._plugins_menu = menubar.addMenu(t("menu.plugins"))
        return self._plugins_menu
    
    def _notify_plugins_cue_selected(self, cue):
        """Plugin értesítése cue kiválasztásról."""
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.on_cue_selected(cue)
            except Exception as e:
                print(f"Plugin cue_selected hiba ({plugin.info.name}): {e}")
    
    def _notify_plugins_project_opened(self, project):
        """Plugin értesítése projekt megnyitásról."""
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.on_project_opened(project)
            except Exception as e:
                print(f"Plugin project_opened hiba ({plugin.info.name}): {e}")
    
    def _notify_plugins_project_closed(self):
        """Plugin értesítése projekt bezárásról."""
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.on_project_closed()
            except Exception as e:
                print(f"Plugin project_closed hiba ({plugin.info.name}): {e}")
    
    def _set_theme(self, theme_type: ThemeType):
        """Téma beállítása."""
        self.theme_manager.set_theme(theme_type)
        self._apply_theme()
        self.settings.setValue("theme", theme_type.value)
    
    def _update_title(self):
        """Ablak címének frissítése."""
        title = f"{APP_NAME} {APP_VERSION}"
        
        if self.project_manager.is_open and self.project_manager.project is not None:
            project_name = self.project_manager.project.get_display_title()
            title = f"{project_name} - {title}"
            
            if self.project_manager.is_dirty:
                title = f"• {title}"
        
        self.setWindowTitle(title)
    
    def _update_ui_state(self):
        """UI állapot frissítése."""
        has_project = self.project_manager.is_open
        
        self.action_save.setEnabled(has_project)
        self.action_save_as.setEnabled(has_project)
        self.action_import_srt.setEnabled(has_project)
        self.action_import_video.setEnabled(has_project)
        self.action_export_pdf.setEnabled(has_project)
        self.action_export_srt.setEnabled(has_project)
        self.action_settings.setEnabled(has_project)
        self.action_recalc_lipsync.setEnabled(has_project)
        self.action_next_empty.setEnabled(has_project)
        self.action_next_lipsync.setEnabled(has_project)
        self.action_next_comment.setEnabled(has_project)
        
        self.action_add_cue.setEnabled(has_project)
        self.action_insert_cue_before.setEnabled(has_project)
        self.action_insert_cue_after.setEnabled(has_project)
        self.action_delete_mode.setEnabled(has_project)
        self.action_edit_timing.setEnabled(has_project)
        
        self.cue_list.setEnabled(has_project)
        self.cue_editor.setEnabled(has_project)
        self.video_player.setEnabled(has_project)
        self.comments_panel.setEnabled(has_project)
        
        self._update_delete_mode_ui()
        self._update_statistics()
    
    def _update_delete_mode_ui(self):
        """Törlés mód UI frissítése."""
        if self._delete_mode:
            self._extracted_from__update_delete_mode_ui_4("🗑️ TÖRLÉS MÓD AKTÍV", True)
        else:
            self._extracted_from__update_delete_mode_ui_4("", False)

    # TODO Rename this here and in `_update_delete_mode_ui`
    def _extracted_from__update_delete_mode_ui_4(self, arg0, arg1):
        self.delete_mode_label.setText(arg0)
        self.action_delete_cue.setEnabled(arg1)
        self.cue_list.set_delete_mode(arg1)
    
    def _update_statistics(self):
        """Statisztikák frissítése."""
        if not self.project_manager.is_open:
            self.stats_label.setText("")
            return
        
        stats = self.project_manager.get_statistics()
        text = (
            f"Összesen: {stats['total_cues']} │ "
            f"Fordítva: {stats['translated_cues']} │ "
            f"Lip-sync hibák: {stats['lipsync_issues']} │ "
            f"{stats['completion_percent']:.0f}%"
        )
        self.stats_label.setText(text)
    
    def _refresh_cue_list(self):
        """Cue lista frissítése."""
        if self.project_manager.is_open:
            cues = self.project_manager.get_cues()
            self.cue_list.set_cues(cues)
    
    def _check_save_changes(self) -> bool:
        """Mentetlen változások ellenőrzése."""
        if not self.project_manager.is_dirty:
            return True
        
        reply = QMessageBox.question(
            self, "Mentetlen változások",
            "Vannak mentetlen változások. Menteni szeretné?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )
        
        if reply == QMessageBox.StandardButton.Save:
            return self._on_save_project()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        return False
    
    def closeEvent(self, event: QCloseEvent):
        """Ablak bezárása."""
        if self._check_save_changes():
            self._save_settings()
            self.project_manager.close()
            event.accept()
        else:
            event.ignore()
    
    # === Slots ===
    
    @Slot()
    def _on_new_project(self):
        if not self._check_save_changes():
            return
        self.project_manager.new_project()
        self._refresh_cue_list()
        self._update_title()
        self._update_ui_state()
        self.statusBar().showMessage("Új projekt létrehozva", 3000)
    
    @Slot()
    def _on_open_project(self):
        if not self._check_save_changes():
            return
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Projekt megnyitása", start_dir, get_project_filter()
        )
        
        if file_path:
            self._do_open_project(file_path)
    
    def _do_open_project(self, file_path: str):
        """
        Projekt megnyitása.
        
        Args:
            file_path: Projekt fájl elérési útja
        """
        try:
            # sourcery skip: merge-nested-ifs
            self.project_manager.open_project(Path(file_path))
            self._refresh_cue_list()
            
            project = self.project_manager.project
            if project is not None and project.has_video():
                video_path = Path(project.video_path)
                if video_path.exists():
                    self.video_player.load_video(video_path)
                else:
                    # Videó nem található - lecsatoljuk és figyelmeztetünk
                    self.project_manager.update_project(video_path="")
                    self.video_player._show_no_video()
                    QMessageBox.warning(
                        self, "Videó nem található",
                        f"A projekthez csatolt videó nem található:\n\n{video_path}\n\n"
                        "A videó lecsatolva. A Fájl → Import → Videó menüből újra csatolhatod."
                    )
            
            self._update_title()
            self._update_ui_state()
            self.statusBar().showMessage("Projekt megnyitva", 3000)
            
            # Plugin esemény
            if project is not None:
                for plugin in self.plugin_manager.get_ui_plugins():
                    plugin.on_project_opened(project)
                
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Nem sikerült megnyitni: {e}")
    
    def open_project_file(self, file_path: str):
        """
        Projekt megnyitása fájl elérési úttal (pl. parancssorból).
        
        Args:
            file_path: Projekt fájl elérési útja
        """
        if not self._check_save_changes():
            return
        
        if Path(file_path).exists():
            self._do_open_project(file_path)
        else:
            QMessageBox.critical(self, "Hiba", f"A fájl nem található:\n{file_path}")
    
    @Slot()
    def _on_save_project(self) -> bool:
        if not self.project_manager.is_open:
            return False
        
        if self.project_manager.project_path is None:
            return self._on_save_project_as()
        
        try:
            self.project_manager.save_project()
            self._update_title()
            self.statusBar().showMessage("Projekt mentve", 3000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Hiba", f"Mentési hiba: {e}")
            return False
    
    @Slot()
    def _on_save_project_as(self) -> bool:
        if not self.project_manager.is_open:
            return False
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        default_file = Path(start_dir) / f"projekt{PROJECT_EXTENSION}" if start_dir else f"projekt{PROJECT_EXTENSION}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Projekt mentése", str(default_file), get_project_filter()
        )
        
        if file_path:
            try:
                if not file_path.endswith(PROJECT_EXTENSION):
                    file_path += PROJECT_EXTENSION
                
                # Pass the path to save_project which handles the file creation
                self.project_manager.save_project(Path(file_path))
                self._update_title()
                self.statusBar().showMessage("Projekt mentve", 3000)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Hiba", f"Mentési hiba: {e}")
        return False
    
    @Slot()
    def _on_import_srt(self):
        if not self.project_manager.is_open:
            return
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        
        file_path, _ = QFileDialog.getOpenFileName(self, t("menu.file.import_srt").replace("...", ""), start_dir, get_srt_filter())
        
        if file_path:
            try:
                count, errors = self.project_manager.import_srt(Path(file_path))
                self._refresh_cue_list()
                self._update_statistics()
                
                # Lock source text after import
                self.cue_editor.set_source_locked(True)
                
                msg = t("messages.srt_imported", count=count)
                if errors:
                    msg += f"\n\n{t('messages.warnings')}:\n" + "\n".join(errors[:5])
                
                QMessageBox.information(self, t("menu.file.import"), msg)
                self._update_title()
            except Exception as e:
                QMessageBox.critical(self, t("messages.error"), t("messages.error_loading", error=str(e)))
    
    @Slot()
    def _on_import_video(self):
        if not self.project_manager.is_open:
            return
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        
        file_path, _ = QFileDialog.getOpenFileName(self, t("menu.file.import_video").replace("...", ""), start_dir, get_video_filter())
        
        if file_path:
            try:
                self.video_player.load_video(Path(file_path))
                self.project_manager.update_project(video_path=file_path)
                self._update_title()
                self.statusBar().showMessage(t("messages.video_loaded", name=Path(file_path).name), 3000)
            except Exception as e:
                QMessageBox.critical(self, t("messages.error"), t("messages.error_loading", error=str(e)))
    
    @Slot()
    def _on_export_pdf(self):
        if not self.project_manager.is_open or self.project_manager.project is None:
            return
        
        project = self.project_manager.project
        default_name = project.get_display_title()
        default_name = "".join(c for c in default_name if c.isalnum() or c in " -_")
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        default_file = Path(start_dir) / f"{default_name}.pdf" if start_dir else f"{default_name}.pdf"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, t("menu.file.export_pdf").replace("...", ""), str(default_file), "PDF (*.pdf)"
        )
        
        if file_path:
            try:
                cues = self.project_manager.get_cues()
                exporter = PDFExporter()
                exporter.export(Path(file_path), project, cues)
                QMessageBox.information(self, t("menu.file.export"), t("messages.export_success", path=file_path))
            except Exception as e:
                QMessageBox.critical(self, t("messages.error"), t("messages.export_error", error=str(e)))
    
    @Slot()
    def _on_export_srt(self):
        if not self.project_manager.is_open:
            return
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        default_file = Path(start_dir) / "forditas.srt" if start_dir else "forditas.srt"
        
        file_path, _ = QFileDialog.getSaveFileName(self, t("menu.file.export_srt").replace("...", ""), str(default_file), get_srt_filter())
        
        if file_path:
            try:
                from dubsync.services.srt_parser import export_to_srt
                cues = self.project_manager.get_cues()
                content = export_to_srt(cues, use_translated=True)
                Path(file_path).write_text(content, encoding="utf-8")
                QMessageBox.information(self, t("menu.file.export"), t("messages.export_success", path=file_path))
            except Exception as e:
                QMessageBox.critical(self, t("messages.error"), t("messages.export_error", error=str(e)))
    
    def _on_plugin_export(self, plugin):
        """Plugin export végrehajtása."""
        if not self.project_manager.is_open or self.project_manager.project is None:
            return
        
        project = self.project_manager.project
        default_name = project.get_display_title()
        default_name = "".join(c for c in default_name if c.isalnum() or c in " -_")
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        default_file = Path(start_dir) / f"{default_name}{plugin.file_extension}" if start_dir else f"{default_name}{plugin.file_extension}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"{plugin.info.name}",
            str(default_file),
            plugin.file_filter
        )
        
        if file_path:
            try:
                cues = self.project_manager.get_cues()
                plugin.export(Path(file_path), self.project_manager.project, cues)
                QMessageBox.information(
                    self, t("menu.file.export"), 
                    t("messages.export_success", path=file_path)
                )
            except Exception as e:
                QMessageBox.critical(self, t("messages.error"), t("messages.export_error", error=str(e)))
    
    @Slot()
    def _on_project_settings(self):
        if not self.project_manager.is_open or self.project_manager.project is None:
            return
        
        dialog = ProjectSettingsDialog(self.project_manager.project, self)
        if dialog.exec():
            self.project_manager.update_project(
                title=dialog.title_edit.text(),
                series_title=dialog.series_edit.text(),
                season=dialog.season_edit.text(),
                episode=dialog.episode_edit.text(),
                episode_title=dialog.episode_title_edit.text(),
                translator=dialog.translator_edit.text(),
                editor=dialog.editor_edit.text(),
                frame_rate=dialog.framerate_spin.value(),
            )
            self._update_title()
    
    @Slot()
    def _on_theme_settings(self):
        dialog = ThemeSettingsDialog(self)
        if dialog.exec():
            theme_type = dialog.get_selected_theme()
            if theme_type == ThemeType.CUSTOM:
                if custom_colors := dialog.get_custom_colors():
                    self.theme_manager.set_custom_colors(custom_colors)
                    # Egyedi színek mentése
                    self.settings_manager.custom_theme_colors = {
                        "primary": custom_colors.primary,
                        "background": custom_colors.background,
                        "surface": custom_colors.surface,
                        "foreground": custom_colors.foreground,
                    }
                    self.settings_manager.save_settings()
            else:
                self.theme_manager.set_theme(theme_type)
            
            self._apply_theme()
            self.settings.setValue("theme", theme_type.value)
    
    @Slot()
    def _on_app_settings(self):
        """Alkalmazás beállítások dialógus."""
        from dubsync.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=self, plugin_manager=self.plugin_manager)
        dialog.theme_changed.connect(self._apply_theme)
        
        if dialog.exec():
            # Beállítások mentve
            self.statusBar().showMessage(t("messages.settings_saved"), 3000)
    
    @Slot()
    def _on_toggle_delete_mode(self):
        self._delete_mode = self.action_delete_mode.isChecked()
        self._update_delete_mode_ui()
        
        if self._delete_mode:
            self.statusBar().showMessage(t("messages.delete_mode_on"), 3000)
        else:
            self.statusBar().showMessage(t("messages.delete_mode_off"), 2000)
    
    @Slot()
    def _on_add_cue(self):
        if not self.project_manager.is_open:
            return
        
        # Try to get current video position for new cue timing
        video_position_ms = None
        if self.video_player.player.hasVideo():
            video_position_ms = self.video_player.player.position()
        
        cue = self.project_manager.add_new_cue(time_in_ms=video_position_ms)
        self._refresh_cue_list()
        self.cue_list.select_cue(cue.id)
        self._update_title()
        self._update_statistics()
        
        # Unlock source text for new cue
        self.cue_editor.set_source_locked(False)
        
        self.statusBar().showMessage(t("messages.cue_added"), 2000)
    
    @Slot()
    def _on_insert_cue_before(self):
        """Sor beszúrása az aktuális elé."""
        if not self.project_manager.is_open:
            return
        
        current_index = self.cue_list.get_current_index()
        if current_index <= 1:
            current_index = 1
        else:
            current_index -= 1
        
        cue = self.project_manager.insert_cue_at(current_index)
        self._refresh_cue_list()
        self.cue_list.select_cue(cue.id)
        self._update_title()
        self._update_statistics()
        self.statusBar().showMessage(t("messages.cue_inserted_before", index=current_index), 2000)
    
    @Slot()
    def _on_insert_cue_after(self):
        """Sor beszúrása az aktuális mögé."""
        if not self.project_manager.is_open:
            return
        
        current_index = self.cue_list.get_current_index()
        if current_index == 0:
            current_index = 1
        
        cue = self.project_manager.insert_cue_at(current_index + 1)
        self._refresh_cue_list()
        self.cue_list.select_cue(cue.id)
        self._update_title()
        self._update_statistics()
        self.statusBar().showMessage(t("messages.cue_inserted_after", index=current_index), 2000)
    
    @Slot(int)
    def _on_insert_cue_at(self, after_index: int):
        if not self.project_manager.is_open:
            return
        
        cue = self.project_manager.insert_cue_at(after_index + 1)
        self._refresh_cue_list()
        self.cue_list.select_cue(cue.id)
        self._update_title()
        self._update_statistics()
    
    @Slot()
    def _on_delete_cue(self):
        if not self._delete_mode or not self.project_manager.is_open:
            return
        
        if cue_id := self.cue_list.get_selected_cue_id():
            self._on_delete_cue_confirmed(cue_id)
    
    @Slot(int)
    def _on_delete_cue_confirmed(self, cue_id: int):
        if not self._delete_mode:
            QMessageBox.warning(
                self, t("menu.edit.delete_mode"),
                t("messages.delete_mode_required")
            )
            return
        
        reply = QMessageBox.question(
            self, t("dialogs.confirm_delete.title"), t("dialogs.confirm_delete.message", index=cue_id),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if cue := self.project_manager.get_cue(cue_id):
                cue_data = {
                    'id': cue.id,
                    'project_id': cue.project_id,
                    'cue_index': cue.cue_index,
                    'time_in_ms': cue.time_in_ms,
                    'time_out_ms': cue.time_out_ms,
                    'source_text': cue.source_text,
                    'translated_text': cue.translated_text,
                    'character_name': cue.character_name,
                    'notes': cue.notes,
                    'sfx_notes': cue.sfx_notes,
                    'status': cue.status.value,
                    'lip_sync_ratio': cue.lip_sync_ratio,
                }
                
                # Create and push undo command
                cmd = DeleteCueCommand(self, cue_data)
                self._undo_stack.push(cmd)
                
                self.statusBar().showMessage(t("messages.cue_deleted"), 3000)
    
    @Slot()
    def _on_edit_timing(self):
        if not self.project_manager.is_open:
            return
        
        cue_id = self.cue_list.get_selected_cue_id()
        if not cue_id:
            QMessageBox.information(self, t("dialogs.timing_editor.title"), t("messages.select_cue_for_timing"))
            return
        
        if cue := self.project_manager.get_cue(cue_id):
            self.cue_editor.show_timing_editor(cue)
    
    @Slot()
    def _on_timing_changed(self):
        if cue := self.cue_editor.get_cue():
            self.project_manager.save_cue(cue)
            self._refresh_cue_list()
            self._update_title()
            self._update_statistics()
            self.statusBar().showMessage(t("messages.timing_saved"), 2000)
    
    @Slot()
    def _on_recalculate_lipsync(self):
        if not self.project_manager.is_open:
            return
        
        count = self.project_manager.recalculate_all_lipsync()
        self._refresh_cue_list()
        self._update_statistics()
        self.statusBar().showMessage(t("messages.lipsync_recalculated", count=count), 3000)
    
    @Slot()
    def _on_goto_next_empty(self):
        if not self.project_manager.is_open or self.project_manager.db is None or self.project_manager.project is None:
            return
        
        from dubsync.models.cue import Cue
        current_index = self.cue_list.get_current_index()
        
        if cue := Cue.find_next_empty(
            self.project_manager.db, current_index, self.project_manager.project.id
        ):
            self.cue_list.select_cue(cue.id)
        else:
            self.statusBar().showMessage(t("messages.no_more_empty_cues"), 3000)
    
    @Slot()
    def _on_goto_next_lipsync_issue(self):
        if not self.project_manager.is_open or self.project_manager.db is None or self.project_manager.project is None:
            return
        
        from dubsync.models.cue import Cue
        current_index = self.cue_list.get_current_index()
        
        if cue := Cue.find_next_lipsync_issue(
            self.project_manager.db, current_index, self.project_manager.project.id
        ):
            self.cue_list.select_cue(cue.id)
        else:
            self.statusBar().showMessage(t("messages.no_more_lipsync_issues"), 3000)
    
    @Slot()
    def _on_goto_next_comment(self):
        self.statusBar().showMessage(t("messages.searching_next_comment"), 3000)
    
    @Slot()
    def _on_about(self):
        """Névjegy - Beállítások Névjegy fülét nyitja meg."""
        from dubsync.ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, initial_tab="about")
        dialog.exec()
    
    @Slot()
    def _on_tutorial(self):
        """Tutorial ablak megnyitása."""
        from dubsync.ui.dialogs import TutorialDialog
        dialog = TutorialDialog(self)
        dialog.exec()
    
    @Slot()
    def _toggle_fullscreen(self):
        """Teljes képernyő váltás."""
        if self.isFullScreen():
            self.showNormal()
            self.action_fullscreen.setChecked(False)
        else:
            self.showFullScreen()
            self.action_fullscreen.setChecked(True)
    
    @Slot(int)
    def _on_cue_selected(self, cue_id: int):
        if (cue := self.project_manager.get_cue(cue_id)) and self.project_manager.db is not None:
            self.cue_editor.set_cue(cue)
            self.comments_panel.set_cue(cue, self.project_manager.db)
            self.video_player.seek_to(cue.time_in_ms)
            
            # Set subtitle for fullscreen video
            subtitle_text = cue.translated_text or cue.source_text
            self.video_player.set_subtitle(subtitle_text)
            
            # Plugin értesítés
            self._notify_plugins_cue_selected(cue)
    
    @Slot(int)
    def _on_cue_double_clicked(self, cue_id: int):
        if self._delete_mode:
            self._on_delete_cue_confirmed(cue_id)
        elif cue := self.project_manager.get_cue(cue_id):
            self.video_player.play_segment(cue.time_in_ms, cue.time_out_ms)
    
    @Slot()
    def _on_cue_saved(self):
        if cue := self.cue_editor.get_cue():
            # Save the current cue index BEFORE refreshing (refresh loses selection)
            current_cue_index = cue.cue_index
            
            self.project_manager.save_cue(cue)
            self._refresh_cue_list()
            self._update_title()
            self._update_statistics()
            
            # Go to the next cue in sequence based on saved index
            self._goto_next_cue_from_index(current_cue_index)
    
    @Slot()
    def _on_cue_status_changed(self):
        self._on_cue_saved()
    
    @Slot(int)
    def _on_video_position_changed(self, position_ms: int):
        from dubsync.models.cue import Cue
        if self.project_manager.is_open and self.project_manager.db is not None and self.project_manager.project is not None:
            if cue := Cue.find_at_time(
                self.project_manager.db, position_ms, self.project_manager.project.id
            ):
                self.cue_list.highlight_cue(cue.id)
    
    @Slot()
    def _on_comment_added(self):
        self._update_title()
    
    def _goto_next_cue(self):
        """Ugrás a következő sorra."""
        if not self.project_manager.is_open:
            return
        
        current_index = self.cue_list.get_current_index()
        self._goto_next_cue_from_index(current_index)
    
    def _goto_next_cue_from_index(self, current_index: int):
        """
        Ugrás a következő sorra adott index alapján.
        
        Args:
            current_index: Jelenlegi cue index
        """
        if not self.project_manager.is_open:
            return
        
        cues = self.project_manager.get_cues()
        
        # Keressük a következő cue-t
        for cue in cues:
            if cue.cue_index > current_index:
                self.cue_list.select_cue(cue.id)
                return
        
        # Ha nincs több, maradunk az utolsón
        self.statusBar().showMessage(t("messages.last_cue"), 2000)
    
    @Slot()
    def _on_goto_next_cue(self):
        """Navigáció a következő sorra (Ctrl+Down)."""
        self._goto_next_cue()
    
    @Slot()
    def _on_goto_prev_cue(self):
        """Navigáció az előző sorra (Ctrl+Up)."""
        if not self.project_manager.is_open:
            return
        
        current_index = self.cue_list.get_current_index()
        cues = self.project_manager.get_cues()
        
        # Keressük az előző cue-t (visszafelé)
        prev_cue = None
        for cue in cues:
            if cue.cue_index < current_index:
                prev_cue = cue
            else:
                break
        
        if prev_cue:
            self.cue_list.select_cue(prev_cue.id)
        else:
            self.statusBar().showMessage(t("messages.first_cue"), 2000)
