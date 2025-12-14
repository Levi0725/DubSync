"""
DubSync - Professzionális Szinkronfordítói Editor

Egy teljes értékű, stabil, Windows-os asztali alkalmazás
szinkronfordításra (dubbing) optimalizálva.

Fő funkciók:
- SRT import és kezelés
- Videó lejátszás lip-sync becsléssel
- Cue-alapú szerkesztő felület
- Lektori megjegyzések
- Professzionális PDF export
- Bővíthető plugin architektúra
"""

__version__ = "1.0.0"
__author__ = "Levente Kulacsy"
__license__ = "MIT"

from dubsync.app import DubSyncApp

__all__ = ["DubSyncApp", "__version__"]
