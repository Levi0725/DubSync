"""
DubSync Plugin System

Bővíthető plugin architektúra.

A plugin rendszer lehetővé teszi:
- Export pluginok (DOCX, CSV, stb.)
- QA pluginok (egyedi szabályellenőrzés)
- Egyedi funkciók hozzáadása

Plugin interface:
- Minden plugin egy Python modul
- A modul definiál egy Plugin osztályt
- A Plugin osztály implementálja a PluginInterface-t
"""

from dubsync.plugins.base import PluginInterface, PluginManager
from dubsync.plugins.registry import PluginRegistry

__all__ = [
    "PluginInterface",
    "PluginManager",
    "PluginRegistry",
]
