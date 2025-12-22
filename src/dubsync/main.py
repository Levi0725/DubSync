"""
DubSync - Main Entry Point

Initializes and starts the DubSync application.
"""

import sys
import argparse
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="dubsync",
        description="DubSync - Professional Dubbing Translation Editor"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Project file to open (.dubsync)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (verbose output)"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit"
    )
    return parser.parse_args()


def main():
    """
    Primary application entry point.
    """
    from dubsync.utils.constants import APP_NAME, APP_VERSION, PROJECT_EXTENSION
    
    # Parse arguments first
    args = parse_arguments()
    
    if args.version:
        print(f"{APP_NAME} v{APP_VERSION}")
        sys.exit(0)
    
    # Initialize logging system early
    from dubsync.services.logger import initialize_logging, get_logger
    project_root = Path(__file__).parent.parent.parent
    initialize_logging(
        log_dir=project_root / "logs",
        debug_mode=args.debug,
        console_output=args.debug  # Console output only in debug mode
    )
    logger = get_logger(__name__)
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")
    
    # Initialize crash handler
    from dubsync.services.crash_handler import initialize_crash_handler, log_activity
    crash_reports_dir = project_root / "crash_reports"
    initialize_crash_handler(APP_VERSION, crash_reports_dir)
    log_activity("Application starting", f"Version {APP_VERSION}")
    
    # Import Qt after logging is set up
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QFont
    from dubsync.app import DubSyncApp
    
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("DubSync")
    logger.info("QApplication created")
    log_activity("QApplication created")
    
    # Default font for Hungarian characters
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    main_window = DubSyncApp()
    main_window.show()
    logger.info("Main window shown")
    log_activity("Main window shown")
    
    # Check for file argument (open with .dubsync file)
    if args.file and args.file.endswith(PROJECT_EXTENSION):
        logger.info(f"Opening file from argument: {args.file}")
        log_activity("Opening file from argument", args.file)
        # Use QTimer to open after event loop starts
        QTimer.singleShot(100, lambda: main_window.open_project_file(args.file))
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
