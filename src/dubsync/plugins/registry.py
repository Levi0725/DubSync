"""
DubSync Plugin Registry

Plugin discovery and registration.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Optional, List, Type

from dubsync.plugins.base import PluginInterface, PluginManager
from dubsync.plugins.context import (
    PluginContext,
    PluginContextManager,
    PluginCapabilities,
    PLUGIN_API_VERSION,
)
from dubsync.services.settings_manager import SettingsManager
from dubsync.services.logger import get_logger

logger = get_logger(__name__)


class PluginRegistry:
    """
    Plugin registry and loader.
    
    Plugin discovery and loading from the plugins directory.
    """
    
    def __init__(self, manager: PluginManager):
        """
        Initialization.
        
        Args:
            manager: PluginManager object
        """
        self.manager = manager
        self.settings = SettingsManager()
        self._plugin_paths: List[Path] = []
        self._context_manager = PluginContextManager.get_instance()
    
    def add_plugin_path(self, path: Path) -> None:
        """
        Add plugin search path.
        
        Args:
            path: Directory path
        """
        if path.is_dir() and path not in self._plugin_paths:
            self._plugin_paths.append(path)
    
    def discover_plugins(self) -> List[str]:
        """
        Discover plugins in all search paths.
        
        Returns:
            List of found plugin files and packages
        """
        discovered = []

        for plugin_dir in self._plugin_paths:
            if not plugin_dir.exists():
                continue

            # Look for Python files
            discovered.extend(
                str(file_path)
                for file_path in plugin_dir.glob("*.py")
                if not file_path.name.startswith("_")
            )
            # Look for packages (directories with __init__.py)
            for subdir in plugin_dir.iterdir():
                if subdir.is_dir():
                    init_file = subdir / "__init__.py"
                    if init_file.exists():
                        discovered.append(str(subdir))

        return discovered
    
    def load_plugin_from_file(self, file_path: Path) -> Optional[PluginInterface]:
        """
        Load plugin from file.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Plugin object or None
        """
        try:
            # Generate unique module name
            module_name = f"dubsync_plugin_{file_path.stem}"
            
            # Load module
            spec = importlib.util.spec_from_file_location(
                module_name,
                file_path
            )
            
            if spec is None or spec.loader is None:
                return None
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Find Plugin class
            plugin_class = self._find_plugin_class(module)
            if plugin_class is None:
                return None
            
            # Instantiate plugin
            plugin = plugin_class()
            
            # Set plugin directory
            plugin._plugin_dir = file_path.parent
            
            # Pre-load plugin locales before accessing plugin.info
            # This ensures translations are available when info property is accessed
            plugin._load_plugin_locales()
            
            # Check API version compatibility
            min_api = plugin.info.min_api_version
            if min_api > PLUGIN_API_VERSION:
                logger.warning(
                    f"Plugin {plugin.info.id} requires API v{min_api}, "
                    f"but current version is v{PLUGIN_API_VERSION}. Skipping."
                )
                return None
            
            # Create and assign context for the plugin
            capabilities = self._determine_capabilities(plugin)
            context = self._context_manager.create_context(
                plugin_id=plugin.info.id,
                plugin_name=plugin.info.name,
                capabilities=capabilities
            )
            plugin.set_context(context)
            logger.debug(f"Created context for plugin: {plugin.info.id}")
            
            return plugin
            
        except Exception as e:
            logger.error(f"Plugin loading error ({file_path}): {e}")
            return None
    
    def _determine_capabilities(self, plugin: PluginInterface) -> PluginCapabilities:
        """
        Determine plugin capabilities based on its type.
        
        Args:
            plugin: Plugin instance
            
        Returns:
            PluginCapabilities based on plugin type
        """
        from dubsync.plugins.base import (
            ExportPlugin, QAPlugin, UIPlugin, ServicePlugin, TranslationPlugin
        )
        
        # Default capabilities
        caps = PluginCapabilities()
        
        # Adjust based on plugin type
        if isinstance(plugin, UIPlugin):
            caps.can_show_ui = True
            caps.can_access_project = True
        elif isinstance(plugin, QAPlugin):
            caps.can_access_project = True
            caps.can_modify_cues = False  # QA is read-only
        elif isinstance(plugin, ExportPlugin):
            caps.can_access_project = True
            caps.can_access_filesystem = True
        elif isinstance(plugin, TranslationPlugin):
            caps.can_access_network = True
        elif isinstance(plugin, ServicePlugin):
            caps.can_access_network = True
        
        return caps
    
    def _find_plugin_class(self, module) -> Optional[Type[PluginInterface]]:
        """
        Find plugin class in the module.
        
        Args:
            module: Python module
            
        Returns:
            Plugin class or None
        """
        # Look for class named "Plugin"
        if hasattr(module, "Plugin"):
            cls = getattr(module, "Plugin")
            if isinstance(cls, type) and issubclass(cls, PluginInterface):
                return cls
        
        # Look for any class implementing PluginInterface
        for name in dir(module):
            if name.startswith("_"):
                continue
            
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, PluginInterface) and
                obj is not PluginInterface):
                return obj
        
        return None
    
    def load_all_plugins(self) -> int:
        """
        Load all discovered plugins.
        
        Returns:
            Number of successfully loaded plugins
        """
        loaded = 0
        discovered = self.discover_plugins()
        
        # Plugins enabled in settings
        enabled_plugins = self.settings.enabled_plugins
        
        for plugin_path in discovered:
            path = Path(plugin_path)
            
            if path.is_file():
                plugin = self.load_plugin_from_file(path)
            elif path.is_dir():
                init_file = path / "__init__.py"
                plugin = self.load_plugin_from_file(init_file)
            else:
                continue
            
            if plugin:
                # Is the plugin enabled?
                is_enabled = plugin.info.id in enabled_plugins
                
                if self.manager.register(plugin, enabled=is_enabled):
                    loaded += 1
                    status = "✓" if is_enabled else "○"
                    logger.info(f"Plugin loaded [{status}]: {plugin.info}")
        
        return loaded


def get_default_plugin_paths() -> List[Path]:
    """
    Alapértelmezett plugin könyvtárak lekérése.
    
    Returns:
        Könyvtár elérési utak listája
    """
    paths = []

    # Built-in plugins
    builtin_path = Path(__file__).parent / "builtin"
    if builtin_path.exists():
        paths.append(builtin_path)

    # External plugins (külső pluginok)
    external_path = Path(__file__).parent / "external"
    if external_path.exists():
        paths.append(external_path)

    # User plugins (in app data)
    import os
    if appdata := os.environ.get("APPDATA", ""):
        user_plugin_path = Path(appdata) / "DubSync" / "plugins"
        user_plugin_path.mkdir(parents=True, exist_ok=True)
        paths.append(user_plugin_path)

    return paths
