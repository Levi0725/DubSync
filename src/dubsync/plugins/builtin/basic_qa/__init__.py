"""
DubSync Basic QA Plugin

Alapvető minőségellenőrzési szabályok a fordítások ellenőrzéséhez.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QGroupBox, QDockWidget,
    QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor

from dubsync.plugins.base import (
    QAPlugin, UIPlugin, QAIssue, PluginInfo, PluginType
)
from dubsync.models.project import Project
from dubsync.models.cue import Cue
from dubsync.utils.constants import LIPSYNC_THRESHOLD_WARNING


class QAResultsWidget(QWidget):
    """QA eredmények megjelenítő widget."""
    
    # Signal: cue_id amikor egy hibára kattintanak
    issue_selected = Signal(int)
    
    def __init__(self, plugin: 'BasicQAPlugin', parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self._issues: List[QAIssue] = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("🔍 QA Ellenőrzés")
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)
        
        # Összesítő
        self.summary_label = QLabel("Nincs ellenőrzés futtatva")
        self.summary_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.summary_label)
        
        # Eredmények fa
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["#", "Probléma", "Javaslat"])
        self.results_tree.setRootIsDecorated(False)
        self.results_tree.setAlternatingRowColors(True)
        self.results_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        header_view = self.results_tree.header()
        header_view.setStretchLastSection(True)
        header_view.resizeSection(0, 50)
        header_view.resizeSection(1, 200)
        
        layout.addWidget(self.results_tree)
        
        # Gombok
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("▶️ Ellenőrzés futtatása")
        self.run_btn.clicked.connect(self._run_check)
        btn_layout.addWidget(self.run_btn)
        
        self.clear_btn = QPushButton("🗑️ Törlés")
        self.clear_btn.clicked.connect(self._clear_results)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
    
    def _run_check(self):
        """QA ellenőrzés futtatása."""
        if not self.plugin._main_window:
            return
        
        pm = self.plugin._main_window.project_manager
        if not pm.is_open:
            self.summary_label.setText("⚠️ Nincs megnyitott projekt")
            return
        
        project = pm.project
        cues = pm.get_cues()
        
        self._issues = self.plugin.check(project, cues)
        self._display_results()
    
    def _display_results(self):
        """Eredmények megjelenítése."""
        self.results_tree.clear()
        
        errors = sum(1 for i in self._issues if i.severity == "error")
        warnings = sum(1 for i in self._issues if i.severity == "warning")
        infos = sum(1 for i in self._issues if i.severity == "info")
        
        if not self._issues:
            self.summary_label.setText("✅ Nincs probléma!")
            self.summary_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            return
        
        self.summary_label.setText(
            f"🔴 {errors} hiba │ 🟡 {warnings} figyelmeztetés │ 🔵 {infos} info"
        )
        self.summary_label.setStyleSheet("color: #fff; font-size: 11px;")
        
        # Severity színek
        colors = {
            "error": QColor("#f44336"),
            "warning": QColor("#ff9800"),
            "info": QColor("#2196F3"),
        }
        
        for issue in self._issues:
            item = QTreeWidgetItem([
                str(issue.cue_id) if issue.cue_id else "-",
                issue.message,
                issue.suggestion or ""
            ])
            
            color = colors.get(issue.severity, QColor("#888"))
            item.setForeground(0, color)
            item.setForeground(1, color)
            
            item.setData(0, Qt.ItemDataRole.UserRole, issue.cue_id)
            
            self.results_tree.addTopLevelItem(item)
    
    def _clear_results(self):
        """Eredmények törlése."""
        self._issues = []
        self.results_tree.clear()
        self.summary_label.setText("Nincs ellenőrzés futtatva")
        self.summary_label.setStyleSheet("color: #888; font-size: 11px;")
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Hibára ugrás dupla kattintáskor."""
        cue_id = item.data(0, Qt.ItemDataRole.UserRole)
        if cue_id:
            self.issue_selected.emit(cue_id)


