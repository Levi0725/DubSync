"""
DubSync Locale Manager

Central language manager for multilingual support.
"""


import contextlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field


@dataclass
class LanguageInfo:
    """Language metadata."""
    code: str           # ISO 639-1 code (e.g., "en", "hu")
    name: str           # Native name (e.g., "English", "Magyar")
    name_en: str        # English name (e.g., "English", "Hungarian")
    flag: str = ""      # Emoji flag (e.g., "🇬🇧", "🇭🇺")
    rtl: bool = False   # Right-to-left writing
    
    def __str__(self) -> str:
        return f"{self.flag} {self.name}" if self.flag else self.name


class LocaleManager:
    """
    Central language manager singleton.
    
    Manages language files, translations, and language settings.
    Supports plugin-specific translations as well.
    """
    
    _instance: Optional['LocaleManager'] = None
    
    # Available languages (extendable with plugins)
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
        
        # Current language
        self._current_language: str = self.FALLBACK_LANGUAGE
        
        # Loaded translations: {language_code: {key: value}}
        self._translations: Dict[str, Dict[str, Any]] = {}
        
        # Plugin translations: {plugin_id: {language_code: {key: value}}}
        self._plugin_translations: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # Registered languages (built-in + plugins)
        self._languages: Dict[str, LanguageInfo] = dict(self.BUILTIN_LANGUAGES)
        
        # Language change callbacks
        self._language_changed_callbacks: List[Callable[[str], None]] = []
        
        # Load built-in languages
        self._load_builtin_languages()
    
    def _get_locales_dir(self) -> Path:
        """Directory of language files."""
        return Path(__file__).parent / "locales"
    
    def _load_builtin_languages(self):
        """Load built-in languages."""
        locales_dir = self._get_locales_dir()
        
        for lang_code in self.BUILTIN_LANGUAGES.keys():
            self._load_language_file(lang_code, locales_dir / f"{lang_code}.json")
    
    def _load_language_file(self, lang_code: str, file_path: Path) -> bool:
        """
        Load language file.
        
        Args:
            lang_code: Language code (e.g., "en")
            file_path: Path to JSON file
            
        Returns:
            True if successful
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
        Flatten nested dictionary into dotted keys.
        
        Example:
            {"menu": {"file": "File"}} -> {"menu.file": "File"}
        """
        items: Dict[str, str] = {}
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items |= self._flatten_dict(v, new_key)
            else:
                items[new_key] = str(v)
        return items
    
    @property
    def current_language(self) -> str:
        """Current language code."""
        return self._current_language
    
    @property
    def current_language_info(self) -> LanguageInfo:
        """Current language information."""
        return self._languages.get(
            self._current_language,
            self.BUILTIN_LANGUAGES[self.FALLBACK_LANGUAGE]
        )
    
    def get_available_languages(self) -> List[LanguageInfo]:
        """List of available languages."""
        return list(self._languages.values())
    
    def set_language(self, language_code: str) -> bool:
        """
        Set language.
        
        Args:
            language_code: New language code
            
        Returns:
            True if successful
        """
        if language_code not in self._languages:
            print(f"Language not available: {language_code}")
            return False
        
        if language_code != self._current_language:
            self._current_language = language_code
            
            # Call language change callbacks
            for callback in self._language_changed_callbacks:
                try:
                    callback(language_code)
                except Exception as e:
                    print(f"Error in language change callback: {e}")
        
        return True
    
    def register_language_changed_callback(self, callback: Callable[[str], None]):
        """Register language change callback."""
        if callback not in self._language_changed_callbacks:
            self._language_changed_callbacks.append(callback)
    
    def unregister_language_changed_callback(self, callback: Callable[[str], None]):
        """Unregister language change callback."""
        if callback in self._language_changed_callbacks:
            self._language_changed_callbacks.remove(callback)
    
    def translate(self, key: str, **kwargs) -> str:
        """
        Translate text.
        
        Args:
            key: Translation key (e.g., "menu.file.save")
            **kwargs: Replacement parameters
            
        Returns:
            Translated text, or the key if no translation is found
        """
        # Translate current language
        translations = self._translations.get(self._current_language, {})
        text = translations.get(key)

        # Fallback to English
        if text is None and self._current_language != self.FALLBACK_LANGUAGE:
            fallback_translations = self._translations.get(self.FALLBACK_LANGUAGE, {})
            text = fallback_translations.get(key)

        # If no translation, return the key
        if text is None:
            return key

        # Replace parameters
        if kwargs:
            with contextlib.suppress(KeyError, ValueError):
                text = text.format(**kwargs)
        return text
    
    def translate_plugin(self, plugin_id: str, key: str, **kwargs) -> str:
        """
        Translate plugin text.
        
        Args:
            plugin_id: Plugin identifier
            key: Translation key
            **kwargs: Replacement parameters
            
        Returns:
            Translated text
        """
        # Search plugin translations
        plugin_trans = self._plugin_translations.get(plugin_id, {})
        translations = plugin_trans.get(self._current_language, {})
        text = translations.get(key)

        # Fallback to English
        if text is None and self._current_language != self.FALLBACK_LANGUAGE:
            fallback_trans = plugin_trans.get(self.FALLBACK_LANGUAGE, {})
            text = fallback_trans.get(key)

        # Fallback to base translations
        if text is None:
            return self.translate(key, **kwargs)

        # Replace parameters
        if kwargs:
            with contextlib.suppress(KeyError, ValueError):
                text = text.format(**kwargs)
        return text
    
    def register_language(self, lang_info: LanguageInfo, translations_file: Optional[Path] = None) -> bool:
        """
        Register a new language (for plugins).
        
        Args:
            lang_info: Language information
            translations_file: Translations JSON file (optional)
            
        Returns:
            True if successful
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
        Register plugin translations.
        
        Args:
            plugin_id: Plugin identifier
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
        Load plugin translations from file.
        
        Args:
            plugin_id: Plugin identifier
            lang_code: Language code
            file_path: JSON file path
            
        Returns:
            True if successful
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
        """Check if a translation exists for the key."""
        translations = self._translations.get(self._current_language, {})
        if key in translations:
            return True
        
        fallback = self._translations.get(self.FALLBACK_LANGUAGE, {})
        return key in fallback


# === Convenience functions ===

def get_locale_manager() -> LocaleManager:
    """Get the LocaleManager singleton."""
    return LocaleManager()


def t(key: str, **kwargs) -> str:
    """
    Translate text (shortcut).
    
    Args:
        key: Translation key
        **kwargs: Replacement parameters
        
    Returns:
        Translated text
        
    Example:
        t("menu.file")
        t("messages.items_count", count=5)
        t("plugins.my_plugin.title")  # From the plugin's own locale
    """
    manager = get_locale_manager()
    
    # If key starts with plugins.{plugin_id}.*, then from plugin translations
    if key.startswith("plugins."):
        parts = key.split(".", 2)  # ["plugins", "plugin_id", "rest.of.key"]
        if len(parts) >= 3:
            plugin_id = parts[1]
            plugin_key = parts[2]
            result = manager.translate_plugin(plugin_id, plugin_key, **kwargs)
            # If result is not plugin_key, then a translation was found
            if result != plugin_key:
                return result
    
    # Alap fordítás
    return manager.translate(key, **kwargs)


def t_plugin(plugin_id: str, key: str, **kwargs) -> str:
    """
    Translate plugin text.
    
    Args:
        plugin_id: Plugin identifier
        key: Translation key
        **kwargs: Replacement parameters
        
    Returns:
        Translated text
    """
    return get_locale_manager().translate_plugin(plugin_id, key, **kwargs)


def get_available_languages() -> List[LanguageInfo]:
    """List of available languages."""
    return get_locale_manager().get_available_languages()


def get_current_language() -> str:
    """Current language code."""
    return get_locale_manager().current_language


def set_language(language_code: str) -> bool:
    """
    Set language.
    
    Args:
        language_code: Language code (e.g. "en", "hu")
        
    Returns:
        True if successful
    """
    return get_locale_manager().set_language(language_code)
