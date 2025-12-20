"""
DubSync Crash Handler

Comprehensive crash logging and error handling system.
All crash reports are in English for universal debugging.
"""


import contextlib
import sys
import os
import platform
import traceback
import datetime
import json
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from collections import deque
from enum import Enum


class ErrorCode(Enum):
    """
    Error codes for crash reports.
    
    See ERROR_CODES.md for detailed descriptions.
    """
    # General errors (1xxx)
    UNKNOWN_ERROR = 1000
    UNHANDLED_EXCEPTION = 1001
    ASSERTION_ERROR = 1002

    # File errors (2xxx)
    FILE_NOT_FOUND = 2001
    FILE_READ_ERROR = 2002
    FILE_WRITE_ERROR = 2003
    FILE_PERMISSION_ERROR = 2004
    FILE_CORRUPT = 2005

    # Database errors (3xxx)
    DATABASE_ERROR = 3001
    DATABASE_CORRUPT = 3002
    DATABASE_LOCKED = 3003
    DATABASE_SCHEMA_ERROR = 3004

    # UI errors (4xxx)
    UI_INITIALIZATION_ERROR = 4001
    UI_RENDER_ERROR = 4002
    WIDGET_ERROR = 4003

    # Plugin errors (5xxx)
    PLUGIN_LOAD_ERROR = 5001
    PLUGIN_EXECUTION_ERROR = 5002
    PLUGIN_DEPENDENCY_ERROR = 5003

    # Media errors (6xxx)
    VIDEO_LOAD_ERROR = 6001
    VIDEO_PLAYBACK_ERROR = 6002
    AUDIO_ERROR = 6003

    # Import/Export errors (7xxx)
    SRT_PARSE_ERROR = 7001
    SRT_EXPORT_ERROR = 7002
    PDF_EXPORT_ERROR = 7003
    PROJECT_LOAD_ERROR = 7004
    PROJECT_SAVE_ERROR = 7005

    # Memory errors (8xxx)
    OUT_OF_MEMORY = 8001
    RESOURCE_EXHAUSTED = 8002

    # Network errors (9xxx)
    NETWORK_ERROR = 9001
    DOWNLOAD_ERROR = 9002


@dataclass
class ActivityLogEntry:
    """Single activity log entry."""
    timestamp: str
    action: str
    details: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "details": self.details
        }


