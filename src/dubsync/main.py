"""
DubSync - Main Entry Point

Initializes and starts the DubSync application.
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
    Primary application entry point.
    """
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont
    
    from dubsync.app import DubSyncApp
    from dubsync.utils.constants import APP_NAME, APP_VERSION, PROJECT_EXTENSION
    from dubsync.services.crash_handler import initialize_crash_handler, log_activity
    
    # Initialize crash handler early
    crash_reports_dir = Path(__file__).parent.parent.parent / "crash_reports"
    initialize_crash_handler(APP_VERSION, crash_reports_dir)
    log_activity("Application starting", f"Version {APP_VERSION}")
    
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("DubSync")
    log_activity("QApplication created")
    
    # Default font for Hungarian characters
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    main_window = DubSyncApp()
    main_window.show()
    log_activity("Main window shown")
    
    # Check for file argument (open with .dubsync file)
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if file_path.endswith(PROJECT_EXTENSION):
            log_activity("Opening file from argument", file_path)
            # Use QTimer to open after event loop starts
            QTimer.singleShot(100, lambda: main_window.open_project_file(file_path))
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