class BasicQAPlugin(QAPlugin, UIPlugin):
    """
    Alapvető QA plugin UI-val.
    
    Ellenőrzi:
    - Fordítatlan cue-k
    - Túl hosszú lip-sync
    - Üres karakter nevek
    - Dupla szóközök
    - Felesleges whitespace
    """
    
    def __init__(self):
        super().__init__()
        self._dock: Optional[QDockWidget] = None
        self._widget: Optional[QAResultsWidget] = None
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="builtin.qa.basic",
            name="Alapvető QA",
            version="1.1.0",
            author="Levente Kulacsy",
            description="Alapvető minőségellenőrzési szabályok",
            plugin_type=PluginType.QA,
            icon="🔍",
            readme_path="README.md"
        )
    
    def check(self, project: Project, cues: List[Cue]) -> List[QAIssue]:
        """QA ellenőrzés végrehajtása."""
        issues = []
        
        for cue in cues:
            # Hiányzó fordítás
            if not cue.translated_text or not cue.translated_text.strip():
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="warning",
                    message="Hiányzó fordítás",
                    suggestion="Adjon meg fordítást a cue-hoz"
                ))
            
            # Lip-sync hiba
            if cue.lip_sync_ratio and cue.lip_sync_ratio > LIPSYNC_THRESHOLD_WARNING:
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="error",
                    message=f"Túl hosszú szöveg (lip-sync: {cue.lip_sync_ratio:.0%})",
                    suggestion="Rövidítse a fordítást"
                ))
            
            text = cue.translated_text or ""
            
            # Dupla szóközök
            if "  " in text:
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="info",
                    message="Dupla szóköz a szövegben",
                    suggestion="Távolítsa el a dupla szóközöket"
                ))
            
            # Hiányzó karakter név
            if text and not cue.character_name:
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="info",
                    message="Hiányzó karakter név",
                    suggestion="Adja meg a beszélő karakter nevét"
                ))
            
            # Felesleges whitespace
            if text and (text != text.strip()):
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="info",
                    message="Felesleges szóköz a szöveg elején/végén",
                    suggestion="Távolítsa el a felesleges szóközöket"
                ))
        
        return issues
    
    # UIPlugin interfész
    
    def create_dock_widget(self) -> Optional[QDockWidget]:
        """QA dock widget létrehozása."""
        self._dock = QDockWidget("🔍 QA Ellenőrzés", self._main_window)
        self._dock.setObjectName("qaCheckDock")
        self._dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        
        self._widget = QAResultsWidget(self)
        self._widget.issue_selected.connect(self._on_issue_selected)
        self._dock.setWidget(self._widget)
        
        return self._dock
    
    def create_menu_items(self) -> List[QAction]:
        """Menü elemek létrehozása."""
        actions = []
        
        # Panel toggle
        toggle_action = QAction("🔍 QA Panel", self._main_window)
        toggle_action.setCheckable(True)
        toggle_action.setChecked(True)
        toggle_action.triggered.connect(self._toggle_dock)
        actions.append(toggle_action)
        
        # Ellenőrzés futtatása
        run_action = QAction("▶️ QA Ellenőrzés futtatása", self._main_window)
        run_action.setShortcut("F7")
        run_action.triggered.connect(self._run_check_from_menu)
        actions.append(run_action)
        
        return actions
    
    def _toggle_dock(self, checked: bool):
        """Dock megjelenítése/elrejtése."""
        if self._dock:
            self._dock.setVisible(checked)
    
    def _run_check_from_menu(self):
        """Ellenőrzés futtatása menüből."""
        if self._widget:
            self._widget._run_check()
    
    def _on_issue_selected(self, cue_id: int):
        """Hibára ugrás."""
        if self._main_window:
            # Cue lista pozícionálása
            cue_list = self._main_window.cue_list
            if hasattr(cue_list, 'select_by_cue_id'):
                cue_list.select_by_cue_id(cue_id)
    
    def get_long_description(self) -> str:
        """README tartalom."""
        from pathlib import Path
        readme_path = Path(__file__).parent / "README.md"
        if readme_path.exists():
            return readme_path.read_text(encoding='utf-8')
        return self.info.description


# Plugin export
Plugin = BasicQAPlugin
