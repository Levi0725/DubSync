"""
DubSync Theme System

Theme management for the user interface.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ThemeType(Enum):
    """Built-in theme types."""
    DARK = "dark"
    DARK_CONTRAST = "dark_contrast"
    LIGHT = "light"
    CUSTOM = "custom"


@dataclass
class ThemeColors:
    """Theme colors."""
    # Basic colors
    background: str
    background_alt: str
    foreground: str
    foreground_muted: str
    
    # Surface elements
    surface: str
    surface_hover: str
    surface_selected: str
    border: str
    
    # Accent colors
    primary: str
    primary_hover: str
    secondary: str
    
    # Status colors
    success: str
    warning: str
    error: str
    info: str
    
    # Lip-sync colors
    lipsync_good: str
    lipsync_warning: str
    lipsync_error: str
    
    # Other
    input_background: str
    input_border: str
    scrollbar: str
    scrollbar_hover: str


# Built-in themes
THEMES: Dict[ThemeType, ThemeColors] = {
    ThemeType.DARK: ThemeColors(
        background="#1e1e1e",
        background_alt="#252526",
        foreground="#d4d4d4",
        foreground_muted="#808080",
        surface="#2d2d30",
        surface_hover="#3e3e42",
        surface_selected="#094771",
        border="#3c3c3c",
        primary="#0078d4",
        primary_hover="#1084d8",
        secondary="#6c757d",
        success="#4caf50",
        warning="#ffc107",
        error="#f44336",
        info="#2196f3",
        lipsync_good="#4caf50",
        lipsync_warning="#ffc107",
        lipsync_error="#f44336",
        input_background="#3c3c3c",
        input_border="#555555",
        scrollbar="#5a5a5a",
        scrollbar_hover="#6e6e6e",
    ),
    ThemeType.DARK_CONTRAST: ThemeColors(
        background="#000000",
        background_alt="#0a0a0a",
        foreground="#ffffff",
        foreground_muted="#a0a0a0",
        surface="#1a1a1a",
        surface_hover="#2a2a2a",
        surface_selected="#0055aa",
        border="#ffffff",
        primary="#4fc3f7",
        primary_hover="#81d4fa",
        secondary="#b0bec5",
        success="#69f0ae",
        warning="#ffd740",
        error="#ff5252",
        info="#40c4ff",
        lipsync_good="#69f0ae",
        lipsync_warning="#ffd740",
        lipsync_error="#ff5252",
        input_background="#1a1a1a",
        input_border="#ffffff",
        scrollbar="#666666",
        scrollbar_hover="#888888",
    ),
    ThemeType.LIGHT: ThemeColors(
        background="#ffffff",
        background_alt="#f5f5f5",
        foreground="#1e1e1e",
        foreground_muted="#666666",
        surface="#f0f0f0",
        surface_hover="#e0e0e0",
        surface_selected="#cce5ff",
        border="#d0d0d0",
        primary="#0078d4",
        primary_hover="#106ebe",
        secondary="#6c757d",
        success="#28a745",
        warning="#ffc107",
        error="#dc3545",
        info="#17a2b8",
        lipsync_good="#28a745",
        lipsync_warning="#ffc107",
        lipsync_error="#dc3545",
        input_background="#ffffff",
        input_border="#ced4da",
        scrollbar="#c0c0c0",
        scrollbar_hover="#a0a0a0",
    ),
    ThemeType.CUSTOM: ThemeColors(
        # Default to dark theme, but user can modify
        background="#1e1e1e",
        background_alt="#252526",
        foreground="#d4d4d4",
        foreground_muted="#808080",
        surface="#2d2d30",
        surface_hover="#3e3e42",
        surface_selected="#094771",
        border="#3c3c3c",
        primary="#0078d4",
        primary_hover="#1084d8",
        secondary="#6c757d",
        success="#4caf50",
        warning="#ffc107",
        error="#f44336",
        info="#2196f3",
        lipsync_good="#4caf50",
        lipsync_warning="#ffc107",
        lipsync_error="#f44336",
        input_background="#3c3c3c",
        input_border="#555555",
        scrollbar="#5a5a5a",
        scrollbar_hover="#6e6e6e",
    ),
}


def get_theme(theme_type: ThemeType) -> ThemeColors:
    """
    Get theme colors.
    
    Args:
        theme_type: Theme type
    
    Returns:
        ThemeColors object
    """
    return THEMES.get(theme_type, THEMES[ThemeType.DARK])


def generate_stylesheet(colors: ThemeColors) -> str:
    """
    Generate Qt stylesheet from theme colors.
    
    Args:
        colors: ThemeColors object
    
    Returns:
        Qt stylesheet string
    """
    return f"""
