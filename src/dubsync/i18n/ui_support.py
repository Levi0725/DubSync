"""
DubSync i18n UI Support

UI komponensekhez készült helper osztályok és függvények.
Helper classes and functions for UI components.
"""


import contextlib
from typing import Optional, Callable, List
from functools import partial

from PySide6.QtCore import QObject, Signal


class TranslatableUI(QObject):
    """
    Mixin osztály fordítható UI komponensekhez.
    
    Automatikusan frissíti az UI elemeket nyelvváltáskor.
    
    Használat:
        class MyWidget(QWidget, TranslatableUI):
            def __init__(self):
                super().__init__()
                self.setup_i18n()
                self._setup_ui()
            
            def retranslate_ui(self):
                self.my_button.setText(t("buttons.ok"))
    """
    
    language_changed = Signal(str)
    
    def setup_i18n(self):
        """i18n inicializálása - hívd meg a __init__-ben."""
        with contextlib.suppress(Exception):
            from dubsync.i18n import get_locale_manager

            locale_manager = get_locale_manager()
            locale_manager.register_language_changed_callback(self._on_language_changed)
    
    def cleanup_i18n(self):
        """i18n cleanup - hívd meg a destruktorban ha szükséges."""
        with contextlib.suppress(Exception):
            from dubsync.i18n import get_locale_manager

            locale_manager = get_locale_manager()
            locale_manager.unregister_language_changed_callback(self._on_language_changed)
    
    def _on_language_changed(self, new_lang: str):
        """Nyelv változás kezelése."""
        self.language_changed.emit(new_lang)
        self.retranslate_ui()
    
    def retranslate_ui(self):
        """
        UI elemek újrafordítása.
        
        Override this method in subclasses.
        """
        pass


class UITextBinder:
    """
    UI szövegek automatikus kötése fordítási kulcsokhoz.
    
    Használat:
        binder = UITextBinder()
        binder.bind(button, "setText", "buttons.ok")
        binder.bind(label, "setText", "labels.name", name="John")
        
        # Nyelvváltáskor
        binder.update_all()
    """
    
    def __init__(self):
        self._bindings: List[tuple] = []
    
    def bind(
        self,
        widget,
        method_name: str,
        translation_key: str,
        **kwargs
    ):
        """
        Widget szöveg kötése fordítási kulcshoz.
        
        Args:
            widget: Qt widget
            method_name: Metódus neve (pl. "setText", "setWindowTitle")
            translation_key: Fordítási kulcs
            **kwargs: Fordítás paraméterek
        """
        self._bindings.append((widget, method_name, translation_key, kwargs))
        # Kezdeti érték beállítása
        self._apply_binding(widget, method_name, translation_key, kwargs)
    
    def _apply_binding(self, widget, method_name: str, key: str, kwargs: dict):
        """Kötés alkalmazása."""
        with contextlib.suppress(Exception):
            from dubsync.i18n import t

            text = t(key, **kwargs)
            if method := getattr(widget, method_name, None):
                method(text)
    
    def update_all(self):
        """Összes kötés frissítése."""
        for widget, method_name, key, kwargs in self._bindings:
            self._apply_binding(widget, method_name, key, kwargs)
    
    def clear(self):
        """Kötések törlése."""
        self._bindings.clear()


def create_action_with_i18n(
    parent,
    text_key: str,
    icon: str = "",
    shortcut: Optional[str] = None,
    triggered: Optional[Callable] = None,
    checkable: bool = False,
    **text_kwargs
):
    """
    QAction létrehozása i18n támogatással.
    
    Args:
        parent: Parent widget
        text_key: Fordítási kulcs
        icon: Ikon szöveg/emoji (opcionális)
        shortcut: Gyorsbillentyű (opcionális)
        triggered: Callback függvény (opcionális)
        checkable: Checkable-e
        **text_kwargs: Fordítás paraméterek
    
    Returns:
        QAction objektum
    """
    from PySide6.QtGui import QAction, QKeySequence
    from dubsync.i18n import t
    
    text = t(text_key, **text_kwargs)
    if icon:
        text = f"{icon} {text}"
    
    action = QAction(text, parent)
    
    if shortcut:
        action.setShortcut(QKeySequence(shortcut))
    
    if triggered:
        action.triggered.connect(triggered)
    
    if checkable:
        action.setCheckable(True)
    
    # Fordítási kulcs tárolása az action-ben (későbbi frissítéshez)
    action.setProperty("i18n_key", text_key)
    action.setProperty("i18n_icon", icon)
    action.setProperty("i18n_kwargs", text_kwargs)
    
    return action


def update_action_text(action):
    """
    QAction szövegének frissítése a tárolt fordítási kulcs alapján.
    
    Args:
        action: QAction objektum
    """
    from dubsync.i18n import t
    
    key = action.property("i18n_key")
    if not key:
        return
    
    icon = action.property("i18n_icon") or ""
    kwargs = action.property("i18n_kwargs") or {}
    
    text = t(key, **kwargs)
    if icon:
        text = f"{icon} {text}"
    
    action.setText(text)
