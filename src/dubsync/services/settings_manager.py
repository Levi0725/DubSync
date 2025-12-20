"""
DubSync Settings Manager

App settings management.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set
from dataclasses import dataclass, field, asdict

from PySide6.QtCore import QSettings, QStandardPaths


@dataclass
class AppSettings:
    """Application settings."""
    # General settings
    default_save_path: str = ""
    default_author_name: str = ""
    auto_save_enabled: bool = True
    auto_save_interval: int = 5  # in minutes
    
    # UI settings
    theme: str = "dark"
    custom_theme_colors: Dict[str, str] = field(default_factory=dict)  # Custom theme colors
    font_size: int = 10
    show_line_numbers: bool = True
    compact_mode: bool = False
    
    # Language settings (i18n)
    language: str = "en"  # ISO 639-1 code (en, hu, etc.)
    
    # Lip-sync settings
    lipsync_chars_per_second: float = 13.0
    lipsync_warning_threshold: float = 0.95
    lipsync_error_threshold: float = 1.05
    
    # Export settings
    default_export_format: str = "pdf"
    include_source_in_export: bool = True
    
    # Plugin settings
    enabled_plugins: Set[str] = field(default_factory=set)
    plugin_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    plugin_panel_visibility: Dict[str, bool] = field(default_factory=dict)  # Plugin panel visibility on startup
    
    # Last paths
    last_project_path: str = ""
    last_import_path: str = ""
    last_export_path: str = ""
    recent_projects: list = field(default_factory=list)


class SettingsManager:
    """
    Settings manager.
    
    Central place for managing application settings.
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
        """Get configuration directory."""
        # Windows: %APPDATA%/DubSync
        config_path = Path(QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppDataLocation
        ))
        config_path.mkdir(parents=True, exist_ok=True)
        return config_path
    
    @property
    def config_dir(self) -> Path:
        """Configuration directory."""
        return self._config_dir
    
    @property
    def plugins_dir(self) -> Path:
        """Plugins directory."""
        plugins_path = self._config_dir / "plugins"
        plugins_path.mkdir(parents=True, exist_ok=True)
        return plugins_path
    
    def _load_settings(self) -> None:
        """Load settings."""
        if self._settings_file.exists():
            try:
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Update settings
                for key, value in data.items():
                    if hasattr(self._settings, key):
                        if key == 'enabled_plugins':
                            setattr(self._settings, key, set(value))
                        else:
                            setattr(self._settings, key, value)
            except Exception as e:
                print(f"Error loading settings: {e}")
        
        # Set default save path
        if not self._settings.default_save_path:
            docs_path = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            )
            self._settings.default_save_path = docs_path
    
    def save_settings(self) -> None:
        """Save settings."""
        try:
            data = asdict(self._settings)
            # Convert set to list for JSON
            data['enabled_plugins'] = list(data['enabled_plugins'])
            
            with open(self._settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    # Getters and setters
    
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
        General setting retrieval by key.
        
        Args:
            key: The name of the setting (e.g., 'data_dir', 'theme', etc.)
            default: Default value if it does not exist
            
        Returns:
            The value of the setting or the default
        """
        # Special handling for data_dir
        if key == "data_dir":
            return str(self._config_dir)
        
        # Try to get from AppSettings
        if hasattr(self._settings, key):
            return getattr(self._settings, key)
        
        return default
    
    def get_plugin_settings(self, plugin_id: str) -> Dict[str, Any]:
        """Get plugin settings."""
        return self._settings.plugin_settings.get(plugin_id, {})
    
    def set_plugin_settings(self, plugin_id: str, settings: Dict[str, Any]) -> None:
        """Save plugin settings."""
        self._settings.plugin_settings[plugin_id] = settings
    
    def get_plugin_panel_visible(self, plugin_id: str) -> bool:
        """Get plugin panel visibility at startup."""
        return self._settings.plugin_panel_visibility.get(plugin_id, False)
    
    def set_plugin_panel_visible(self, plugin_id: str, visible: bool) -> None:
        """Set plugin panel visibility at startup."""
        self._settings.plugin_panel_visibility[plugin_id] = visible
    
    @property
    def recent_projects(self) -> list:
        return self._settings.recent_projects
    
    def add_recent_project(self, path: str) -> None:
        """Add recent project."""
        if path in self._settings.recent_projects:
            self._settings.recent_projects.remove(path)
        self._settings.recent_projects.insert(0, path)
        # Maximum 10 recent
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
        """Get custom theme colors."""
        return self._settings.custom_theme_colors
    
    @custom_theme_colors.setter
    def custom_theme_colors(self, value: Dict[str, str]) -> None:
        """Set custom theme colors."""
        self._settings.custom_theme_colors = value
    
    # Qt Settings save/load for window geometry
    
    def save_geometry(self, key: str, value: bytes) -> None:
        """Save geometry."""
        self._qt_settings.setValue(f"geometry/{key}", value)
    
    def load_geometry(self, key: str) -> Optional[bytes]:
        """Load geometry."""
        return self._qt_settings.value(f"geometry/{key}")
    
    def save_state(self, key: str, value: bytes) -> None:
        """Save state."""
        self._qt_settings.setValue(f"state/{key}", value)
    
    def load_state(self, key: str) -> Optional[bytes]:
        """Load state."""
        return self._qt_settings.value(f"state/{key}")