/* === GLOBAL === */
QWidget {{
    background-color: {colors.background};
    color: {colors.foreground};
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}}

QMainWindow {{
    background-color: {colors.background};
}}

/* === MENU BAR === */
QMenuBar {{
    background-color: {colors.surface};
    border-bottom: 1px solid {colors.border};
    padding: 2px;
}}

QMenuBar::item {{
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected {{
    background-color: {colors.surface_hover};
}}

QMenu {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    border-radius: 4px;
    padding: 4px;
}}

QMenu::icon {{
    margin-left: 8px;
    padding-right: 4px;
}}

QMenu::item {{
    padding: 8px 24px 8px 32px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {colors.surface_selected};
}}

QMenu::separator {{
    height: 1px;
    background-color: {colors.border};
    margin: 4px 8px;
}}

/* === TOOLBAR === */
QToolBar {{
    background-color: {colors.surface};
    border-bottom: 1px solid {colors.border};
    padding: 4px;
    spacing: 4px;
}}

QToolBar::separator {{
    width: 1px;
    background-color: {colors.border};
    margin: 4px 8px;
}}

QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 6px;
}}

QToolButton:hover {{
    background-color: {colors.surface_hover};
    border-color: {colors.border};
}}

QToolButton:pressed {{
    background-color: {colors.surface_selected};
}}

/* === STATUS BAR === */
QStatusBar {{
    background-color: {colors.surface};
    border-top: 1px solid {colors.border};
}}

QStatusBar::item {{
    border: none;
}}

/* === DOCK WIDGET === */
QDockWidget {{
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(float.png);
}}

QDockWidget::title {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    padding: 6px;
    text-align: left;
}}

/* === SPLITTER === */
QSplitter::handle {{
    background-color: {colors.border};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* === TABLE WIDGET === */
QTableWidget {{
    background-color: {colors.background_alt};
    alternate-background-color: {colors.surface};
    gridline-color: {colors.border};
    border: 1px solid {colors.border};
    border-radius: 4px;
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

QTableWidget::item:selected {{
    background-color: {colors.surface_selected};
}}

QHeaderView::section {{
    background-color: {colors.surface};
    color: {colors.foreground};
    padding: 8px;
    border: none;
    border-right: 1px solid {colors.border};
    border-bottom: 1px solid {colors.border};
    font-weight: bold;
}}

/* === INPUT FIELDS === */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {colors.input_background};
    border: 1px solid {colors.input_border};
    border-radius: 4px;
    padding: 6px;
    min-height: 20px;
    color: {colors.foreground};
    selection-background-color: {colors.primary};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {colors.primary};
}}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background-color: {colors.surface};
    color: {colors.foreground_muted};
}}

/* === COMBO BOX === */
QComboBox {{
    background-color: {colors.input_background};
    border: 1px solid {colors.input_border};
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 80px;
    min-height: 20px;
    color: {colors.foreground};
}}

QComboBox:hover {{
    border-color: {colors.primary};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: url(down-arrow.png);
    width: 12px;
    height: 12px;
}}

QComboBox QAbstractItemView {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    selection-background-color: {colors.surface_selected};
    color: {colors.foreground};
    padding: 4px;
}}

QComboBox QAbstractItemView::item {{
    padding: 6px 12px;
    min-height: 24px;
    color: {colors.foreground};
}}

QComboBox QAbstractItemView::item:selected {{
    background-color: {colors.surface_selected};
    color: {colors.foreground};
}}

/* === PUSH BUTTON === */
QPushButton {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {colors.surface_hover};
    border-color: {colors.primary};
}}

QPushButton:pressed {{
    background-color: {colors.surface_selected};
}}

