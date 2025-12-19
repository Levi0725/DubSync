"""
DubSync Video Player Widget

Videó lejátszó és vezérlő a lip-sync ellenőrzéshez.
"""

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QStyle, QSizePolicy, QFrame, QStackedLayout
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl, QTimer
from PySide6.QtGui import QKeySequence, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from dubsync.utils.time_utils import ms_to_timecode


class SubtitleOverlay(QLabel):
    """Felirat overlay widget a videó felett."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 160);
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
                margin: 20px;
            }
        """)
        self.setWordWrap(True)
        self.hide()


class FullscreenVideoWidget(QWidget):
    """Teljes képernyős videó ablak feliratokkal."""
    
    closed = Signal()
    
    def __init__(self, player: QMediaPlayer, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("DubSync - Videó")
        self.setStyleSheet("background-color: black;")
        
        self._player = player
        self._original_video_output = None
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container for video and overlay
        self.video_container = QWidget()
        self.video_container.setStyleSheet("background-color: black;")
        container_layout = QStackedLayout(self.video_container)
        container_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        # Video widget
        self.video_widget = QVideoWidget()
        container_layout.addWidget(self.video_widget)
        
        # Subtitle overlay
        self.subtitle_label = SubtitleOverlay()
        container_layout.addWidget(self.subtitle_label)
        
        layout.addWidget(self.video_container)
        
        # Hint label
        hint_label = QLabel("ESC - Kilépés | Szóköz - Lejátszás/Megállítás")
        hint_label.setStyleSheet("color: #666; padding: 5px;")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)
    
    def show_fullscreen(self):
        """Teljes képernyő megjelenítése."""
        self._original_video_output = self._player.videoOutput()
        self._player.setVideoOutput(self.video_widget)
        self.showFullScreen()
    
    def close_fullscreen(self):
        """Teljes képernyő bezárása."""
        if self._original_video_output:
            self._player.setVideoOutput(self._original_video_output)
        self.close()
        self.closed.emit()
    
    def set_subtitle(self, text: str):
        """Felirat beállítása."""
        if text:
            self.subtitle_label.setText(text)
            self.subtitle_label.show()
        else:
            self.subtitle_label.hide()
    
    def keyPressEvent(self, event):
        """Billentyű kezelés."""
        if event.key() == Qt.Key.Key_Escape:
            self.close_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._player.pause()
            else:
                self._player.play()
        else:
            super().keyPressEvent(event)


