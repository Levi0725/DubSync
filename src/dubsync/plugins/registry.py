"""
DubSync Plugin Registry

Plugin felfedezés és regisztrálás.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Optional, List, Type

from dubsync.plugins.base import PluginInterface, PluginManager
from dubsync.services.settings_manager import SettingsManager


class PluginRegistry:
    """
    Plugin registry és loader.
    
    Pluginok felfedezése és betöltése a plugins könyvtárból.
    """
    
    def __init__(self, manager: PluginManager):
        """
        Inicializálás.
        
        Args:
            manager: PluginManager objektum
        """
        self.manager = manager
        self.settings = SettingsManager()
        self._plugin_paths: List[Path] = []
    
    def add_plugin_path(self, path: Path) -> None:
        """
        Plugin keresési útvonal hozzáadása.
        
        Args:
            path: Könyvtár útvonal
        """
        if path.is_dir() and path not in self._plugin_paths:
            self._plugin_paths.append(path)
    
    def discover_plugins(self) -> List[str]:
        """
        Pluginok felfedezése az összes keresési útvonalon.
        
        Returns:
            Talált plugin fájlok listája
        """
        discovered = []
        
        for plugin_dir in self._plugin_paths:
            if not plugin_dir.exists():
                continue
            
            # Look for Python files
            for file_path in plugin_dir.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue
                discovered.append(str(file_path))
            
            # Look for packages (directories with __init__.py)
            for subdir in plugin_dir.iterdir():
                if subdir.is_dir():
                    init_file = subdir / "__init__.py"
                    if init_file.exists():
                        discovered.append(str(subdir))
        
        return discovered
    
    def load_plugin_from_file(self, file_path: Path) -> Optional[PluginInterface]:
        """
        Plugin betöltése fájlból.
        
        Args:
            file_path: Python fájl elérési útja
            
        Returns:
            Plugin objektum vagy None
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
            
            # Plugin könyvtár beállítása
            plugin._plugin_dir = file_path.parent
            
            return plugin
            
        except Exception as e:
            print(f"Plugin betöltési hiba ({file_path}): {e}")
            return None
    
    def _find_plugin_class(self, module) -> Optional[Type[PluginInterface]]:
        """
        Plugin osztály keresése a modulban.
        
        Args:
            module: Python modul
            
        Returns:
            Plugin osztály vagy None
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
        Összes felfedezett plugin betöltése.
        
        Returns:
            Sikeresen betöltött pluginok száma
        """
        loaded = 0
        discovered = self.discover_plugins()
        
        # Beállításokból engedélyezett pluginok
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
                # Plugin engedélyezett-e?
                is_enabled = plugin.info.id in enabled_plugins
                
                if self.manager.register(plugin, enabled=is_enabled):
                    loaded += 1
                    status = "✓" if is_enabled else "○"
                    print(f"Plugin betöltve [{status}]: {plugin.info}")
        
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
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        user_plugin_path = Path(appdata) / "DubSync" / "plugins"
        user_plugin_path.mkdir(parents=True, exist_ok=True)
        paths.append(user_plugin_path)
    
    return paths
