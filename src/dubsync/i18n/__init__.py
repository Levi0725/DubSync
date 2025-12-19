"""
DubSync Internationalization (i18n) Module

Ez a modul biztosítja a többnyelvű támogatást az alkalmazáshoz.
This module provides multilingual support for the application.

Használat / Usage:
    from dubsync.i18n import t, get_locale_manager
    
    # Szöveg fordítása / Translate text
    translated = t("menu.file")
    
    # Paraméterezett fordítás / Parameterized translation
    translated = t("messages.items_count", count=5)
    
    # Nyelv váltása / Change language
    locale_manager = get_locale_manager()
    locale_manager.set_language("hu")

Plugin használat / Plugin usage:
    from dubsync.i18n.plugin_support import TranslatablePlugin, create_plugin_translations
    
    # Egyszerű fordítás regisztráció
    create_plugin_translations(
        "my_plugin",
        en={"title": "My Plugin"},
        hu={"title": "Az én pluginom"}
    )
    
    # Vagy mixin osztállyal
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
