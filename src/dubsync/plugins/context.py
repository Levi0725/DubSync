"""
DubSync Plugin Context

Central API for plugins - provides safe access to application features.
Includes API versioning for compatibility checking.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from pathlib import Path
from enum import Enum, auto
import logging
from functools import wraps

if TYPE_CHECKING:
    from dubsync.models.project import Project
    from dubsync.models.cue import Cue
    from PySide6.QtWidgets import QMainWindow, QWidget

# Plugin API version - increment when breaking changes are made
PLUGIN_API_VERSION = 1
PLUGIN_API_VERSION_MIN = 1  # Minimum supported version


class PluginEvent(Enum):
    """Plugin events that can be subscribed to."""
    PROJECT_OPENED = auto()
    PROJECT_CLOSED = auto()
    PROJECT_SAVED = auto()
    CUE_SELECTED = auto()
    CUE_CHANGED = auto()
    CUE_ADDED = auto()
    CUE_DELETED = auto()
    EXPORT_STARTED = auto()
    EXPORT_FINISHED = auto()
    QA_CHECK_STARTED = auto()
    QA_CHECK_FINISHED = auto()
    LANGUAGE_CHANGED = auto()
    SETTINGS_CHANGED = auto()


@dataclass
class PluginCapabilities:
    """Describes what a plugin is allowed to do."""
    can_modify_cues: bool = False
    can_access_project: bool = True
    can_show_ui: bool = False
    can_access_settings: bool = True
    can_access_network: bool = False
    can_access_filesystem: bool = False


def requires_api_version(min_version: int):
    """
    Decorator to mark methods that require a minimum API version.
    
    Args:
        min_version: Minimum required API version
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if PLUGIN_API_VERSION < min_version:
                raise NotImplementedError(
                    f"This feature requires Plugin API v{min_version}, "
                    f"but current version is v{PLUGIN_API_VERSION}"
                )
            return func(self, *args, **kwargs)
        wrapper._min_api_version = min_version
        return wrapper
    return decorator


