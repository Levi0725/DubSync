"""
DubSync Main Window

Main application window for the dubbing editor.
"""

from pathlib import Path
from typing import Optional, cast

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QMenu, QToolBar, QFileDialog, QMessageBox,
    QLabel, QDockWidget, QApplication, QDialog,
    QFormLayout, QComboBox, QColorDialog, QPushButton, QDialogButtonBox
)
from PySide6.QtCore import Qt, Signal, Slot, QSettings, QSize
from PySide6.QtGui import QAction, QKeySequence, QCloseEvent, QUndoStack, QUndoCommand

from dubsync.utils.constants import APP_NAME, APP_VERSION, PROJECT_EXTENSION
from dubsync.i18n import t
from dubsync.services.project_manager import (
    ProjectManager, get_project_filter, get_srt_filter, get_video_filter
)
from dubsync.services.pdf_export import PDFExporter
from dubsync.services.settings_manager import SettingsManager
from dubsync.services.crash_handler import log_activity, get_crash_handler
from dubsync.ui.cue_list import CueListWidget
from dubsync.ui.cue_editor import CueEditorWidget
from dubsync.ui.video_player import VideoPlayerWidget
from dubsync.ui.comments_panel import CommentsPanelWidget
from dubsync.ui.timeline_widget import TimelineWidget
from dubsync.ui.dialogs import ProjectSettingsDialog, BatchTimingDialog
from dubsync.ui.theme import ThemeManager, ThemeType, ThemeColors, THEMES
from dubsync.plugins.base import PluginManager
from dubsync.resources import get_icon, get_icon_manager


