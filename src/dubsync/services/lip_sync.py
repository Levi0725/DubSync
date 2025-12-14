"""
DubSync Lip-Sync Estimator

Lip-sync becslő rendszer a szinkronfordításhoz.

A rendszer időalapú becslést használ, nem fonetikai elemzést:
- Magyar átlagos beszédsebesség: 12-15 karakter/másodperc
- Angol átlagos beszédsebesség: 14-17 karakter/másodperc (gyorsabb)
- Figyelembe veszi az eredeti szöveg hosszát is
- Szögletes zárójelben lévő instrukciók kihagyása
- Szóközöket és írásjeleket is számolja (természetes ritmus)
- Három kategória: jó, határeset, túl hosszú
"""

import re
from typing import Optional, Tuple
from dataclasses import dataclass

from dubsync.models.cue import Cue
from dubsync.utils.constants import (
    CHARS_PER_SECOND_NORMAL,
    CHARS_PER_SECOND_SLOW,
    CHARS_PER_SECOND_FAST,
    LIPSYNC_THRESHOLD_GOOD,
    LIPSYNC_THRESHOLD_WARNING,
    LipSyncStatus,
)

# Angol beszédsebesség (általában gyorsabb mint a magyar)
CHARS_PER_SECOND_ENGLISH: float = 15.0


@dataclass
class LipSyncResult:
    """
    Lip-sync becslés eredménye.
    """
    text_length: int            # Szöveg hossza (karakterek)
    available_time_ms: int      # Rendelkezésre álló idő (ms)
    estimated_time_ms: int      # Becsült beszédidő (ms)
    ratio: float                # Arány (becsült / rendelkezésre álló)
    status: LipSyncStatus       # Státusz (jó, figyelmeztetés, túl hosszú)
    
    @property
    def is_ok(self) -> bool:
        """Elfogadható-e a lip-sync."""
        return self.status in (LipSyncStatus.GOOD, LipSyncStatus.WARNING)
    
    @property
    def overflow_ms(self) -> int:
        """Túlcsordulás milliszekundumban (ha negatív, van hely)."""
        return self.estimated_time_ms - self.available_time_ms
    
    @property
    def overflow_chars(self) -> int:
        """Hány karakterrel hosszabb a kelleténél."""
        if self.overflow_ms <= 0:
            return 0
        return int(self.overflow_ms * CHARS_PER_SECOND_NORMAL / 1000)
    
    def get_status_text(self) -> str:
        """Státusz szöveges leírása."""
        if self.status == LipSyncStatus.GOOD:
            return "Megfelelő"
        elif self.status == LipSyncStatus.WARNING:
            return "Határeset"
        elif self.status == LipSyncStatus.TOO_LONG:
            return f"Túl hosszú (~{self.overflow_chars} karakterrel)"
        else:
            return "Nincs adat"