class PluginContext:
    """
    Plugin context - central API for plugins.
    
    Provides safe, versioned access to application features.
    Plugins should use this instead of accessing internal APIs directly.
    
    Example:
        class MyPlugin(QAPlugin):
            def check(self, project, cues):
                # Use context for logging
                self.context.log_info("Starting check...")
                
                # Get project metadata
                name = self.context.get_project_name()
                
                # Subscribe to events
                self.context.subscribe(PluginEvent.CUE_CHANGED, self.on_cue_changed)
    """
    
    def __init__(
        self,
        plugin_id: str,
        plugin_name: str,
        capabilities: Optional[PluginCapabilities] = None
    ):
        """
        Initialize plugin context.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_name: Human-readable plugin name
            capabilities: Plugin capability restrictions
        """
        self._plugin_id = plugin_id
        self._plugin_name = plugin_name
        self._capabilities = capabilities or PluginCapabilities()
        self._logger = logging.getLogger(f"plugin.{plugin_id}")
        self._event_handlers: Dict[PluginEvent, List[Callable]] = {}
        self._main_window: Optional["QMainWindow"] = None
        self._project: Optional["Project"] = None
        self._settings: Dict[str, Any] = {}
        
    # =========================================================================
    # API Version Information
    # =========================================================================
    
    @property
    def api_version(self) -> int:
        """Get current Plugin API version."""
        return PLUGIN_API_VERSION
    
    @property
    def api_version_min(self) -> int:
        """Get minimum supported Plugin API version."""
        return PLUGIN_API_VERSION_MIN
    
    def is_api_compatible(self, required_version: int) -> bool:
        """
        Check if the current API version is compatible with required version.
        
        Args:
            required_version: Version required by the plugin
            
        Returns:
            True if compatible
        """
        return PLUGIN_API_VERSION_MIN <= required_version <= PLUGIN_API_VERSION
    
    # =========================================================================
    # Logging
    # =========================================================================
    
    def log_debug(self, message: str) -> None:
        """Log debug message."""
        self._logger.debug(f"[{self._plugin_name}] {message}")
    
    def log_info(self, message: str) -> None:
        """Log info message."""
        self._logger.info(f"[{self._plugin_name}] {message}")
    
    def log_warning(self, message: str) -> None:
        """Log warning message."""
        self._logger.warning(f"[{self._plugin_name}] {message}")
    
    def log_error(self, message: str) -> None:
        """Log error message."""
        self._logger.error(f"[{self._plugin_name}] {message}")
    
    def log_exception(self, message: str, exc: Exception) -> None:
        """Log exception with traceback."""
        self._logger.exception(f"[{self._plugin_name}] {message}: {exc}")
    
    # =========================================================================
    # Project Access (read-only by default)
    # =========================================================================
    
    def set_project(self, project: Optional["Project"]) -> None:
        """
        Set current project reference.
        Called by the plugin system, not by plugins.
        """
        self._project = project
    
    def get_project_name(self) -> Optional[str]:
        """Get current project name."""
        if self._project:
            return self._project.name
        return None
    
    def get_project_path(self) -> Optional[Path]:
        """Get current project file path."""
        if self._project and self._project.file_path:
            return Path(self._project.file_path)
        return None
    
    def get_source_language(self) -> Optional[str]:
        """Get project source language code."""
        if self._project:
            return self._project.source_language
        return None
    
    def get_target_language(self) -> Optional[str]:
        """Get project target language code."""
        if self._project:
            return self._project.target_language
        return None
    
    def get_cue_count(self) -> int:
        """Get number of cues in project."""
        if self._project:
            return len(self._project.cues) if self._project.cues else 0
        return 0
    
    def get_video_path(self) -> Optional[Path]:
        """Get linked video file path."""
        if self._project and self._project.video_path:
            return Path(self._project.video_path)
        return None
    
    # =========================================================================
    # Cue Access (requires can_modify_cues for writes)
    # =========================================================================
    
    def get_cue_by_id(self, cue_id: int) -> Optional["Cue"]:
        """
        Get cue by ID.
        
        Args:
            cue_id: Cue database ID
            
        Returns:
            Cue object or None
        """
        if not self._project or not self._project.cues:
            return None
        for cue in self._project.cues:
            if cue.id == cue_id:
                return cue
        return None
    
    def get_cue_by_index(self, index: int) -> Optional["Cue"]:
        """
        Get cue by index.
        
        Args:
            index: Zero-based cue index
            
        Returns:
            Cue object or None
        """
        if not self._project or not self._project.cues:
            return None
        if 0 <= index < len(self._project.cues):
            return self._project.cues[index]
        return None
    
    def iter_cues(self):
        """Iterate over all cues."""
        if self._project and self._project.cues:
            yield from self._project.cues
    
    # =========================================================================
    # Event System
    # =========================================================================
    
    def subscribe(self, event: PluginEvent, handler: Callable) -> None:
        """
        Subscribe to an event.
        
        Args:
            event: Event type to subscribe to
            handler: Callback function
        """
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        if handler not in self._event_handlers[event]:
            self._event_handlers[event].append(handler)
            self.log_debug(f"Subscribed to {event.name}")
    
    def unsubscribe(self, event: PluginEvent, handler: Callable) -> None:
        """
        Unsubscribe from an event.
        
        Args:
            event: Event type to unsubscribe from
            handler: Callback function to remove
        """
        if event in self._event_handlers and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)
            self.log_debug(f"Unsubscribed from {event.name}")
    
    def _dispatch_event(self, event: PluginEvent, *args, **kwargs) -> None:
        """
        Dispatch event to all subscribers.
        Called by the plugin system, not by plugins.
        """
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    self.log_exception(f"Error in event handler for {event.name}", e)
    
    # =========================================================================
    # Settings Access
    # =========================================================================
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get plugin setting value.
        
        Args:
            key: Setting key
            default: Default value if not found
            
        Returns:
            Setting value
        """
        return self._settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set plugin setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        if self._capabilities.can_access_settings:
            self._settings[key] = value
            self.log_debug(f"Setting '{key}' updated")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all plugin settings."""
        return self._settings.copy()
    
    def load_settings(self, settings: Dict[str, Any]) -> None:
        """
        Load settings from dict.
        Called by the plugin system, not by plugins.
        """
        self._settings = settings.copy()
    
    # =========================================================================
    # UI Access (requires can_show_ui)
    # =========================================================================
    
    def set_main_window(self, window: "QMainWindow") -> None:
        """
        Set main window reference.
        Called by the plugin system, not by plugins.
        """
        self._main_window = window
    
    def get_main_window(self) -> Optional["QMainWindow"]:
        """
        Get main window reference.
        
        Returns:
            QMainWindow or None if UI access not allowed
        """
        if self._capabilities.can_show_ui:
            return self._main_window
        return None
    
    def show_message(self, title: str, message: str, level: str = "info") -> None:
        """
        Show message dialog to user.
        
        Args:
            title: Dialog title
            message: Message text
            level: "info", "warning", or "error"
        """
        if not self._capabilities.can_show_ui or not self._main_window:
            self.log_info(f"[{level.upper()}] {title}: {message}")
            return
        
        from PySide6.QtWidgets import QMessageBox
        
        if level == "error":
            QMessageBox.critical(self._main_window, title, message)
        elif level == "warning":
            QMessageBox.warning(self._main_window, title, message)
        else:
            QMessageBox.information(self._main_window, title, message)
    
    def show_status_message(self, message: str, timeout_ms: int = 3000) -> None:
        """
        Show temporary message in status bar.
        
        Args:
            message: Message text
            timeout_ms: Display duration in milliseconds
        """
        if self._capabilities.can_show_ui and self._main_window:
            status_bar = self._main_window.statusBar()
            if status_bar:
                status_bar.showMessage(message, timeout_ms)
        else:
            self.log_info(f"Status: {message}")
    
    # =========================================================================
    # Application Info
    # =========================================================================
    
    def get_app_version(self) -> str:
        """Get DubSync application version."""
        from dubsync.utils.constants import APP_VERSION
        return APP_VERSION
    
    def get_app_name(self) -> str:
        """Get application name."""
        from dubsync.utils.constants import APP_NAME
        return APP_NAME
    
    def get_app_language(self) -> str:
        """Get current UI language code."""
        from dubsync.i18n import get_current_language
        return get_current_language()
    
    # =========================================================================
    # Translation Support
    # =========================================================================
    
    def translate(self, key: str, **kwargs) -> str:
        """
        Get translated string for plugin.
        
        Args:
            key: Translation key
            **kwargs: Format arguments
            
        Returns:
            Translated string
        """
        from dubsync.i18n.plugin_support import get_plugin_translation
        return get_plugin_translation(self._plugin_id, key, **kwargs)
    
    def t(self, key: str, **kwargs) -> str:
        """Shorthand for translate()."""
        return self.translate(key, **kwargs)


