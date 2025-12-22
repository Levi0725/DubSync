"""
DubSync Basic QA Plugin

Alapvető minőségellenőrzési szabályok a fordítások ellenőrzéséhez.
Extended with CPS (characters per second), overlap, and minimum duration checks.
"""

from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem, QGroupBox, QDockWidget,
    QHeaderView, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QColor

from dubsync.plugins.base import (
    QAPlugin, UIPlugin, QAIssue, PluginInfo, PluginType
)
from dubsync.models.project import Project
from dubsync.models.cue import Cue
from dubsync.utils.constants import LIPSYNC_THRESHOLD_WARNING
from dubsync.i18n import t


# Default QA thresholds
DEFAULT_MAX_CPS = 20.0  # Characters per second
DEFAULT_MIN_CPS = 5.0   # Minimum CPS (too slow to read)
DEFAULT_MIN_DURATION_MS = 500  # Minimum cue duration
DEFAULT_MAX_DURATION_MS = 10000  # Maximum cue duration (10 seconds)


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
        header = QLabel(t("plugins.basic_qa.header"))
        header.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(header)
        
        # Összesítő
        self.summary_label = QLabel(t("plugins.basic_qa.no_check"))
        self.summary_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.summary_label)
        
        # Eredmények fa
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels([
            t("plugins.basic_qa.columns.index"),
            t("plugins.basic_qa.columns.issue"),
            t("plugins.basic_qa.columns.suggestion")
        ])
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
        
        self.run_btn = QPushButton(t("plugins.basic_qa.run"))
        self.run_btn.clicked.connect(self._run_check)
        btn_layout.addWidget(self.run_btn)
        
        self.clear_btn = QPushButton(t("plugins.basic_qa.clear"))
        self.clear_btn.clicked.connect(self._clear_results)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
    
    def _run_check(self):
        """QA ellenőrzés futtatása."""
        if not self.plugin._main_window:
            return
        
        pm = getattr(self.plugin._main_window, 'project_manager', None)
        if not pm or not pm.is_open:
            self.summary_label.setText(t("plugins.basic_qa.no_project"))
            return
        
        project = pm.project
        cues = pm.get_cues()
        
        self._issues = self.plugin.check(project, cues)
        self._display_results()
    
    def _display_results(self):
        """Eredmények megjelenítése."""
        self.results_tree.clear()

        errors = sum(i.severity == "error" for i in self._issues)
        warnings = sum(i.severity == "warning" for i in self._issues)
        infos = sum(i.severity == "info" for i in self._issues)

        if not self._issues:
            self.summary_label.setText(t("plugins.basic_qa.no_issues"))
            self.summary_label.setStyleSheet("color: #4CAF50; font-size: 11px;")
            return

        self.summary_label.setText(
            f"🔴 {errors} {t('plugins.basic_qa.errors')} │ 🟡 {warnings} {t('plugins.basic_qa.warnings')} │ 🔵 {infos} info"
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
        self.summary_label.setText(t("plugins.basic_qa.no_check"))
        self.summary_label.setStyleSheet("color: #888; font-size: 11px;")
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Hibára ugrás dupla kattintáskor."""
        if cue_id := item.data(0, Qt.ItemDataRole.UserRole):
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
    - CPS (characters per second) - too fast / too slow
    - Overlap between consecutive cues
    - Minimum/Maximum duration
    """
    
    def __init__(self):
        super().__init__()
        self._dock: Optional[QDockWidget] = None
        self._widget: Optional[QAResultsWidget] = None
        # QA settings with defaults
        self._settings: Dict[str, Any] = {
            "check_cps": True,
            "max_cps": DEFAULT_MAX_CPS,
            "min_cps": DEFAULT_MIN_CPS,
            "check_overlap": True,
            "check_duration": True,
            "min_duration_ms": DEFAULT_MIN_DURATION_MS,
            "max_duration_ms": DEFAULT_MAX_DURATION_MS,
            "check_lipsync": True,
            "check_missing_translation": True,
            "check_double_space": True,
            "check_missing_character": True,
            "check_whitespace": True,
        }
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            id="basic_qa",
            name=t("plugins.basic_qa.name"),
            version="2.0.0",
            author="Levente Kulacsy",
            description=t("plugins.basic_qa.description"),
            plugin_type=PluginType.QA,
            icon="",
            readme_path="README.md"
        )
    
    def load_settings(self, settings: Dict[str, Any]) -> None:
        """Load plugin settings."""
        self._settings.update(settings)
    
    def save_settings(self) -> Dict[str, Any]:
        """Save plugin settings."""
        return self._settings.copy()
    
    def get_settings_widget(self) -> Optional[QWidget]:
        """Get settings widget."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # CPS settings
        cps_group = QGroupBox(t("plugins.basic_qa.settings.cps_group"))
        cps_layout = QFormLayout(cps_group)
        
        self.check_cps_cb = QCheckBox()
        self.check_cps_cb.setChecked(self._settings["check_cps"])
        cps_layout.addRow(t("plugins.basic_qa.settings.check_cps"), self.check_cps_cb)
        
        self.max_cps_spin = QDoubleSpinBox()
        self.max_cps_spin.setRange(10, 40)
        self.max_cps_spin.setValue(self._settings["max_cps"])
        self.max_cps_spin.setSuffix(" CPS")
        cps_layout.addRow(t("plugins.basic_qa.settings.max_cps"), self.max_cps_spin)
        
        self.min_cps_spin = QDoubleSpinBox()
        self.min_cps_spin.setRange(1, 15)
        self.min_cps_spin.setValue(self._settings["min_cps"])
        self.min_cps_spin.setSuffix(" CPS")
        cps_layout.addRow(t("plugins.basic_qa.settings.min_cps"), self.min_cps_spin)
        
        layout.addWidget(cps_group)
        
        # Duration settings
        duration_group = QGroupBox(t("plugins.basic_qa.settings.duration_group"))
        duration_layout = QFormLayout(duration_group)
        
        self.check_duration_cb = QCheckBox()
        self.check_duration_cb.setChecked(self._settings["check_duration"])
        duration_layout.addRow(t("plugins.basic_qa.settings.check_duration"), self.check_duration_cb)
        
        self.min_duration_spin = QSpinBox()
        self.min_duration_spin.setRange(100, 2000)
        self.min_duration_spin.setValue(self._settings["min_duration_ms"])
        self.min_duration_spin.setSuffix(" ms")
        duration_layout.addRow(t("plugins.basic_qa.settings.min_duration"), self.min_duration_spin)
        
        self.max_duration_spin = QSpinBox()
        self.max_duration_spin.setRange(3000, 30000)
        self.max_duration_spin.setValue(self._settings["max_duration_ms"])
        self.max_duration_spin.setSuffix(" ms")
        duration_layout.addRow(t("plugins.basic_qa.settings.max_duration"), self.max_duration_spin)
        
        layout.addWidget(duration_group)
        
        # Overlap settings
        overlap_group = QGroupBox(t("plugins.basic_qa.settings.overlap_group"))
        overlap_layout = QFormLayout(overlap_group)
        
        self.check_overlap_cb = QCheckBox()
        self.check_overlap_cb.setChecked(self._settings["check_overlap"])
        overlap_layout.addRow(t("plugins.basic_qa.settings.check_overlap"), self.check_overlap_cb)
        
        layout.addWidget(overlap_group)
        
        layout.addStretch()
        
        # Connect signals
        self.check_cps_cb.stateChanged.connect(self._save_settings_from_widget)
        self.max_cps_spin.valueChanged.connect(self._save_settings_from_widget)
        self.min_cps_spin.valueChanged.connect(self._save_settings_from_widget)
        self.check_duration_cb.stateChanged.connect(self._save_settings_from_widget)
        self.min_duration_spin.valueChanged.connect(self._save_settings_from_widget)
        self.max_duration_spin.valueChanged.connect(self._save_settings_from_widget)
        self.check_overlap_cb.stateChanged.connect(self._save_settings_from_widget)
        
        return widget
    
    def _save_settings_from_widget(self):
        """Save settings from widget values."""
        if hasattr(self, 'check_cps_cb'):
            self._settings["check_cps"] = self.check_cps_cb.isChecked()
            self._settings["max_cps"] = self.max_cps_spin.value()
            self._settings["min_cps"] = self.min_cps_spin.value()
            self._settings["check_duration"] = self.check_duration_cb.isChecked()
            self._settings["min_duration_ms"] = self.min_duration_spin.value()
            self._settings["max_duration_ms"] = self.max_duration_spin.value()
            self._settings["check_overlap"] = self.check_overlap_cb.isChecked()
    
    def check(self, project: Project, cues: List[Cue]) -> List[QAIssue]:
        """QA ellenőrzés végrehajtása."""
        issues = []
        
        # Sort cues by time for overlap detection
        sorted_cues = sorted(cues, key=lambda c: c.time_in_ms)
        
        for i, cue in enumerate(sorted_cues):
            duration_ms = cue.time_out_ms - cue.time_in_ms
            duration_s = duration_ms / 1000.0
            text = cue.translated_text or ""
            char_count = len(text.replace(" ", ""))  # Characters without spaces
            
            # ============================================
            # NEW: CPS (Characters Per Second) check
            # ============================================
            if self._settings["check_cps"] and text.strip() and duration_s > 0:
                cps = char_count / duration_s
                
                if cps > self._settings["max_cps"]:
                    issues.append(QAIssue(
                        cue_id=cue.id,
                        severity="error",
                        message=t("plugins.basic_qa.issues.cps_too_high", cps=f"{cps:.1f}"),
                        suggestion=t("plugins.basic_qa.issues.cps_too_high_suggestion", 
                                    max_cps=f"{self._settings['max_cps']:.1f}")
                    ))
                elif cps < self._settings["min_cps"] and char_count > 5:
                    issues.append(QAIssue(
                        cue_id=cue.id,
                        severity="info",
                        message=t("plugins.basic_qa.issues.cps_too_low", cps=f"{cps:.1f}"),
                        suggestion=t("plugins.basic_qa.issues.cps_too_low_suggestion")
                    ))
            
            # ============================================
            # NEW: Overlap detection
            # ============================================
            if self._settings["check_overlap"] and i > 0:
                prev_cue = sorted_cues[i - 1]
                if cue.time_in_ms < prev_cue.time_out_ms:
                    overlap_ms = prev_cue.time_out_ms - cue.time_in_ms
                    issues.append(QAIssue(
                        cue_id=cue.id,
                        severity="error",
                        message=t("plugins.basic_qa.issues.overlap", 
                                 overlap_ms=overlap_ms, prev_id=prev_cue.id),
                        suggestion=t("plugins.basic_qa.issues.overlap_suggestion")
                    ))
            
            # ============================================
            # NEW: Duration check (min/max)
            # ============================================
            if self._settings["check_duration"]:
                if duration_ms < self._settings["min_duration_ms"]:
                    issues.append(QAIssue(
                        cue_id=cue.id,
                        severity="warning",
                        message=t("plugins.basic_qa.issues.duration_too_short", 
                                 duration_ms=duration_ms),
                        suggestion=t("plugins.basic_qa.issues.duration_too_short_suggestion",
                                    min_ms=self._settings["min_duration_ms"])
                    ))
                elif duration_ms > self._settings["max_duration_ms"]:
                    issues.append(QAIssue(
                        cue_id=cue.id,
                        severity="warning",
                        message=t("plugins.basic_qa.issues.duration_too_long",
                                 duration_ms=duration_ms),
                        suggestion=t("plugins.basic_qa.issues.duration_too_long_suggestion")
                    ))
            
            # ============================================
            # Existing checks
            # ============================================
            
            # Hiányzó fordítás
            if self._settings.get("check_missing_translation", True) and (not text or not text.strip()):
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="warning",
                    message=t("plugins.basic_qa.issues.missing_translation"),
                    suggestion=t("plugins.basic_qa.issues.missing_translation_suggestion")
                ))
            
            # Lip-sync hiba
            if self._settings.get("check_lipsync", True) and (cue.lip_sync_ratio and cue.lip_sync_ratio > LIPSYNC_THRESHOLD_WARNING):
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="error",
                    message=t("plugins.basic_qa.issues.lipsync_too_long", ratio=f"{cue.lip_sync_ratio:.0%}"),
                    suggestion=t("plugins.basic_qa.issues.lipsync_suggestion")
                ))
            # Dupla szóközök
            if self._settings.get("check_double_space", True) and "  " in text:
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="info",
                    message=t("plugins.basic_qa.issues.double_space"),
                    suggestion=t("plugins.basic_qa.issues.double_space_suggestion")
                ))
            
            # Hiányzó karakter név
            if self._settings.get("check_missing_character", True) and (text and not cue.character_name):
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="info",
                    message=t("plugins.basic_qa.issues.missing_character"),
                    suggestion=t("plugins.basic_qa.issues.missing_character_suggestion")
                ))
            
            # Felesleges whitespace
            if self._settings.get("check_whitespace", True) and (text and (text != text.strip())):
                issues.append(QAIssue(
                    cue_id=cue.id,
                    severity="info",
                    message=t("plugins.basic_qa.issues.extra_whitespace"),
                    suggestion=t("plugins.basic_qa.issues.extra_whitespace_suggestion")
                ))
        
        return issues
    
    # UIPlugin interfész
    
    def create_dock_widget(self) -> Optional[QDockWidget]:
        """QA dock widget létrehozása."""
        self._dock = QDockWidget(t("plugins.basic_qa.header"), self._main_window)
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
        # Panel toggle
        toggle_action = QAction(t("plugins.basic_qa.panel"), self._main_window)
        toggle_action.setCheckable(True)
        toggle_action.setChecked(True)
        toggle_action.triggered.connect(self._toggle_dock)
        actions = [toggle_action]
        # Ellenőrzés futtatása
        run_action = QAction(t("plugins.basic_qa.run_qa"), self._main_window)
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
            cue_list = getattr(self._main_window, 'cue_list', None)
            if cue_list and hasattr(cue_list, 'select_by_cue_id'):
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
