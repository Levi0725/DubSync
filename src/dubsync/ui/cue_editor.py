"""
DubSync Cue Editor Widget

Cue editor panel for translation and editing.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QLabel,
    QFrame, QSizePolicy, QDialog, QDialogButtonBox, QSpinBox
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QPalette

from dubsync.models.cue import Cue
from dubsync.utils.constants import (
    CueStatus,
    COLOR_LIPSYNC_GOOD, COLOR_LIPSYNC_WARNING, COLOR_LIPSYNC_TOO_LONG
)
from dubsync.utils.time_utils import ms_to_timecode, format_duration
from dubsync.services.lip_sync import LipSyncEstimator, LipSyncResult
from dubsync.i18n import t


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
        """Setup UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header with time info - always visible
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.index_label = QLabel(t("cue_editor.index"))
        self.index_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(self.index_label)
        
        self.time_label = QLabel("00:00:00 → 00:00:00")
        self.time_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.time_label)
        
        self.duration_label = QLabel("(0.0s)")
        self.duration_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.duration_label)
        
        header_layout.addStretch()
        
        # Status selector
        self.status_combo = QComboBox()
        self.status_combo.addItem(t("status.new"), CueStatus.NEW.value)
        self.status_combo.addItem(t("status.translated"), CueStatus.TRANSLATED.value)
        self.status_combo.addItem(t("status.needs_revision"), CueStatus.NEEDS_REVISION.value)
        self.status_combo.addItem(t("status.approved"), CueStatus.APPROVED.value)
        header_layout.addWidget(QLabel(t("cue_editor.status_label")))
        header_layout.addWidget(self.status_combo)
        
        # Collapse button
        self.collapse_btn = QPushButton()
        self.collapse_btn.setText("[-]")
        self.collapse_btn.setToolTip(t("cue_editor.collapse_tooltip"))
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setCheckable(True)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        header_layout.addWidget(self.collapse_btn)
        
        layout.addWidget(header_widget)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Collapsible content container
        self.content_widget = QWidget()
        content_main_layout = QVBoxLayout(self.content_widget)
        content_main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - Source and translation
        left_layout = QVBoxLayout()
        
        # Character name
        char_layout = QHBoxLayout()
        char_layout.addWidget(QLabel(t("cue_editor.character")))
        self.character_edit = QLineEdit()
        self.character_edit.setPlaceholderText(t("cue_editor.character_placeholder"))
        char_layout.addWidget(self.character_edit)
        
        # Source lock button
        self.source_lock_btn = QPushButton()
        self.source_lock_btn.setText("[L]")
        self.source_lock_btn.setToolTip(t("cue_editor.source_lock_tooltip"))
        self.source_lock_btn.setFixedSize(28, 28)
        self.source_lock_btn.setCheckable(True)
        self.source_lock_btn.setChecked(True)  # Default: locked
        self.source_lock_btn.clicked.connect(self._on_source_lock_toggled)
        char_layout.addWidget(self.source_lock_btn)
        
        left_layout.addLayout(char_layout)
        
        # Source text (lockable)
        left_layout.addWidget(QLabel(t("cue_editor.source_text")))
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setMaximumHeight(80)
        self._source_locked = True
        self._update_source_text_style()
        left_layout.addWidget(self.source_text)
        
        # Translated text
        left_layout.addWidget(QLabel(t("cue_editor.translation")))
        self.translated_text = QTextEdit()
        self.translated_text.setPlaceholderText(t("cue_editor.translation_placeholder"))
        self.translated_text.setMinimumHeight(100)
        left_layout.addWidget(self.translated_text)
        
        content_layout.addLayout(left_layout, 2)
        
        # Right side - Notes and lip-sync
        right_layout = QVBoxLayout()
        
        # Lip-sync indicator
        lipsync_group = QGroupBox(t("cue_editor.lipsync_group"))
        lipsync_layout = QVBoxLayout(lipsync_group)
        lipsync_layout.setSpacing(4)
        
        self.lipsync_indicator = QFrame()
        self.lipsync_indicator.setMinimumHeight(40)
        self.lipsync_indicator.setMaximumHeight(40)
        self.lipsync_indicator.setStyleSheet(
            "background-color: #CCCCCC; border-radius: 4px;"
        )
        
        # Label inside the indicator
        indicator_layout = QVBoxLayout(self.lipsync_indicator)
        indicator_layout.setContentsMargins(4, 0, 4, 0)
        self.lipsync_label = QLabel(t("cue_editor.no_data"))
        self.lipsync_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lipsync_label.setStyleSheet("background: transparent; color: white; font-weight: bold;")
        indicator_layout.addWidget(self.lipsync_label)
        
        lipsync_layout.addWidget(self.lipsync_indicator)
        
        self.lipsync_details = QLabel("")
        self.lipsync_details.setStyleSheet("color: #666; font-size: 11px;")
        self.lipsync_details.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lipsync_details.setWordWrap(True)
        self.lipsync_details.setMinimumHeight(36)
        lipsync_layout.addWidget(self.lipsync_details)
        
        right_layout.addWidget(lipsync_group)
        
        # Notes
        right_layout.addWidget(QLabel(t("cue_editor.notes")))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(t("cue_editor.notes_placeholder"))
        self.notes_edit.setMaximumHeight(60)
        right_layout.addWidget(self.notes_edit)
        
        # SFX notes
        right_layout.addWidget(QLabel(t("cue_editor.sfx")))
        self.sfx_edit = QTextEdit()
        self.sfx_edit.setPlaceholderText(t("cue_editor.sfx_placeholder"))
        self.sfx_edit.setMaximumHeight(60)
        right_layout.addWidget(self.sfx_edit)
        
        content_layout.addLayout(right_layout, 1)
        
        content_main_layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton(t("cue_editor.save"))
        self.save_btn.setShortcut("Ctrl+Return")
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px 16px; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        button_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton(t("cue_editor.reset"))
        self.reset_btn.setStyleSheet(
            "QPushButton { padding: 8px 16px; }"
        )
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        # Quick status buttons
        self.approve_btn = QPushButton(t("cue_editor.approve"))
        self.approve_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 6px 12px; border: none; border-radius: 4px; }"
        )
        button_layout.addWidget(self.approve_btn)
        
        self.revision_btn = QPushButton(t("cue_editor.revision"))
        self.revision_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; "
            "padding: 6px 12px; border: none; border-radius: 4px; }"
        )
        button_layout.addWidget(self.revision_btn)
        
        content_main_layout.addLayout(button_layout)
        
        # Add content widget to main layout
        layout.addWidget(self.content_widget)
        
        # Collapsed state
        self._collapsed = False
    
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
        self._collapsed = self.collapse_btn.isChecked()
        self.content_widget.setVisible(not self._collapsed)
        self.collapse_btn.setText("[+]" if self._collapsed else "[-]")
        
        # Set maximum height when collapsed to make widget smaller
        if self._collapsed:
            self.setMaximumHeight(60)  # Just header height
        else:
            self.setMaximumHeight(16777215)  # Reset to default max
    
    @Slot()
    def _on_source_lock_toggled(self):
        """Toggle source lock."""
        self._source_locked = self.source_lock_btn.isChecked()
        self.source_text.setReadOnly(self._source_locked)
        self._update_source_text_style()
    
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
        """Update lip-sync indicator."""
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
        
        # Details
        max_chars = self._lip_sync_estimator.calculate_max_chars(self._cue.duration_ms)
        current_chars = result.text_length
        
        self.lipsync_details.setText(
            f"{current_chars} / ~{max_chars} karakter | "
            f"Becsült: {result.estimated_time_ms/1000:.1f}s / "
            f"{self._cue.duration_ms/1000:.1f}s"
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
        self.lipsync_details.setText("")
        
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
