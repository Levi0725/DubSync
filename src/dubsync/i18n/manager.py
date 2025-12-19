"""
DubSync Locale Manager

Központi nyelvkezelő a többnyelvű támogatáshoz.
Central language manager for multilingual support.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field


@dataclass
class LanguageInfo:
    """Nyelv metaadatok / Language metadata."""
    code: str           # ISO 639-1 kód (pl. "en", "hu")
    name: str           # Natív név (pl. "English", "Magyar")
    name_en: str        # Angol név (pl. "English", "Hungarian")
    flag: str = ""      # Emoji zászló (pl. "🇬🇧", "🇭🇺")
    rtl: bool = False   # Jobbról balra írás
    
    def __str__(self) -> str:
        return f"{self.flag} {self.name}" if self.flag else self.name


class LocaleManager:
    """
    Központi nyelvkezelő singleton.
    
    Kezeli a nyelvi fájlokat, fordításokat és nyelvi beállításokat.
    Támogatja a plugin-ek saját fordításait is.
    """
    
    _instance: Optional['LocaleManager'] = None
    
    # Elérhető nyelvek (bővíthető plugin-ekkel)
    BUILTIN_LANGUAGES: Dict[str, LanguageInfo] = {
        "en": LanguageInfo(
            code="en",
            name="English",
            name_en="English",
            flag="🇬🇧"
        ),
        "hu": LanguageInfo(
            code="hu",
            name="Magyar",
            name_en="Hungarian",
            flag="🇭🇺"
        ),
    }
    
    FALLBACK_LANGUAGE = "en"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Jelenlegi nyelv
        self._current_language: str = self.FALLBACK_LANGUAGE
        
        # Betöltött fordítások: {language_code: {key: value}}
        self._translations: Dict[str, Dict[str, Any]] = {}
        
        # Plugin fordítások: {plugin_id: {language_code: {key: value}}}
        self._plugin_translations: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # Regisztrált nyelvek (beépített + plugin)
        self._languages: Dict[str, LanguageInfo] = dict(self.BUILTIN_LANGUAGES)
        
        # Nyelv változás callback-ek
        self._language_changed_callbacks: List[Callable[[str], None]] = []
        
        # Alap nyelvek betöltése
        self._load_builtin_languages()
    
    def _get_locales_dir(self) -> Path:
        """Nyelvi fájlok könyvtára."""
        return Path(__file__).parent / "locales"
    
    def _load_builtin_languages(self):
        """Beépített nyelvek betöltése."""
        locales_dir = self._get_locales_dir()
        
        for lang_code in self.BUILTIN_LANGUAGES.keys():
            self._load_language_file(lang_code, locales_dir / f"{lang_code}.json")
    
    def _load_language_file(self, lang_code: str, file_path: Path) -> bool:
        """
        Nyelvi fájl betöltése.
        
        Args:
            lang_code: Nyelv kód (pl. "en")
            file_path: JSON fájl útvonala
            
        Returns:
            True ha sikeres
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._translations[lang_code] = self._flatten_dict(data)
                    return True
            else:
                print(f"Language file not found: {file_path}")
                return False
        except Exception as e:
            print(f"Error loading language file {file_path}: {e}")
            return False
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '') -> Dict[str, str]:
        """
        Beágyazott szótár lapítása pontozott kulcsokká.
        
        Példa:
            {"menu": {"file": "Fájl"}} -> {"menu.file": "Fájl"}
        """
        items: Dict[str, str] = {}
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self._flatten_dict(v, new_key))
            else:
                items[new_key] = str(v)
        return items
    
    @property
    def current_language(self) -> str:
        """Jelenlegi nyelv kódja."""
        return self._current_language
    
    @property
    def current_language_info(self) -> LanguageInfo:
        """Jelenlegi nyelv információi."""
        return self._languages.get(
            self._current_language,
            self.BUILTIN_LANGUAGES[self.FALLBACK_LANGUAGE]
        )
    
    def get_available_languages(self) -> List[LanguageInfo]:
        """Elérhető nyelvek listája."""
        return list(self._languages.values())
    
    def set_language(self, language_code: str) -> bool:
        """
        Nyelv beállítása.
        
        Args:
            language_code: Új nyelv kódja
            
        Returns:
            True ha sikeres
        """
        if language_code not in self._languages:
            print(f"Language not available: {language_code}")
            return False
        
        if language_code != self._current_language:
            self._current_language = language_code
            
            # Callback-ek meghívása
            for callback in self._language_changed_callbacks:
                try:
                    callback(language_code)
                except Exception as e:
                    print(f"Error in language change callback: {e}")
        
        return True
    
    def register_language_changed_callback(self, callback: Callable[[str], None]):
        """Nyelv változás callback regisztrálása."""
        if callback not in self._language_changed_callbacks:
            self._language_changed_callbacks.append(callback)
    
    def unregister_language_changed_callback(self, callback: Callable[[str], None]):
        """Nyelv változás callback eltávolítása."""
        if callback in self._language_changed_callbacks:
            self._language_changed_callbacks.remove(callback)
    
    def translate(self, key: str, **kwargs) -> str:
        """
        Szöveg fordítása.
        
        Args:
            key: Fordítási kulcs (pl. "menu.file.save")
            **kwargs: Helyettesítő paraméterek
            
        Returns:
            Fordított szöveg, vagy a kulcs ha nincs fordítás
        """
        # Jelenlegi nyelv fordítása
        translations = self._translations.get(self._current_language, {})
        text = translations.get(key)
        
        # Fallback az angol nyelvre
        if text is None and self._current_language != self.FALLBACK_LANGUAGE:
            fallback_translations = self._translations.get(self.FALLBACK_LANGUAGE, {})
            text = fallback_translations.get(key)
        
        # Ha nincs fordítás, visszaadjuk a kulcsot
        if text is None:
            return key
        
        # Paraméterek helyettesítése
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return text
    
    def translate_plugin(self, plugin_id: str, key: str, **kwargs) -> str:
        """
        Plugin szöveg fordítása.
        
        Args:
            plugin_id: Plugin azonosító
            key: Fordítási kulcs
            **kwargs: Helyettesítő paraméterek
            
        Returns:
            Fordított szöveg
        """
        # Plugin fordítások keresése
        plugin_trans = self._plugin_translations.get(plugin_id, {})
        translations = plugin_trans.get(self._current_language, {})
        text = translations.get(key)
        
        # Fallback az angol nyelvre
        if text is None and self._current_language != self.FALLBACK_LANGUAGE:
            fallback_trans = plugin_trans.get(self.FALLBACK_LANGUAGE, {})
            text = fallback_trans.get(key)
        
        # Fallback az alap fordításokra
        if text is None:
            return self.translate(key, **kwargs)
        
        # Paraméterek helyettesítése
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        
        return text
    
    def register_language(self, lang_info: LanguageInfo, translations_file: Optional[Path] = None) -> bool:
        """
        Új nyelv regisztrálása (plugin-ek számára).
        
        Args:
            lang_info: Nyelv információi
            translations_file: Fordítások JSON fájlja (opcionális)
            
        Returns:
            True ha sikeres
        """
        code = lang_info.code
        
        if code in self._languages:
            print(f"Language already registered: {code}")
            return False
        
        self._languages[code] = lang_info
        
        if translations_file:
            self._load_language_file(code, translations_file)
        
        return True
    
    def register_plugin_translations(
        self,
        plugin_id: str,
        translations: Dict[str, Dict[str, Any]]
    ):
        """
        Plugin fordítások regisztrálása.
        
        Args:
            plugin_id: Plugin azonosító
            translations: {language_code: {key: value}}
        """
        if plugin_id not in self._plugin_translations:
            self._plugin_translations[plugin_id] = {}
        
        for lang_code, trans_dict in translations.items():
            self._plugin_translations[plugin_id][lang_code] = self._flatten_dict(trans_dict)
    
    def load_plugin_translations_from_file(
        self,
        plugin_id: str,
        lang_code: str,
        file_path: Path
    ) -> bool:
        """
        Plugin fordítások betöltése fájlból.
        
        Args:
            plugin_id: Plugin azonosító
            lang_code: Nyelv kód
            file_path: JSON fájl útvonala
            
        Returns:
            True ha sikeres
        """
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if plugin_id not in self._plugin_translations:
                        self._plugin_translations[plugin_id] = {}
                    
                    self._plugin_translations[plugin_id][lang_code] = self._flatten_dict(data)
                    return True
        except Exception as e:
            print(f"Error loading plugin translations: {e}")
        return False
    
    def has_translation(self, key: str) -> bool:
        """Ellenőrzi, hogy létezik-e fordítás a kulcshoz."""
        translations = self._translations.get(self._current_language, {})
        if key in translations:
            return True
        
        fallback = self._translations.get(self.FALLBACK_LANGUAGE, {})
        return key in fallback