class VideoPlayerWidget(QWidget):
    """
    Videó lejátszó widget.
    
    Funkciók:
    - Videó lejátszás/megállítás
    - Frame-pontos keresés
    - Szegmens lejátszás (cue időtartama)
    - Lassított lejátszás
    """
    
    # Signals
    position_changed = Signal(int)  # position in ms
    duration_changed = Signal(int)  # duration in ms
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._segment_end: Optional[int] = None
        self._is_segment_playing = False
        
        self._setup_ui()
        self._setup_player()
        self._connect_signals()
    
    def _setup_ui(self):
        """UI felépítése."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Video display
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 225)
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.video_widget, 1)
        
        # Controls container
        controls_frame = QFrame()
        controls_frame.setStyleSheet(
            "QFrame { background-color: #2d2d2d; padding: 4px; }"
        )
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 4, 8, 4)
        
        # Progress slider
        slider_layout = QHBoxLayout()
        
        self.position_label = QLabel("00:00:00")
        self.position_label.setStyleSheet("color: white; font-family: monospace;")
        slider_layout.addWidget(self.position_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #555;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -4px 0;
                background: #0078d4;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #0078d4;
                border-radius: 3px;
            }
            QSlider::handle:horizontal:disabled {
                background: #555;
            }
            QSlider::sub-page:horizontal:disabled {
                background: #444;
            }
        """)
        slider_layout.addWidget(self.progress_slider)
        
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setStyleSheet("color: white; font-family: monospace;")
        slider_layout.addWidget(self.duration_label)
        
        controls_layout.addLayout(slider_layout)
        
        # Playback controls
        buttons_layout = QHBoxLayout()
        
        # Play/Pause
        self.play_btn = QPushButton("▶")
        self.play_btn.setMinimumSize(44, 32)
        self.play_btn.setStyleSheet(self._get_button_style())
        buttons_layout.addWidget(self.play_btn)
        
        # Stop
        self.stop_btn = QPushButton("■")
        self.stop_btn.setMinimumSize(44, 32)
        self.stop_btn.setStyleSheet(self._get_button_style())
        buttons_layout.addWidget(self.stop_btn)
        
        buttons_layout.addSpacing(20)
        
        # Frame step buttons
        self.prev_frame_btn = QPushButton("◀|")
        self.prev_frame_btn.setMinimumSize(44, 32)
        self.prev_frame_btn.setStyleSheet(self._get_button_style())
        self.prev_frame_btn.setToolTip("Előző frame (←)")
        buttons_layout.addWidget(self.prev_frame_btn)
        
        self.next_frame_btn = QPushButton("|▶")
        self.next_frame_btn.setMinimumSize(44, 32)
        self.next_frame_btn.setStyleSheet(self._get_button_style())
        self.next_frame_btn.setToolTip("Következő frame (→)")
        buttons_layout.addWidget(self.next_frame_btn)
        
        buttons_layout.addSpacing(20)
        
        # Jump buttons
        self.back_5s_btn = QPushButton("-5s")
        self.back_5s_btn.setMinimumSize(48, 32)
        self.back_5s_btn.setStyleSheet(self._get_button_style())
        buttons_layout.addWidget(self.back_5s_btn)
        
        self.forward_5s_btn = QPushButton("+5s")
        self.forward_5s_btn.setMinimumSize(48, 32)
        self.forward_5s_btn.setStyleSheet(self._get_button_style())
        buttons_layout.addWidget(self.forward_5s_btn)
        
        buttons_layout.addStretch()
        
        # Speed control
        speed_label = QLabel("Sebesség:")
        speed_label.setStyleSheet("color: white;")
        buttons_layout.addWidget(speed_label)
        
        self.speed_05_btn = QPushButton("0.5x")
        self.speed_05_btn.setMinimumSize(50, 32)
        self.speed_05_btn.setCheckable(True)
        self.speed_05_btn.setStyleSheet(self._get_button_style(True))
        buttons_layout.addWidget(self.speed_05_btn)
        
        self.speed_1_btn = QPushButton("1x")
        self.speed_1_btn.setMinimumSize(44, 32)
        self.speed_1_btn.setCheckable(True)
        self.speed_1_btn.setChecked(True)
        self.speed_1_btn.setStyleSheet(self._get_button_style(True))
        buttons_layout.addWidget(self.speed_1_btn)
        
        self.speed_15_btn = QPushButton("1.5x")
        self.speed_15_btn.setMinimumSize(50, 32)
        self.speed_15_btn.setCheckable(True)
        self.speed_15_btn.setStyleSheet(self._get_button_style(True))
        buttons_layout.addWidget(self.speed_15_btn)
        
        buttons_layout.addSpacing(20)
        
        # Loop segment
        self.loop_btn = QPushButton("🔁 Loop")
        self.loop_btn.setMinimumSize(70, 32)
        self.loop_btn.setCheckable(True)
        self.loop_btn.setStyleSheet(self._get_button_style(True))
        self.loop_btn.setToolTip("Cue ismétlése")
        buttons_layout.addWidget(self.loop_btn)
        
        # Fullscreen button
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setMinimumSize(44, 32)
        self.fullscreen_btn.setStyleSheet(self._get_button_style())
        self.fullscreen_btn.setToolTip("Teljes képernyő (F)")
        buttons_layout.addWidget(self.fullscreen_btn)
        
        controls_layout.addLayout(buttons_layout)
        
        layout.addWidget(controls_frame)
        
        # No video placeholder
        self.no_video_label = QLabel("Nincs betöltött videó")
        self.no_video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_video_label.setStyleSheet(
            "color: #999; font-size: 16px; background-color: #1a1a1a;"
        )
        layout.addWidget(self.no_video_label)
        
        self.no_video_label.hide()
    
    def _get_button_style(self, checkable: bool = False) -> str:
        """Gomb stílus."""
        base = """
            QPushButton {
                background-color: #444;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #555;
            }
        """
        if checkable:
            base += """
            QPushButton:checked {
                background-color: #0078d4;
            }
            QPushButton:checked:hover {
                background-color: #1084d8;
            }
            """
        return base
    
    def _setup_player(self):
        """Média lejátszó beállítása."""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        
        # Position check timer for segment playback
        self._position_timer = QTimer()
        self._position_timer.setInterval(50)  # 50ms precision
        self._position_timer.timeout.connect(self._check_segment_end)
    
    def _connect_signals(self):
        """Signal kapcsolatok."""
        # Player signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        
        # Control buttons
        self.play_btn.clicked.connect(self._toggle_playback)
        self.stop_btn.clicked.connect(self._stop)
        
        self.prev_frame_btn.clicked.connect(lambda: self._step_frame(-1))
        self.next_frame_btn.clicked.connect(lambda: self._step_frame(1))
        
        self.back_5s_btn.clicked.connect(lambda: self._seek_relative(-5000))
        self.forward_5s_btn.clicked.connect(lambda: self._seek_relative(5000))
        
        # Speed buttons
        self.speed_05_btn.clicked.connect(lambda: self._set_speed(0.5))
        self.speed_1_btn.clicked.connect(lambda: self._set_speed(1.0))
        self.speed_15_btn.clicked.connect(lambda: self._set_speed(1.5))
        
        # Slider
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        
        # Fullscreen
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        
        # Fullscreen widget (lazy init)
        self._fullscreen_widget: Optional[FullscreenVideoWidget] = None
        self._current_subtitle_text = ""
    
    def load_video(self, video_path: Path):
        """
        Videó betöltése.
        
        Args:
            video_path: Videó fájl elérési útja
        """
        if not video_path.exists():
            self._show_no_video()
            return
        
        self.player.setSource(QUrl.fromLocalFile(str(video_path)))
        self.no_video_label.hide()
        self.video_widget.show()
    
    def _show_no_video(self):
        """Nincs videó állapot megjelenítése."""
        self.video_widget.hide()
        self.no_video_label.show()
    
    def seek_to(self, position_ms: int):
        """
        Ugrás adott pozícióra.
        
        Args:
            position_ms: Pozíció milliszekundumban
        """
        self.player.setPosition(position_ms)
    
    def play_segment(self, start_ms: int, end_ms: int):
        """
        Szegmens lejátszása (cue).
        
        Args:
            start_ms: Kezdő pozíció
            end_ms: Záró pozíció
        """
        self._segment_end = end_ms
        self._is_segment_playing = True
        self.player.setPosition(start_ms)
        self.player.play()
        self._position_timer.start()
    
    def _check_segment_end(self):
        """Szegmens végének ellenőrzése."""
        if not self._is_segment_playing:
            self._position_timer.stop()
            return
        
        if self._segment_end and self.player.position() >= self._segment_end:
            if self.loop_btn.isChecked():
                # Loop: seek back to segment start
                segment_start = self._segment_end - (
                    self._segment_end - self.player.position()
                )
                # We need to track segment start too
                self.player.setPosition(max(0, self._segment_end - 5000))
            else:
                self.player.pause()
                self._is_segment_playing = False
                self._position_timer.stop()
    
    @Slot()
    def _toggle_playback(self):
        """Lejátszás/megállítás váltása."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self._is_segment_playing = False
            self.player.play()
    
    @Slot()
    def _stop(self):
        """Megállítás."""
        self.player.stop()
        self._is_segment_playing = False
        self._position_timer.stop()
    
    def _step_frame(self, direction: int):
        """
        Frame lépés.
        
        Args:
            direction: -1 hátra, +1 előre
        """
        # Assuming 25 fps, 1 frame = 40ms
        frame_ms = 40
        new_pos = self.player.position() + (direction * frame_ms)
        self.player.setPosition(max(0, new_pos))
    
    def _seek_relative(self, offset_ms: int):
        """
        Relatív ugrás.
        
        Args:
            offset_ms: Eltolás milliszekundumban
        """
        new_pos = self.player.position() + offset_ms
        new_pos = max(0, min(new_pos, self.player.duration()))
        self.player.setPosition(new_pos)
    
    def _set_speed(self, rate: float):
        """
        Lejátszási sebesség beállítása.
        
        Args:
            rate: Sebesség szorzó
        """
        self.player.setPlaybackRate(rate)
        
        # Update button states
        self.speed_05_btn.setChecked(rate == 0.5)
        self.speed_1_btn.setChecked(rate == 1.0)
        self.speed_15_btn.setChecked(rate == 1.5)
    
    @Slot(int)
    def _on_position_changed(self, position: int):
        """Pozíció változott."""
        self.position_label.setText(ms_to_timecode(position)[:8])
        
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(position)
        
        self.position_changed.emit(position)
    
    @Slot(int)
    def _on_duration_changed(self, duration: int):
        """Időtartam változott."""
        self.duration_label.setText(ms_to_timecode(duration)[:8])
        self.progress_slider.setRange(0, duration)
        self.duration_changed.emit(duration)
    
    @Slot(QMediaPlayer.PlaybackState)
    def _on_state_changed(self, state: QMediaPlayer.PlaybackState):
        """Lejátszási állapot változott."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")
    
    @Slot()
    def _on_slider_pressed(self):
        """Slider megnyomva."""
        self.player.pause()
    
    @Slot()
    def _on_slider_released(self):
        """Slider elengedve."""
        self.player.setPosition(self.progress_slider.value())
    
    @Slot(int)
    def _on_slider_moved(self, position: int):
        """Slider mozgatva."""
        self.position_label.setText(ms_to_timecode(position)[:8])
    
    def keyPressEvent(self, event):
        """Billentyűzet kezelése."""
        key = event.key()
        
        if key == Qt.Key.Key_Space:
            self._toggle_playback()
        elif key == Qt.Key.Key_Left:
            self._step_frame(-1)
        elif key == Qt.Key.Key_Right:
            self._step_frame(1)
        elif key == Qt.Key.Key_Home:
            self.seek_to(0)
        elif key == Qt.Key.Key_F:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)
    
    def _toggle_fullscreen(self):
        """Teljes képernyő váltása."""
        if self._fullscreen_widget is None:
            self._fullscreen_widget = FullscreenVideoWidget(self.player, self)
            self._fullscreen_widget.closed.connect(self._on_fullscreen_closed)
        
        if self._fullscreen_widget.isVisible():
            self._fullscreen_widget.close_fullscreen()
        else:
            self._fullscreen_widget.show_fullscreen()
            # Set current subtitle
            if self._current_subtitle_text:
                self._fullscreen_widget.set_subtitle(self._current_subtitle_text)
    
    def _on_fullscreen_closed(self):
        """Teljes képernyő bezárva."""
        pass  # Video output already restored by close_fullscreen
    
    def set_subtitle(self, text: str):
        """
        Felirat beállítása (fullscreen módhoz).
        
        Args:
            text: Felirat szöveg
        """
        self._current_subtitle_text = text
        if self._fullscreen_widget and self._fullscreen_widget.isVisible():
            self._fullscreen_widget.set_subtitle(text)
