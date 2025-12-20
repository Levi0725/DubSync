"""
DubSync i18n UI Support

Helper classes and functions for UI components.
"""


import contextlib
from typing import Optional, Callable, List
from functools import partial

from PySide6.QtCore import QObject, Signal


class TranslatableUI(QObject):
    """
    Mixin class for translatable UI components.
    
    Automatically updates UI elements on language change.
    
    Usage:
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
        """Initialize i18n - call in __init__."""
        with contextlib.suppress(Exception):
            from dubsync.i18n import get_locale_manager

            locale_manager = get_locale_manager()
            locale_manager.register_language_changed_callback(self._on_language_changed)
    
    def cleanup_i18n(self):
        """i18n cleanup - call in destructor if needed."""
        with contextlib.suppress(Exception):
            from dubsync.i18n import get_locale_manager

            locale_manager = get_locale_manager()
            locale_manager.unregister_language_changed_callback(self._on_language_changed)
    
    def _on_language_changed(self, new_lang: str):
        """Language change handler."""
        self.language_changed.emit(new_lang)
        self.retranslate_ui()
    
    def retranslate_ui(self):
        """
        Retranslate UI elements.
        
        Override this method in subclasses.
        """
        pass


class UITextBinder:
    """
    Automatic binding of UI texts to translation keys.
    
    Usage:
        binder = UITextBinder()
        binder.bind(button, "setText", "buttons.ok")
        binder.bind(label, "setText", "labels.name", name="John")
        
        # On language change
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
        Bind widget text to a translation key.
        
        Args:
            widget: Qt widget
            method_name: Method name (e.g., "setText", "setWindowTitle")
            translation_key: Translation key
            **kwargs: Translation parameters
        """
        self._bindings.append((widget, method_name, translation_key, kwargs))
        # Initial value setting
        self._apply_binding(widget, method_name, translation_key, kwargs)
    
    def _apply_binding(self, widget, method_name: str, key: str, kwargs: dict):
        """Apply binding."""
        with contextlib.suppress(Exception):
            from dubsync.i18n import t

            text = t(key, **kwargs)
            if method := getattr(widget, method_name, None):
                method(text)
    
    def update_all(self):
        """Update all bindings."""
        for widget, method_name, key, kwargs in self._bindings:
            self._apply_binding(widget, method_name, key, kwargs)
    
    def clear(self):
        """Clear all bindings."""
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
    Create QAction with i18n support.
    
    Args:
        parent: Parent widget
        text_key: Translation key
        icon: Icon text/emoji (optional)
        shortcut: Shortcut (optional)
        triggered: Callback function (optional)
        checkable: Whether checkable
        **text_kwargs: Translation parameters
    
    Returns:
        QAction object
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
    
    # Store translation key in the action (for later updates)
    action.setProperty("i18n_key", text_key)
    action.setProperty("i18n_icon", icon)
    action.setProperty("i18n_kwargs", text_kwargs)
    
    return action


def update_action_text(action):
    """
    Update QAction text based on stored translation key.
    
    Args:
        action: QAction object
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
