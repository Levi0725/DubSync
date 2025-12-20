"""
DubSync Plugin Base

Plugin default classes and interfaces.
Supports export, QA, import, tool, UI, and service plugins.
"""


import contextlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from dubsync.models.project import Project
    from dubsync.models.cue import Cue
    from PySide6.QtWidgets import QWidget, QMainWindow, QDockWidget, QAction


class PluginType(Enum):
    """
    Plugin types.
    """
    EXPORT = auto()      # Export plugin (PDF, DOCX, CSV, etc.)
    QA = auto()          # Quality assurance plugin
    IMPORT = auto()      # Import plugin (custom formats)
    TOOL = auto()        # Other tool plugin
    UI = auto()          # UI extension plugin (windows, panels, menus)
    SERVICE = auto()     # Background service plugin (APIs, translators)
    LANGUAGE = auto()    # Language extension plugin (i18n)


@dataclass
class PluginDependency:
    """Plugin dependency description."""
    package_name: str       # pip package name
    min_version: str = ""   # Minimum version (optional)
    optional: bool = False  # Optional dependency


@dataclass
class PluginInfo:
    """
    Plugin metadata.
    """
    id: str                     # Unique identifier
    name: str                   # Display name
    version: str                # Version (e.g., "1.0.0")
    author: str                 # Author
    description: str            # Short description
    plugin_type: PluginType     # Plugin type
    dependencies: List[PluginDependency] = field(default_factory=list)
    homepage: str = ""          # Plugin homepage URL
    readme_path: str = ""       # README.md relative path
    icon: str = ""              # Icon emoji or path
    
    def __str__(self) -> str:
        return f"{self.name} v{self.version} by {self.author}"


class PluginInterface(ABC):
    """
    Plugin interface.
    
    Every plugin must implement this interface.
    """
    
    _plugin_dir: Optional[Path] = None  # Plugin directory path
    
    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """
        Plugin információk.
        
        Returns:
            PluginInfo objektum
        """
        pass
    
    def initialize(self) -> bool:
        """
        Plugin initialization.
        
        Called on load. Automatically loads the plugin 
        locale files from the locales/ folder if it exists.
        Returns False to prevent the plugin from loading.
        
        Returns:
            True, if successful
        """
        self._load_plugin_locales()
        return True
    
    def _load_plugin_locales(self) -> None:
        """
        Plugin locale file loading.
        
        Loads all JSON files from the plugin's locales/ folder.
        """
        try:
            # Determine plugin directory
            import inspect
            plugin_file = inspect.getfile(self.__class__)
            plugin_dir = Path(plugin_file).parent
            locales_dir = plugin_dir / "locales"
            
            if locales_dir.exists() and locales_dir.is_dir():
                from dubsync.i18n.plugin_support import load_plugin_translations_from_locales_dir
                load_plugin_translations_from_locales_dir(self.info.id, locales_dir)
        except Exception as e:
            print(f"Error loading plugin locales for {self.info.id}: {e}")
    
    def shutdown(self) -> None:
        """
        Plugin shutdown.
        
        Called when the application is closing.
        """
        pass
    
    def get_settings_widget(self) -> Optional["QWidget"]:
        """
        Get settings widget.
        
        Returns:
            QWidget for settings, or None
        """
        return None
    
    def load_settings(self, settings: Dict[str, Any]) -> None:
        """
        Load plugin settings.
        
        Args:
            settings: Previously saved settings
        """
        pass
    
    def save_settings(self) -> Dict[str, Any]:
        """
        Save plugin settings.
        
        Returns:
            Settings to save
        """
        return {}
    
    def get_long_description(self) -> str:
        """
        Get long description (README content).
        
        Returns:
            Markdown formatted description
        """
        if self._plugin_dir and self.info.readme_path:
            with contextlib.suppress(Exception):
                readme_path = self._plugin_dir / self.info.readme_path
                if readme_path.exists():
                    return readme_path.read_text(encoding='utf-8')
        return self.info.description


