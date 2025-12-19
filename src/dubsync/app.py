"""
DubSync Application

Fő alkalmazás osztály.
"""

from dubsync.ui.main_window import MainWindow
from dubsync.plugins.base import PluginManager
from dubsync.plugins.registry import PluginRegistry, get_default_plugin_paths
from dubsync.services.settings_manager import SettingsManager


class DubSyncApp(MainWindow):
    """
    DubSync alkalmazás fő osztálya.
    
    Ez a MainWindow kiterjesztése, amely az alkalmazás
    teljes funkcionalitását biztosítja.
    """
    
    def __init__(self):
        # i18n inicializálása a beállított nyelvvel
        self._init_i18n()
        
        # Plugin manager létrehozása és pluginok betöltése
        plugin_manager = self._load_plugins()
        
        # MainWindow inicializálása plugin manager-rel
        super().__init__(plugin_manager)
    
    def _init_i18n(self):
        """
        Többnyelvűség (i18n) inicializálása.
        
        Beállítja a nyelvet a mentett beállítások alapján.
        """
        try:
            from dubsync.i18n import get_locale_manager
            
            settings = SettingsManager()
            locale_manager = get_locale_manager()
            
            # Mentett nyelv betöltése
            saved_lang = settings.language
            if saved_lang:
                locale_manager.set_language(saved_lang)
            
            print(f"Nyelv beállítva: {locale_manager.current_language}")
        except Exception as e:
            print(f"i18n inicializálási hiba: {e}")
    
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
