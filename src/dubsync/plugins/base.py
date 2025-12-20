"""
DubSync Plugin Base

Plugin alap osztályok és interfészek.
Támogatja az export, QA, import, tool, UI és service pluginokat.
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
    Plugin típusok.
    """
    EXPORT = auto()      # Export plugin (PDF, DOCX, CSV, stb.)
    QA = auto()          # Minőségellenőrzés plugin
    IMPORT = auto()      # Import plugin (egyedi formátumok)
    TOOL = auto()        # Egyéb eszköz plugin
    UI = auto()          # UI bővítő plugin (ablakok, panelek, menük)
    SERVICE = auto()     # Háttérszolgáltatás plugin (API-k, fordítók)
    LANGUAGE = auto()    # Nyelv bővítő plugin (i18n)


@dataclass
class PluginDependency:
    """Plugin függőség leírása."""
    package_name: str       # pip package név
    min_version: str = ""   # Minimum verzió (opcionális)
    optional: bool = False  # Opcionális függőség


@dataclass
class PluginInfo:
    """
    Plugin metaadatok.
    """
    id: str                     # Egyedi azonosító
    name: str                   # Megjelenített név
    version: str                # Verzió (pl. "1.0.0")
    author: str                 # Szerző
    description: str            # Rövid leírás
    plugin_type: PluginType     # Plugin típus
    dependencies: List[PluginDependency] = field(default_factory=list)
    homepage: str = ""          # Plugin honlap URL
    readme_path: str = ""       # README.md relatív útvonal
    icon: str = ""              # Ikon emoji vagy path
    
    def __str__(self) -> str:
        return f"{self.name} v{self.version} by {self.author}"


class PluginInterface(ABC):
    """
    Plugin interfész.
    
    Minden plugin-nak implementálnia kell ezt az interfészt.
    """
    
    _plugin_dir: Optional[Path] = None  # Plugin könyvtár útvonala
    
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
        Plugin inicializálása.
        
        Betöltéskor hívódik. Automatikusan betölti a plugin 
        locale fájljait a locales/ mappából ha létezik.
        Visszatérési érték False esetén a plugin nem töltődik be.
        
        Returns:
            True, ha sikeres
        """
        self._load_plugin_locales()
        return True
    
    def _load_plugin_locales(self) -> None:
        """
        Plugin locale fájlok betöltése.
        
        A plugin locales/ mappájából tölti be az összes JSON fájlt.
        """
        try:
            # Plugin könyvtár meghatározása
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
        Plugin leállítása.
        
        Az alkalmazás bezárásakor hívódik.
        """
        pass
    
    def get_settings_widget(self) -> Optional["QWidget"]:
        """
        Beállítások widget lekérése.
        
        Returns:
            QWidget a beállításokhoz, vagy None
        """
        return None
    
    def load_settings(self, settings: Dict[str, Any]) -> None:
        """
        Plugin beállítások betöltése.
        
        Args:
            settings: Korábban mentett beállítások
        """
        pass
    
    def save_settings(self) -> Dict[str, Any]:
        """
        Plugin beállítások mentése.
        
        Returns:
            Mentendő beállítások
        """
        return {}
    
    def get_long_description(self) -> str:
        """
        Hosszú leírás lekérése (README tartalma).
        
        Returns:
            Markdown formátumú leírás
        """
        if self._plugin_dir and self.info.readme_path:
            with contextlib.suppress(Exception):
                readme_path = self._plugin_dir / self.info.readme_path
                if readme_path.exists():
                    return readme_path.read_text(encoding='utf-8')
        return self.info.description


