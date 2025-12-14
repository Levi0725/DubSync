"""
DubSync Cue List Widget

Cue lista megjelenítése és kezelése.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit, QComboBox, QLabel,
    QPushButton, QMenu
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QColor, QBrush, QAction

from dubsync.models.cue import Cue
from dubsync.utils.constants import (
    CueStatus, LipSyncStatus,
    COLOR_LIPSYNC_GOOD, COLOR_LIPSYNC_WARNING, COLOR_LIPSYNC_TOO_LONG,
    COLOR_STATUS_NEW, COLOR_STATUS_TRANSLATED, COLOR_STATUS_NEEDS_REVISION, COLOR_STATUS_APPROVED,
    LIPSYNC_THRESHOLD_GOOD, LIPSYNC_THRESHOLD_WARNING
)
from dubsync.utils.time_utils import ms_to_timecode


class CueListWidget(QWidget):
    """
    Cue lista widget.
    
    Táblázatos megjelenítés időkóddal, karakterrel, státusszal, lip-sync jelzővel.
    """
    
    # Signals
    cue_selected = Signal(int)  # cue_id
    cue_double_clicked = Signal(int)  # cue_id
    insert_cue_requested = Signal(int)  # after_index
    delete_cue_requested = Signal(int)  # cue_id
    
    # Column indices
    COL_INDEX = 0
    COL_TIME_IN = 1
    COL_TIME_OUT = 2
    COL_CHARACTER = 3
    COL_TEXT = 4
    COL_STATUS = 5
    COL_LIPSYNC = 6
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._cues: List[Cue] = []
        self._cue_id_map: dict = {}  # row -> cue_id
        self._highlighted_cue_id: Optional[int] = None
        self._delete_mode: bool = False
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """UI felépítése."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Filter bar
        filter_layout = QHBoxLayout()
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Keresés...")
        self.search_edit.setClearButtonEnabled(True)
        filter_layout.addWidget(self.search_edit)
        
        self.status_filter = QComboBox()
        self.status_filter.addItem("Minden státusz", None)
        self.status_filter.addItem("Új", CueStatus.NEW.value)
        self.status_filter.addItem("Fordítva", CueStatus.TRANSLATED.value)
        self.status_filter.addItem("Javítandó", CueStatus.NEEDS_REVISION.value)
        self.status_filter.addItem("Jóváhagyva", CueStatus.APPROVED.value)
        filter_layout.addWidget(self.status_filter)
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "#", "Kezdés", "Vége", "Karakter", "Szöveg", "Státusz", "LS"
        ])
        
        # Table settings
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        
        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(self.COL_INDEX, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TIME_IN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TIME_OUT, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_CHARACTER, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_TEXT, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_STATUS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(self.COL_LIPSYNC, QHeaderView.ResizeMode.Fixed)
        
        self.table.setColumnWidth(self.COL_INDEX, 40)
        self.table.setColumnWidth(self.COL_TIME_IN, 90)
        self.table.setColumnWidth(self.COL_TIME_OUT, 90)
        self.table.setColumnWidth(self.COL_CHARACTER, 100)
        self.table.setColumnWidth(self.COL_STATUS, 80)
        self.table.setColumnWidth(self.COL_LIPSYNC, 30)
        
        layout.addWidget(self.table)
        
        # Info bar
        self.info_label = QLabel("")
        layout.addWidget(self.info_label)
    
    def _connect_signals(self):
        """Signal kapcsolatok."""
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_double_clicked)
        self.search_edit.textChanged.connect(self._apply_filter)
        self.status_filter.currentIndexChanged.connect(self._apply_filter)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
    
    def set_cues(self, cues: List[Cue]):
        """
        Cue lista beállítása.
        
        Args:
            cues: Cue objektumok listája
        """
        self._cues = cues
        self._refresh_table()
    
    def _refresh_table(self):
        """Táblázat frissítése."""
        self.table.setRowCount(0)
        self._cue_id_map.clear()
        
        search_text = self.search_edit.text().lower()
        status_filter = self.status_filter.currentData()
        
        filtered_cues = []
        for cue in self._cues:
            # Status filter
            if status_filter is not None and cue.status.value != status_filter:
                continue
            
            # Text search
            if search_text:
                searchable = (
                    cue.source_text.lower() +
                    cue.translated_text.lower() +
                    cue.character_name.lower()
                )
                if search_text not in searchable:
                    continue
            
            filtered_cues.append(cue)
        
        self.table.setRowCount(len(filtered_cues))
        
        for row, cue in enumerate(filtered_cues):
            self._cue_id_map[row] = cue.id
            self._populate_row(row, cue)
        
        self.info_label.setText(
            f"{len(filtered_cues)} / {len(self._cues)} cue"
        )
    
    def _populate_row(self, row: int, cue: Cue):
        """Sor feltöltése cue adatokkal."""
        # Index
        item = QTableWidgetItem(str(cue.cue_index))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, self.COL_INDEX, item)
        
        # Time in
        item = QTableWidgetItem(ms_to_timecode(cue.time_in_ms)[:8])
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, self.COL_TIME_IN, item)
        
        # Time out
        item = QTableWidgetItem(ms_to_timecode(cue.time_out_ms)[:8])
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, self.COL_TIME_OUT, item)
        
        # Character
        item = QTableWidgetItem(cue.character_name or "-")
        self.table.setItem(row, self.COL_CHARACTER, item)
        
        # Text (show translated if available, else source)
        text = cue.translated_text if cue.translated_text else cue.source_text
        # Truncate long text
        if len(text) > 50:
            text = text[:47] + "..."
        text = text.replace("\n", " ")
        item = QTableWidgetItem(text)
        if not cue.translated_text:
            item.setForeground(QBrush(QColor("#999999")))
        self.table.setItem(row, self.COL_TEXT, item)
        
        # Status
        status_text, status_color = self._get_status_display(cue.status)
        item = QTableWidgetItem(status_text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setBackground(QBrush(QColor(status_color)))
        item.setForeground(QBrush(QColor("#FFFFFF")))
        self.table.setItem(row, self.COL_STATUS, item)
        
        # Lip-sync indicator
        ls_text, ls_color = self._get_lipsync_display(cue)
        item = QTableWidgetItem(ls_text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setBackground(QBrush(QColor(ls_color)))
        self.table.setItem(row, self.COL_LIPSYNC, item)
    
    def _get_status_display(self, status: CueStatus) -> tuple:
        """Státusz megjelenítési adatok."""
        status_map = {
            CueStatus.NEW: ("Új", COLOR_STATUS_NEW),
            CueStatus.TRANSLATED: ("Kész", COLOR_STATUS_TRANSLATED),
            CueStatus.NEEDS_REVISION: ("Javít", COLOR_STATUS_NEEDS_REVISION),
            CueStatus.APPROVED: ("OK", COLOR_STATUS_APPROVED),
        }
        return status_map.get(status, ("?", "#999999"))
    
    def _get_lipsync_display(self, cue: Cue) -> tuple:
        """Lip-sync megjelenítési adatok."""
        if cue.lip_sync_ratio is None:
            return ("?", "#CCCCCC")
        
        if cue.lip_sync_ratio <= LIPSYNC_THRESHOLD_GOOD:
            return ("✓", COLOR_LIPSYNC_GOOD)
        elif cue.lip_sync_ratio <= LIPSYNC_THRESHOLD_WARNING:
            return ("!", COLOR_LIPSYNC_WARNING)
        else:
            return ("✗", COLOR_LIPSYNC_TOO_LONG)
    
    @Slot()
    def _apply_filter(self):
        """Szűrő alkalmazása."""
        self._refresh_table()
    
    @Slot()
    def _on_selection_changed(self):
        """Kijelölés változott."""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            cue_id = self._cue_id_map.get(row)
            if cue_id:
                self.cue_selected.emit(cue_id)
    
    @Slot(QTableWidgetItem)
    def _on_double_clicked(self, item: QTableWidgetItem):
        """Dupla kattintás."""
        row = item.row()
        cue_id = self._cue_id_map.get(row)
        if cue_id:
            self.cue_double_clicked.emit(cue_id)
    
    def get_current_index(self) -> int:
        """
        Jelenlegi cue index lekérése.
        
        Returns:
            Cue index vagy 0
        """
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            cue_id = self._cue_id_map.get(row)
            for cue in self._cues:
                if cue.id == cue_id:
                    return cue.cue_index
        return 0
    
    def select_cue(self, cue_id: int):
        """
        Cue kiválasztása azonosító alapján.
        
        Args:
            cue_id: Cue azonosító
        """
        for row, mapped_id in self._cue_id_map.items():
            if mapped_id == cue_id:
                self.table.selectRow(row)
                self.table.scrollToItem(self.table.item(row, 0))
                break
    
    def highlight_cue(self, cue_id: int):
        """
        Cue kiemelése (videó pozíció alapján).
        
        Args:
            cue_id: Cue azonosító
        """
        # Remove previous highlight
        if self._highlighted_cue_id:
            for row, mapped_id in self._cue_id_map.items():
                if mapped_id == self._highlighted_cue_id:
                    # Reset background
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item and col not in (self.COL_STATUS, self.COL_LIPSYNC):
                            item.setBackground(QBrush())
                    break
        
        # Set new highlight
        self._highlighted_cue_id = cue_id
        for row, mapped_id in self._cue_id_map.items():
            if mapped_id == cue_id:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and col not in (self.COL_STATUS, self.COL_LIPSYNC):
                        item.setBackground(QBrush(QColor("#FFFACD")))  # Light yellow
                break
    
    def set_delete_mode(self, enabled: bool):
        """
        Törlés mód beállítása.
        
        Args:
            enabled: Mód engedélyezve
        """
        self._delete_mode = enabled
        
        if enabled:
            self.table.setStyleSheet("""
                QTableWidget::item:selected {
                    background-color: #ffcccc;
                    color: #cc0000;
                }
            """)
        else:
            self.table.setStyleSheet("")
    
    def get_selected_cue_id(self) -> Optional[int]:
        """
        Kijelölt cue azonosító lekérése.
        
        Returns:
            Cue azonosító vagy None
        """
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            return self._cue_id_map.get(row)
        return None
    
    @Slot()
    def _on_context_menu(self, pos):
        """Kontextus menü megjelenítése."""
        item = self.table.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        insert_action = QAction("➕ Sor beszúrása ide", self)
        insert_action.triggered.connect(lambda: self._request_insert(item.row()))
        menu.addAction(insert_action)
        
        if self._delete_mode:
            delete_action = QAction("🗑️ Sor törlése", self)
            delete_action.triggered.connect(lambda: self._request_delete(item.row()))
            menu.addAction(delete_action)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))
    
    def _request_insert(self, row: int):
        """Beszúrás kérése."""
        cue_id = self._cue_id_map.get(row)
        if cue_id:
            for cue in self._cues:
                if cue.id == cue_id:
                    self.insert_cue_requested.emit(cue.cue_index)
                    break
    
    def _request_delete(self, row: int):
        """Törlés kérése."""
        cue_id = self._cue_id_map.get(row)
        if cue_id:
            self.delete_cue_requested.emit(cue_id)