QPushButton:disabled {{
    background-color: {colors.surface};
    color: {colors.foreground_muted};
    border-color: {colors.border};
}}

QPushButton#primaryButton {{
    background-color: {colors.primary};
    border-color: {colors.primary};
    color: white;
}}

QPushButton#primaryButton:hover {{
    background-color: {colors.primary_hover};
}}

QPushButton#successButton {{
    background-color: {colors.success};
    border-color: {colors.success};
    color: white;
}}

QPushButton#warningButton {{
    background-color: {colors.warning};
    border-color: {colors.warning};
    color: black;
}}

QPushButton#dangerButton {{
    background-color: {colors.error};
    border-color: {colors.error};
    color: white;
}}

/* === GROUP BOX === */
QGroupBox {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px;
    padding-top: 24px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    background-color: {colors.surface};
    color: {colors.foreground};
    font-weight: bold;
}}

/* === SCROLL BAR === */
QScrollBar:vertical {{
    background-color: {colors.background_alt};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {colors.scrollbar};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {colors.scrollbar_hover};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {colors.background_alt};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {colors.scrollbar};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {colors.scrollbar_hover};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* === FRAME === */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    background-color: {colors.border};
}}

/* === TAB WIDGET === */
QTabWidget::pane {{
    background-color: {colors.background};
    border: 1px solid {colors.border};
    border-radius: 4px;
}}

QTabBar::tab {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {colors.background};
    border-bottom-color: {colors.background};
}}

QTabBar::tab:hover {{
    background-color: {colors.surface_hover};
}}

/* === LABEL === */
QLabel {{
    background-color: transparent;
}}

QLabel#titleLabel {{
    font-size: 14pt;
    font-weight: bold;
}}

QLabel#subtitleLabel {{
    font-size: 10pt;
    color: {colors.foreground_muted};
}}

/* === CHECK BOX === */
QCheckBox {{
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {colors.border};
    border-radius: 4px;
    background-color: {colors.input_background};
}}

QCheckBox::indicator:checked {{
    background-color: {colors.primary};
    border-color: {colors.primary};
}}

QCheckBox::indicator:hover {{
    border-color: {colors.primary};
}}

/* === SPIN BOX === */
QSpinBox, QDoubleSpinBox {{
    background-color: {colors.input_background};
    border: 1px solid {colors.input_border};
    border-radius: 4px;
    padding: 6px;
    min-height: 20px;
    color: {colors.foreground};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {colors.primary};
}}

/* === PROGRESS BAR === */
QProgressBar {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    border-radius: 4px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {colors.primary};
    border-radius: 3px;
}}

/* === TOOLTIP === */
QToolTip {{
    background-color: {colors.surface};
    border: 1px solid {colors.border};
    color: {colors.foreground};
    padding: 6px;
    border-radius: 4px;
}}

/* === DIALOG === */
QDialog {{
    background-color: {colors.background};
}}

/* === MESSAGE BOX === */
QMessageBox {{
    background-color: {colors.background};
}}

/* === SLIDER === */
QSlider::groove:horizontal {{
    background-color: {colors.surface};
    height: 6px;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: {colors.primary};
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -5px 0;
}}

QSlider::handle:horizontal:hover {{
    background-color: {colors.primary_hover};
}}
"""


class ThemeManager:
    """
    Theme manager singleton.
    """
    _instance: Optional["ThemeManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._current_theme = ThemeType.DARK
        self._custom_colors: Optional[ThemeColors] = None
        self._initialized = True
    
    @property
    def current_theme(self) -> ThemeType:
        return self._current_theme
    
    @property
    def colors(self) -> ThemeColors:
        if self._current_theme == ThemeType.CUSTOM and self._custom_colors:
            return self._custom_colors
        return get_theme(self._current_theme)
    
    def set_theme(self, theme_type: ThemeType):
        """Set theme."""
        self._current_theme = theme_type
    
    def set_custom_colors(self, colors: ThemeColors):
        """Set custom colors."""
        self._custom_colors = colors
        self._current_theme = ThemeType.CUSTOM
    
    def get_stylesheet(self) -> str:
        """Get current stylesheet."""
        return generate_stylesheet(self.colors)
