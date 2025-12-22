"""
DubSync Logging System

Rotating file logger with configurable log levels.
Logs at boundary points (file ops, import/export, plugin load, DB operations).
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime


# Log configuration
LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "dubsync.log"
MAX_LOG_SIZE = 2 * 1024 * 1024  # 2 MB per file
MAX_LOG_FILES = 5  # Keep 5 backup files (total max ~10MB)
DEFAULT_LOG_LEVEL = logging.INFO
DEBUG_LOG_LEVEL = logging.DEBUG

# Log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class LogManager:
    """
    Centralized logging manager singleton.
    
    Provides rotating file logging with configurable levels.
    """
    
    _instance: Optional["LogManager"] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._log_dir: Optional[Path] = None
        self._file_handler: Optional[RotatingFileHandler] = None
        self._console_handler: Optional[logging.StreamHandler] = None
        self._debug_mode: bool = False
        self._root_logger = logging.getLogger("dubsync")
    
    def initialize(
        self,
        log_dir: Optional[Path] = None,
        debug_mode: bool = False,
        console_output: bool = True
    ) -> None:
        """
        Initialize the logging system.
        
        Args:
            log_dir: Directory for log files (default: project_root/logs)
            debug_mode: Enable DEBUG level logging
            console_output: Also output to console (for development)
        """
        # Determine log directory
        if log_dir:
            self._log_dir = log_dir
        else:
            # Default: logs folder in project root
            self._log_dir = Path(__file__).parent.parent.parent.parent / LOG_DIR_NAME

        self._log_dir.mkdir(parents=True, exist_ok=True)

        self._debug_mode = debug_mode
        log_level = DEBUG_LOG_LEVEL if debug_mode else DEFAULT_LOG_LEVEL

        # Configure root logger for dubsync
        self._root_logger.setLevel(log_level)

        # Remove existing handlers
        self._root_logger.handlers.clear()

        # File handler with rotation
        log_file = self._log_dir / LOG_FILE_NAME
        self._file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=MAX_LOG_FILES,
            encoding='utf-8'
        )
        self._file_handler.setLevel(log_level)
        self._file_handler.setFormatter(
            logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
        )
        self._root_logger.addHandler(self._file_handler)

        # Console handler (optional)
        if console_output:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setLevel(log_level)
            self._console_handler.setFormatter(
                logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
            )
            self._root_logger.addHandler(self._console_handler)

        # Log startup
        self._root_logger.info("=" * 60)
        self._root_logger.info("DubSync logging initialized")
        self._root_logger.info(f"Log directory: {self._log_dir}")
        self._root_logger.info(f"Debug mode: {debug_mode}")
        self._root_logger.info("=" * 60)
    
    def set_debug_mode(self, enabled: bool) -> None:
        """Enable or disable debug mode at runtime."""
        self._debug_mode = enabled
        log_level = DEBUG_LOG_LEVEL if enabled else DEFAULT_LOG_LEVEL
        
        self._root_logger.setLevel(log_level)
        
        if self._file_handler:
            self._file_handler.setLevel(log_level)
        if self._console_handler:
            self._console_handler.setLevel(log_level)
        
        self._root_logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    @property
    def debug_mode(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug_mode
    
    @property
    def log_dir(self) -> Optional[Path]:
        """Get log directory path."""
        return self._log_dir
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger for a specific module.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        if name.startswith("dubsync."):
            return logging.getLogger(name)
        return logging.getLogger(f"dubsync.{name}")
    
    def shutdown(self) -> None:
        """Shutdown logging system."""
        self._root_logger.info("DubSync logging shutdown")
        logging.shutdown()


# Global instance
_log_manager: Optional[LogManager] = None


def get_log_manager() -> LogManager:
    """Get the LogManager singleton."""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
    return _log_manager


def initialize_logging(
    log_dir: Optional[Path] = None,
    debug_mode: bool = False,
    console_output: bool = False
) -> None:
    """
    Initialize the logging system.
    
    Call this early in application startup.
    
    Args:
        log_dir: Directory for log files
        debug_mode: Enable DEBUG level logging
        console_output: Also output to console
    """
    get_log_manager().initialize(log_dir, debug_mode, console_output)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (usually __name__)
        
    Returns:
        Logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("File opened")
        logger.error("Failed to save", exc_info=True)
    """
    return get_log_manager().get_logger(name)


def set_debug_mode(enabled: bool) -> None:
    """Enable or disable debug mode."""
    get_log_manager().set_debug_mode(enabled)


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    return get_log_manager().debug_mode


# Convenience logging functions for boundary points
def log_file_operation(operation: str, path: str, success: bool = True, error: str = None) -> None:
    """Log file operation (open, save, import, export)."""
    logger = get_logger("file_ops")
    if success:
        logger.info(f"{operation}: {path}")
    else:
        logger.error(f"{operation} FAILED: {path} - {error}")


def log_project_operation(operation: str, details: str = None) -> None:
    """Log project operation (create, open, close, save)."""
    logger = get_logger("project")
    msg = operation
    if details:
        msg += f": {details}"
    logger.info(msg)


def log_plugin_operation(operation: str, plugin_id: str, success: bool = True, error: str = None) -> None:
    """Log plugin operation (load, enable, disable, execute)."""
    logger = get_logger("plugins")
    if success:
        logger.info(f"{operation}: {plugin_id}")
    else:
        logger.error(f"{operation} FAILED: {plugin_id} - {error}")


def log_database_operation(operation: str, details: str = None) -> None:
    """Log database operation (migrate, query, transaction)."""
    logger = get_logger("database")
    msg = operation
    if details:
        msg += f": {details}"
    logger.debug(msg)  # DB ops are usually DEBUG level


def log_exception(message: str, exc_info: bool = True) -> None:
    """Log an exception with stack trace."""
    logger = get_logger("error")
    logger.error(message, exc_info=exc_info)
