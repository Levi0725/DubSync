"""
DubSync Application

Primary application class for DubSync.
"""

from dubsync.ui.main_window import MainWindow
from dubsync.plugins.base import PluginManager
from dubsync.plugins.registry import PluginRegistry, get_default_plugin_paths
from dubsync.services.settings_manager import SettingsManager


class DubSyncApp(MainWindow):
    """
    Primary application class for DubSync.
    
    This is an extension of MainWindow that provides
    the full functionality of the application.
    """
    
    def __init__(self):
        # Initialize i18n with the set language
        self._init_i18n()
        
        # Create plugin manager and load plugins
        plugin_manager = self._load_plugins()
        
        # Initialize MainWindow with plugin manager
        super().__init__(plugin_manager)
    
    def _init_i18n(self):
        """
        Initialize internationalization (i18n).
        
        Sets the language based on saved settings.
        """
        try:
            from dubsync.i18n import get_locale_manager

            settings = SettingsManager()
            locale_manager = get_locale_manager()

            if saved_lang := settings.language:
                locale_manager.set_language(saved_lang)

            print(f"Language set to: {locale_manager.current_language}")
        except Exception as e:
            print(f"i18n initialization error: {e}")
    
    def _load_plugins(self) -> PluginManager:
        """
        Initialize plugin system and load plugins.
        
        Returns:
            PluginManager with loaded plugins
        """
        manager = PluginManager()
        registry = PluginRegistry(manager)
        
        # Add default plugin directories
        for path in get_default_plugin_paths():
            registry.add_plugin_path(path)
        
        # Load plugins
        loaded = registry.load_all_plugins()
        print(f"Total of {loaded} plugins loaded.")
        
        return manager
