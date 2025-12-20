"""
DubSync i18n Plugin Support

Helper functions for plugin i18n support.
"""

from pathlib import Path
from typing import Dict, Any, Optional


def create_plugin_translations(
    plugin_id: str,
    en: Dict[str, Any],
    hu: Optional[Dict[str, Any]] = None,
    **other_languages: Dict[str, Any]
) -> None:
    """
    Register plugin translations.
    
    Args:
        plugin_id: Plugin identifier
        en: English translations (required, this is the fallback)
        hu: Hungarian translations (optional)
        **other_languages: Additional languages (e.g., de={...}, es={...})
    
    Example:
        create_plugin_translations(
            "my_plugin",
            en={
                "name": "My Plugin",
                "description": "A great plugin"
            },
            hu={
                "name": "Az én pluginom",
                "description": "Egy nagyszerű plugin"
            }
        )
    """
    try:
        from dubsync.i18n import get_locale_manager
        
        locale_manager = get_locale_manager()
        
        translations = {"en": en}
        
        if hu:
            translations["hu"] = hu
        
        for lang_code, trans in other_languages.items():
            translations[lang_code] = trans
        
        locale_manager.register_plugin_translations(plugin_id, translations)
        
    except Exception as e:
        print(f"Error registering plugin translations for {plugin_id}: {e}")


def load_plugin_translations_from_locales_dir(
    plugin_id: str,
    locales_dir: Path
) -> None:
    """
    Load plugin translations from the locales directory.
    
    Args:
        plugin_id: Plugin identifier
        locales_dir: Directory of language files
    
    Example:
        Directory structure:
            my_plugin/
                locales/
                    en.json
                    hu.json
                    de.json
    """
    try:
        from dubsync.i18n import get_locale_manager
        
        locale_manager = get_locale_manager()
        
        if not locales_dir.exists():
            return
        
        for lang_file in locales_dir.glob("*.json"):
            lang_code = lang_file.stem  # pl. "en", "hu"
            locale_manager.load_plugin_translations_from_file(
                plugin_id, lang_code, lang_file
            )
            
    except Exception as e:
        print(f"Error loading plugin translations from {locales_dir}: {e}")


class TranslatablePlugin:
    """
    Mixin class for translatable plugins.
    
    Example usage:
        class MyPlugin(UIPlugin, TranslatablePlugin):
            def initialize(self):
                self.register_translations()
                return True
                
            def get_translations(self):
                return {
                    "en": {"title": "My Plugin"},
                    "hu": {"title": "Az én pluginom"}
                }
    """
    
    def get_translations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get plugin translations.
        
        Override this method to provide translations.
        
        Returns:
            {language_code: {key: value}}
        """
        return {}
    
    def register_translations(self) -> None:
        """Register plugin translations."""
        from dubsync.plugins.base import PluginInterface

        if not isinstance(self, PluginInterface):
            return

        if translations := self.get_translations():
            try:
                from dubsync.i18n import get_locale_manager
                locale_manager = get_locale_manager()
                locale_manager.register_plugin_translations(
                    self.info.id,
                    translations
                )
            except Exception as e:
                print(f"Error registering translations: {e}")
    
    def t(self, key: str, **kwargs) -> str:
        """
        Translate plugin text.
        
        Args:
            key: Translation key
            **kwargs: Replacement parameters
            
        Returns:
            Translated text
        """
        from dubsync.plugins.base import PluginInterface
        
        if not isinstance(self, PluginInterface):
            return key
        
        try:
            from dubsync.i18n import t_plugin
            return t_plugin(self.info.id, key, **kwargs)
        except Exception:
            return key