class LipSyncEstimator:
    """
    Lip-sync becslő osztály.
    
    A becslés a szöveg hossza és a rendelkezésre álló idő
    alapján történik. Figyelembe veszi az eredeti (angol) szöveg
    hosszát is a reális becsléshez.
    """
    
    # Regex pattern a szögletes zárójelben lévő instrukciók eltávolításához
    BRACKET_PATTERN = re.compile(r'\[.*?\]')
    
    def __init__(
        self, 
        chars_per_second: float = CHARS_PER_SECOND_NORMAL,
        source_chars_per_second: float = CHARS_PER_SECOND_ENGLISH
    ):
        """
        Inicializálás.
        
        Args:
            chars_per_second: Karakterek másodpercenként célnyelvhez (alapértelmezett: 13 - magyar)
            source_chars_per_second: Karakterek másodpercenként forrásnyelvhez (alapértelmezett: 15 - angol)
        """
        self.chars_per_second = chars_per_second
        self.source_chars_per_second = source_chars_per_second
    
    def estimate(
        self, 
        text: str, 
        duration_ms: int,
        source_text: str = ""
    ) -> LipSyncResult:
        """
        Lip-sync becslés egy szövegre.
        
        Ha van forrásszöveg, akkor a becslés figyelembe veszi
        az eredeti szöveg hosszát is - ha az eredeti rövid volt,
        akkor a fordítás is lehet rövidebb időre tervezve.
        
        Args:
            text: Szöveg (fordítás)
            duration_ms: Rendelkezésre álló idő milliszekundumban
            source_text: Eredeti (angol) szöveg a reálisabb becsléshez
            
        Returns:
            LipSyncResult a becslés eredményével
        """
        # Clean and measure text
        cleaned_text = self._prepare_text(text)
        text_length = len(cleaned_text)
        
        # Calculate estimated speaking time for translation
        if text_length == 0:
            estimated_ms = 0
        else:
            estimated_seconds = text_length / self.chars_per_second
            estimated_ms = int(estimated_seconds * 1000)
        
        # If we have source text, adjust based on original speaking speed
        # This handles cases where the original was spoken quickly
        effective_duration = duration_ms
        if source_text:
            cleaned_source = self._prepare_text(source_text)
            source_length = len(cleaned_source)
            if source_length > 0:
                # Calculate how fast the original was spoken
                source_speed = (source_length / duration_ms) * 1000  # chars per second
                
                # If the original was spoken faster than average English speed,
                # adjust the available time proportionally
                if source_speed > self.source_chars_per_second:
                    # The original was fast - give more leeway to translation
                    speed_ratio = source_speed / self.source_chars_per_second
                    effective_duration = int(duration_ms * speed_ratio)
        
        # Calculate ratio using effective duration
        if effective_duration > 0:
            ratio = estimated_ms / effective_duration
        else:
            ratio = float('inf') if text_length > 0 else 0.0
        
        # Determine status
        status = self._get_status(ratio)
        
        return LipSyncResult(
            text_length=text_length,
            available_time_ms=duration_ms,
            estimated_time_ms=estimated_ms,
            ratio=ratio,
            status=status,
        )
    
    def estimate_cue(self, cue: Cue) -> LipSyncResult:
        """
        Lip-sync becslés egy cue-ra.
        
        A fordított szöveget használja, ha van, egyébként a forrást.
        Figyelembe veszi az eredeti szöveg hosszát is.
        
        Args:
            cue: Cue objektum
            
        Returns:
            LipSyncResult a becslés eredményével
        """
        text = cue.translated_text if cue.translated_text else cue.source_text
        source = cue.source_text if cue.translated_text else ""
        return self.estimate(text, cue.duration_ms, source)
    
    def update_cue_ratio(self, cue: Cue) -> float:
        """
        Cue lip_sync_ratio frissítése.
        
        Args:
            cue: Cue objektum (módosítva lesz)
            
        Returns:
            Új arány érték
        """
        result = self.estimate_cue(cue)
        cue.lip_sync_ratio = result.ratio
        return result.ratio
    
    def _prepare_text(self, text: str) -> str:
        """
        Szöveg előkészítése a becsléshez.
        
        - Szögletes zárójelben lévő instrukciók eltávolítása [pl. sóhajt]
        - Sortörések szóközre cserélése
        - Többszörös szóközök normalizálása
        """
        if not text:
            return ""
        
        # Remove bracketed instructions (e.g., [sighs], [sóhajt], [quietly])
        text = self.BRACKET_PATTERN.sub('', text)
        
        # Replace newlines with spaces
        text = text.replace("\n", " ")
        
        # Normalize multiple spaces
        text = " ".join(text.split())
        
        return text.strip()
    
    def _get_status(self, ratio: float) -> LipSyncStatus:
        """
        Státusz meghatározása az arány alapján.
        """
        if ratio <= LIPSYNC_THRESHOLD_GOOD:
            return LipSyncStatus.GOOD
        elif ratio <= LIPSYNC_THRESHOLD_WARNING:
            return LipSyncStatus.WARNING
        else:
            return LipSyncStatus.TOO_LONG
    
    def calculate_max_chars(self, duration_ms: int) -> int:
        """
        Maximum karakterszám kiszámítása adott időtartamra.
        
        Args:
            duration_ms: Időtartam milliszekundumban
            
        Returns:
            Maximum karakterszám
        """
        seconds = duration_ms / 1000.0
        return int(seconds * self.chars_per_second)
    
    def calculate_min_duration(self, text: str) -> int:
        """
        Minimum szükséges idő kiszámítása adott szövegre.
        
        Args:
            text: Szöveg
            
        Returns:
            Minimum idő milliszekundumban
        """
        cleaned = self._prepare_text(text)
        if not cleaned:
            return 0
        
        seconds = len(cleaned) / self.chars_per_second
        return int(seconds * 1000)


def get_lipsync_color(status: LipSyncStatus) -> str:
    """
    Lip-sync státuszhoz tartozó szín lekérése.
    
    Args:
        status: LipSyncStatus enum érték
        
    Returns:
        Hex szín string
    """
    from dubsync.utils.constants import (
        COLOR_LIPSYNC_GOOD,
        COLOR_LIPSYNC_WARNING,
        COLOR_LIPSYNC_TOO_LONG,
        COLOR_LIPSYNC_UNKNOWN,
    )
    
    colors = {
        LipSyncStatus.GOOD: COLOR_LIPSYNC_GOOD,
        LipSyncStatus.WARNING: COLOR_LIPSYNC_WARNING,
        LipSyncStatus.TOO_LONG: COLOR_LIPSYNC_TOO_LONG,
        LipSyncStatus.UNKNOWN: COLOR_LIPSYNC_UNKNOWN,
    }
    
    return colors.get(status, COLOR_LIPSYNC_UNKNOWN)


# Convenience functions
def estimate_lipsync(text: str, duration_ms: int) -> LipSyncResult:
    """
    Quick lip-sync becslés.
    """
    estimator = LipSyncEstimator()
    return estimator.estimate(text, duration_ms)


def check_cue_lipsync(cue: Cue) -> Tuple[LipSyncStatus, float]:
    """
    Cue lip-sync ellenőrzése.
    
    Returns:
        Tuple (státusz, arány)
    """
    estimator = LipSyncEstimator()
    result = estimator.estimate_cue(cue)
    return result.status, result.ratio
