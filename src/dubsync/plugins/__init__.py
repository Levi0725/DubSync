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
"""

from dubsync.plugins.base import PluginInterface, PluginManager
from dubsync.plugins.registry import PluginRegistry

__all__ = [
    "PluginInterface",
    "PluginManager",
    "PluginRegistry",
]