# === Kényelmi függvények / Convenience functions ===

def get_locale_manager() -> LocaleManager:
    """LocaleManager singleton lekérése."""
    return LocaleManager()


def t(key: str, **kwargs) -> str:
    """
    Szöveg fordítása (rövidítés).
    
    Args:
        key: Fordítási kulcs
        **kwargs: Helyettesítő paraméterek
        
    Returns:
        Fordított szöveg
        
    Példa:
        t("menu.file")
        t("messages.items_count", count=5)
        t("plugins.my_plugin.title")  # Plugin saját locale-jából
    """
    manager = get_locale_manager()
    
    # Ha plugins.{plugin_id}.* kulcs, akkor plugin fordításból
    if key.startswith("plugins."):
        parts = key.split(".", 2)  # ["plugins", "plugin_id", "rest.of.key"]
        if len(parts) >= 3:
            plugin_id = parts[1]
            plugin_key = parts[2]
            result = manager.translate_plugin(plugin_id, plugin_key, **kwargs)
            # Ha nem plugin_key-t adja vissza, akkor találtunk fordítást
            if result != plugin_key:
                return result
    
    # Alap fordítás
    return manager.translate(key, **kwargs)


def t_plugin(plugin_id: str, key: str, **kwargs) -> str:
    """
    Plugin szöveg fordítása.
    
    Args:
        plugin_id: Plugin azonosító
        key: Fordítási kulcs
        **kwargs: Helyettesítő paraméterek
        
    Returns:
        Fordított szöveg
    """
    return get_locale_manager().translate_plugin(plugin_id, key, **kwargs)


def get_available_languages() -> List[LanguageInfo]:
    """Elérhető nyelvek listája."""
    return get_locale_manager().get_available_languages()


def get_current_language() -> str:
    """Jelenlegi nyelv kódja."""
    return get_locale_manager().current_language


def set_language(language_code: str) -> bool:
    """
    Nyelv beállítása.
    
    Args:
        language_code: Nyelv kód (pl. "en", "hu")
        
    Returns:
        True ha sikeres
    """
    return get_locale_manager().set_language(language_code)