class PluginContextManager:
    """
    Manages plugin contexts for all loaded plugins.
    
    Singleton that provides and tracks all plugin contexts.
    """
    
    _instance: Optional["PluginContextManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._contexts: Dict[str, PluginContext] = {}
            cls._instance._main_window = None
            cls._instance._project = None
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> "PluginContextManager":
        """Get singleton instance."""
        return cls()
    
    def create_context(
        self,
        plugin_id: str,
        plugin_name: str,
        capabilities: Optional[PluginCapabilities] = None
    ) -> PluginContext:
        """
        Create context for a plugin.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_name: Human-readable plugin name
            capabilities: Plugin capability restrictions
            
        Returns:
            New PluginContext instance
        """
        context = PluginContext(plugin_id, plugin_name, capabilities)
        
        # Set current state
        if self._main_window:
            context.set_main_window(self._main_window)
        if self._project:
            context.set_project(self._project)
        
        self._contexts[plugin_id] = context
        return context
    
    def get_context(self, plugin_id: str) -> Optional[PluginContext]:
        """Get context for a plugin."""
        return self._contexts.get(plugin_id)
    
    def set_main_window(self, window: "QMainWindow") -> None:
        """Set main window for all contexts."""
        self._main_window = window
        for context in self._contexts.values():
            context.set_main_window(window)
    
    def set_project(self, project: Optional["Project"]) -> None:
        """Set project for all contexts."""
        self._project = project
        for context in self._contexts.values():
            context.set_project(project)
    
    def dispatch_event(self, event: PluginEvent, *args, **kwargs) -> None:
        """Dispatch event to all plugin contexts."""
        for context in self._contexts.values():
            context._dispatch_event(event, *args, **kwargs)
    
    def shutdown(self) -> None:
        """Shutdown all contexts."""
        self._contexts.clear()
        self._main_window = None
        self._project = None


# Convenience functions
def get_context_manager() -> PluginContextManager:
    """Get the plugin context manager instance."""
    return PluginContextManager.get_instance()


def dispatch_plugin_event(event: PluginEvent, *args, **kwargs) -> None:
    """Dispatch event to all plugins."""
    get_context_manager().dispatch_event(event, *args, **kwargs)
