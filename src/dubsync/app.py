"""
DubSync Application

Fő alkalmazás osztály.
"""

from dubsync.ui.main_window import MainWindow
from dubsync.plugins.base import PluginManager
from dubsync.plugins.registry import PluginRegistry, get_default_plugin_paths


class DubSyncApp(MainWindow):
    """
    DubSync alkalmazás fő osztálya.
    
    Ez a MainWindow kiterjesztése, amely az alkalmazás
    teljes funkcionalitását biztosítja.
    """
    
    def __init__(self):
        # Plugin manager létrehozása és pluginok betöltése
        plugin_manager = self._load_plugins()
        
        # MainWindow inicializálása plugin manager-rel
        super().__init__(plugin_manager)
    
    def _load_plugins(self) -> PluginManager:
        """
        Plugin rendszer inicializálása és pluginok betöltése.
        
        Returns:
            PluginManager a betöltött pluginokkal
        """
        manager = PluginManager()
        registry = PluginRegistry(manager)
        
        # Alapértelmezett plugin könyvtárak hozzáadása
        for path in get_default_plugin_paths():
            registry.add_plugin_path(path)
        
        # Pluginok betöltése
        loaded = registry.load_all_plugins()
        print(f"Összesen {loaded} plugin betöltve.")
        
        return manager
