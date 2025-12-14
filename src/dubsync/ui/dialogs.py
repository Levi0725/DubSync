"""
DubSync Dialogs

Dialógus ablakok.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QDoubleSpinBox, QDialogButtonBox,
    QLabel, QPushButton, QGroupBox, QTextBrowser
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from dubsync.models.project import Project
from dubsync.utils.constants import APP_NAME, APP_VERSION


class ProjectSettingsDialog(QDialog):
    """
    Projekt beállítások dialógus.
    """
    
    def __init__(self, project: Project, parent=None):
        super().__init__(parent)
        
        self.project = project
        self.setWindowTitle("Projekt beállítások")
        self.setMinimumWidth(450)
        
        self._setup_ui()
        self._load_values()
    
    def _setup_ui(self):
        """UI felépítése."""
        layout = QVBoxLayout(self)
        
        # Form
        form = QFormLayout()
        
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Projekt neve...")
        form.addRow("Projekt cím:", self.title_edit)
        
        self.series_edit = QLineEdit()
        self.series_edit.setPlaceholderText("Sorozat címe...")
        form.addRow("Sorozat:", self.series_edit)
        
        # Season/Episode row
        season_layout = QHBoxLayout()
        self.season_edit = QLineEdit()
        self.season_edit.setPlaceholderText("1")
        self.season_edit.setMaximumWidth(60)
        season_layout.addWidget(self.season_edit)
        season_layout.addWidget(QLabel("Évad"))
        
        self.episode_edit = QLineEdit()
        self.episode_edit.setPlaceholderText("1")
        self.episode_edit.setMaximumWidth(60)
        season_layout.addWidget(self.episode_edit)
        season_layout.addWidget(QLabel("Rész"))
        season_layout.addStretch()
        
        form.addRow("Évad/Rész:", season_layout)
        
        self.episode_title_edit = QLineEdit()
        self.episode_title_edit.setPlaceholderText("Epizód címe...")
        form.addRow("Rész címe:", self.episode_title_edit)
        
        form.addRow("", QLabel(""))  # Spacer
        
        self.translator_edit = QLineEdit()
        self.translator_edit.setPlaceholderText("Fordító neve...")
        form.addRow("Fordító:", self.translator_edit)
        
        self.editor_edit = QLineEdit()
        self.editor_edit.setPlaceholderText("Lektor neve...")
        form.addRow("Lektor:", self.editor_edit)
        
        form.addRow("", QLabel(""))  # Spacer
        
        # Technical settings
        tech_group = QGroupBox("Technikai beállítások")
        tech_layout = QFormLayout(tech_group)
        
        self.framerate_spin = QDoubleSpinBox()
        self.framerate_spin.setRange(1.0, 120.0)
        self.framerate_spin.setValue(25.0)
        self.framerate_spin.setDecimals(3)
        self.framerate_spin.setSuffix(" fps")
        tech_layout.addRow("Frame rate:", self.framerate_spin)
        
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
    
    def _load_values(self):
        """Értékek betöltése a projektből."""
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
    Névjegy dialógus.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(f"{APP_NAME} - Névjegy")
        self.setFixedSize(400, 300)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI felépítése."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Title
        title = QLabel(f"<h1>{APP_NAME}</h1>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Version
        version = QLabel(f"<p>Verzió: {APP_VERSION}</p>")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        # Description
        desc = QLabel(
            "<p>Professzionális szinkronfordítói editor</p>"
            "<p>Fordítók és lektorok számára</p>"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # Features
        features = QLabel(
            "<p><b>Funkciók:</b></p>"
            "<ul>"
            "<li>SRT import/export</li>"
            "<li>Videó lejátszás lip-sync ellenőrzéssel</li>"
            "<li>Lektori megjegyzések</li>"
            "<li>PDF szövegkönyv export</li>"
            "<li>Plugin támogatás</li>"
            "</ul>"
        )
        features.setWordWrap(True)
        layout.addWidget(features)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Bezárás")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class ProgressDialog(QDialog):
    """
    Folyamat dialógus hosszú műveletekhéz.
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
        """Folyamat frissítése."""
        self.progress_label.setText(f"{current} / {total}")
    
    def set_message(self, message: str):
        """Üzenet frissítése."""
        self.message_label.setText(message)


class TutorialDialog(QDialog):
    """
    Tutorial dialógus - Alkalmazás bemutatása.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(f"{APP_NAME} - Útmutató")
        self.setMinimumSize(600, 500)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """UI felépítése."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"<h2>🎬 Üdvözöljük a {APP_NAME}-ban!</h2>")
        layout.addWidget(title)
        
        # Tutorial content
        content = QTextBrowser()
        content.setOpenExternalLinks(True)
        content.setHtml(self._get_tutorial_content())
        layout.addWidget(content)
        
        # Close button
        close_btn = QPushButton("Megértettem!")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _get_tutorial_content(self) -> str:
        """Tutorial tartalom generálása."""
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