class ExportPlugin(PluginInterface):
    """
    Export plugin base class.
    
    Export plugins export to custom formats.
    """
    
    @property
    def file_extension(self) -> str:
        """
        Output file extension.
        
        Returns:
            Extension (e.g., ".docx")
        """
        return ".txt"
    
    @property
    def file_filter(self) -> str:
        """
        File dialog filter.
        
        Returns:
            Filter string (e.g., "Word Document (*.docx)")
        """
        return f"Text Files (*{self.file_extension})"
    
    @abstractmethod
    def export(
        self,
        output_path: Path,
        project: "Project",
        cues: List["Cue"],
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Perform export.
        
        Args:
            output_path: Output file path
            project: Project object
            cues: Cue list
            options: Custom options (optional)
            
        Returns:
            True, if successful
        """
        pass


@dataclass
class QAIssue:
    """
    QA issue description.
    """
    cue_id: int             # Affected cue ID
    severity: str           # "error", "warning", "info"
    message: str            # Issue description
    suggestion: str = ""    # Suggestion for fix


class QAPlugin(PluginInterface):
    """
    QA (quality assurance) plugin base class.
    
    QA plugins check custom rules.
    """
    
    @abstractmethod
    def check(
        self,
        project: "Project",
        cues: List["Cue"]
    ) -> List[QAIssue]:
        """
        Perform check.
        
        Args:
            project: Project object
            cues: Cue list
            
        Returns:
            List of found issues
        """
        pass


class UIPlugin(PluginInterface):
    """
    UI extension plugin base class.
    
    UI plugins can add new windows, panels, menus.
    """
    
    _main_window: Optional["QMainWindow"] = None
    
    def set_main_window(self, main_window: "QMainWindow") -> None:
        """Set main window reference."""
        self._main_window = main_window
    
    def create_dock_widget(self) -> Optional["QDockWidget"]:
        """
        Create dockable widget.
        
        Returns:
            QDockWidget or None
        """
        return None
    
    def create_menu_items(self) -> List["QAction"]:
        """
        Create menu items.
        
        Returns:
            List of QAction for the menu
        """
        return []
    
    def create_toolbar_items(self) -> List["QAction"]:
        """
        Create toolbar items.
        
        Returns:
            List of QAction for the toolbar
        """
        return []
    
    def on_cue_selected(self, cue: "Cue") -> None:
        """
        Cue selection event.
        
        Args:
            cue: Selected cue
        """
        pass
    
    def on_project_opened(self, project: "Project") -> None:
        """
        Project opened event.
        
        Args:
            project: Opened project
        """
        pass
    
    def on_project_closed(self) -> None:
        """Project closed event."""
        pass


class ServicePlugin(PluginInterface):
    """
    Background service plugin base class.
    
    Service plugins provide APIs, translators, and other services.
    """
    
    @abstractmethod
    def get_service_name(self) -> str:
        """
        Service name.
        
        Returns:
            Service identifier name
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if the service is available.
        
        Returns:
            True if available
        """
        return True
    
    def get_status(self) -> str:
        """
        Service status.
        
        Returns:
            Status text
        """
        return "OK" if self.is_available() else "Unavailable"


class TranslationPlugin(ServicePlugin):
    """
    Translation service plugin base class.
    
    Translation plugins provide text translation.
    """
    
    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Translate text.
        
        Args:
            text: Text to translate
            source_lang: Source language code (e.g., "en")
            target_lang: Target language code (e.g., "hu")
            
        Returns:
            Translated text
        """
        pass
    
    def get_supported_languages(self) -> List[tuple]:
        """
        Get supported language pairs.
        
        Returns:
            List of (source_code, target_code, display_name) tuples
        """
        return []
    
    def get_service_name(self) -> str:
        return f"translator_{self.info.id}"


class LanguagePlugin(PluginInterface):
    """
    Language extension plugin base class.
    
    Language plugins can add new languages to the application.
    """
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """
        Language ISO 639-1 code.
        
        Returns:
            Language code (e.g., "de", "es", "fr")
        """
        pass
    
    @property
    @abstractmethod
    def language_name(self) -> str:
        """
        Language native name.
        
        Returns:
            Native name (e.g., "Deutsch", "Español")
        """
        pass
    
    @property
    def language_name_en(self) -> str:
        """
        Language name in English.
        
        Returns:
            English name (e.g., "German", "Spanish")
        """
        return self.language_name
    
    @property
    def language_flag(self) -> str:
        """
        Language flag emoji.
        
        Returns:
            Flag emoji (e.g., "🇩🇪", "🇪🇸")
        """
        return ""
    
    @property
    def is_rtl(self) -> bool:
        """
        Is right-to-left writing.
        
        Returns:
            True if RTL language
        """
        return False
    
    def get_translations_path(self) -> Optional["Path"]:
        """
        Path to translations JSON file.
        
        Returns:
            Path object or None
        """
        if self._plugin_dir:
            path = self._plugin_dir / "locales" / f"{self.language_code}.json"
            if path.exists():
                return path
        return None
    
    def initialize(self) -> bool:
        """
        Plugin initialization - language registration.
        
        Returns:
            True if successful
        """
        try:
            from dubsync.i18n import get_locale_manager
            from dubsync.i18n.manager import LanguageInfo
            
            locale_mgr = get_locale_manager()
            
            # Create language info
            lang_info = LanguageInfo(
                code=self.language_code,
                name=self.language_name,
                name_en=self.language_name_en,
                flag=self.language_flag,
                rtl=self.is_rtl
            )
            
            # Register language
            translations_path = self.get_translations_path()
            locale_mgr.register_language(lang_info, translations_path)
            
            return True
        except Exception as e:
            print(f"Error initializing language plugin: {e}")
            return False


class PluginManager:
    """
    Plugin manager.
    
    Loading, managing, and running plugins.
    """
    
    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}
        self._export_plugins: Dict[str, ExportPlugin] = {}
        self._qa_plugins: Dict[str, QAPlugin] = {}
        self._ui_plugins: Dict[str, UIPlugin] = {}
        self._service_plugins: Dict[str, ServicePlugin] = {}
        self._translation_plugins: Dict[str, TranslationPlugin] = {}
        self._language_plugins: Dict[str, LanguagePlugin] = {}
        self._enabled_plugins: set = set()
        self._plugin_settings: Dict[str, Dict[str, Any]] = {}
    
    def register(self, plugin: PluginInterface, enabled: bool = False) -> bool:
        """
        Register plugin.
        
        Args:
            plugin: Plugin object
            enabled: Enabled by default (default: False)
            
        Returns:
            True if successful
        """
        info = plugin.info
        
        if info.id in self._plugins:
            return False
        
        if not plugin.initialize():
            return False
        
        self._plugins[info.id] = plugin
        
        if enabled:
            self._enabled_plugins.add(info.id)
        
        # Type-based registration - a plugin can be multiple types at once!
        if isinstance(plugin, TranslationPlugin):
            self._translation_plugins[info.id] = plugin
        
        if isinstance(plugin, ServicePlugin):
            self._service_plugins[info.id] = plugin
        
        if isinstance(plugin, UIPlugin):
            self._ui_plugins[info.id] = plugin
        
        if isinstance(plugin, ExportPlugin):
            self._export_plugins[info.id] = plugin
        
        if isinstance(plugin, QAPlugin):
            self._qa_plugins[info.id] = plugin
        
        if isinstance(plugin, LanguagePlugin):
            self._language_plugins[info.id] = plugin
        
        return True
    
    def unregister(self, plugin_id: str) -> bool:
        """
        Unregister plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if successful
        """
        if plugin_id not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_id]
        plugin.shutdown()
        
        del self._plugins[plugin_id]
        self._enabled_plugins.discard(plugin_id)
        self._export_plugins.pop(plugin_id, None)
        self._qa_plugins.pop(plugin_id, None)
        self._ui_plugins.pop(plugin_id, None)
        self._service_plugins.pop(plugin_id, None)
        self._translation_plugins.pop(plugin_id, None)
        self._language_plugins.pop(plugin_id, None)
        
        return True
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable plugin."""
        if plugin_id in self._plugins:
            self._enabled_plugins.add(plugin_id)
            return True
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable plugin."""
        self._enabled_plugins.discard(plugin_id)
        return True
    
    def is_enabled(self, plugin_id: str) -> bool:
        """Check if plugin is enabled."""
        return plugin_id in self._enabled_plugins
    
    def get_enabled_plugins(self) -> set:
        """Get list of enabled plugins."""
        return self._enabled_plugins.copy()
    
    def set_enabled_plugins(self, enabled: set) -> None:
        """Set enabled plugins."""
        self._enabled_plugins = enabled.copy()
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Get plugin by identifier."""
        return self._plugins.get(plugin_id)
    
    def get_all_plugins(self) -> List[PluginInterface]:
        """Get all plugins."""
        return list(self._plugins.values())
    
    def get_export_plugins(self, enabled_only: bool = True) -> List[ExportPlugin]:
        """Get export plugins."""
        plugins = list(self._export_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_qa_plugins(self, enabled_only: bool = True) -> List[QAPlugin]:
        """Get QA plugins."""
        plugins = list(self._qa_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_ui_plugins(self, enabled_only: bool = True) -> List[UIPlugin]:
        """Get UI plugins."""
        plugins = list(self._ui_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_service_plugins(self, enabled_only: bool = True) -> List[ServicePlugin]:
        """Get service plugins."""
        plugins = list(self._service_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_translation_plugins(self, enabled_only: bool = True) -> List[TranslationPlugin]:
        """Get translation plugins."""
        plugins = list(self._translation_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_language_plugins(self, enabled_only: bool = True) -> List[LanguagePlugin]:
        """Get language plugins."""
        plugins = list(self._language_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def save_plugin_settings(self, plugin_id: str, settings: Dict[str, Any]) -> None:
        """Save plugin settings."""
        self._plugin_settings[plugin_id] = settings
    
    def get_plugin_settings(self, plugin_id: str) -> Dict[str, Any]:
        """Get plugin settings."""
        return self._plugin_settings.get(plugin_id, {})
    
    def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in self._plugins.values():
            plugin.shutdown()
        
        self._plugins.clear()
        self._export_plugins.clear()
        self._qa_plugins.clear()
        self._ui_plugins.clear()
        self._service_plugins.clear()
        self._translation_plugins.clear()
        self._language_plugins.clear()
        self._enabled_plugins.clear()