class DeleteCueCommand(QUndoCommand):
    """Undo command for deleting a cue."""
    
    def __init__(self, main_window, cue_data: dict, parent=None):
        super().__init__(t("dialogs.confirm_delete.title"), parent)
        self._main_window = main_window
        self._cue_data = cue_data
        self._cue_id = cue_data.get('id')
    
    def redo(self):
        """Perform deletion."""
        if self._cue_id:
            self._main_window.project_manager.delete_cue(self._cue_id)
            self._main_window._refresh_cue_list()
            self._main_window._update_title()
            self._main_window._update_statistics()
    
    def undo(self):
        """Undo deletion - restore cue."""
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
    """Theme settings dialog."""
    
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
        
        # If custom theme, load saved colors
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
        color = QColorDialog.getColor(QColor(current), self, f"Choose {key} color")
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
    """Main window for the DubSync application."""
    
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
        """Setup UI."""
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)

        layout = self._extracted_from__setup_ui_9(central, 4)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.main_splitter)

        # ═══════════════════════════════════════════════════════════════
        # LEFT PANEL: Cue List + Timeline (stacked vertically)
        # ═══════════════════════════════════════════════════════════════
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Cue list (main)
        self.cue_list = CueListWidget()
        left_layout.addWidget(self.cue_list, 1)
        
        # Timeline widget underneath cue list
        self.timeline_container = QWidget()
        timeline_container_layout = QVBoxLayout(self.timeline_container)
        timeline_container_layout.setContentsMargins(0, 0, 0, 0)
        timeline_container_layout.setSpacing(0)
        
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setMaximumHeight(100)
        self.timeline_widget.setMinimumHeight(60)
        timeline_container_layout.addWidget(self.timeline_widget)
        
        left_layout.addWidget(self.timeline_container, 0)
        
        self.main_splitter.addWidget(left_widget)

        # ═══════════════════════════════════════════════════════════════
        # RIGHT PANEL: Video Player + Cue Editor (with adjustable splitter)
        # ═══════════════════════════════════════════════════════════════
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setHandleWidth(4)
        
        # Video player at top (adjustable height)
        self.video_player = VideoPlayerWidget()
        self.video_player.setMinimumHeight(150)
        right_splitter.addWidget(self.video_player)

        # Cue editor at bottom
        self.cue_editor = CueEditorWidget()
        self.cue_editor.setMinimumHeight(120)
        right_splitter.addWidget(self.cue_editor)
        
        # Set initial sizes: video 60%, editor 40%
        right_splitter.setSizes([350, 250])
        
        self.main_splitter.addWidget(right_splitter)

        self.comments_dock = QDockWidget(t("comments_panel.title"), self)
        self.comments_dock.setObjectName("commentsDock")
        self.comments_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.comments_panel = CommentsPanelWidget()
        self.comments_dock.setWidget(self.comments_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.comments_dock)

        self.main_splitter.setSizes([400, 800])

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_9(self, arg0, arg1):
        result = QVBoxLayout(arg0)
        result.setContentsMargins(arg1, arg1, arg1, arg1)
        result.setSpacing(4)

        return result
    
    def _create_action(self, text: str, icon_name: str = "", shortcut: str = "") -> QAction:
        """Create an action with optional icon and shortcut."""
        action = QAction(text, self)
        if icon_name:
            icon = get_icon(icon_name)
            if not icon.isNull():
                action.setIcon(icon)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        return action
    
    def _setup_menus(self):
        """Setup menus."""
        menubar = self.menuBar()
        
        # === File menu ===
        file_menu = menubar.addMenu(t("menu.file._title"))
        
        self.action_new = self._create_action(t("menu.file.new"), "file_new")
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self._on_new_project)
        file_menu.addAction(self.action_new)
        
        self.action_open = self._create_action(t("menu.file.open"), "file_open")
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self._on_open_project)
        file_menu.addAction(self.action_open)
        
        self.action_save = self._create_action(t("menu.file.save"), "file_save")
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self._on_save_project)
        file_menu.addAction(self.action_save)
        
        self.action_save_as = self._create_action(t("menu.file.save_as"), "file_save_as")
        self.action_save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.action_save_as.triggered.connect(self._on_save_project_as)
        file_menu.addAction(self.action_save_as)
        
        file_menu.addSeparator()
        
        self.import_menu = file_menu.addMenu(t("menu.file.import"))
        self.import_menu.setIcon(get_icon("file_import"))
        
        self.action_import_srt = self._create_action(t("menu.file.import_srt"), "file_import")
        self.action_import_srt.triggered.connect(self._on_import_srt)
        self.import_menu.addAction(self.action_import_srt)
        
        self.action_import_video = self._create_action(t("menu.file.import_video"), "player_play")
        self.action_import_video.triggered.connect(self._on_import_video)
        self.import_menu.addAction(self.action_import_video)
        
        self.export_menu = file_menu.addMenu(t("menu.file.export"))
        self.export_menu.setIcon(get_icon("file_export"))
        
        self.action_export_pdf = self._create_action(t("menu.file.export_pdf"), "file_pdf")
        self.action_export_pdf.triggered.connect(self._on_export_pdf)
        self.export_menu.addAction(self.action_export_pdf)
        
        self.action_export_srt = self._create_action(t("menu.file.export_srt"), "file_export")
        self.action_export_srt.triggered.connect(self._on_export_srt)
        self.export_menu.addAction(self.action_export_srt)
        
        # Plugin export formats will be added later in _setup_plugins()
        
        file_menu.addSeparator()
        
        self.action_settings = self._create_action(t("menu.file.project_settings"), "settings")
        self.action_settings.triggered.connect(self._on_project_settings)
        file_menu.addAction(self.action_settings)
        
        self.action_app_settings = self._create_action(t("menu.file.app_settings"), "settings_general")
        self.action_app_settings.setShortcut(QKeySequence("Ctrl+,"))
        self.action_app_settings.triggered.connect(self._on_app_settings)
        file_menu.addAction(self.action_app_settings)
        
        file_menu.addSeparator()
        
        self.action_exit = self._create_action(t("menu.file.exit"), "close")
        self.action_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.action_exit.triggered.connect(self.close)
        file_menu.addAction(self.action_exit)
        
        # === Edit menu ===
        edit_menu = menubar.addMenu(t("menu.edit._title"))
        
        self.action_undo = self._undo_stack.createUndoAction(self, t("menu.edit.undo"))
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.setIcon(get_icon("edit_undo"))
        edit_menu.addAction(self.action_undo)
        
        self.action_redo = self._undo_stack.createRedoAction(self, t("menu.edit.redo"))
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.setIcon(get_icon("edit_redo"))
        edit_menu.addAction(self.action_redo)
        
        edit_menu.addSeparator()
        
        self.action_add_cue = self._create_action(t("menu.edit.add_cue"), "cue_add")
        self.action_add_cue.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.action_add_cue.triggered.connect(self._on_add_cue)
        edit_menu.addAction(self.action_add_cue)
        
        self.action_insert_cue_before = self._create_action(t("menu.edit.insert_before"), "cue_move_up")
        self.action_insert_cue_before.setShortcut(QKeySequence("Ctrl+Shift+Up"))
        self.action_insert_cue_before.triggered.connect(self._on_insert_cue_before)
        edit_menu.addAction(self.action_insert_cue_before)
        
        self.action_insert_cue_after = self._create_action(t("menu.edit.insert_after"), "cue_move_down")
        self.action_insert_cue_after.setShortcut(QKeySequence("Ctrl+Shift+Down"))
        self.action_insert_cue_after.triggered.connect(self._on_insert_cue_after)
        edit_menu.addAction(self.action_insert_cue_after)
        
        self.action_delete_mode = self._create_action(t("menu.edit.delete_mode"), "edit_delete")
        self.action_delete_mode.setShortcut(QKeySequence("Ctrl+D"))
        self.action_delete_mode.setCheckable(True)
        self.action_delete_mode.triggered.connect(self._on_toggle_delete_mode)
        edit_menu.addAction(self.action_delete_mode)
        
        self.action_delete_cue = self._create_action(t("menu.edit.delete_cue"), "cue_delete")
        self.action_delete_cue.setShortcut(QKeySequence.StandardKey.Delete)
        self.action_delete_cue.triggered.connect(self._on_delete_cue)
        self.action_delete_cue.setEnabled(False)
        edit_menu.addAction(self.action_delete_cue)
        
        edit_menu.addSeparator()
        
        self.action_edit_timing = self._create_action(t("menu.edit.edit_timing"), "cue_timing")
        self.action_edit_timing.setShortcut(QKeySequence("Ctrl+T"))
        self.action_edit_timing.triggered.connect(self._on_edit_timing)
        edit_menu.addAction(self.action_edit_timing)
        
        self.action_batch_timing = self._create_action(t("menu.edit.batch_timing"), "cue_sync")
        self.action_batch_timing.setShortcut(QKeySequence("Ctrl+Shift+T"))
        self.action_batch_timing.triggered.connect(self._on_batch_timing)
        edit_menu.addAction(self.action_batch_timing)
        
        edit_menu.addSeparator()
        
        self.action_recalc_lipsync = self._create_action(t("menu.edit.recalc_lipsync"), "sync")
        self.action_recalc_lipsync.triggered.connect(self._on_recalculate_lipsync)
        edit_menu.addAction(self.action_recalc_lipsync)
        
        # === Navigate menu ===
        nav_menu = menubar.addMenu(t("menu.navigate._title"))
        
        self.action_prev_cue = self._create_action(t("menu.navigate.prev_cue"), "chevron_left")
        self.action_prev_cue.setShortcut(QKeySequence("Ctrl+Up"))
        self.action_prev_cue.triggered.connect(self._on_goto_prev_cue)
        nav_menu.addAction(self.action_prev_cue)
        
        self.action_next_cue = self._create_action(t("menu.navigate.next_cue"), "chevron_right")
        self.action_next_cue.setShortcut(QKeySequence("Ctrl+Down"))
        self.action_next_cue.triggered.connect(self._on_goto_next_cue)
        nav_menu.addAction(self.action_next_cue)
        
        nav_menu.addSeparator()
        
        self.action_next_empty = self._create_action(t("menu.navigate.next_empty"), "edit_find")
        self.action_next_empty.setShortcut(QKeySequence("Ctrl+E"))
        self.action_next_empty.triggered.connect(self._on_goto_next_empty)
        nav_menu.addAction(self.action_next_empty)
        
        self.action_next_lipsync = self._create_action(t("menu.navigate.next_lipsync"), "warning")
        self.action_next_lipsync.setShortcut(QKeySequence("Ctrl+L"))
        self.action_next_lipsync.triggered.connect(self._on_goto_next_lipsync_issue)
        nav_menu.addAction(self.action_next_lipsync)
        
        self.action_next_comment = self._create_action(t("menu.navigate.next_comment"), "comment_unresolved")
        self.action_next_comment.setShortcut(QKeySequence("Ctrl+M"))
        self.action_next_comment.triggered.connect(self._on_goto_next_comment)
        nav_menu.addAction(self.action_next_comment)
        
        # === View menu ===
        self.view_menu = menubar.addMenu(t("menu.view._title"))
        
        # Panels directly in the menu (better UX)
        self.view_menu.addSection(t("menu.view.panels"))
        
        self.action_toggle_comments = self.comments_dock.toggleViewAction()
        self.action_toggle_comments.setText(t("menu.view.comments_panel"))
        self.action_toggle_comments.setIcon(get_icon("view_comments"))
        self.view_menu.addAction(self.action_toggle_comments)
        
        # Timeline toggle
        self.action_toggle_timeline = self._create_action(t("menu.view.timeline_panel"), "view_timeline")
        self.action_toggle_timeline.setCheckable(True)
        self.action_toggle_timeline.setChecked(True)
        self.action_toggle_timeline.triggered.connect(self._toggle_timeline)
        self.view_menu.addAction(self.action_toggle_timeline)
        
        # Plugin panels will be added later in _setup_plugins()
        
        self.view_menu.addSeparator()
        
        self.action_fullscreen = self._create_action(t("menu.view.fullscreen"), "view_fullscreen")
        self.action_fullscreen.setShortcut(QKeySequence("F11"))
        self.action_fullscreen.setCheckable(True)
        self.action_fullscreen.triggered.connect(self._toggle_fullscreen)
        self.view_menu.addAction(self.action_fullscreen)
        
        # === Help menu ===
        help_menu = menubar.addMenu(t("menu.help._title"))
        
        self.action_tutorial = self._create_action(t("menu.help.tutorial"), "help")
        self.action_tutorial.setShortcut(QKeySequence("F1"))
        self.action_tutorial.triggered.connect(self._on_tutorial)
        help_menu.addAction(self.action_tutorial)
        
        help_menu.addSeparator()
        
        self.action_about = self._create_action(t("menu.help.about"), "about")
        self.action_about.triggered.connect(self._on_about)
        help_menu.addAction(self.action_about)
    
    def _setup_toolbar(self):
        """Setup toolbar."""
        toolbar = QToolBar(t("toolbar.main"))
        toolbar.setObjectName("mainToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
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
        """Setup status bar."""
        statusbar = self.statusBar()
        
        self.delete_mode_label = QLabel("")
        self.delete_mode_label.setStyleSheet("color: #f44336; font-weight: bold;")
        statusbar.addWidget(self.delete_mode_label)
        
        self.progress_label = QLabel("")
        statusbar.addWidget(self.progress_label)
        
        self.stats_label = QLabel("")
        statusbar.addPermanentWidget(self.stats_label)
    
    def _connect_signals(self):
        """Connect signal-slot."""
        self.cue_list.cue_selected.connect(self._on_cue_selected)
        self.cue_list.cue_double_clicked.connect(self._on_cue_double_clicked)
        self.cue_list.insert_cue_requested.connect(self._on_insert_cue_at)
        self.cue_list.delete_cue_requested.connect(self._on_delete_cue_confirmed)
        
        self.cue_editor.cue_saved.connect(self._on_cue_saved)
        self.cue_editor.status_changed.connect(self._on_cue_status_changed)
        self.cue_editor.timing_changed.connect(self._on_timing_changed)
        
        self.video_player.position_changed.connect(self._on_video_position_changed)
        
        self.comments_panel.comment_added.connect(self._on_comment_added)
        
        # Timeline signals
        self.timeline_widget.cue_selected.connect(self._on_cue_selected)
        self.timeline_widget.cue_double_clicked.connect(self._on_cue_double_clicked)
        self.timeline_widget.playhead_moved.connect(self._on_timeline_playhead_moved)
        self.timeline_widget.cue_moved.connect(self._on_timeline_cue_moved)
        self.timeline_widget.cue_resized.connect(self._on_timeline_cue_resized)
    
    def _load_settings(self):
        """Load settings."""
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
        """Save settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("theme", self.theme_manager.current_theme.value)
    
    def _apply_theme(self):
        """Apply theme."""
        stylesheet = self.theme_manager.get_stylesheet()
        app = QApplication.instance()
        if app is not None:
            cast(QApplication, app).setStyleSheet(stylesheet)
        
        # Update icon colors based on theme
        from PySide6.QtGui import QColor
        icon_manager = get_icon_manager()
        icon_color = QColor(self.theme_manager.colors.foreground)
        icon_manager.set_icon_color(icon_color)
        
        # Rebuild menus to apply new icon colors
        self._refresh_menu_icons()
        
        # Update widget icons
        if hasattr(self, 'video_player'):
            self.video_player.update_icons()
    
    def _setup_plugins(self):
        """Setup plugin UI elements."""
        # Add export plugins to File->Export menu
        for export_plugin in self.plugin_manager.get_export_plugins(enabled_only=True):
            try:
                action = QAction(export_plugin.info.name + "...", self)
                action.setIcon(get_icon("file_export"))
                action.setData(export_plugin.info.id)
                action.triggered.connect(lambda checked, p=export_plugin: self._on_plugin_export(p))
                self.export_menu.addAction(action)
            except Exception as e:
                print(f"Export plugin error ({export_plugin.info.name}): {e}")
        
        # UI plugins
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.set_main_window(self)
                
                if dock := plugin.create_dock_widget():
                    self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
                    self._plugin_docks.append(dock)
                    
                    # Hide on start unless otherwise set
                    show_on_start = self.settings_manager.get_plugin_panel_visible(plugin.info.id)
                    if not show_on_start:
                        dock.hide()
                    
                    # Add panel toggle directly to the View menu
                    toggle_action = dock.toggleViewAction()
                    toggle_action.setText(plugin.info.name)
                    toggle_action.setIcon(get_icon("plugin"))
                    self.view_menu.insertAction(self.action_fullscreen, toggle_action)
                
                if menu_items := plugin.create_menu_items():
                    plugins_menu = self._get_or_create_plugins_menu()
                    for action in menu_items:
                        if not action.icon().isNull():
                            pass  # Keep existing icon
                        else:
                            action.setIcon(get_icon("plugin"))
                        plugins_menu.addAction(action)
                
            except Exception as e:
                print(f"Plugin UI error ({plugin.info.name}): {e}")
    
    def _get_or_create_plugins_menu(self) -> QMenu:
        """Get or create plugins menu."""
        if not hasattr(self, '_plugins_menu'):
            menubar = self.menuBar()
            self._plugins_menu = menubar.addMenu(t("menu.plugins"))
        return self._plugins_menu
    
    def _notify_plugins_cue_selected(self, cue):
        """Notify plugins of cue selection."""
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.on_cue_selected(cue)
            except Exception as e:
                print(f"Plugin cue_selected error ({plugin.info.name}): {e}")
    
    def _notify_plugins_project_opened(self, project):
        """Notify plugins of project opened."""
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.on_project_opened(project)
            except Exception as e:
                print(f"Plugin project_opened error ({plugin.info.name}): {e}")
    
    def _notify_plugins_project_closed(self):
        """Notify plugins of project closed."""
        for plugin in self.plugin_manager.get_ui_plugins(enabled_only=True):
            try:
                plugin.on_project_closed()
            except Exception as e:
                print(f"Plugin project_closed error ({plugin.info.name}): {e}")
    
    def _set_theme(self, theme_type: ThemeType):
        """Set theme."""
        self.theme_manager.set_theme(theme_type)
        self._apply_theme()
        self.settings.setValue("theme", theme_type.value)
    
    def _refresh_menu_icons(self):
        """Refresh all menu icons with current theme colors."""
        # File menu actions
        if hasattr(self, 'action_new'):
            self.action_new.setIcon(get_icon("file_new"))
        if hasattr(self, 'action_open'):
            self.action_open.setIcon(get_icon("file_open"))
        if hasattr(self, 'action_save'):
            self.action_save.setIcon(get_icon("file_save"))
        if hasattr(self, 'action_save_as'):
            self.action_save_as.setIcon(get_icon("file_save_as"))
        if hasattr(self, 'action_import_srt'):
            self.action_import_srt.setIcon(get_icon("file_import"))
        if hasattr(self, 'action_import_video'):
            self.action_import_video.setIcon(get_icon("player_play"))
        if hasattr(self, 'action_export_pdf'):
            self.action_export_pdf.setIcon(get_icon("file_pdf"))
        if hasattr(self, 'action_export_srt'):
            self.action_export_srt.setIcon(get_icon("file_export"))
        if hasattr(self, 'action_settings'):
            self.action_settings.setIcon(get_icon("settings"))
        if hasattr(self, 'action_app_settings'):
            self.action_app_settings.setIcon(get_icon("settings_general"))
        if hasattr(self, 'action_exit'):
            self.action_exit.setIcon(get_icon("close"))
        
        # Edit menu actions
        if hasattr(self, 'action_undo'):
            self.action_undo.setIcon(get_icon("edit_undo"))
        if hasattr(self, 'action_redo'):
            self.action_redo.setIcon(get_icon("edit_redo"))
        if hasattr(self, 'action_add_cue'):
            self.action_add_cue.setIcon(get_icon("cue_add"))
        if hasattr(self, 'action_insert_cue_before'):
            self.action_insert_cue_before.setIcon(get_icon("cue_move_up"))
        if hasattr(self, 'action_insert_cue_after'):
            self.action_insert_cue_after.setIcon(get_icon("cue_move_down"))
        if hasattr(self, 'action_delete_mode'):
            self.action_delete_mode.setIcon(get_icon("edit_delete"))
        if hasattr(self, 'action_delete_cue'):
            self.action_delete_cue.setIcon(get_icon("cue_delete"))
        if hasattr(self, 'action_edit_timing'):
            self.action_edit_timing.setIcon(get_icon("cue_timing"))
        if hasattr(self, 'action_batch_timing'):
            self.action_batch_timing.setIcon(get_icon("cue_sync"))
        if hasattr(self, 'action_recalc_lipsync'):
            self.action_recalc_lipsync.setIcon(get_icon("sync"))
        
        # Navigate menu actions
        if hasattr(self, 'action_prev_cue'):
            self.action_prev_cue.setIcon(get_icon("chevron_left"))
        if hasattr(self, 'action_next_cue'):
            self.action_next_cue.setIcon(get_icon("chevron_right"))
        if hasattr(self, 'action_next_empty'):
            self.action_next_empty.setIcon(get_icon("edit_find"))
        if hasattr(self, 'action_next_lipsync'):
            self.action_next_lipsync.setIcon(get_icon("warning"))
        if hasattr(self, 'action_next_comment'):
            self.action_next_comment.setIcon(get_icon("comment_unresolved"))
        
        # View menu actions
        if hasattr(self, 'action_toggle_comments'):
            self.action_toggle_comments.setIcon(get_icon("view_comments"))
        if hasattr(self, 'action_toggle_timeline'):
            self.action_toggle_timeline.setIcon(get_icon("view_timeline"))
        if hasattr(self, 'action_fullscreen'):
            self.action_fullscreen.setIcon(get_icon("view_fullscreen"))
        
        # Help menu actions
        if hasattr(self, 'action_tutorial'):
            self.action_tutorial.setIcon(get_icon("help"))
        if hasattr(self, 'action_about'):
            self.action_about.setIcon(get_icon("about"))
        
        # Submenus
        if hasattr(self, 'import_menu'):
            self.import_menu.setIcon(get_icon("file_import"))
        if hasattr(self, 'export_menu'):
            self.export_menu.setIcon(get_icon("file_export"))

    def _update_title(self):
        """Update window title."""
        title = f"{APP_NAME} {APP_VERSION}"
        
        if self.project_manager.is_open and self.project_manager.project is not None:
            project_name = self.project_manager.project.get_display_title()
            title = f"{project_name} - {title}"
            
            if self.project_manager.is_dirty:
                title = f"• {title}"
        
        self.setWindowTitle(title)
    
    def _update_ui_state(self):
        """Update UI state."""
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
        self.action_batch_timing.setEnabled(has_project)
        
        self.cue_list.setEnabled(has_project)
        self.cue_editor.setEnabled(has_project)
        self.video_player.setEnabled(has_project)
        self.comments_panel.setEnabled(has_project)
        
        self._update_delete_mode_ui()
        self._update_statistics()
    
    def _update_delete_mode_ui(self):
        """Update delete mode UI."""
        if self._delete_mode:
            self._extracted_from__update_delete_mode_ui_4(t("messages.delete_mode_on"), True)
        else:
            self._extracted_from__update_delete_mode_ui_4(t("messages.delete_mode_off"), False)

    # TODO Rename this here and in `_update_delete_mode_ui`
    def _extracted_from__update_delete_mode_ui_4(self, arg0, arg1):
        self.delete_mode_label.setText(arg0)
        self.action_delete_cue.setEnabled(arg1)
        self.cue_list.set_delete_mode(arg1)
    
    def _update_statistics(self):
        """Update statistics."""
        if not self.project_manager.is_open:
            self.stats_label.setText("")
            return
        
        stats = self.project_manager.get_statistics()
        text = (
            f"Total: {stats['total_cues']} │ "
            f"Translated: {stats['translated_cues']} │ "
            f"Lip-sync issues: {stats['lipsync_issues']} │ "
            f"{stats['completion_percent']:.0f}%"
        )
        self.stats_label.setText(text)
    
    def _refresh_cue_list(self):
        """Refresh cue list."""
        if self.project_manager.is_open:
            cues = self.project_manager.get_cues()
            self.cue_list.set_cues(cues)
            # Also update timeline
            self.timeline_widget.set_cues(cues)
    
    def _check_save_changes(self) -> bool:
        """Check for unsaved changes."""
        if not self.project_manager.is_dirty:
            return True
        
        reply = QMessageBox.question(
            self, t("dialogs.confirm_close.title"),
            t("dialogs.confirm_close.message"),
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
        """Close window."""
        if self._check_save_changes():
            self._save_settings()
            self.project_manager.close()
            event.accept()
        else:
            event.ignore()
    
    # === Slots ===
    
    @Slot()
    def _on_new_project(self):
        log_activity("New project requested")
        if not self._check_save_changes():
            return
        self.project_manager.new_project()
        self._refresh_cue_list()
        self._update_title()
        self._update_ui_state()
        log_activity("New project created")
        self.statusBar().showMessage(t("messages.project_created"), 3000)
    
    @Slot()
    def _on_open_project(self):
        log_activity("Open project dialog requested")
        if not self._check_save_changes():
            return
        
        # Kezdőmappa a beállításokból
        start_dir = self.settings_manager.default_save_path or ""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("dialogs.open_project.title"), start_dir, get_project_filter()
        )
        
        if file_path:
            self._do_open_project(file_path)
    
    def _do_open_project(self, file_path: str):
        """
        Open project.
        
        Args:
            file_path: Project file path
        """
        log_activity("Opening project", file_path)
        try:
            # sourcery skip: merge-nested-ifs
            self.project_manager.open_project(Path(file_path))
            get_crash_handler().set_current_project(file_path)
            self._refresh_cue_list()
            
            project = self.project_manager.project
            if project is not None and project.has_video():
                video_path = Path(project.video_path)
                if video_path.exists():
                    self.video_player.load_video(video_path)
                else:
                    # Video not found - detach and warn
                    self.project_manager.update_project(video_path="")
                    self.video_player._show_no_video()
                    QMessageBox.warning(
                        self, t("messages.warnings"),
                        t("messages.video_not_found", path=video_path)
                    )
            
            self._update_title()
            self._update_ui_state()
            self.statusBar().showMessage(t("messages.project_opened", name=""), 3000)
            
            # Plugin event
            if project is not None:
                for plugin in self.plugin_manager.get_ui_plugins():
                    plugin.on_project_opened(project)
                
        except Exception as e:
            QMessageBox.critical(self, t("messages.error"), t("messages.error_loading", error=str(e)))
    
    def open_project_file(self, file_path: str):
        """
        Open project from file path (e.g., from command line).
        
        Args:
            file_path: Project file path
        """
        if not self._check_save_changes():
            return
        
        if Path(file_path).exists():
            self._do_open_project(file_path)
        else:
            QMessageBox.critical(self, t("messages.error"), t("messages.file_not_found", path=file_path))
    
    @Slot()
    def _on_save_project(self) -> bool:
        if not self.project_manager.is_open:
            return False
        
        if self.project_manager.project_path is None:
            return self._on_save_project_as()
        
        try:
            log_activity("Saving project")
            self.project_manager.save_project()
            self._update_title()
            log_activity("Project saved successfully")
            self.statusBar().showMessage(t("messages.project_saved"), 3000)
            return True
        except Exception as e:
            log_activity("Project save failed", str(e))
            QMessageBox.critical(self, t("messages.error"), t("messages.error_saving", error=str(e)))
            return False
    
    @Slot()
    def _on_save_project_as(self) -> bool:
        log_activity("Save As dialog requested")
        if not self.project_manager.is_open:
            return False
        
        # Starting directory from settings
        start_dir = self.settings_manager.default_save_path or ""
        default_file = Path(start_dir) / f"project{PROJECT_EXTENSION}" if start_dir else f"project{PROJECT_EXTENSION}"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, t("dialogs.save_project.title"), str(default_file), get_project_filter()
        )
        
        if file_path:
            try:
                if not file_path.endswith(PROJECT_EXTENSION):
                    file_path += PROJECT_EXTENSION
                
                log_activity("Saving project as", file_path)
                # Pass the path to save_project which handles the file creation
                self.project_manager.save_project(Path(file_path))
                get_crash_handler().set_current_project(file_path)
                self._update_title()
                log_activity("Project saved successfully", file_path)
                self.statusBar().showMessage(t("messages.project_saved"), 3000)
                return True
            except Exception as e:
                log_activity("Save As failed", str(e))
                QMessageBox.critical(self, t("messages.error"), t("messages.error_saving", error=str(e)))
        return False
    
    @Slot()
    def _on_import_srt(self):
        log_activity("Import SRT dialog requested")
        if not self.project_manager.is_open:
            return
        
        # Starting directory from settings
        start_dir = self.settings_manager.default_save_path or ""
        
        file_path, _ = QFileDialog.getOpenFileName(self, t("menu.file.import_srt").replace("...", ""), start_dir, get_srt_filter())
        
        if file_path:
            try:
                log_activity("Importing SRT", file_path)
                count, errors = self.project_manager.import_srt(Path(file_path))
                self._refresh_cue_list()
                self._update_statistics()
                
                # Lock source text after import
                self.cue_editor.set_source_locked(True)
                
                log_activity("SRT imported", f"{count} cues")
                msg = t("messages.srt_imported", count=count)
                if errors:
                    msg += f"\n\n{t('messages.warnings')}:\n" + "\n".join(errors[:5])
                
                QMessageBox.information(self, t("menu.file.import"), msg)
                self._update_title()
            except Exception as e:
                log_activity("SRT import failed", str(e))
                QMessageBox.critical(self, t("messages.error"), t("messages.error_loading", error=str(e)))
    
    @Slot()
    def _on_import_video(self):
        log_activity("Import video dialog requested")
        if not self.project_manager.is_open:
            return
        
        # Starting directory from settings
        start_dir = self.settings_manager.default_save_path or ""
        
        file_path, _ = QFileDialog.getOpenFileName(self, t("menu.file.import_video").replace("...", ""), start_dir, get_video_filter())
        
        if file_path:
            try:
                log_activity("Loading video", file_path)
                self.video_player.load_video(Path(file_path))
                self.project_manager.update_project(video_path=file_path)
                self._update_title()
                log_activity("Video loaded successfully")
                self.statusBar().showMessage(t("messages.video_loaded", name=Path(file_path).name), 3000)
            except Exception as e:
                log_activity("Video load failed", str(e))
                QMessageBox.critical(self, t("messages.error"), t("messages.error_loading", error=str(e)))
    
    @Slot()
    def _on_export_pdf(self):
        log_activity("Export PDF dialog requested")
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
                log_activity("Exporting PDF", file_path)
                cues = self.project_manager.get_cues()
                exporter = PDFExporter()
                exporter.export(Path(file_path), project, cues)
                log_activity("PDF exported successfully")
                QMessageBox.information(self, t("menu.file.export"), t("messages.export_success", path=file_path))
            except Exception as e:
                log_activity("PDF export failed", str(e))
                QMessageBox.critical(self, t("messages.error"), t("messages.export_error", error=str(e)))
    
    @Slot()
    def _on_export_srt(self):
        log_activity("Export SRT dialog requested")
        if not self.project_manager.is_open:
            return
        
        # Starting directory from settings
        start_dir = self.settings_manager.default_save_path or ""
        default_file = Path(start_dir) / "translation.srt" if start_dir else "translation.srt"
        
        file_path, _ = QFileDialog.getSaveFileName(self, t("menu.file.export_srt").replace("...", ""), str(default_file), get_srt_filter())
        
        if file_path:
            try:
                log_activity("Exporting SRT", file_path)
                from dubsync.services.srt_parser import export_to_srt
                cues = self.project_manager.get_cues()
                content = export_to_srt(cues, use_translated=True)
                Path(file_path).write_text(content, encoding="utf-8")
                log_activity("SRT exported successfully")
                QMessageBox.information(self, t("menu.file.export"), t("messages.export_success", path=file_path))
            except Exception as e:
                log_activity("SRT export failed", str(e))
                QMessageBox.critical(self, t("messages.error"), t("messages.export_error", error=str(e)))
    
    def _on_plugin_export(self, plugin):
        """Execute plugin export."""
        if not self.project_manager.is_open or self.project_manager.project is None:
            return
        
        project = self.project_manager.project
        default_name = project.get_display_title()
        default_name = "".join(c for c in default_name if c.isalnum() or c in " -_")
        
        # Starting directory from settings
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
        """Application settings dialog."""
        from dubsync.ui.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(parent=self, plugin_manager=self.plugin_manager)
        dialog.theme_changed.connect(self._apply_theme)
        
        if dialog.exec():
            # Settings saved
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
        """Insert cue before the current one."""
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
        """Insert cue after the current one."""
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
    def _on_batch_timing(self):
        """Open batch timing adjustment dialog."""
        if not self.project_manager.is_open:
            return
        
        cues = self.project_manager.get_cues()
        if not cues:
            QMessageBox.information(
                self, 
                t("dialogs.batch_timing.title"), 
                t("messages.no_cues_to_adjust")
            )
            return
        
        # Get selected cues count (for now, we don't have multi-select)
        selected_count = 1 if self.cue_list.get_selected_cue_id() else 0
        
        dialog = BatchTimingDialog(
            cue_count=len(cues),
            selected_count=selected_count,
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_settings()
            offset_ms = settings["offset_ms"]
            scope = settings["scope"]
            ripple = settings["ripple"]
            
            if offset_ms == 0:
                return
            
            self._apply_batch_timing(offset_ms, scope, ripple)
    
    def _apply_batch_timing(self, offset_ms: int, scope: str, ripple: bool):
        """
        Apply batch timing adjustment to cues.
        
        Args:
            offset_ms: Time offset in milliseconds
            scope: "all", "selected", or "from_current"
            ripple: Whether to use ripple edit
        """
        cues = self.project_manager.get_cues()
        if not cues:
            return
        
        # Sort cues by time_in
        sorted_cues = sorted(cues, key=lambda c: c.time_in_ms)
        
        # Determine which cues to modify
        current_cue_id = self.cue_list.get_selected_cue_id()
        current_index = 0
        
        if current_cue_id:
            for i, cue in enumerate(sorted_cues):
                if cue.id == current_cue_id:
                    current_index = i
                    break
        
        cues_to_modify = []
        
        if scope == "all":
            cues_to_modify = sorted_cues
        elif scope == "selected" and current_cue_id:
            # For now, just the current cue
            cues_to_modify = [sorted_cues[current_index]]
        elif scope == "from_current":
            cues_to_modify = sorted_cues[current_index:]
        
        if not cues_to_modify:
            return
        
        # Apply offset
        modified_count = 0
        for cue in cues_to_modify:
            # Ensure times don't go negative
            new_time_in = max(0, cue.time_in_ms + offset_ms)
            new_time_out = max(new_time_in + 1, cue.time_out_ms + offset_ms)
            
            cue.time_in_ms = new_time_in
            cue.time_out_ms = new_time_out
            
            self.project_manager.save_cue(cue)
            modified_count += 1
        
        # Refresh UI
        self._refresh_cue_list()
        self._update_title()
        self._update_statistics()
        
        # Log and show status
        log_activity("Batch timing applied", f"{modified_count} cues, {offset_ms}ms offset")
        self.statusBar().showMessage(
            t("messages.batch_timing_applied", count=modified_count, offset=offset_ms),
            3000
        )
    
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
        """About - Opens the About tab in Settings."""
        from dubsync.ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, initial_tab="about")
        dialog.exec()
    
    @Slot()
    def _on_tutorial(self):
        """Open tutorial window."""
        from dubsync.ui.dialogs import TutorialDialog
        dialog = TutorialDialog(self)
        dialog.exec()
    
    @Slot()
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
            self.action_fullscreen.setChecked(False)
        else:
            self.showFullScreen()
            self.action_fullscreen.setChecked(True)
    
    @Slot()
    def _toggle_timeline(self):
        """Toggle timeline visibility."""
        visible = self.action_toggle_timeline.isChecked()
        self.timeline_container.setVisible(visible)
    
    @Slot(int)
    def _on_cue_selected(self, cue_id: int):
        if (cue := self.project_manager.get_cue(cue_id)) and self.project_manager.db is not None:
            self.cue_editor.set_cue(cue)
            self.comments_panel.set_cue(cue, self.project_manager.db)
            self.video_player.seek_to(cue.time_in_ms)
            
            # Update timeline selection
            self.timeline_widget.set_selected_cue(cue_id)
            
            # Set subtitle for fullscreen video
            subtitle_text = cue.translated_text or cue.source_text
            self.video_player.set_subtitle(subtitle_text)
            
            # Plugin notification
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
            # Update timeline playhead
            self.timeline_widget.set_playhead_position(position_ms)
    
    @Slot()
    def _on_comment_added(self):
        self._update_title()
    
    @Slot(int)
    def _on_timeline_playhead_moved(self, position_ms: int):
        """Handle timeline playhead movement."""
        self.video_player.seek_to(position_ms)
        self.timeline_widget.set_playhead_position(position_ms)
    
    @Slot(int, int, int)
    def _on_timeline_cue_moved(self, cue_id: int, new_time_in: int, new_time_out: int):
        """Handle cue moved in timeline via drag & drop."""
        if not self.project_manager.is_open or not self.project_manager.db:
            return
        
        cue = self.project_manager.get_cue(cue_id)
        if cue:
            cue.time_in_ms = new_time_in
            cue.time_out_ms = new_time_out
            cue.save(self.project_manager.db)
            self._refresh_cue_list()
            self._update_statistics()
            self._update_title()
    
    @Slot(int, int, int)
    def _on_timeline_cue_resized(self, cue_id: int, new_time_in: int, new_time_out: int):
        """Handle cue resized in timeline via edge dragging."""
        if not self.project_manager.is_open or not self.project_manager.db:
            return
        
        cue = self.project_manager.get_cue(cue_id)
        if cue:
            cue.time_in_ms = new_time_in
            cue.time_out_ms = new_time_out
            # Recalculate lip-sync ratio using LipSyncEstimator
            from dubsync.services.lip_sync import LipSyncEstimator
            estimator = LipSyncEstimator()
            estimator.update_cue_ratio(cue)
            cue.save(self.project_manager.db)
            self._refresh_cue_list()
            self._update_statistics()
            self._update_title()
            # Update editor if this cue is selected
            selected_cue_id = self.cue_list.get_selected_cue_id()
            if selected_cue_id and selected_cue_id == cue_id:
                self.cue_editor.set_cue(cue)
    
    @Slot(int)
    def _on_video_position_for_timeline(self, position_ms: int):
        """Update timeline playhead when video position changes."""
        self.timeline_widget.set_playhead_position(position_ms)
    
    def _goto_next_cue(self):
        """Navigate to the next cue."""
        if not self.project_manager.is_open:
            return
        
        current_index = self.cue_list.get_current_index()
        self._goto_next_cue_from_index(current_index)
    
    def _goto_next_cue_from_index(self, current_index: int):
        """
        Navigate to the next cue based on the given index.
        
        Args:
            current_index: Current cue index
        """
        if not self.project_manager.is_open:
            return
        
        cues = self.project_manager.get_cues()
        
        # Search for the next cue
        for cue in cues:
            if cue.cue_index > current_index:
                self.cue_list.select_cue(cue.id)
                return
        
        # If there are no more, stay on the last one
        self.statusBar().showMessage(t("messages.last_cue"), 2000)
    
    @Slot()
    def _on_goto_next_cue(self):
        """Navigate to the next cue (Ctrl+Down)."""
        self._goto_next_cue()
    
    @Slot()
    def _on_goto_prev_cue(self):
        """Navigate to the previous cue (Ctrl+Up)."""
        if not self.project_manager.is_open:
            return
        
        current_index = self.cue_list.get_current_index()
        cues = self.project_manager.get_cues()
        
        # Search for the previous cue (backwards)
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
