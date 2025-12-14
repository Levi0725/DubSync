"""
DubSync - Main Entry Point

Alkalmazás indítása és inicializálása.
"""

import sys
import os
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def main():
    """
    Fő belépési pont az alkalmazáshoz.
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    
    from dubsync.app import DubSyncApp
    from dubsync.utils.constants import APP_NAME, APP_VERSION
    
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("DubSync")
    
    # Default font for Hungarian characters
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    main_window = DubSyncApp()
    main_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
