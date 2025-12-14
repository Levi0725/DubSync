"""
DubSync Cue Editor Widget

Cue szerkesztő panel a fordításhoz és szerkesztéshez.
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


class TimingEditorDialog(QDialog):
    """Időzítés szerkesztő dialógus."""
    
    def __init__(self, cue: Cue, parent=None):
        super().__init__(parent)
        self.cue = cue
        self.setWindowTitle("Időzítés szerkesztése")
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
        
        form_layout.addRow("Kezdés:", time_in_layout)
        
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
        
        form_layout.addRow("Vége:", time_out_layout)
        
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
            self.duration_label.setText("⚠️ A vége nem lehet a kezdés előtt!")
        else:
            self.duration_label.setStyleSheet("")
            self.duration_label.setText(f"Hossz: {format_duration(duration)}")
    
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
    Cue szerkesztő widget.
    
    Lehetővé teszi a fordítás, karakter, megjegyzések szerkesztését,
    és megjeleníti a lip-sync becslést.
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
        """UI felépítése."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Header with time info
        header_layout = QHBoxLayout()
        
        self.index_label = QLabel("#-")
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
        self.status_combo.addItem("Új", CueStatus.NEW.value)
        self.status_combo.addItem("Fordítva", CueStatus.TRANSLATED.value)
        self.status_combo.addItem("Javítandó", CueStatus.NEEDS_REVISION.value)
        self.status_combo.addItem("Jóváhagyva", CueStatus.APPROVED.value)
        header_layout.addWidget(QLabel("Státusz:"))
        header_layout.addWidget(self.status_combo)
        
        layout.addLayout(header_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - Source and translation
        left_layout = QVBoxLayout()
        
        # Character name
        char_layout = QHBoxLayout()
        char_layout.addWidget(QLabel("Karakter:"))
        self.character_edit = QLineEdit()
        self.character_edit.setPlaceholderText("Karakter neve...")
        char_layout.addWidget(self.character_edit)
        left_layout.addLayout(char_layout)
        
        # Source text (read-only)
        left_layout.addWidget(QLabel("Forrás szöveg:"))
        self.source_text = QTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setMaximumHeight(80)
        self.source_text.setStyleSheet(
            "background-color: #f5f5f5; color: #666;"
        )
        left_layout.addWidget(self.source_text)
        
        # Translated text
        left_layout.addWidget(QLabel("Fordítás:"))
        self.translated_text = QTextEdit()
        self.translated_text.setPlaceholderText("Írja be a fordítást...")
        self.translated_text.setMinimumHeight(100)
        left_layout.addWidget(self.translated_text)
        
        content_layout.addLayout(left_layout, 2)
        
        # Right side - Notes and lip-sync
        right_layout = QVBoxLayout()
        
        # Lip-sync indicator
        lipsync_group = QGroupBox("Lip-sync becslés")
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
        self.lipsync_label = QLabel("Nincs adat")
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
        right_layout.addWidget(QLabel("Megjegyzés:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Rendezői utasítások, megjegyzések...")
        self.notes_edit.setMaximumHeight(60)
        right_layout.addWidget(self.notes_edit)
        
        # SFX notes
        right_layout.addWidget(QLabel("Háttérhang / SFX:"))
        self.sfx_edit = QTextEdit()
        self.sfx_edit.setPlaceholderText("Háttérzajok, zene, effektek...")
        self.sfx_edit.setMaximumHeight(60)
        right_layout.addWidget(self.sfx_edit)
        
        content_layout.addLayout(right_layout, 1)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Mentés")
        self.save_btn.setShortcut("Ctrl+Return")
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px 16px; border: none; border-radius: 4px; }"
            "QPushButton:hover { background-color: #45a049; }"
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        button_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("Visszaállítás")
        self.reset_btn.setStyleSheet(
            "QPushButton { padding: 8px 16px; }"
        )
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        # Quick status buttons
        self.approve_btn = QPushButton("✓ Jóváhagy")
        self.approve_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 6px 12px; border: none; border-radius: 4px; }"
        )
        button_layout.addWidget(self.approve_btn)
        
        self.revision_btn = QPushButton("⚠ Javítandó")
        self.revision_btn.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; "
            "padding: 6px 12px; border: none; border-radius: 4px; }"
        )
        button_layout.addWidget(self.revision_btn)
        
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Signal kapcsolatok."""
        self.translated_text.textChanged.connect(self._on_text_changed)
        self.character_edit.textChanged.connect(self._mark_dirty)
        self.notes_edit.textChanged.connect(self._mark_dirty)
        self.sfx_edit.textChanged.connect(self._mark_dirty)
        self.status_combo.currentIndexChanged.connect(self._on_status_changed)
        
        self.save_btn.clicked.connect(self._on_save)
        self.reset_btn.clicked.connect(self._on_reset)
        self.approve_btn.clicked.connect(self._on_approve)
        self.revision_btn.clicked.connect(self._on_revision)
    
    def _update_ui_state(self):
        """UI állapot frissítése."""
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
        Cue beállítása szerkesztésre.
        
        Args:
            cue: Cue objektum
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
        Szerkesztett cue lekérése.
        
        Returns:
            Cue objektum az aktuális értékekkel
        """
        if self._cue is None:
            return None
        
        self._cue.character_name = self.character_edit.text()
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
        """Lip-sync indikátor frissítése."""
        if self._cue is None:
            return
        
        text = self.translated_text.toPlainText()
        if not text:
            text = self.source_text.toPlainText()
        
        result = self._lip_sync_estimator.estimate(text, self._cue.duration_ms)
        
        # Update indicator color and text
        if result.ratio <= 0.9:
            color = COLOR_LIPSYNC_GOOD
            status_text = "✓ Megfelelő"
        elif result.ratio <= 1.05:
            color = COLOR_LIPSYNC_WARNING
            status_text = "⚠ Határeset"
        else:
            color = COLOR_LIPSYNC_TOO_LONG
            status_text = "✗ Túl hosszú"
        
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
        """Módosítás jelölése."""
        self._is_dirty = True
        self._update_ui_state()
    
    @Slot()
    def _on_text_changed(self):
        """Szöveg változott."""
        self._mark_dirty()
        self._update_lipsync()
    
    @Slot()
    def _on_status_changed(self):
        """Státusz változott."""
        self._mark_dirty()
    
    @Slot()
    def _on_save(self):
        """Mentés."""
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
        """Visszaállítás."""
        if self._cue:
            self.set_cue(self._cue)
    
    @Slot()
    def _on_approve(self):
        """Gyors jóváhagyás."""
        if self._cue is None:
            return
        
        index = self.status_combo.findData(CueStatus.APPROVED.value)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        self._on_save()
    
    @Slot()
    def _on_revision(self):
        """Gyors javítandó jelölés."""
        if self._cue is None:
            return
        
        index = self.status_combo.findData(CueStatus.NEEDS_REVISION.value)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        self._on_save()
    
    def clear(self):
        """Editor törlése."""
        self._cue = None
        self._is_dirty = False
        
        self.index_label.setText("#-")
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
        self.lipsync_label.setText("Nincs adat")
        self.lipsync_details.setText("")
        
        self._update_ui_state()
    
    def show_timing_editor(self, cue: Cue):
        """
        Időzítés szerkesztő dialógus megnyitása.
        
        Args:
            cue: Szerkesztendő cue
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
