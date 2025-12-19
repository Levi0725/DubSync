"""
DubSync Settings Manager

Alkalmazás beállítások kezelése.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set
from dataclasses import dataclass, field, asdict

from PySide6.QtCore import QSettings, QStandardPaths


@dataclass
class AppSettings:
    """Alkalmazás beállítások."""
    # Általános beállítások
    default_save_path: str = ""
    default_author_name: str = ""
    auto_save_enabled: bool = True
    auto_save_interval: int = 5  # percben
    
    # UI beállítások
    theme: str = "dark"
    custom_theme_colors: Dict[str, str] = field(default_factory=dict)  # Egyedi téma színek
    font_size: int = 10
    show_line_numbers: bool = True
    compact_mode: bool = False
    
    # Nyelvi beállítások (i18n)
    language: str = "en"  # ISO 639-1 kód (en, hu, stb.)
    
    # Lip-sync beállítások
    lipsync_chars_per_second: float = 13.0
    lipsync_warning_threshold: float = 0.95
    lipsync_error_threshold: float = 1.05
    
    # Export beállítások
    default_export_format: str = "pdf"
    include_source_in_export: bool = True
    
    # Plugin beállítások
    enabled_plugins: Set[str] = field(default_factory=set)
    plugin_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    plugin_panel_visibility: Dict[str, bool] = field(default_factory=dict)  # Plugin panel láthatóság induláskor
    
    # Utolsó útvonalak
    last_project_path: str = ""
    last_import_path: str = ""
    last_export_path: str = ""
    recent_projects: list = field(default_factory=list)


class SettingsManager:
    """
    Beállítások kezelő.
    
    Központi hely az alkalmazás beállításainak kezeléséhez.
    """
    
    _instance: Optional['SettingsManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._settings = AppSettings()
        self._qt_settings = QSettings("DubSync", "DubSync")
        self._config_dir = self._get_config_dir()
        self._settings_file = self._config_dir / "settings.json"
        
        self._load_settings()
    
    def _get_config_dir(self) -> Path:
        """Konfiguráció könyvtár lekérése."""
        # Windows: %APPDATA%/DubSync
        config_path = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        ))
        config_path.mkdir(parents=True, exist_ok=True)
        return config_path
    
    @property
    def config_dir(self) -> Path:
        """Konfiguráció könyvtár."""
        return self._config_dir
    
    @property
    def plugins_dir(self) -> Path:
        """Plugin könyvtár."""
        plugins_path = self._config_dir / "plugins"
        plugins_path.mkdir(parents=True, exist_ok=True)
        return plugins_path
    
    def _load_settings(self) -> None:
        """Beállítások betöltése."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Frissítjük a beállításokat
                for key, value in data.items():
                    if hasattr(self._settings, key):
                        if key == 'enabled_plugins':
                            setattr(self._settings, key, set(value))
                        else:
                            setattr(self._settings, key, value)
            except Exception as e:
                print(f"Beállítások betöltési hiba: {e}")
        
        # Alapértelmezett mentési hely beállítása
        if not self._settings.default_save_path:
            docs_path = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            )
            self._settings.default_save_path = docs_path
    
    def save_settings(self) -> None:
        """Beállítások mentése."""
        try:
            data = asdict(self._settings)
            # Set-et listává alakítjuk JSON-hoz
            data['enabled_plugins'] = list(data['enabled_plugins'])
            
            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Beállítások mentési hiba: {e}")
    
    # Getterek és setterek
    
    @property
    def default_save_path(self) -> str:
        return self._settings.default_save_path
    
    @default_save_path.setter
    def default_save_path(self, value: str) -> None:
        self._settings.default_save_path = value
    
    @property
    def default_author_name(self) -> str:
        return self._settings.default_author_name
    
    @default_author_name.setter
    def default_author_name(self, value: str) -> None:
        self._settings.default_author_name = value
    
    @property
    def theme(self) -> str:
        return self._settings.theme
    
    @theme.setter
    def theme(self, value: str) -> None:
        self._settings.theme = value
    
    @property
    def language(self) -> str:
        return self._settings.language
    
    @language.setter
    def language(self, value: str) -> None:
        self._settings.language = value
    
    @property
    def auto_save_enabled(self) -> bool:
        return self._settings.auto_save_enabled
    
    @auto_save_enabled.setter
    def auto_save_enabled(self, value: bool) -> None:
        self._settings.auto_save_enabled = value
    
    @property
    def auto_save_interval(self) -> int:
        return self._settings.auto_save_interval
    
    @auto_save_interval.setter
    def auto_save_interval(self, value: int) -> None:
        self._settings.auto_save_interval = value
    
    @property
    def lipsync_chars_per_second(self) -> float:
        return self._settings.lipsync_chars_per_second
    
    @lipsync_chars_per_second.setter
    def lipsync_chars_per_second(self, value: float) -> None:
        self._settings.lipsync_chars_per_second = value
    
    @property
    def enabled_plugins(self) -> Set[str]:
        return self._settings.enabled_plugins
    
    @enabled_plugins.setter
    def enabled_plugins(self, value: Set[str]) -> None:
        self._settings.enabled_plugins = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Általános beállítás lekérése kulcs alapján.
        
        Args:
            key: A beállítás neve (pl. 'data_dir', 'theme', stb.)
            default: Alapértelmezett érték ha nem létezik
            
        Returns:
            A beállítás értéke vagy az alapértelmezett
        """
        # Speciális kezelés a data_dir-hez
        if key == "data_dir":
            return str(self._config_dir)
        
        # Próbáljuk meg az AppSettings-ből lekérni
        if hasattr(self._settings, key):
            return getattr(self._settings, key)
        
        return default
    
    def get_plugin_settings(self, plugin_id: str) -> Dict[str, Any]:
        """Plugin beállítások lekérése."""
        return self._settings.plugin_settings.get(plugin_id, {})
    
    def set_plugin_settings(self, plugin_id: str, settings: Dict[str, Any]) -> None:
        """Plugin beállítások mentése."""
        self._settings.plugin_settings[plugin_id] = settings
    
    def get_plugin_panel_visible(self, plugin_id: str) -> bool:
        """Plugin panel indulási láthatóság lekérése."""
        return self._settings.plugin_panel_visibility.get(plugin_id, False)
    
    def set_plugin_panel_visible(self, plugin_id: str, visible: bool) -> None:
        """Plugin panel indulási láthatóság beállítása."""
        self._settings.plugin_panel_visibility[plugin_id] = visible
    
    @property
    def recent_projects(self) -> list:
        return self._settings.recent_projects
    
    def add_recent_project(self, path: str) -> None:
        """Legutóbbi projekt hozzáadása."""
        if path in self._settings.recent_projects:
            self._settings.recent_projects.remove(path)
        self._settings.recent_projects.insert(0, path)
        # Maximum 10 legutóbbi
        self._settings.recent_projects = self._settings.recent_projects[:10]
    
    @property
    def last_project_path(self) -> str:
        return self._settings.last_project_path
    
    @last_project_path.setter
    def last_project_path(self, value: str) -> None:
        self._settings.last_project_path = value
    
    @property
    def font_size(self) -> int:
        return self._settings.font_size
    
    @font_size.setter
    def font_size(self, value: int) -> None:
        self._settings.font_size = value
    
    @property
    def custom_theme_colors(self) -> Dict[str, str]:
        """Egyedi téma színek lekérése."""
        return self._settings.custom_theme_colors
    
    @custom_theme_colors.setter
    def custom_theme_colors(self, value: Dict[str, str]) -> None:
        """Egyedi téma színek beállítása."""
        self._settings.custom_theme_colors = value
    
    # Qt Settings mentés/betöltés ablak geometriához
    
    def save_geometry(self, key: str, value: bytes) -> None:
        """Geometria mentése."""
        self._qt_settings.setValue(f"geometry/{key}", value)
    
    def load_geometry(self, key: str) -> Optional[bytes]:
        """Geometria betöltése."""
        return self._qt_settings.value(f"geometry/{key}")
    
    def save_state(self, key: str, value: bytes) -> None:
        """Állapot mentése."""
        self._qt_settings.setValue(f"state/{key}", value)
    
    def load_state(self, key: str) -> Optional[bytes]:
        """Állapot betöltése."""
        return self._qt_settings.value(f"state/{key}")