@dataclass
class SystemInfo:
    """System information for crash reports."""
    os_name: str
    os_version: str
    os_architecture: str
    python_version: str
    app_version: str
    qt_version: str
    available_memory_mb: Optional[int] = None
    cpu_count: Optional[int] = None
    
    @classmethod
    def collect(cls, app_version: str = "unknown") -> "SystemInfo":
        """Collect current system information."""
        try:
            import psutil
            available_memory = psutil.virtual_memory().available // (1024 * 1024)
        except ImportError:
            available_memory = None
        
        try:
            from PySide6.QtCore import qVersion
            qt_ver = qVersion()
        except ImportError:
            qt_ver = "unknown"
        
        return cls(
            os_name=platform.system(),
            os_version=platform.version(),
            os_architecture=platform.machine(),
            python_version=platform.python_version(),
            app_version=app_version,
            qt_version=qt_ver,
            available_memory_mb=available_memory,
            cpu_count=os.cpu_count()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrashReport:
    """Complete crash report."""
    error_code: int
    error_name: str
    error_message: str
    traceback_text: str
    timestamp: str
    system_info: Dict[str, Any]
    activity_log: List[Dict[str, Any]]
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "crash_report": {
                "error_code": self.error_code,
                "error_name": self.error_name,
                "error_message": self.error_message,
                "timestamp": self.timestamp,
            },
            "traceback": self.traceback_text,
            "system_info": self.system_info,
            "activity_log": self.activity_log,
            "additional_info": self.additional_info
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class CrashHandler:
    """
    Global crash handler singleton.
    
    Handles:
    - Activity logging in background
    - Crash report generation
    - Error dialog display
    - Crash report file saving
    """
    
    _instance: Optional["CrashHandler"] = None
    
    # Maximum activity log entries to keep
    MAX_ACTIVITY_LOG = 500
    
    # GitHub issues URL
    GITHUB_ISSUES_URL = "https://github.com/Levi0725/DubSync/issues"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._activity_log: deque = deque(maxlen=self.MAX_ACTIVITY_LOG)
        self._lock = threading.Lock()
        self._app_version = "unknown"
        self._crash_reports_dir: Optional[Path] = None
        self._original_excepthook = sys.excepthook
        self._crash_callbacks: List[Callable[[CrashReport], None]] = []
        self._current_project_path: Optional[str] = None
        self._ui_state: Dict[str, Any] = {}
    
    def initialize(
        self,
        app_version: str,
        crash_reports_dir: Optional[Path] = None
    ) -> None:
        """
        Initialize the crash handler.
        
        Args:
            app_version: Application version string
            crash_reports_dir: Directory for crash reports
        """
        self._app_version = app_version
        
        if crash_reports_dir:
            self._crash_reports_dir = crash_reports_dir
        else:
            # Default: crash_reports in project root
            self._crash_reports_dir = Path(__file__).parent.parent.parent.parent / "crash_reports"
        
        self._crash_reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Install global exception hook
        sys.excepthook = self._exception_hook
        
        self.log_activity("CrashHandler initialized")
    
    def shutdown(self) -> None:
        """Restore original exception hook."""
        sys.excepthook = self._original_excepthook
    
    def log_activity(
        self,
        action: str,
        details: Optional[str] = None
    ) -> None:
        """
        Log user activity.
        
        Args:
            action: Action description (e.g., "Opened project")
            details: Optional additional details
        """
        timestamp = datetime.datetime.now().isoformat()
        entry = ActivityLogEntry(
            timestamp=timestamp,
            action=action,
            details=details
        )
        
        with self._lock:
            self._activity_log.append(entry)
    
    def set_current_project(self, path: Optional[str]) -> None:
        """Set current project path for crash reports."""
        self._current_project_path = path
        if path:
            self.log_activity("Project set", path)
    
    def set_ui_state(self, key: str, value: Any) -> None:
        """Store UI state information for crash reports."""
        self._ui_state[key] = value
    
    def register_crash_callback(
        self,
        callback: Callable[[CrashReport], None]
    ) -> None:
        """Register callback to be called on crash."""
        self._crash_callbacks.append(callback)
    
    def _get_activity_log_list(self) -> List[Dict[str, Any]]:
        """Get activity log as list of dicts."""
        with self._lock:
            return [entry.to_dict() for entry in self._activity_log]
    
    def _classify_exception(
        self,
        exc_type: type,
        exc_value: BaseException
    ) -> ErrorCode:
        """Classify exception into error code."""
        exc_name = exc_type.__name__
        exc_msg = str(exc_value).lower()
        
        # File errors
        if exc_type is FileNotFoundError:
            return ErrorCode.FILE_NOT_FOUND
        if exc_type is PermissionError:
            return ErrorCode.FILE_PERMISSION_ERROR
        if exc_type is IOError or "read" in exc_msg or "write" in exc_msg:
            if "read" in exc_msg:
                return ErrorCode.FILE_READ_ERROR
            return ErrorCode.FILE_WRITE_ERROR
        
        # Memory errors
        if exc_type is MemoryError:
            return ErrorCode.OUT_OF_MEMORY
        
        # Assertion errors
        if exc_type is AssertionError:
            return ErrorCode.ASSERTION_ERROR
        
        # Database errors
        if "database" in exc_msg or "sqlite" in exc_msg:
            if "locked" in exc_msg:
                return ErrorCode.DATABASE_LOCKED
            if "corrupt" in exc_msg:
                return ErrorCode.DATABASE_CORRUPT
            return ErrorCode.DATABASE_ERROR
        
        # SRT errors
        if "srt" in exc_msg:
            if "parse" in exc_msg:
                return ErrorCode.SRT_PARSE_ERROR
            return ErrorCode.SRT_EXPORT_ERROR
        
        # PDF errors
        if "pdf" in exc_msg:
            return ErrorCode.PDF_EXPORT_ERROR
        
        # Video errors
        if "video" in exc_msg or "media" in exc_msg:
            return ErrorCode.VIDEO_LOAD_ERROR
        
        # Plugin errors
        if "plugin" in exc_msg:
            if "load" in exc_msg:
                return ErrorCode.PLUGIN_LOAD_ERROR
            if "dependency" in exc_msg:
                return ErrorCode.PLUGIN_DEPENDENCY_ERROR
            return ErrorCode.PLUGIN_EXECUTION_ERROR
        
        # UI errors
        if "widget" in exc_msg or "qt" in exc_msg or "gui" in exc_msg:
            return ErrorCode.UI_RENDER_ERROR
        
        return ErrorCode.UNHANDLED_EXCEPTION
    
    def _create_crash_report(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb,
        error_code: Optional[ErrorCode] = None
    ) -> CrashReport:
        """Create a crash report from exception info."""
        if error_code is None:
            error_code = self._classify_exception(exc_type, exc_value)
        
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        
        system_info = SystemInfo.collect(self._app_version)
        
        additional_info = {
            "current_project": self._current_project_path,
            "ui_state": self._ui_state.copy()
        }
        
        return CrashReport(
            error_code=error_code.value,
            error_name=error_code.name,
            error_message=str(exc_value),
            traceback_text=tb_text,
            timestamp=datetime.datetime.now().isoformat(),
            system_info=system_info.to_dict(),
            activity_log=self._get_activity_log_list(),
            additional_info=additional_info
        )
    
    def _save_crash_report(self, report: CrashReport) -> Path:
        """Save crash report to file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crash_{timestamp}_{report.error_code}.json"
        filepath = self._crash_reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report.to_json())
        
        return filepath
    
    def _show_crash_dialog(
        self,
        report: CrashReport,
        report_path: Path
    ) -> None:
        """Show crash dialog to user."""
        try:
            from PySide6.QtWidgets import QMessageBox, QApplication
            from PySide6.QtCore import Qt

            # Ensure we have a QApplication
            app = QApplication.instance()
            if app is None:
                return

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("DubSync - Unexpected Error")

            error_text = (
                f"An unexpected error occurred.\n\n"
                f"Error Code: {report.error_code}\n"
                f"Error Type: {report.error_name}\n\n"
                f"A crash report has been saved to:\n"
                f"{report_path}\n\n"
                f"Please report this issue at:\n"
                f"{self.GITHUB_ISSUES_URL}\n\n"
                f"Include the crash report file when reporting."
            )

            msg.setText(error_text)
            msg.setDetailedText(report.traceback_text)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setDefaultButton(QMessageBox.StandardButton.Ok)

            # Make it stay on top
            msg.setWindowFlags(
                msg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )

            msg.exec()

        except Exception as e:
            self._extracted_from__show_crash_dialog_45(report, report_path)

    # TODO Rename this here and in `_show_crash_dialog`
    def _extracted_from__show_crash_dialog_45(self, report, report_path):
        # Fallback to console if dialog fails
        print(f"\n{'='*60}")
        print("DUBSYNC CRASH REPORT")
        print(f"{'='*60}")
        print(f"Error Code: {report.error_code}")
        print(f"Error: {report.error_message}")
        print(f"Report saved to: {report_path}")
        print(f"Report issues at: {self.GITHUB_ISSUES_URL}")
        print(f"{'='*60}\n")
    
    def _exception_hook(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb
    ) -> None:
        """Global exception hook."""
        # Don't handle KeyboardInterrupt
        if issubclass(exc_type, KeyboardInterrupt):
            self._original_excepthook(exc_type, exc_value, exc_tb)
            return

        try:
            # Log the crash
            self.log_activity(
                "CRASH",
                f"{exc_type.__name__}: {exc_value}"
            )

            # Create crash report
            report = self._create_crash_report(exc_type, exc_value, exc_tb)

            # Save report
            report_path = self._save_crash_report(report)

            # Call callbacks
            for callback in self._crash_callbacks:
                with contextlib.suppress(Exception):
                    callback(report)
            # Show dialog
            self._show_crash_dialog(report, report_path)

        except Exception as e:
            # Last resort: print to console
            print(f"Error in crash handler: {e}")
            traceback.print_exception(exc_type, exc_value, exc_tb)

        # Call original hook
        self._original_excepthook(exc_type, exc_value, exc_tb)
    
    def handle_exception(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb,
        error_code: Optional[ErrorCode] = None,
        show_dialog: bool = True
    ) -> Optional[Path]:
        """
        Manually handle an exception.
        
        Use this to handle caught exceptions that should generate
        crash reports without terminating the application.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_tb: Exception traceback
            error_code: Optional specific error code
            show_dialog: Whether to show dialog
            
        Returns:
            Path to crash report file, or None if failed
        """
        try:
            self.log_activity(
                "Exception handled",
                f"{exc_type.__name__}: {exc_value}"
            )
            
            report = self._create_crash_report(
                exc_type, exc_value, exc_tb, error_code
            )
            report_path = self._save_crash_report(report)
            
            if show_dialog:
                self._show_crash_dialog(report, report_path)
            
            return report_path
            
        except Exception as e:
            print(f"Error handling exception: {e}")
            return None


# Convenience functions

def get_crash_handler() -> CrashHandler:
    """Get the CrashHandler singleton."""
    return CrashHandler()


def log_activity(action: str, details: Optional[str] = None) -> None:
    """Log user activity."""
    get_crash_handler().log_activity(action, details)


def initialize_crash_handler(
    app_version: str,
    crash_reports_dir: Optional[Path] = None
) -> None:
    """Initialize the crash handler."""
    get_crash_handler().initialize(app_version, crash_reports_dir)
