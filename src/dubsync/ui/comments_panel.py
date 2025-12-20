"""
DubSync Comments Panel Widget

Lektori megjegyzések panel.
"""

from typing import Optional, List, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLabel, QPushButton, QTextEdit, QLineEdit, QGroupBox
)
from PySide6.QtCore import Qt, Signal, Slot

from dubsync.models.cue import Cue
from dubsync.models.comment import Comment
from dubsync.utils.constants import CommentStatus
from dubsync.services.settings_manager import SettingsManager
from dubsync.i18n import t

if TYPE_CHECKING:
    from dubsync.models.database import Database


class CommentWidget(QFrame):
    """
    Egyetlen megjegyzés widget.
    """
    
    resolved = Signal(int)  # comment_id
    deleted = Signal(int)  # comment_id
    
    def __init__(self, comment: Comment, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self.comment = comment
        self._setup_ui()
    
    def _setup_ui(self):
        """UI felépítése."""
        from dubsync.ui.theme import ThemeManager
        theme = ThemeManager()
        colors = theme.colors

        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            CommentWidget {{
                background-color: {colors.surface};
                border: 1px solid {colors.border};
                border-radius: 4px;
                margin: 2px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        # Header
        header_layout = QHBoxLayout()

        self.author_label = QLabel(f"<b>{self.comment.author}</b>")
        header_layout.addWidget(self.author_label)

        header_layout.addStretch()

        if self.comment.is_resolved:
            resolved_label = QLabel(t("comments_panel.resolved"))
            resolved_label.setStyleSheet(f"color: {colors.success};")
            header_layout.addWidget(resolved_label)

        layout.addLayout(header_layout)

        # Content
        self.content_label = QLabel(self.comment.content)
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(f"color: {colors.foreground};")
        layout.addWidget(self.content_label)

        # Actions
        if self.comment.is_open:
            self._extracted_from__setup_ui_43(colors, layout)

    # TODO Rename this here and in `_setup_ui`
    def _extracted_from__setup_ui_43(self, colors, layout):
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        self.resolve_btn = QPushButton(t("comments_panel.resolve"))
        self.resolve_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors.success};
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {colors.success};
                    opacity: 0.9;
                }}
            """)
        self.resolve_btn.clicked.connect(
            lambda: self.resolved.emit(self.comment.id)
        )
        actions_layout.addWidget(self.resolve_btn)

        layout.addLayout(actions_layout)


class CommentsPanelWidget(QWidget):
    """
    Megjegyzések panel a kiválasztott cue-hoz.
    """
    
    # Signals
    comment_added = Signal()
    comment_resolved = Signal(int)  # comment_id
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._cue: Optional[Cue] = None
        self._db: Optional["Database"] = None
        self._comments: List[Comment] = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """UI felépítése."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Header
        self.header_label = QLabel(t("comments_panel.select_cue"))
        self.header_label.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(self.header_label)
        
        # Scroll area for comments
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.comments_container = QWidget()
        self.comments_layout = QVBoxLayout(self.comments_container)
        self.comments_layout.setContentsMargins(0, 0, 0, 0)
        self.comments_layout.addStretch()
        
        scroll.setWidget(self.comments_container)
        layout.addWidget(scroll, 1)
        
        # New comment section
        new_comment_group = QGroupBox(t("comments_panel.new_comment"))
        new_comment_layout = QVBoxLayout(new_comment_group)
        
        # Author
        author_layout = QHBoxLayout()
        author_layout.addWidget(QLabel(t("comments_panel.author")))
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText(t("comments_panel.author_placeholder"))
        
        # Alapértelmezett név a beállításokból
        settings = SettingsManager()
        default_name = settings.default_author_name
        self.author_edit.setText(default_name or t("comments_panel.default_author"))
        
        author_layout.addWidget(self.author_edit)
        new_comment_layout.addLayout(author_layout)
        
        # Comment text
        self.comment_edit = QTextEdit()
        self.comment_edit.setPlaceholderText(t("comments_panel.content_placeholder"))
        self.comment_edit.setMaximumHeight(80)
        new_comment_layout.addWidget(self.comment_edit)
        
        # Add button - themed
        from dubsync.ui.theme import ThemeManager
        theme = ThemeManager()
        colors = theme.colors
        
        self.add_btn = QPushButton(t("comments_panel.add"))
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.primary};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.primary_hover};
            }}
            QPushButton:disabled {{
                background-color: {colors.surface};
                color: {colors.foreground_muted};
            }}
        """)
        new_comment_layout.addWidget(self.add_btn)
        
        layout.addWidget(new_comment_group)
        
        self._update_ui_state()
    
    def _connect_signals(self):
        """Signal kapcsolatok."""
        self.add_btn.clicked.connect(self._on_add_comment)
    
    def _update_ui_state(self):
        """UI állapot frissítése."""
        has_cue = self._cue is not None
        
        self.add_btn.setEnabled(has_cue)
        self.comment_edit.setEnabled(has_cue)
        self.author_edit.setEnabled(has_cue)
    
    def set_cue(self, cue: Cue, db: "Database"):
        """
        Cue beállítása.
        
        Args:
            cue: Cue objektum
            db: Adatbázis kapcsolat
        """
        self._cue = cue
        self._db = db
        
        self.header_label.setText(t("comments_panel.header", index=cue.cue_index))
        
        self._load_comments()
        self._update_ui_state()
    
    def _load_comments(self):
        """Megjegyzések betöltése."""
        # Clear existing
        while self.comments_layout.count() > 1:  # Keep stretch
            item = self.comments_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if self._cue is None or self._db is None:
            return

        self._comments = Comment.load_for_cue(self._db, self._cue.id)

        # Add comment widgets
        for comment in self._comments:
            widget = CommentWidget(comment)
            widget.resolved.connect(self._on_comment_resolved)
            self.comments_layout.insertWidget(
                self.comments_layout.count() - 1,  # Before stretch
                widget
            )

        if not self._comments:
            self._extracted_from__load_comments_24()

    # TODO Rename this here and in `_load_comments`
    def _extracted_from__load_comments_24(self):
        from dubsync.ui.theme import ThemeManager
        theme = ThemeManager()
        colors = theme.colors

        no_comments = QLabel(t("comments_panel.no_comments"))
        no_comments.setStyleSheet(f"color: {colors.foreground_muted}; padding: 20px;")
        no_comments.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comments_layout.insertWidget(0, no_comments)
    
    @Slot()
    def _on_add_comment(self):
        """Megjegyzés hozzáadása."""
        if self._cue is None or self._db is None:
            return
        
        content = self.comment_edit.toPlainText().strip()
        if not content:
            return
        
        author = self.author_edit.text().strip() or t("comments_panel.default_author")
        
        comment = Comment(
            cue_id=self._cue.id,
            author=author,
            content=content,
            status=CommentStatus.OPEN
        )
        comment.save(self._db)
        
        self.comment_edit.clear()
        self._load_comments()
        self.comment_added.emit()
    
    @Slot(int)
    def _on_comment_resolved(self, comment_id: int):
        """Megjegyzés lezárása."""
        if self._db is None:
            return
        
        for comment in self._comments:
            if comment.id == comment_id:
                comment.resolve(self._db)
                break
        
        self._load_comments()
        self.comment_resolved.emit(comment_id)
    
    def clear(self):
        """Panel törlése."""
        self._cue = None
        self._db = None
        self._comments = []
        
        self.header_label.setText(t("comments_panel.select_cue"))
        self._load_comments()
        self._update_ui_state()