class ExportPlugin(PluginInterface):
    """
    Export plugin alap osztály.
    
    Export pluginok egyedi formátumokba exportálnak.
    """
    
    @property
    def file_extension(self) -> str:
        """
        Kimeneti fájl kiterjesztése.
        
        Returns:
            Kiterjesztés (pl. ".docx")
        """
        return ".txt"
    
    @property
    def file_filter(self) -> str:
        """
        Fájl dialógus szűrő.
        
        Returns:
            Szűrő string (pl. "Word dokumentum (*.docx)")
        """
        return f"Szövegfájl (*{self.file_extension})"
    
    @abstractmethod
    def export(
        self,
        output_path: Path,
        project: "Project",
        cues: List["Cue"],
        options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Export végrehajtása.
        
        Args:
            output_path: Kimeneti fájl elérési útja
            project: Projekt objektum
            cues: Cue lista
            options: Egyedi opciók (opcionális)
            
        Returns:
            True, ha sikeres
        """
        pass


@dataclass
class QAIssue:
    """
    QA probléma leírása.
    """
    cue_id: int             # Érintett cue azonosító
    severity: str           # "error", "warning", "info"
    message: str            # Probléma leírása
    suggestion: str = ""    # Javítási javaslat


class QAPlugin(PluginInterface):
    """
    QA (minőségellenőrzés) plugin alap osztály.
    
    QA pluginok egyedi szabályokat ellenőriznek.
    """
    
    @abstractmethod
    def check(
        self,
        project: "Project",
        cues: List["Cue"]
    ) -> List[QAIssue]:
        """
        Ellenőrzés végrehajtása.
        
        Args:
            project: Projekt objektum
            cues: Cue lista
            
        Returns:
            Talált problémák listája
        """
        pass


class UIPlugin(PluginInterface):
    """
    UI bővítő plugin alap osztály.
    
    UI pluginok új ablakokat, paneleket, menüket adhatnak hozzá.
    """
    
    _main_window: Optional["QMainWindow"] = None
    
    def set_main_window(self, main_window: "QMainWindow") -> None:
        """Fő ablak referencia beállítása."""
        self._main_window = main_window
    
    def create_dock_widget(self) -> Optional["QDockWidget"]:
        """
        Dokkolható widget létrehozása.
        
        Returns:
            QDockWidget vagy None
        """
        return None
    
    def create_menu_items(self) -> List["QAction"]:
        """
        Menü elemek létrehozása.
        
        Returns:
            QAction lista a menühöz
        """
        return []
    
    def create_toolbar_items(self) -> List["QAction"]:
        """
        Eszköztár elemek létrehozása.
        
        Returns:
            QAction lista az eszköztárhoz
        """
        return []
    
    def on_cue_selected(self, cue: "Cue") -> None:
        """
        Cue kiválasztás esemény.
        
        Args:
            cue: Kiválasztott cue
        """
        pass
    
    def on_project_opened(self, project: "Project") -> None:
        """
        Projekt megnyitás esemény.
        
        Args:
            project: Megnyitott projekt
        """
        pass
    
    def on_project_closed(self) -> None:
        """Projekt bezárás esemény."""
        pass


class ServicePlugin(PluginInterface):
    """
    Háttérszolgáltatás plugin alap osztály.
    
    Service pluginok API-kat, fordítókat és más szolgáltatásokat biztosítanak.
    """
    
    @abstractmethod
    def get_service_name(self) -> str:
        """
        Szolgáltatás neve.
        
        Returns:
            Szolgáltatás azonosító név
        """
        pass
    
    def is_available(self) -> bool:
        """
        Ellenőrzi, hogy a szolgáltatás elérhető-e.
        
        Returns:
            True, ha elérhető
        """
        return True
    
    def get_status(self) -> str:
        """
        Szolgáltatás állapot.
        
        Returns:
            Állapot szöveg
        """
        return "OK" if self.is_available() else "Nem elérhető"


class TranslationPlugin(ServicePlugin):
    """
    Fordító szolgáltatás plugin alap osztály.
    
    Translation pluginok szövegfordítást biztosítanak.
    """
    
    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """
        Szöveg fordítása.
        
        Args:
            text: Fordítandó szöveg
            source_lang: Forrásnyelv kód (pl. "en")
            target_lang: Célnyelv kód (pl. "hu")
            
        Returns:
            Lefordított szöveg
        """
        pass
    
    def get_supported_languages(self) -> List[tuple]:
        """
        Támogatott nyelvpárok lekérése.
        
        Returns:
            Lista (source_code, target_code, display_name) tuple-okkal
        """
        return []
    
    def get_service_name(self) -> str:
        return f"translator_{self.info.id}"


class LanguagePlugin(PluginInterface):
    """
    Nyelv bővítő plugin alap osztály.
    
    Language pluginok új nyelveket adhatnak az alkalmazáshoz.
    """
    
    @property
    @abstractmethod
    def language_code(self) -> str:
        """
        Nyelv ISO 639-1 kódja.
        
        Returns:
            Nyelv kód (pl. "de", "es", "fr")
        """
        pass
    
    @property
    @abstractmethod
    def language_name(self) -> str:
        """
        Nyelv natív neve.
        
        Returns:
            Natív név (pl. "Deutsch", "Español")
        """
        pass
    
    @property
    def language_name_en(self) -> str:
        """
        Nyelv angol neve.
        
        Returns:
            Angol név (pl. "German", "Spanish")
        """
        return self.language_name
    
    @property
    def language_flag(self) -> str:
        """
        Nyelv zászló emojija.
        
        Returns:
            Zászló emoji (pl. "🇩🇪", "🇪🇸")
        """
        return ""
    
    @property
    def is_rtl(self) -> bool:
        """
        Jobbról balra írás-e.
        
        Returns:
            True ha RTL nyelv
        """
        return False
    
    def get_translations_path(self) -> Optional["Path"]:
        """
        Fordítások JSON fájl útvonala.
        
        Returns:
            Path objektum vagy None
        """
        if self._plugin_dir:
            path = self._plugin_dir / "locales" / f"{self.language_code}.json"
            if path.exists():
                return path
        return None
    
    def initialize(self) -> bool:
        """
        Plugin inicializálása - nyelv regisztrálása.
        
        Returns:
            True ha sikeres
        """
        try:
            from dubsync.i18n import get_locale_manager
            from dubsync.i18n.manager import LanguageInfo
            
            locale_mgr = get_locale_manager()
            
            # Nyelv info létrehozása
            lang_info = LanguageInfo(
                code=self.language_code,
                name=self.language_name,
                name_en=self.language_name_en,
                flag=self.language_flag,
                rtl=self.is_rtl
            )
            
            # Nyelv regisztrálása
            translations_path = self.get_translations_path()
            locale_mgr.register_language(lang_info, translations_path)
            
            return True
        except Exception as e:
            print(f"Error initializing language plugin: {e}")
            return False


class PluginManager:
    """
    Plugin kezelő.
    
    Pluginok betöltése, kezelése, futtatása.
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
        Plugin regisztrálása.
        
        Args:
            plugin: Plugin objektum
            enabled: Alapból engedélyezett-e (default: False)
            
        Returns:
            True, ha sikeres
        """
        info = plugin.info
        
        if info.id in self._plugins:
            return False
        
        if not plugin.initialize():
            return False
        
        self._plugins[info.id] = plugin
        
        if enabled:
            self._enabled_plugins.add(info.id)
        
        # Típus szerinti regisztráció - plugin lehet egyszerre több típusú is!
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
        Plugin eltávolítása.
        
        Args:
            plugin_id: Plugin azonosító
            
        Returns:
            True, ha sikeres
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
        """Plugin engedélyezése."""
        if plugin_id in self._plugins:
            self._enabled_plugins.add(plugin_id)
            return True
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Plugin letiltása."""
        self._enabled_plugins.discard(plugin_id)
        return True
    
    def is_enabled(self, plugin_id: str) -> bool:
        """Ellenőrzi, hogy a plugin engedélyezett-e."""
        return plugin_id in self._enabled_plugins
    
    def get_enabled_plugins(self) -> set:
        """Engedélyezett pluginok listája."""
        return self._enabled_plugins.copy()
    
    def set_enabled_plugins(self, enabled: set) -> None:
        """Engedélyezett pluginok beállítása."""
        self._enabled_plugins = enabled.copy()
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Plugin lekérése azonosító alapján."""
        return self._plugins.get(plugin_id)
    
    def get_all_plugins(self) -> List[PluginInterface]:
        """Összes plugin lekérése."""
        return list(self._plugins.values())
    
    def get_export_plugins(self, enabled_only: bool = True) -> List[ExportPlugin]:
        """Export pluginok lekérése."""
        plugins = list(self._export_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_qa_plugins(self, enabled_only: bool = True) -> List[QAPlugin]:
        """QA pluginok lekérése."""
        plugins = list(self._qa_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_ui_plugins(self, enabled_only: bool = True) -> List[UIPlugin]:
        """UI pluginok lekérése."""
        plugins = list(self._ui_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_service_plugins(self, enabled_only: bool = True) -> List[ServicePlugin]:
        """Service pluginok lekérése."""
        plugins = list(self._service_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_translation_plugins(self, enabled_only: bool = True) -> List[TranslationPlugin]:
        """Fordító pluginok lekérése."""
        plugins = list(self._translation_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def get_language_plugins(self, enabled_only: bool = True) -> List[LanguagePlugin]:
        """Nyelv pluginok lekérése."""
        plugins = list(self._language_plugins.values())
        if enabled_only:
            plugins = [p for p in plugins if self.is_enabled(p.info.id)]
        return plugins
    
    def save_plugin_settings(self, plugin_id: str, settings: Dict[str, Any]) -> None:
        """Plugin beállítások mentése."""
        self._plugin_settings[plugin_id] = settings
    
    def get_plugin_settings(self, plugin_id: str) -> Dict[str, Any]:
        """Plugin beállítások lekérése."""
        return self._plugin_settings.get(plugin_id, {})
    
    def shutdown_all(self) -> None:
        """Összes plugin leállítása."""
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
