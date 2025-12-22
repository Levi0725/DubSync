"""
DubSync Timeline Widget

Visual timeline for viewing and editing cues.
Shows cues as colored blocks on a time axis.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
    QLabel, QPushButton, QSlider, QFrame, QToolTip,
    QScrollBar, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, Slot, QRect, QRectF, QPointF, QSize, QTimer
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QFontMetrics,
    QPainterPath, QLinearGradient, QMouseEvent, QWheelEvent,
    QPaintEvent, QResizeEvent, QCursor
)

from dubsync.models.cue import Cue
from dubsync.utils.constants import (
    CueStatus, LipSyncStatus,
    COLOR_STATUS_NEW, COLOR_STATUS_TRANSLATED, 
    COLOR_STATUS_NEEDS_REVISION, COLOR_STATUS_APPROVED,
    COLOR_LIPSYNC_GOOD, COLOR_LIPSYNC_WARNING, COLOR_LIPSYNC_TOO_LONG
)
from dubsync.utils.time_utils import ms_to_timecode
from dubsync.i18n import t
from dubsync.resources.icon_manager import get_icon_manager


class DragMode(Enum):
    """Drag interaction mode."""
    NONE = auto()
    MOVE = auto()
    RESIZE_LEFT = auto()
    RESIZE_RIGHT = auto()


@dataclass
class CueBlock:
    """Represents a cue on the timeline."""
    cue: Cue
    rect: QRectF
    selected: bool = False


class TimelineCanvas(QWidget):
    """
    Canvas widget for drawing the timeline.
    
    Features:
    - Horizontal time axis
    - Cue blocks with color-coded status
    - Zoom and pan support
    - Selection and editing
    - Drag & drop cue moving
    - Edge drag for cue resizing
    """
    
    # Signals
    cue_selected = Signal(int)  # Emits cue_id
    cue_double_clicked = Signal(int)  # Emits cue_id
    playhead_moved = Signal(int)  # Emits position in ms
    cue_moved = Signal(int, int, int)  # cue_id, new_time_in_ms, new_time_out_ms
    cue_resized = Signal(int, int, int)  # cue_id, new_time_in_ms, new_time_out_ms
    
    # Constants
    TRACK_HEIGHT = 28
    HEADER_HEIGHT = 20
    MIN_PIXELS_PER_SECOND = 10
    MAX_PIXELS_PER_SECOND = 500
    DEFAULT_PIXELS_PER_SECOND = 50
    RESIZE_HANDLE_WIDTH = 8  # Width of resize handles on edges
    MIN_CUE_DURATION_MS = 100  # Minimum cue duration
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Data
        self._cues: List[Cue] = []
        self._cue_blocks: List[CueBlock] = []
        self._selected_cue_id: Optional[int] = None
        
        # View state
        self._pixels_per_second = self.DEFAULT_PIXELS_PER_SECOND
        self._scroll_offset_x = 0
        self._total_duration_ms = 0
        self._playhead_position_ms = 0
        self._center_playhead = True  # Keep playhead centered
        
        # Interaction state
        self._drag_mode = DragMode.NONE
        self._drag_start_pos = QPointF()
        self._drag_start_time_in = 0
        self._drag_start_time_out = 0
        self._dragging_block: Optional[CueBlock] = None
        self._hovered_block: Optional[CueBlock] = None
        self._hover_edge: Optional[str] = None  # "left", "right", or None
        
        # Setup
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(self.TRACK_HEIGHT + self.HEADER_HEIGHT + 10)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Colors
        self._bg_color = QColor("#1e1e1e")
        self._header_color = QColor("#2d2d2d")
        self._grid_color = QColor("#3d3d3d")
        self._text_color = QColor("#cccccc")
        self._playhead_color = QColor("#ff5722")
        self._selection_color = QColor("#2196F3")
        self._resize_handle_color = QColor("#ffffff")
    
    def set_cues(self, cues: List[Cue]) -> None:
        """Set cues to display."""
        self._cues = cues
        self._recalculate_blocks()
        self.update()
    
    def set_selected_cue(self, cue_id: Optional[int]) -> None:
        """Set currently selected cue."""
        self._selected_cue_id = cue_id
        for block in self._cue_blocks:
            block.selected = block.cue.id == cue_id
        self.update()
        
        # Center on selected cue
        if cue_id:
            self._center_on_cue(cue_id)
    
    def set_playhead_position(self, position_ms: int) -> None:
        """Set playhead position and center it in view."""
        self._playhead_position_ms = position_ms
        if self._center_playhead:
            self._center_on_playhead()
        self.update()
    
    def set_center_playhead(self, center: bool) -> None:
        """Enable/disable automatic playhead centering."""
        self._center_playhead = center
    
    def _center_on_playhead(self) -> None:
        """Center the view on the playhead position."""
        parent = self.parent()
        if parent is None:
            return
        
        scrollbar = getattr(parent, 'horizontalScrollBar', lambda: None)()
        if scrollbar is None:
            return
        
        viewport = getattr(parent, 'viewport', lambda: None)()
        if viewport is None:
            return
        
        playhead_x = self._ms_to_x(self._playhead_position_ms)
        viewport_width = viewport.width()
        
        # Center playhead in viewport
        target_scroll = int(playhead_x - viewport_width / 2)
        target_scroll = max(0, min(target_scroll, scrollbar.maximum()))
        scrollbar.setValue(target_scroll)
    
    def _center_on_cue(self, cue_id: int) -> None:
        """Center the view on a specific cue."""
        for block in self._cue_blocks:
            if block.cue.id == cue_id:
                parent = self.parent()
                if parent is None:
                    return
                
                scrollbar = getattr(parent, 'horizontalScrollBar', lambda: None)()
                if scrollbar is None:
                    return
                
                viewport = getattr(parent, 'viewport', lambda: None)()
                if viewport is None:
                    return
                
                # Center of the cue block
                cue_center_x = block.rect.center().x()
                viewport_width = viewport.width()
                
                # Center cue in viewport
                target_scroll = int(cue_center_x - viewport_width / 2)
                target_scroll = max(0, min(target_scroll, scrollbar.maximum()))
                scrollbar.setValue(target_scroll)
                break
    
    def _scroll_to_playhead(self) -> None:
        """Auto-scroll to keep playhead visible (fallback for edge cases)."""
        # Now using _center_on_playhead instead
        self._center_on_playhead()
    
    def set_zoom(self, pixels_per_second: float) -> None:
        """Set zoom level."""
        self._pixels_per_second = max(
            self.MIN_PIXELS_PER_SECOND,
            min(self.MAX_PIXELS_PER_SECOND, pixels_per_second)
        )
        self._recalculate_blocks()
        self.update()
    
    def get_zoom(self) -> float:
        """Get current zoom level."""
        return self._pixels_per_second
    
    def _recalculate_blocks(self) -> None:
        """Recalculate cue block positions."""
        self._cue_blocks.clear()
        
        if not self._cues:
            self._total_duration_ms = 60000  # Default 1 minute
            return
        
        # Calculate total duration
        self._total_duration_ms = max(
            cue.time_out_ms for cue in self._cues
        ) if self._cues else 60000
        
        # Add some padding
        self._total_duration_ms = int(self._total_duration_ms * 1.1)
        
        # Calculate blocks
        y = self.HEADER_HEIGHT + 5
        height = self.TRACK_HEIGHT - 10
        
        for cue in self._cues:
            x = self._ms_to_x(cue.time_in_ms)
            width = self._ms_to_x(cue.time_out_ms) - x
            width = max(width, 10)  # Minimum width
            
            rect = QRectF(x, y, width, height)
            block = CueBlock(
                cue=cue,
                rect=rect,
                selected=cue.id == self._selected_cue_id
            )
            self._cue_blocks.append(block)
        
        # Update widget width
        total_width = self._ms_to_x(self._total_duration_ms)
        self.setMinimumWidth(int(total_width) + 50)
    
    def _ms_to_x(self, ms: int) -> float:
        """Convert milliseconds to x coordinate."""
        return (ms / 1000.0) * self._pixels_per_second
    
    def _x_to_ms(self, x: float) -> int:
        """Convert x coordinate to milliseconds."""
        return int((x / self._pixels_per_second) * 1000)
    
    def _get_edge_at_pos(self, block: CueBlock, pos: QPointF) -> Optional[str]:
        """Check if position is on a resize handle edge."""
        if not block.rect.contains(pos):
            return None
        
        left_edge = block.rect.left()
        right_edge = block.rect.right()
        
        if pos.x() <= left_edge + self.RESIZE_HANDLE_WIDTH:
            return "left"
        elif pos.x() >= right_edge - self.RESIZE_HANDLE_WIDTH:
            return "right"
        return None
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the timeline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), self._bg_color)
        
        # Draw time grid
        self._draw_time_grid(painter)
        
        # Draw cue blocks
        self._draw_cue_blocks(painter)
        
        # Draw playhead
        self._draw_playhead(painter)
        
        painter.end()
    
    def _draw_time_grid(self, painter: QPainter) -> None:
        """Draw time axis and grid lines."""
        # Header background
        header_rect = QRect(0, 0, self.width(), self.HEADER_HEIGHT)
        painter.fillRect(header_rect, self._header_color)

        # Calculate grid interval based on zoom
        if self._pixels_per_second >= 100:
            interval_sec = 1
        elif self._pixels_per_second >= 50:
            interval_sec = 5
        elif self._pixels_per_second >= 20:
            interval_sec = 10
        else:
            interval_sec = 30

        # Draw grid lines and labels
        painter.setPen(QPen(self._grid_color, 1))
        self._extracted_from__draw_block_19(9, painter)
        total_seconds = self._total_duration_ms / 1000
        current_sec = 0

        while current_sec <= total_seconds:
            x = self._ms_to_x(current_sec * 1000)

            # Grid line
            painter.setPen(QPen(self._grid_color, 1))
            painter.drawLine(int(x), self.HEADER_HEIGHT, int(x), self.height())

            # Time label
            painter.setPen(QPen(self._text_color))
            time_str = self._format_time(current_sec)
            painter.drawText(int(x) + 4, self.HEADER_HEIGHT - 6, time_str)

            current_sec += interval_sec
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds to time string."""
        minutes, secs = divmod(int(seconds), 60)
        return f"{minutes}:{secs:02d}" if minutes > 0 else f"{secs}s"
    
    def _draw_cue_blocks(self, painter: QPainter) -> None:
        """Draw cue blocks."""
        for block in self._cue_blocks:
            self._draw_block(painter, block)
    
    def _draw_block(self, painter: QPainter, block: CueBlock) -> None:
        """Draw a single cue block."""
        cue = block.cue
        rect = block.rect

        # Get status color
        status_colors = {
            CueStatus.NEW: QColor(COLOR_STATUS_NEW),
            CueStatus.TRANSLATED: QColor(COLOR_STATUS_TRANSLATED),
            CueStatus.NEEDS_REVISION: QColor(COLOR_STATUS_NEEDS_REVISION),
            CueStatus.APPROVED: QColor(COLOR_STATUS_APPROVED),
        }
        base_color = status_colors.get(cue.status, QColor("#666666"))

        # Create gradient
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0, base_color.lighter(120))
        gradient.setColorAt(1, base_color.darker(110))

        # Draw block
        painter.setBrush(QBrush(gradient))

        # Border
        if block.selected:
            painter.setPen(QPen(self._selection_color, 2))
        elif block == self._hovered_block:
            painter.setPen(QPen(base_color.lighter(150), 2))
        else:
            painter.setPen(QPen(base_color.darker(130), 1))

        # Rounded rectangle
        painter.drawRoundedRect(rect, 4, 4)
        
        # Draw resize handles when hovered or selected
        if block.selected or block == self._hovered_block:
            self._draw_resize_handles(painter, block)

        # Draw text if block is wide enough
        if rect.width() > 40:
            self._extracted_from__draw_block_36(painter, cue, rect)
        # Lip-sync indicator (small bar at bottom)
        if cue.lip_sync_ratio is not None:
            self._extracted_from__draw_block_48(rect, cue, painter)
    
    def _draw_resize_handles(self, painter: QPainter, block: CueBlock) -> None:
        """Draw resize handles on cue block edges."""
        rect = block.rect
        handle_height = rect.height() - 8
        handle_y = rect.top() + 4
        
        # Left handle
        left_rect = QRectF(
            rect.left() + 2,
            handle_y,
            3,
            handle_height
        )
        
        # Right handle
        right_rect = QRectF(
            rect.right() - 5,
            handle_y,
            3,
            handle_height
        )
        
        # Draw handles
        painter.setBrush(QBrush(self._resize_handle_color.darker(120) if self._hover_edge else self._resize_handle_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Highlight the handle being hovered
        if block == self._hovered_block:
            if self._hover_edge == "left":
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.drawRoundedRect(left_rect, 1, 1)
                painter.setBrush(QBrush(self._resize_handle_color.darker(150)))
                painter.drawRoundedRect(right_rect, 1, 1)
            elif self._hover_edge == "right":
                painter.setBrush(QBrush(self._resize_handle_color.darker(150)))
                painter.drawRoundedRect(left_rect, 1, 1)
                painter.setBrush(QBrush(QColor("#ffffff")))
                painter.drawRoundedRect(right_rect, 1, 1)
            else:
                painter.setBrush(QBrush(self._resize_handle_color.darker(150)))
                painter.drawRoundedRect(left_rect, 1, 1)
                painter.drawRoundedRect(right_rect, 1, 1)
        else:
            painter.setBrush(QBrush(self._resize_handle_color.darker(150)))
            painter.drawRoundedRect(left_rect, 1, 1)
            painter.drawRoundedRect(right_rect, 1, 1)

    # TODO Rename this here and in `_draw_block`
    def _extracted_from__draw_block_48(self, rect, cue, painter):
        indicator_height = 4
        indicator_rect = QRectF(
            rect.left() + 2,
            rect.bottom() - indicator_height - 2,
            rect.width() - 4,
            indicator_height
        )

        if cue.lip_sync_ratio <= 85:
            ls_color = QColor(COLOR_LIPSYNC_GOOD)
        elif cue.lip_sync_ratio <= 100:
            ls_color = QColor(COLOR_LIPSYNC_WARNING)
        else:
            ls_color = QColor(COLOR_LIPSYNC_TOO_LONG)

        painter.setBrush(QBrush(ls_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(indicator_rect, 2, 2)

    # TODO Rename this here and in `_draw_block`
    def _extracted_from__draw_block_36(self, painter, cue, rect):
        painter.setPen(QPen(QColor("#ffffff")))
        self._extracted_from__draw_block_19(8, painter)
        # Clip text to block
        text = f"#{cue.cue_index}"
        if rect.width() > 80 and cue.character_name:
            text = f"#{cue.cue_index} - {cue.character_name}"

        text_rect = rect.adjusted(4, 2, -4, -2)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

    # TODO Rename this here and in `_draw_time_grid` and `_draw_block`
    def _extracted_from__draw_block_19(self, arg0, painter):
        font = QFont()
        font.setPointSize(arg0)
        painter.setFont(font)
    
    def _draw_playhead(self, painter: QPainter) -> None:
        """Draw playhead."""
        x = self._ms_to_x(self._playhead_position_ms)
        
        painter.setPen(QPen(self._playhead_color, 2))
        painter.drawLine(int(x), 0, int(x), self.height())
        
        # Triangle at top
        triangle_size = 8
        path = QPainterPath()
        path.moveTo(x - triangle_size / 2, 0)
        path.lineTo(x + triangle_size / 2, 0)
        path.lineTo(x, triangle_size)
        path.closeSubpath()
        
        painter.setBrush(QBrush(self._playhead_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press."""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()

        # Check if clicked on a block
        for block in self._cue_blocks:
            if block.rect.contains(pos):
                # Check for resize edge
                edge = self._get_edge_at_pos(block, pos)
                
                self._selected_cue_id = block.cue.id
                for b in self._cue_blocks:
                    b.selected = b.cue.id == self._selected_cue_id
                self.cue_selected.emit(block.cue.id)
                
                # Start drag operation
                self._dragging_block = block
                self._drag_start_pos = pos
                self._drag_start_time_in = block.cue.time_in_ms
                self._drag_start_time_out = block.cue.time_out_ms
                
                if edge == "left":
                    self._drag_mode = DragMode.RESIZE_LEFT
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif edge == "right":
                    self._drag_mode = DragMode.RESIZE_RIGHT
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self._drag_mode = DragMode.MOVE
                    self.setCursor(Qt.CursorShape.ClosedHandCursor)
                
                self.update()
                return

        # Clicked on header or empty space - move playhead
        new_pos = self._x_to_ms(pos.x())
        self._playhead_position_ms = max(0, new_pos)
        self.playhead_moved.emit(self._playhead_position_ms)
        self.update()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Handle double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            
            for block in self._cue_blocks:
                if block.rect.contains(pos):
                    self.cue_double_clicked.emit(block.cue.id)
                    return
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release - complete drag operations."""
        if event.button() == Qt.MouseButton.LeftButton and self._dragging_block:
            if self._drag_mode in (DragMode.MOVE, DragMode.RESIZE_LEFT, DragMode.RESIZE_RIGHT):
                cue = self._dragging_block.cue
                
                # Emit appropriate signal
                if self._drag_mode == DragMode.MOVE:
                    self.cue_moved.emit(cue.id, cue.time_in_ms, cue.time_out_ms)
                else:
                    self.cue_resized.emit(cue.id, cue.time_in_ms, cue.time_out_ms)
            
            # Reset drag state
            self._drag_mode = DragMode.NONE
            self._dragging_block = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse move - dragging and hover."""
        pos = event.position()
        
        # Handle active drag
        if self._drag_mode != DragMode.NONE and self._dragging_block:
            self._handle_drag(pos)
            return

        # Update hover state and cursor
        old_hovered = self._hovered_block
        old_edge = self._hover_edge
        self._hovered_block = None
        self._hover_edge = None

        for block in self._cue_blocks:
            if block.rect.contains(pos):
                self._hovered_block = block
                self._hover_edge = self._get_edge_at_pos(block, pos)
                
                # Update cursor based on hover position
                if self._hover_edge in ("left", "right"):
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.setCursor(Qt.CursorShape.OpenHandCursor)

                # Show tooltip
                cue = block.cue
                tooltip = f"#{cue.cue_index} - {cue.character_name or 'N/A'}\n{ms_to_timecode(cue.time_in_ms)} → {ms_to_timecode(cue.time_out_ms)}\n{t(f'status.{cue.status.name.lower()}')}"
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
                break
        else:
            # Not hovering over any block
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if old_hovered != self._hovered_block or old_edge != self._hover_edge:
            self.update()
    
    def _handle_drag(self, pos: QPointF) -> None:
        """Handle drag movement for cue moving/resizing."""
        if not self._dragging_block:
            return
        
        delta_x = pos.x() - self._drag_start_pos.x()
        delta_ms = self._x_to_ms(delta_x) - self._x_to_ms(0)
        
        cue = self._dragging_block.cue
        
        if self._drag_mode == DragMode.MOVE:
            # Move the entire cue
            duration = self._drag_start_time_out - self._drag_start_time_in
            new_time_in = max(0, self._drag_start_time_in + delta_ms)
            new_time_out = new_time_in + duration
            
            cue.time_in_ms = new_time_in
            cue.time_out_ms = new_time_out
            
        elif self._drag_mode == DragMode.RESIZE_LEFT:
            # Resize from left edge (change time_in)
            new_time_in = self._drag_start_time_in + delta_ms
            # Ensure minimum duration and don't go past time_out
            new_time_in = max(0, new_time_in)
            new_time_in = min(new_time_in, self._drag_start_time_out - self.MIN_CUE_DURATION_MS)
            cue.time_in_ms = new_time_in
            
        elif self._drag_mode == DragMode.RESIZE_RIGHT:
            # Resize from right edge (change time_out)
            new_time_out = self._drag_start_time_out + delta_ms
            # Ensure minimum duration
            new_time_out = max(self._drag_start_time_in + self.MIN_CUE_DURATION_MS, new_time_out)
            cue.time_out_ms = new_time_out
        
        # Recalculate block positions
        self._recalculate_blocks()
        self.update()
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom with Ctrl+Wheel
            delta = event.angleDelta().y()
            zoom_factor = 1.1 if delta > 0 else 0.9
            new_zoom = self._pixels_per_second * zoom_factor
            self.set_zoom(new_zoom)
            event.accept()
        else:
            # Pass to parent for scrolling
            event.ignore()


class TimelineWidget(QWidget):
    """
    Complete timeline widget with controls.
    
    Features:
    - Scrollable timeline canvas
    - Zoom controls
    - Track selection
    - Drag & drop cue moving
    - Edge drag cue resizing
    """
    
    # Signals (forwarded from canvas)
    cue_selected = Signal(int)
    cue_double_clicked = Signal(int)
    playhead_moved = Signal(int)
    cue_moved = Signal(int, int, int)  # cue_id, new_time_in_ms, new_time_out_ms
    cue_resized = Signal(int, int, int)  # cue_id, new_time_in_ms, new_time_out_ms
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Setup UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Controls bar
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(4, 2, 4, 2)
        controls_layout.setSpacing(4)
        
        icon_mgr = get_icon_manager()
        icon_size = QSize(14, 14)
        
        # Title
        title_label = QLabel(t("timeline.title") if t("timeline.title") != "timeline.title" else "Timeline")
        title_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        controls_layout.addWidget(title_label)
        
        controls_layout.addStretch()
        
        # Zoom controls
        zoom_out_btn = QPushButton()
        zoom_out_btn.setIcon(icon_mgr.get_icon("view_zoom_out", size=icon_size))
        zoom_out_btn.setIconSize(icon_size)
        zoom_out_btn.setFixedSize(20, 20)
        zoom_out_btn.setToolTip(t("timeline.zoom_out") if t("timeline.zoom_out") != "timeline.zoom_out" else "Zoom out")
        zoom_out_btn.clicked.connect(self._zoom_out)
        controls_layout.addWidget(zoom_out_btn)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setFixedWidth(80)
        self.zoom_slider.setFixedHeight(16)
        self.zoom_slider.setToolTip(t("timeline.zoom") if t("timeline.zoom") != "timeline.zoom" else "Zoom level")
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self.zoom_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #3d3d3d;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px;
                margin: -3px 0;
                background: #0078d4;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: #1a8cdf;
            }
        """)
        controls_layout.addWidget(self.zoom_slider)
        
        zoom_in_btn = QPushButton()
        zoom_in_btn.setIcon(icon_mgr.get_icon("view_zoom_in", size=icon_size))
        zoom_in_btn.setIconSize(icon_size)
        zoom_in_btn.setFixedSize(20, 20)
        zoom_in_btn.setToolTip(t("timeline.zoom_in") if t("timeline.zoom_in") != "timeline.zoom_in" else "Zoom in")
        zoom_in_btn.clicked.connect(self._zoom_in)
        controls_layout.addWidget(zoom_in_btn)
        
        # Fit to view button
        fit_btn = QPushButton()
        fit_btn.setIcon(icon_mgr.get_icon("view_zoom_fit", size=icon_size))
        fit_btn.setIconSize(icon_size)
        fit_btn.setFixedSize(20, 20)
        fit_btn.setToolTip(t("timeline.fit_to_view") if t("timeline.fit_to_view") != "timeline.fit_to_view" else "Fit to view")
        fit_btn.clicked.connect(self._fit_to_view)
        controls_layout.addWidget(fit_btn)
        
        layout.addLayout(controls_layout)
        
        # Scroll area with canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.canvas = TimelineCanvas()
        self.scroll_area.setWidget(self.canvas)
        
        layout.addWidget(self.scroll_area)
        
        # Set minimum height - more compact
        self.setMinimumHeight(80)
    
    def _connect_signals(self) -> None:
        """Connect signals."""
        self.canvas.cue_selected.connect(self.cue_selected)
        self.canvas.cue_double_clicked.connect(self.cue_double_clicked)
        self.canvas.playhead_moved.connect(self.playhead_moved)
        self.canvas.cue_moved.connect(self.cue_moved)
        self.canvas.cue_resized.connect(self.cue_resized)
    
    def set_cues(self, cues: List[Cue]) -> None:
        """Set cues to display."""
        self.canvas.set_cues(cues)
    
    def set_selected_cue(self, cue_id: Optional[int]) -> None:
        """Set selected cue."""
        self.canvas.set_selected_cue(cue_id)
    
    def set_playhead_position(self, position_ms: int) -> None:
        """Set playhead position."""
        self.canvas.set_playhead_position(position_ms)
    
    def _on_zoom_changed(self, value: int) -> None:
        """Handle zoom slider change."""
        self.canvas.set_zoom(float(value))
    
    def _zoom_in(self) -> None:
        """Zoom in."""
        current = self.zoom_slider.value()
        self.zoom_slider.setValue(min(500, int(current * 1.2)))
    
    def _zoom_out(self) -> None:
        """Zoom out."""
        current = self.zoom_slider.value()
        self.zoom_slider.setValue(max(10, int(current / 1.2)))
    
    def _fit_to_view(self) -> None:
        """Fit timeline to view."""
        if not self.canvas._cues:
            return

        # Calculate zoom to fit all cues
        total_duration_sec = self.canvas._total_duration_ms / 1000
        if total_duration_sec > 0:
            available_width = self.scroll_area.viewport().width() - 20

            new_zoom = available_width / total_duration_sec
            new_zoom = max(10, min(500, new_zoom))
            self.zoom_slider.setValue(int(new_zoom))
