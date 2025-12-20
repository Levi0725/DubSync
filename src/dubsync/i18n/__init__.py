"""
DubSync Internationalization (i18n) Module

This module provides multilingual support for the application.

Usage:
    from dubsync.i18n import t, get_locale_manager
    
    # Translate text
    translated = t("menu.file")
    
    # Parameterized translation
    translated = t("messages.items_count", count=5)
    
    # Change language
    locale_manager = get_locale_manager()
    locale_manager.set_language("hu")

Plugin usage:
    from dubsync.i18n.plugin_support import TranslatablePlugin, create_plugin_translations
    
    # Simple translation registration
    create_plugin_translations(
        "my_plugin",
        en={"title": "My Plugin"},
        hu={"title": "Az én pluginom"}
    )
    
    # Or with a mixin class
    class MyPlugin(UIPlugin, TranslatablePlugin):
        def get_translations(self):
            return {"en": {...}, "hu": {...}}
"""

from dubsync.i18n.manager import (
    LocaleManager,
    LanguageInfo,
    get_locale_manager,
    t,
    t_plugin,
    get_available_languages,
    get_current_language,
    set_language,
)

from dubsync.i18n.plugin_support import (
    TranslatablePlugin,
    create_plugin_translations,
    load_plugin_translations_from_locales_dir,
)

__all__ = [
    # Manager
    "LocaleManager",
    "LanguageInfo",
    "get_locale_manager",
    "t",
    "t_plugin",
    "get_available_languages",
    "get_current_language",
    "set_language",
    # Plugin support
    "TranslatablePlugin",
    "create_plugin_translations",
    "load_plugin_translations_from_locales_dir",
]
