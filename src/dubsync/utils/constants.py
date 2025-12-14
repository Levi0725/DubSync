"""
DubSync Constants

Alkalmazás-szintű konstansok és enumerációk.
"""

from enum import Enum, auto
from typing import Final

# Application info
APP_NAME: Final[str] = "DubSync"
APP_VERSION: Final[str] = "1.0.0"
APP_DESCRIPTION: Final[str] = "Professzionális Szinkronfordítói Editor"

# File extensions
PROJECT_EXTENSION: Final[str] = ".dubsync"
SRT_EXTENSION: Final[str] = ".srt"
SUPPORTED_VIDEO_EXTENSIONS: Final[tuple] = (".mp4", ".mkv", ".avi", ".mov", ".webm")

# Database
DB_FILENAME: Final[str] = "project.db"
DB_VERSION: Final[int] = 1

# Lip-sync estimation constants
# Átlagos magyar beszédsebesség: ~12-15 karakter/másodperc
CHARS_PER_SECOND_SLOW: Final[float] = 10.0  # Lassú beszéd
CHARS_PER_SECOND_NORMAL: Final[float] = 13.0  # Normál beszéd
CHARS_PER_SECOND_FAST: Final[float] = 16.0  # Gyors beszéd

# Lip-sync thresholds
LIPSYNC_THRESHOLD_GOOD: Final[float] = 0.9  # 90% alatt = jó
LIPSYNC_THRESHOLD_WARNING: Final[float] = 1.05  # 105% alatt = figyelmeztetés
# 105% felett = túl hosszú


class CueStatus(Enum):
    """
    Cue állapotok a fordítási workflow-ban.
    """
    NEW = auto()           # Új, még nem fordított
    TRANSLATED = auto()    # Fordítás kész
    NEEDS_REVISION = auto() # Javítandó
    APPROVED = auto()      # Jóváhagyva


class LipSyncStatus(Enum):
    """
    Lip-sync becslés eredménye.
    """
    GOOD = auto()      # Zöld - jó hosszúság
    WARNING = auto()   # Sárga - határeset
    TOO_LONG = auto()  # Piros - túl hosszú
    UNKNOWN = auto()   # Nincs adat


class CommentStatus(Enum):
    """
    Megjegyzés állapota.
    """
    OPEN = auto()      # Nyitott
    RESOLVED = auto()  # Lezárt


# UI Colors (hex)
COLOR_LIPSYNC_GOOD: Final[str] = "#4CAF50"      # Zöld
COLOR_LIPSYNC_WARNING: Final[str] = "#FFC107"   # Sárga
COLOR_LIPSYNC_TOO_LONG: Final[str] = "#F44336"  # Piros
COLOR_LIPSYNC_UNKNOWN: Final[str] = "#9E9E9E"   # Szürke

COLOR_STATUS_NEW: Final[str] = "#2196F3"        # Kék
COLOR_STATUS_TRANSLATED: Final[str] = "#FF9800" # Narancs
COLOR_STATUS_NEEDS_REVISION: Final[str] = "#E91E63"  # Rózsaszín
COLOR_STATUS_APPROVED: Final[str] = "#4CAF50"   # Zöld

# Default values
DEFAULT_FRAME_RATE: Final[float] = 25.0
DEFAULT_LANGUAGE: Final[str] = "hu"
