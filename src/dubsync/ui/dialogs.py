"""
DubSync Dialogs

Dialog windows.
"""

from typing import Optional, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDoubleSpinBox, QDialogButtonBox,
    QLabel, QPushButton, QGroupBox, QTextBrowser,
    QSpinBox, QCheckBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from dubsync.models.project import Project
from dubsync.utils.constants import APP_NAME, APP_VERSION
from dubsync.i18n import t


class ProjectSettingsDialog(QDialog):
    """
    Project settings dialog.
    """
    
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        
        self.project = project
        self.setWindowTitle(t("dialogs.project_settings.title"))
        self.setMinimumWidth(450)
        
        self._setup_ui()
        self._load_values()
    
    def _setup_ui(self):
        """Setup UI."""
        layout = QVBoxLayout(self)

        # Form
        form = QFormLayout()

        self.title_edit = self._extracted_from__setup_ui_8(
            "dialogs.project_settings.project_title_placeholder",
            form,
            "dialogs.project_settings.project_title",
        )
        self.series_edit = self._extracted_from__setup_ui_8(
            "dialogs.project_settings.series_placeholder",
            form,
            "dialogs.project_settings.series",
        )
        # Season/Episode row
        season_layout = QHBoxLayout()
        self.season_edit = self._extracted_from__setup_ui_18(
            season_layout, "dialogs.project_settings.season"
        )
        self.episode_edit = self._extracted_from__setup_ui_18(
            season_layout, "dialogs.project_settings.episode"
        )
        season_layout.addStretch()

        form.addRow(f"{t('dialogs.project_settings.season')}/{t('dialogs.project_settings.episode')}:", season_layout)

        self.episode_title_edit = self._extracted_from__setup_ui_8(
            "dialogs.project_settings.episode_title_placeholder",
            form,
            "dialogs.project_settings.episode_title",
        )
        form.addRow("", QLabel(""))  # Spacer

        self.translator_edit = self._extracted_from__setup_ui_8(
            "dialogs.project_settings.translator_placeholder",
            form,
            "dialogs.project_settings.translator",
        )
        self.editor_edit = self._extracted_from__setup_ui_8(
            "dialogs.project_settings.editor_placeholder",
            form,
            "dialogs.project_settings.editor",
        )
        form.addRow("", QLabel(""))  # Spacer

        # Technical settings
        tech_group = QGroupBox(t("dialogs.project_settings.technical"))
        tech_layout = QFormLayout(tech_group)

        self.framerate_spin = QDoubleSpinBox()
        self.framerate_spin.setRange(1.0, 120.0)
        self.framerate_spin.setValue(25.0)
        self.framerate_spin.setDecimals(3)
        self.framerate_spin.setSuffix(" fps")
        tech_layout.addRow(t("dialogs.project_settings.framerate"), self.framerate_spin)

        layout.addLayout(form)
        layout.addWidget(tech_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_18(self, season_layout, arg1):
        result = QLineEdit()
        result.setPlaceholderText("1")
        result.setMaximumWidth(60)
        season_layout.addWidget(result)
        season_layout.addWidget(QLabel(t(arg1)))

        return result

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_8(self, arg0, form, arg2):
        result = QLineEdit()
        result.setPlaceholderText(t(arg0))
        form.addRow(t(arg2), result)

        return result
    
    def _load_values(self):
        """Load values from the project."""
        self.title_edit.setText(self.project.title)
        self.series_edit.setText(self.project.series_title)
        self.season_edit.setText(self.project.season)
        self.episode_edit.setText(self.project.episode)
        self.episode_title_edit.setText(self.project.episode_title)
        self.translator_edit.setText(self.project.translator)
        self.editor_edit.setText(self.project.editor)
        self.framerate_spin.setValue(self.project.frame_rate)


class AboutDialog(QDialog):
    """
    About dialog.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(t("dialogs.about.title", app_name=APP_NAME))
        self.setFixedSize(400, 300)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        title = QLabel(f"<h1>{APP_NAME}</h1>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Version
        version = QLabel(f"<p>{t('dialogs.about.version', version=APP_VERSION)}</p>")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        # Description
        desc = QLabel(
            f"<p>{t('dialogs.about.description')}</p>"
            f"<p>{t('dialogs.about.for_whom')}</p>"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # Features
        features = QLabel(
            f"<p><b>{t('dialogs.about.features_title')}</b></p>"
            "<ul>"
            f"<li>{t('dialogs.about.features.srt')}</li>"
            f"<li>{t('dialogs.about.features.video')}</li>"
            f"<li>{t('dialogs.about.features.comments')}</li>"
            f"<li>{t('dialogs.about.features.pdf')}</li>"
            f"<li>{t('dialogs.about.features.plugins')}</li>"
            "</ul>"
        )
        features.setWordWrap(True)
        layout.addWidget(features)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton(t("dialogs.about.close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ProgressDialog(QDialog):
    """
    Progress dialog for long operations.
    """
    
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(300, 100)
        
        layout = QVBoxLayout(self)
        
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)
        
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #666;")
        layout.addWidget(self.progress_label)
    
    def set_progress(self, current: int, total: int):
        """Update progress."""
        self.progress_label.setText(t("dialogs.progress.progress_format", current=current, total=total))
    
    def set_message(self, message: str):
        """Update message."""
        self.message_label.setText(message)


class TutorialDialog(QDialog):
    """
    Tutorial dialog - Application introduction.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(t("dialogs.tutorial.title", app_name=APP_NAME))
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"<h2>{t('dialogs.tutorial.welcome', app_name=APP_NAME)}</h2>")
        layout.addWidget(title)
        
        # Tutorial content
        content = QTextBrowser()
        content.setOpenExternalLinks(True)
        content.setHtml(self._get_tutorial_content())
        layout.addWidget(content)
        
        # Close button
        close_btn = QPushButton(t("dialogs.tutorial.understood"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _get_tutorial_content(self) -> str:
        """Generate tutorial content."""
        return """
        <style>
            h3 { color: #4CAF50; margin-top: 15px; }
            p { margin: 5px 0; }
            ul { margin: 5px 0; }
            .shortcut { background: #333; padding: 2px 6px; border-radius: 3px; }
        </style>
        
        <h3>📁 1. Projekt létrehozása</h3>
        <p>Kezdj egy új projektet a <span class="shortcut">Ctrl+N</span> billentyűkkel, vagy nyiss meg egy meglévőt a <span class="shortcut">Ctrl+O</span> kombinációval.</p>
        
        <h3>📥 2. SRT felirat importálása</h3>
        <p>Importálj egy SRT fájlt a <b>Fájl → Import → SRT felirat</b> menüpontból. Az időzítések és forrásszövegek automatikusan betöltődnek.</p>
        
        <h3>🎥 3. Videó hozzáadása</h3>
        <p>Adj hozzá videófájlt a <b>Fájl → Import → Videó</b> menüből. A videó segít a lip-sync ellenőrzésben.</p>
        
        <h3>✏️ 4. Fordítás</h3>
        <p>Kattints egy sorra a bal oldali listában, majd írd be a fordítást a szerkesztőben. A lip-sync mutató jelzi, ha a szöveg túl hosszú.</p>
        <ul>
            <li><b>Zöld</b>: Megfelelő hosszúság</li>
            <li><b>Sárga</b>: Határértéken</li>
            <li><b>Piros</b>: Túl hosszú</li>
        </ul>
        
        <h3>💾 5. Mentés és navigáció</h3>
        <p>A sor mentése után <span class="shortcut">Ctrl+S</span> automatikusan a következő sorra ugrik.</p>
        <p>Gyors navigáció:</p>
        <ul>
            <li><span class="shortcut">Ctrl+E</span> - Következő fordítatlan sor</li>
            <li><span class="shortcut">Ctrl+L</span> - Következő lip-sync hiba</li>
        </ul>
        
        <h3>🔌 6. Pluginok</h3>
        <p>Engedélyezz pluginokat a <b>Beállítások → Pluginok</b> fülön:</p>
        <ul>
            <li><b>🌍 Fordító</b>: Argos Translate offline fordítás</li>
            <li><b>🔍 QA</b>: Minőségellenőrzés</li>
            <li><b>📊 CSV Export</b>: Táblázatkezelőkhöz</li>
        </ul>
        
        <h3>📤 7. Exportálás</h3>
        <p>Exportáld a kész munkát:</p>
        <ul>
            <li><b>PDF</b>: Professzionális szövegkönyv</li>
            <li><b>SRT</b>: Szinkronizált felirat</li>
            <li><b>CSV</b>: Táblázatos formátum</li>
        </ul>
        
        <h3>⌨️ Hasznos billentyűparancsok</h3>
        <table style="margin-left: 10px;">
            <tr><td><span class="shortcut">Ctrl+N</span></td><td>Új projekt</td></tr>
            <tr><td><span class="shortcut">Ctrl+O</span></td><td>Megnyitás</td></tr>
            <tr><td><span class="shortcut">Ctrl+S</span></td><td>Mentés</td></tr>
            <tr><td><span class="shortcut">Ctrl+,</span></td><td>Beállítások</td></tr>
            <tr><td><span class="shortcut">Ctrl+D</span></td><td>Törlés mód</td></tr>
            <tr><td><span class="shortcut">F11</span></td><td>Teljes képernyő</td></tr>
            <tr><td><span class="shortcut">F7</span></td><td>QA ellenőrzés</td></tr>
        </table>
        
        <h3>❓ Segítség</h3>
        <p>További információkért lásd a dokumentációt vagy a <b>Súgó → Névjegy</b> menüpontot.</p>
        """


class BatchTimingDialog(QDialog):
    """
    Batch timing adjustment dialog.
    
    Allows applying time offset to multiple cues at once.
    Supports ripple edit (moving all subsequent cues).
    """
    
    def __init__(self, cue_count: int, selected_count: int = 0, parent=None):
        """
        Initialize batch timing dialog.
        
        Args:
            cue_count: Total number of cues in project
            selected_count: Number of currently selected cues
            parent: Parent widget
        """
        super().__init__(parent)
        self.cue_count = cue_count
        self.selected_count = selected_count
        
        self.setWindowTitle(t("dialogs.batch_timing.title"))
        self.setMinimumWidth(400)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI elements."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # Description
        desc_label = QLabel(t("dialogs.batch_timing.description"))
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # Offset input
        offset_group = QGroupBox(t("dialogs.batch_timing.offset_group"))
        offset_layout = QFormLayout(offset_group)
        
        offset_row = QHBoxLayout()
        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-99999, 99999)
        self.offset_spin.setValue(0)
        self.offset_spin.setSuffix(" ms")
        self.offset_spin.setMinimumWidth(120)
        offset_row.addWidget(self.offset_spin)
        
        # Quick offset buttons
        quick_btns = QHBoxLayout()
        quick_btns.setSpacing(4)
        for offset in [-1000, -500, -100, 100, 500, 1000]:
            btn = QPushButton(f"{'+' if offset > 0 else ''}{offset}")
            btn.setMaximumWidth(50)
            btn.clicked.connect(lambda checked, o=offset: self.offset_spin.setValue(
                self.offset_spin.value() + o
            ))
            quick_btns.addWidget(btn)
        offset_row.addLayout(quick_btns)
        
        offset_layout.addRow(t("dialogs.batch_timing.offset"), offset_row)
        layout.addWidget(offset_group)
        
        # Scope selection
        scope_group = QGroupBox(t("dialogs.batch_timing.scope_group"))
        scope_layout = QVBoxLayout(scope_group)
        
        self.scope_group = QButtonGroup(self)
        
        self.all_cues_radio = QRadioButton(
            t("dialogs.batch_timing.all_cues", count=self.cue_count)
        )
        self.all_cues_radio.setChecked(True)
        self.scope_group.addButton(self.all_cues_radio, 0)
        scope_layout.addWidget(self.all_cues_radio)
        
        self.selected_cues_radio = QRadioButton(
            t("dialogs.batch_timing.selected_cues", count=self.selected_count)
        )
        self.selected_cues_radio.setEnabled(self.selected_count > 0)
        self.scope_group.addButton(self.selected_cues_radio, 1)
        scope_layout.addWidget(self.selected_cues_radio)
        
        self.from_current_radio = QRadioButton(
            t("dialogs.batch_timing.from_current")
        )
        self.scope_group.addButton(self.from_current_radio, 2)
        scope_layout.addWidget(self.from_current_radio)
        
        layout.addWidget(scope_group)
        
        # Ripple edit option
        ripple_group = QGroupBox(t("dialogs.batch_timing.ripple_group"))
        ripple_layout = QVBoxLayout(ripple_group)
        
        self.ripple_check = QCheckBox(t("dialogs.batch_timing.ripple_edit"))
        self.ripple_check.setChecked(False)
        ripple_layout.addWidget(self.ripple_check)
        
        ripple_desc = QLabel(t("dialogs.batch_timing.ripple_description"))
        ripple_desc.setWordWrap(True)
        ripple_desc.setStyleSheet("color: #888; font-size: 10px; margin-left: 20px;")
        ripple_layout.addWidget(ripple_desc)
        
        layout.addWidget(ripple_group)
        
        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet(
            "background: #2a2a2a; padding: 8px; border-radius: 4px; color: #4CAF50;"
        )
        self._update_preview()
        layout.addWidget(self.preview_label)
        
        # Connect signals for preview update
        self.offset_spin.valueChanged.connect(self._update_preview)
        self.scope_group.buttonClicked.connect(self._update_preview)
        self.ripple_check.stateChanged.connect(self._update_preview)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _update_preview(self):
        """Update preview text."""
        offset = self.offset_spin.value()
        scope_id = self.scope_group.checkedId()
        ripple = self.ripple_check.isChecked()
        
        if offset == 0:
            self.preview_label.setText(t("dialogs.batch_timing.preview_no_change"))
            return
        
        direction = t("dialogs.batch_timing.later") if offset > 0 else t("dialogs.batch_timing.earlier")
        
        if scope_id == 0:  # All cues
            scope_text = t("dialogs.batch_timing.preview_all")
        elif scope_id == 1:  # Selected
            scope_text = t("dialogs.batch_timing.preview_selected", count=self.selected_count)
        else:  # From current
            scope_text = t("dialogs.batch_timing.preview_from_current")
        
        ripple_text = t("dialogs.batch_timing.preview_ripple") if ripple else ""
        
        self.preview_label.setText(
            f"⏱️ {scope_text} {direction} {abs(offset)}ms{ripple_text}"
        )
    
    def get_settings(self) -> dict:
        """
        Get dialog settings.
        
        Returns:
            Dictionary with offset, scope, and ripple settings
        """
        scope_map = {0: "all", 1: "selected", 2: "from_current"}
        return {
            "offset_ms": self.offset_spin.value(),
            "scope": scope_map.get(self.scope_group.checkedId(), "all"),
            "ripple": self.ripple_check.isChecked()
        }
