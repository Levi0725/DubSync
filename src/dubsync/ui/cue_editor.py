"""
DubSync Cue Editor Widget

Cue editor panel for translation and editing.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QLabel,
    QFrame, QSizePolicy, QDialog, QDialogButtonBox, QSpinBox,
    QSplitter, QToolButton
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QColor, QPalette

from dubsync.models.cue import Cue
from dubsync.utils.constants import (
    CueStatus,
    COLOR_LIPSYNC_GOOD, COLOR_LIPSYNC_WARNING, COLOR_LIPSYNC_TOO_LONG
)
from dubsync.utils.time_utils import ms_to_timecode, format_duration
from dubsync.services.lip_sync import LipSyncEstimator, LipSyncResult
from dubsync.i18n import t
from dubsync.resources.icon_manager import get_icon_manager


class TimingEditorDialog(QDialog):
    """Timing editor dialog."""
    
    def __init__(self, cue: Cue, parent=None):
        super().__init__(parent)
        self.cue = cue
        self.setWindowTitle(t("dialogs.timing_editor.title"))
        self.setMinimumWidth(350)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Time in
        time_in_layout = QHBoxLayout()
        self.hours_in = QSpinBox()
        self.hours_in.setRange(0, 99)
        self.hours_in.setValue(cue.time_in_ms // 3600000)
        time_in_layout.addWidget(self.hours_in)
        time_in_layout.addWidget(QLabel(":"))
        
        self.mins_in = QSpinBox()
        self.mins_in.setRange(0, 59)
        self.mins_in.setValue((cue.time_in_ms % 3600000) // 60000)
        time_in_layout.addWidget(self.mins_in)
        time_in_layout.addWidget(QLabel(":"))
        
        self.secs_in = QSpinBox()
        self.secs_in.setRange(0, 59)
        self.secs_in.setValue((cue.time_in_ms % 60000) // 1000)
        time_in_layout.addWidget(self.secs_in)
        time_in_layout.addWidget(QLabel(","))
        
        self.ms_in = QSpinBox()
        self.ms_in.setRange(0, 999)
        self.ms_in.setValue(cue.time_in_ms % 1000)
        time_in_layout.addWidget(self.ms_in)
        
        form_layout.addRow(t("dialogs.timing_editor.start"), time_in_layout)
        
        # Time out
        time_out_layout = QHBoxLayout()
        self.hours_out = QSpinBox()
        self.hours_out.setRange(0, 99)
        self.hours_out.setValue(cue.time_out_ms // 3600000)
        time_out_layout.addWidget(self.hours_out)
        time_out_layout.addWidget(QLabel(":"))
        
        self.mins_out = QSpinBox()
        self.mins_out.setRange(0, 59)
        self.mins_out.setValue((cue.time_out_ms % 3600000) // 60000)
        time_out_layout.addWidget(self.mins_out)
        time_out_layout.addWidget(QLabel(":"))
        
        self.secs_out = QSpinBox()
        self.secs_out.setRange(0, 59)
        self.secs_out.setValue((cue.time_out_ms % 60000) // 1000)
        time_out_layout.addWidget(self.secs_out)
        time_out_layout.addWidget(QLabel(","))
        
        self.ms_out = QSpinBox()
        self.ms_out.setRange(0, 999)
        self.ms_out.setValue(cue.time_out_ms % 1000)
        time_out_layout.addWidget(self.ms_out)
        
        form_layout.addRow(t("dialogs.timing_editor.end"), time_out_layout)
        
        layout.addLayout(form_layout)
        
        # Duration preview
        self.duration_label = QLabel()
        self._update_duration()
        layout.addWidget(self.duration_label)
        
        # Connect spinbox changes
        for spin in [self.hours_in, self.mins_in, self.secs_in, self.ms_in,
                     self.hours_out, self.mins_out, self.secs_out, self.ms_out]:
            spin.valueChanged.connect(self._update_duration)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _update_duration(self):
        time_in = self.get_time_in_ms()
        time_out = self.get_time_out_ms()
        duration = time_out - time_in
        
        if duration < 0:
            self.duration_label.setStyleSheet("color: red;")
            self.duration_label.setText(t("dialogs.timing_editor.error_end_before_start"))
        else:
            self.duration_label.setStyleSheet("")
            self.duration_label.setText(t("dialogs.timing_editor.duration", duration=format_duration(duration)))
    
    def get_time_in_ms(self) -> int:
        return (self.hours_in.value() * 3600000 +
                self.mins_in.value() * 60000 +
                self.secs_in.value() * 1000 +
                self.ms_in.value())
    
    def get_time_out_ms(self) -> int:
        return (self.hours_out.value() * 3600000 +
                self.mins_out.value() * 60000 +
                self.secs_out.value() * 1000 +
                self.ms_out.value())


class CueEditorWidget(QWidget):
    """
    Cue editor widget.
    
    Allows editing of translation, character, comments,
    and displays lip-sync estimation.
    """
    
    # Signals
    cue_saved = Signal()
    status_changed = Signal()
    timing_changed = Signal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._cue: Optional[Cue] = None
        self._lip_sync_estimator = LipSyncEstimator()
        self._is_dirty = False
        
        self._setup_ui()
        self._connect_signals()
        self._update_ui_state()
    
    def _setup_ui(self):
        """Setup UI - compact modern design."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        icon_mgr = get_icon_manager()
        
        # ═══════════════════════════════════════════════════════════════
        # COMPACT HEADER BAR
        # ═══════════════════════════════════════════════════════════════
        header_widget = QWidget()
        header_widget.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(8)
        
        # Index badge
        self.index_label = QLabel("#-")
        self.index_label.setStyleSheet(
            "font-weight: bold; font-size: 12px; "
            "background: #2196F3; color: white; padding: 2px 6px; border-radius: 3px;"
        )
        self.index_label.setFixedWidth(40)
        self.index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.index_label)
        
        # Time info (compact)
        self.time_label = QLabel("00:00:00 → 00:00:00")
        self.time_label.setStyleSheet("color: #888; font-size: 11px; font-family: monospace;")
        header_layout.addWidget(self.time_label)
        
        self.duration_label = QLabel("(0.0s)")
        self.duration_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(self.duration_label)
        
        header_layout.addStretch()
        
        # Status combo (compact)
        self.status_combo = QComboBox()
        self.status_combo.setFixedWidth(120)
        self.status_combo.setStyleSheet("font-size: 11px;")
        self.status_combo.addItem(t("status.new"), CueStatus.NEW.value)
        self.status_combo.addItem(t("status.translated"), CueStatus.TRANSLATED.value)
        self.status_combo.addItem(t("status.needs_revision"), CueStatus.NEEDS_REVISION.value)
        self.status_combo.addItem(t("status.approved"), CueStatus.APPROVED.value)
        header_layout.addWidget(self.status_combo)
        
        # Quick action buttons (toolbar style)
        self.approve_btn = QToolButton()
        self.approve_btn.setIcon(icon_mgr.get_icon("success"))
        self.approve_btn.setIconSize(QSize(14, 14))
        self.approve_btn.setToolTip(t("cue_editor.approve"))
        self.approve_btn.setStyleSheet(
            "QToolButton { background: #4CAF50; border-radius: 3px; padding: 3px; }"
            "QToolButton:hover { background: #45a049; }"
        )
        header_layout.addWidget(self.approve_btn)
        
        self.revision_btn = QToolButton()
        self.revision_btn.setIcon(icon_mgr.get_icon("warning"))
        self.revision_btn.setIconSize(QSize(14, 14))
        self.revision_btn.setToolTip(t("cue_editor.revision"))
        self.revision_btn.setStyleSheet(
            "QToolButton { background: #FF9800; border-radius: 3px; padding: 3px; }"
            "QToolButton:hover { background: #F57C00; }"
        )
        header_layout.addWidget(self.revision_btn)
        
        # Collapse button
        self.collapse_btn = QToolButton()
        self.collapse_btn.setIcon(icon_mgr.get_icon("collapse"))
        self.collapse_btn.setIconSize(QSize(14, 14))
        self.collapse_btn.setToolTip(t("cue_editor.collapse_tooltip"))
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.setStyleSheet(
            "QToolButton { border: none; padding: 3px; }"
            "QToolButton:hover { background: rgba(128,128,128,0.2); border-radius: 3px; }"
        )
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.collapse_btn)
        
        layout.addWidget(header_widget)
        
        # ═══════════════════════════════════════════════════════════════
        # COLLAPSIBLE CONTENT
        # ═══════════════════════════════════════════════════════════════
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        
        # Main splitter: left (texts) | right (info)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(3)
        
        # ─────────────────────────────────────────────────────────────
        # LEFT PANEL: Character + Source + Translation
        # ─────────────────────────────────────────────────────────────
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(4)
        
        # Character row
        char_row = QHBoxLayout()
        char_row.setSpacing(4)
        char_label = QLabel(t("cue_editor.character"))
        char_label.setStyleSheet("font-size: 11px; color: #888;")
        char_label.setFixedWidth(60)
        char_row.addWidget(char_label)
        self.character_edit = QLineEdit()
        self.character_edit.setPlaceholderText(t("cue_editor.character_placeholder"))
        self.character_edit.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        self.character_edit.setFixedHeight(24)
        char_row.addWidget(self.character_edit)
        
        # Source lock button
        self.source_lock_btn = QToolButton()
        self.source_lock_btn.setIcon(icon_mgr.get_icon("lock"))
        self.source_lock_btn.setIconSize(QSize(12, 12))
        self.source_lock_btn.setToolTip(t("cue_editor.source_lock_tooltip"))
        self.source_lock_btn.setCheckable(True)
        self.source_lock_btn.setChecked(True)
        self.source_lock_btn.setStyleSheet(
            "QToolButton { border: none; padding: 2px; }"
            "QToolButton:checked { background: rgba(244,67,54,0.2); border-radius: 3px; }"
        )
        self.source_lock_btn.clicked.connect(self._on_source_lock_toggled)
        char_row.addWidget(self.source_lock_btn)
        left_layout.addLayout(char_row)
        
        # Source text (compact)
        source_label = QLabel(t("cue_editor.source_text"))
        source_label.setStyleSheet("font-size: 10px; color: #888; margin-top: 2px;")
        left_layout.addWidget(source_label)
        
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setMaximumHeight(50)
        self.source_text.setStyleSheet(
            "QTextEdit { font-size: 11px; background: rgba(0,0,0,0.05); "
            "border: 1px solid #ddd; border-radius: 3px; padding: 2px; }"
        )
        self._source_locked = True
        left_layout.addWidget(self.source_text)
        
        # Translation text
        trans_label = QLabel(t("cue_editor.translation"))
        trans_label.setStyleSheet("font-size: 10px; color: #888; margin-top: 2px;")
        left_layout.addWidget(trans_label)
        
        self.translated_text = QTextEdit()
        self.translated_text.setPlaceholderText(t("cue_editor.translation_placeholder"))
        self.translated_text.setStyleSheet(
            "QTextEdit { font-size: 12px; border: 1px solid #4CAF50; "
            "border-radius: 3px; padding: 4px; }"
        )
        left_layout.addWidget(self.translated_text, 1)
        
        main_splitter.addWidget(left_panel)
        
        # ─────────────────────────────────────────────────────────────
        # RIGHT PANEL: Lip-sync + Notes + SFX
        # ─────────────────────────────────────────────────────────────
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(4)
        
        # Lip-sync compact widget
        lipsync_frame = QFrame()
        lipsync_frame.setStyleSheet(
            "QFrame { background: rgba(0,0,0,0.03); border-radius: 4px; }"
        )
        lipsync_layout = QVBoxLayout(lipsync_frame)
        lipsync_layout.setContentsMargins(6, 4, 6, 4)
        lipsync_layout.setSpacing(2)
        
        # Lip-sync header row
        lipsync_header = QHBoxLayout()
        lipsync_title = QLabel(t("cue_editor.lipsync_group"))
        lipsync_title.setStyleSheet("font-size: 10px; font-weight: bold; color: #666;")
        lipsync_header.addWidget(lipsync_title)
        lipsync_header.addStretch()
        
        self.lipsync_info_btn = QToolButton()
        self.lipsync_info_btn.setIcon(icon_mgr.get_icon("info"))
        self.lipsync_info_btn.setIconSize(QSize(10, 10))
        self.lipsync_info_btn.setToolTip(t("cue_editor.lipsync_disclaimer"))
        self.lipsync_info_btn.setCursor(Qt.CursorShape.WhatsThisCursor)
        self.lipsync_info_btn.setStyleSheet(
            "QToolButton { border: none; padding: 1px; }"
        )
        lipsync_header.addWidget(self.lipsync_info_btn)
        lipsync_layout.addLayout(lipsync_header)
        
        # Status indicator bar
        self.lipsync_indicator = QFrame()
        self.lipsync_indicator.setMinimumHeight(24)
        self.lipsync_indicator.setMaximumHeight(24)
        self.lipsync_indicator.setStyleSheet(
            "background-color: #CCCCCC; border-radius: 3px;"
        )
        
        indicator_layout = QHBoxLayout(self.lipsync_indicator)
        indicator_layout.setContentsMargins(6, 0, 6, 0)
        self.lipsync_label = QLabel(t("cue_editor.no_data"))
        self.lipsync_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lipsync_label.setStyleSheet(
            "background: transparent; color: white; font-weight: bold; font-size: 11px;"
        )
        indicator_layout.addWidget(self.lipsync_label)
        lipsync_layout.addWidget(self.lipsync_indicator)
        
        # Progress bar
        self.lipsync_progress_frame = QFrame()
        self.lipsync_progress_frame.setMinimumHeight(6)
        self.lipsync_progress_frame.setMaximumHeight(6)
        self.lipsync_progress_frame.setStyleSheet(
            "background-color: #333; border-radius: 3px;"
        )
        lipsync_layout.addWidget(self.lipsync_progress_frame)
        
        self.lipsync_fill = QFrame(self.lipsync_progress_frame)
        self.lipsync_fill.setGeometry(0, 0, 0, 6)
        self.lipsync_fill.setStyleSheet(
            "background-color: #4CAF50; border-radius: 3px;"
        )
        
        # Details row
        details_layout = QHBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        self.lipsync_chars_label = QLabel("")
        self.lipsync_chars_label.setStyleSheet("color: #888; font-size: 10px;")
        details_layout.addWidget(self.lipsync_chars_label)
        details_layout.addStretch()
        self.lipsync_time_label = QLabel("")
        self.lipsync_time_label.setStyleSheet("color: #888; font-size: 10px;")
        details_layout.addWidget(self.lipsync_time_label)
        lipsync_layout.addLayout(details_layout)
        
        right_layout.addWidget(lipsync_frame)
        
        # Notes (fills available space)
        notes_label = QLabel(t("cue_editor.notes"))
        notes_label.setStyleSheet("font-size: 10px; color: #888;")
        right_layout.addWidget(notes_label)
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(t("cue_editor.notes_placeholder"))
        self.notes_edit.setMinimumHeight(30)
        self.notes_edit.setStyleSheet(
            "QTextEdit { font-size: 11px; border: 1px solid #ddd; border-radius: 3px; }"
        )
        right_layout.addWidget(self.notes_edit, 1)  # stretch factor 1
        
        # SFX (fills available space)
        sfx_label = QLabel(t("cue_editor.sfx"))
        sfx_label.setStyleSheet("font-size: 10px; color: #888;")
        right_layout.addWidget(sfx_label)
        
        self.sfx_edit = QTextEdit()
        self.sfx_edit.setPlaceholderText(t("cue_editor.sfx_placeholder"))
        self.sfx_edit.setMinimumHeight(30)
        self.sfx_edit.setStyleSheet(
            "QTextEdit { font-size: 11px; border: 1px solid #ddd; border-radius: 3px; }"
        )
        right_layout.addWidget(self.sfx_edit, 1)  # stretch factor 1
        
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 200])
        
        content_layout.addWidget(main_splitter, 1)
        
        # ─────────────────────────────────────────────────────────────
        # BOTTOM ACTION BAR
        # ─────────────────────────────────────────────────────────────
        action_bar = QWidget()
        action_bar.setStyleSheet("background: transparent;")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(4, 2, 4, 2)
        action_layout.setSpacing(4)
        
        self.save_btn = QPushButton(t("cue_editor.save"))
        self.save_btn.setIcon(icon_mgr.get_icon("file_save"))
        self.save_btn.setIconSize(QSize(14, 14))
        self.save_btn.setShortcut("Ctrl+Return")
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 4px 12px; border: none; border-radius: 3px; font-size: 11px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        action_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton(t("cue_editor.reset"))
        self.reset_btn.setIcon(icon_mgr.get_icon("refresh"))
        self.reset_btn.setIconSize(QSize(14, 14))
        self.reset_btn.setStyleSheet(
            "QPushButton { padding: 4px 12px; font-size: 11px; }"
        )
        action_layout.addWidget(self.reset_btn)
        
        action_layout.addStretch()
        
        content_layout.addWidget(action_bar)
        
        layout.addWidget(self.content_widget, 1)
        
        # Collapsed state
        self._collapsed = False
        
        # Install event filter for progress bar resize
        self.lipsync_progress_frame.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Event filter to handle progress bar resize."""
        from PySide6.QtCore import QEvent
        if obj == self.lipsync_progress_frame and event.type() == QEvent.Type.Resize:
            # Update fill bar on resize
            self._update_lipsync_progress_bar()
        return super().eventFilter(obj, event)
    
    def _update_lipsync_progress_bar(self):
        """Update progress bar fill width based on current text."""
        if self._cue is None:
            return
            
        translated = self.translated_text.toPlainText()
        source = self.source_text.toPlainText()
        text = translated if translated else source
        
        # Calculate chars
        result = self._lip_sync_estimator.estimate(text, self._cue.duration_ms, source if translated else "")
        max_chars = self._lip_sync_estimator.calculate_max_chars(self._cue.duration_ms)
        current_chars = result.text_length
        
        # Calculate fill width
        progress_width = self.lipsync_progress_frame.width()
        if max_chars > 0:
            fill_ratio = min(current_chars / max_chars, 1.5)
            fill_width = int(progress_width * min(fill_ratio, 1.0))
        else:
            fill_width = 0
        
        # Get current color
        from dubsync.utils.constants import LIPSYNC_THRESHOLD_GOOD, LIPSYNC_THRESHOLD_WARNING
        if result.ratio <= LIPSYNC_THRESHOLD_GOOD:
            color = COLOR_LIPSYNC_GOOD
        elif result.ratio <= LIPSYNC_THRESHOLD_WARNING:
            color = COLOR_LIPSYNC_WARNING
        else:
            color = COLOR_LIPSYNC_TOO_LONG
        
        self.lipsync_fill.setGeometry(0, 0, fill_width, 8)
        self.lipsync_fill.setStyleSheet(f"background-color: {color}; border-radius: 4px;")

    def _connect_signals(self):
        """Connect signals."""
        self.translated_text.textChanged.connect(self._on_text_changed)
        self.character_edit.textChanged.connect(self._mark_dirty)
        self.notes_edit.textChanged.connect(self._mark_dirty)
        self.sfx_edit.textChanged.connect(self._mark_dirty)
        self.source_text.textChanged.connect(self._mark_dirty)
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        
        self.save_btn.clicked.connect(self._on_save)
        self.reset_btn.clicked.connect(self._on_reset)
        self.approve_btn.clicked.connect(self._on_approve)
        self.revision_btn.clicked.connect(self._on_revision)
    
    @Slot()
    def _toggle_collapse(self):
        """Toggle editor content collapse/expand."""
        icon_mgr = get_icon_manager()
        self._collapsed = self.collapse_btn.isChecked()
        self.content_widget.setVisible(not self._collapsed)
        if self._collapsed:
            self.collapse_btn.setIcon(icon_mgr.get_icon("expand"))
        else:
            self.collapse_btn.setIcon(icon_mgr.get_icon("collapse"))
        
        # Set fixed height when collapsed to make widget smaller
        if self._collapsed:
            self.setFixedHeight(36)  # Compact header height
        else:
            self.setMinimumHeight(120)
            self.setMaximumHeight(16777215)  # Reset to default max
    
    @Slot()
    def _on_source_lock_toggled(self):
        """Toggle source lock."""
        icon_mgr = get_icon_manager()
        self._source_locked = self.source_lock_btn.isChecked()
        self.source_text.setReadOnly(self._source_locked)
        self._update_source_text_style()
        if self._source_locked:
            self.source_lock_btn.setIcon(icon_mgr.get_icon("lock"))
        else:
            self.source_lock_btn.setIcon(icon_mgr.get_icon("unlock"))
    
    def _update_source_text_style(self):
        """Update source text style based on lock state."""
        from dubsync.ui.theme import ThemeManager
        theme = ThemeManager()
        colors = theme.colors
        
        if self._source_locked:
            self.source_lock_btn.setText("[L]")
            # Locked: slightly muted appearance
            self.source_text.setStyleSheet(
                f"background-color: {colors.surface}; color: {colors.foreground_muted};"
            )
        else:
            self.source_lock_btn.setText("[U]")
            # Unlocked: normal editable appearance
            self.source_text.setStyleSheet(
                f"background-color: {colors.input_background}; color: {colors.foreground};"
            )
    
    def set_source_locked(self, locked: bool):
        """
        Set source lock state.
        
        Args:
            locked: True to lock
        """
        self._source_locked = locked
        self.source_lock_btn.setChecked(locked)
        self.source_text.setReadOnly(locked)
        self._update_source_text_style()
    
    def apply_theme(self):
        """Apply theme - call on theme change."""
        self._update_source_text_style()
    
    def _update_ui_state(self):
        """Update UI state."""
        has_cue = self._cue is not None
        
        self.character_edit.setEnabled(has_cue)
        self.translated_text.setEnabled(has_cue)
        self.notes_edit.setEnabled(has_cue)
        self.sfx_edit.setEnabled(has_cue)
        self.status_combo.setEnabled(has_cue)
        self.save_btn.setEnabled(has_cue and self._is_dirty)
        self.reset_btn.setEnabled(has_cue and self._is_dirty)
        self.approve_btn.setEnabled(has_cue)
        self.revision_btn.setEnabled(has_cue)
    
    def set_cue(self, cue: Cue):
        """
        Set cue for editing.
        
        Args:
            cue: Cue object
        """
        self._cue = cue
        self._is_dirty = False
        
        # Update header
        self.index_label.setText(f"#{cue.cue_index}")
        self.time_label.setText(
            f"{cue.time_in_timecode[:8]} → {cue.time_out_timecode[:8]}"
        )
        self.duration_label.setText(f"({format_duration(cue.duration_ms)})")
        
        # Update fields
        self.character_edit.setText(cue.character_name)
        self.source_text.setPlainText(cue.source_text)
        self.translated_text.setPlainText(cue.translated_text)
        self.notes_edit.setPlainText(cue.notes)
        self.sfx_edit.setPlainText(cue.sfx_notes)
        
        # Update status
        index = self.status_combo.findData(cue.status.value)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        # Update lip-sync
        self._update_lipsync()
        
        self._update_ui_state()
    
    def get_cue(self) -> Optional[Cue]:
        """
        Get edited cue.
        
        Returns:
            Cue object with current values
        """
        if self._cue is None:
            return None
        
        self._cue.character_name = self.character_edit.text()
        self._cue.source_text = self.source_text.toPlainText()  # Allow editing if unlocked
        self._cue.translated_text = self.translated_text.toPlainText()
        self._cue.notes = self.notes_edit.toPlainText()
        self._cue.sfx_notes = self.sfx_edit.toPlainText()
        
        status_value = self.status_combo.currentData()
        self._cue.status = CueStatus(status_value)
        
        # Update lip-sync ratio
        if self._cue.translated_text:
            self._lip_sync_estimator.update_cue_ratio(self._cue)
        
        return self._cue
    
    def _update_lipsync(self):
        """Update lip-sync indicator with visual progress bar."""
        if self._cue is None:
            return
        
        # Get translated text, or source if no translation
        translated = self.translated_text.toPlainText()
        source = self.source_text.toPlainText()
        
        # Use same logic as estimate_cue: if translated exists, compare to source
        if translated:
            text = translated
            source_for_calc = source
        else:
            text = source
            source_for_calc = ""  # No adjustment if using source as text
        
        result = self._lip_sync_estimator.estimate(text, self._cue.duration_ms, source_for_calc)
        
        # Update cue's lip_sync_ratio for synchronization with cue_list
        self._cue.lip_sync_ratio = result.ratio
        
        # Update indicator color and text using same thresholds as cue_list
        from dubsync.utils.constants import LIPSYNC_THRESHOLD_GOOD, LIPSYNC_THRESHOLD_WARNING
        
        if result.ratio <= LIPSYNC_THRESHOLD_GOOD:
            color = COLOR_LIPSYNC_GOOD
            status_text = t("cue_editor.lipsync.good", ratio=int(result.ratio * 100))
        elif result.ratio <= LIPSYNC_THRESHOLD_WARNING:
            color = COLOR_LIPSYNC_WARNING
            status_text = t("cue_editor.lipsync.close", ratio=int(result.ratio * 100))
        else:
            color = COLOR_LIPSYNC_TOO_LONG
            status_text = t("cue_editor.lipsync.too_long", ratio=int(result.ratio * 100))
        
        self.lipsync_indicator.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )
        self.lipsync_label.setStyleSheet(
            "background: transparent; color: white; font-weight: bold;"
        )
        
        self.lipsync_label.setText(status_text)
        
        # Update progress bar
        max_chars = self._lip_sync_estimator.calculate_max_chars(self._cue.duration_ms)
        current_chars = result.text_length
        
        # Calculate fill width as percentage of max chars
        progress_width = self.lipsync_progress_frame.width()
        if max_chars > 0:
            fill_ratio = min(current_chars / max_chars, 1.5)  # Cap at 150%
            fill_width = int(progress_width * min(fill_ratio, 1.0))
        else:
            fill_width = 0
            fill_ratio = 0
        
        # Set fill bar width and color
        self.lipsync_fill.setGeometry(0, 0, fill_width, 8)
        self.lipsync_fill.setStyleSheet(
            f"background-color: {color}; border-radius: 4px;"
        )
        
        # Update detail labels
        self.lipsync_chars_label.setText(f"{current_chars} / ~{max_chars} kar")
        self.lipsync_time_label.setText(
            f"{result.estimated_time_ms/1000:.1f}s / {self._cue.duration_ms/1000:.1f}s"
        )
    
    @Slot()
    def _mark_dirty(self):
        """Mark as dirty."""
        self._is_dirty = True
        self._update_ui_state()
    
    @Slot()
    def _on_text_changed(self):
        """Text changed."""
        self._mark_dirty()
        self._update_lipsync()
    
    @Slot()
    def _on_status_changed(self):
        """Status changed."""
        self._mark_dirty()
    
    @Slot()
    def _on_save(self):
        """Save."""
        if self._cue is None:
            return
        
        # Auto-update status if translated
        if self.translated_text.toPlainText() and self._cue.status == CueStatus.NEW:
            index = self.status_combo.findData(CueStatus.TRANSLATED.value)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
        
        self._is_dirty = False
        self._update_ui_state()
        self.cue_saved.emit()
    
    @Slot()
    def _on_reset(self):
        """Reset."""
        if self._cue:
            self.set_cue(self._cue)
    
    @Slot()
    def _on_approve(self):
        """Quick approve."""
        if self._cue is None:
            return
        
        index = self.status_combo.findData(CueStatus.APPROVED.value)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        self._on_save()
    
    @Slot()
    def _on_revision(self):
        """Quick mark as needs revision."""
        if self._cue is None:
            return
        
        index = self.status_combo.findData(CueStatus.NEEDS_REVISION.value)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        self._on_save()
    
    def clear(self):
        """Clear editor."""
        self._cue = None
        self._is_dirty = False
        
        self.index_label.setText(t("cue_editor.index"))
        self.time_label.setText("00:00:00 → 00:00:00")
        self.duration_label.setText("(0.0s)")
        self.character_edit.clear()
        self.source_text.clear()
        self.translated_text.clear()
        self.notes_edit.clear()
        self.sfx_edit.clear()
        self.status_combo.setCurrentIndex(0)
        
        self.lipsync_indicator.setStyleSheet(
            "background-color: #CCCCCC; border-radius: 4px;"
        )
        self.lipsync_label.setText(t("cue_editor.no_data"))
        self.lipsync_chars_label.setText("")
        self.lipsync_time_label.setText("")
        self.lipsync_fill.setGeometry(0, 0, 0, 8)
        
        self._update_ui_state()
    
    def show_timing_editor(self, cue: Cue):
        """
        Show timing editor dialog.
        
        Args:
            cue: Cue to edit
        """
        dialog = TimingEditorDialog(cue, self)
        if dialog.exec():
            time_in = dialog.get_time_in_ms()
            time_out = dialog.get_time_out_ms()
            
            if time_out > time_in:
                cue.time_in_ms = time_in
                cue.time_out_ms = time_out
                
                # Update the current cue reference if it's the same
                if self._cue and self._cue.id == cue.id:
                    self._cue.time_in_ms = time_in
                    self._cue.time_out_ms = time_out
                    self.time_label.setText(
                        f"{cue.time_in_timecode[:8]} → {cue.time_out_timecode[:8]}"
                    )
                    self.duration_label.setText(f"({format_duration(cue.duration_ms)})")
                    self._update_lipsync()
                
                # Emit signal with the modified cue
                self.timing_changed.emit()
