"""
DubSync Plugin System

Expandable plugin architecture.

The plugin system allows:
- Export plugins (DOCX, CSV, etc.)
- QA plugins (custom rule checks)
- Adding custom features

Plugin interface:
- Each plugin is a Python module
- The module defines a Plugin class
- The Plugin class implements the PluginInterface

Plugin API versioning:
- PLUGIN_API_VERSION indicates the current API version
- Plugins can specify min_api_version in PluginInfo
- Incompatible plugins are skipped during loading
"""

from dubsync.plugins.base import PluginInterface, PluginManager
from dubsync.plugins.registry import PluginRegistry
from dubsync.plugins.context import (
    PluginContext,
    PluginContextManager,
    PluginCapabilities,
    PluginEvent,
    PLUGIN_API_VERSION,
    PLUGIN_API_VERSION_MIN,
    get_context_manager,
    dispatch_plugin_event,
)

__all__ = [
    # Core
    "PluginInterface",
    "PluginManager",
    "PluginRegistry",
    # Context API
    "PluginContext",
    "PluginContextManager",
    "PluginCapabilities",
    "PluginEvent",
    # Version info
    "PLUGIN_API_VERSION",
    "PLUGIN_API_VERSION_MIN",
    # Helpers
    "get_context_manager",
    "dispatch_plugin_event",
]
