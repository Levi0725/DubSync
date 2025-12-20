"""
DubSync Lip-Sync Estimator

Lip-sync estimation system for dubbing translation.

The system uses time-based estimation, not phonetic analysis:
- Hungarian average speech rate: 12-15 characters/second
- English average speech rate: 14-17 characters/second (faster)
- Takes into account the length of the original text as well
- Ignores instructions in square brackets
- Counts spaces and punctuation (natural rhythm)
- Three categories: good, borderline, too long
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

# English speech rate (generally faster than Hungarian)
CHARS_PER_SECOND_ENGLISH: float = 15.0


@dataclass
class LipSyncResult:
    """
    Lip-sync estimation result.
    """
    text_length: int            # Text length (characters)
    available_time_ms: int      # Available time (ms)
    estimated_time_ms: int      # Estimated speaking time (ms)
    ratio: float                # Ratio (estimated / available)
    status: LipSyncStatus       # Status (good, warning, too long)
    
    @property
    def is_ok(self) -> bool:
        """Is the lip-sync acceptable?"""
        return self.status in (LipSyncStatus.GOOD, LipSyncStatus.WARNING)
    
    @property
    def overflow_ms(self) -> int:
        """Overflow in milliseconds (negative means there is room)."""
        return self.estimated_time_ms - self.available_time_ms
    
    @property
    def overflow_chars(self) -> int:
        """How many characters longer than allowed."""
        if self.overflow_ms <= 0:
            return 0
        return int(self.overflow_ms * CHARS_PER_SECOND_NORMAL / 1000)
    
    def get_status_text(self) -> str:
        """Status text description."""
        if self.status == LipSyncStatus.GOOD:
            return "Good"
        elif self.status == LipSyncStatus.WARNING:
            return "Borderline"
        elif self.status == LipSyncStatus.TOO_LONG:
            return f"Too long (~{self.overflow_chars} characters over)"
        else:
            return "No data"


class LipSyncEstimator:
    """
    Lip-sync estimator class.
    
    The estimation is based on the length of the text and the available time.
    It also takes into account the original (English) text length for a more realistic estimate.
    """
    
    # Regex pattern to remove instructions in square brackets
    BRACKET_PATTERN = re.compile(r'\[.*?\]')
    
    def __init__(
        self, 
        chars_per_second: float = CHARS_PER_SECOND_NORMAL,
        source_chars_per_second: float = CHARS_PER_SECOND_ENGLISH
    ):
        """
        Initialization.
        
        Args:
            chars_per_second: Characters per second for target language (default: 13 - Hungarian)
            source_chars_per_second: Characters per second for source language (default: 15 - English)
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
        Lip-sync estimation for a text.
        
        If there is source text, the estimation takes into account
        the length of the original text - if the original was short,
        the translation may also be planned for a shorter time.
        
        Args:
            text: Text (translation)
            duration_ms: Available time in milliseconds
            source_text: Original (English) text for more realistic estimation
            
        Returns:
            LipSyncResult with the estimation result
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
        Lip-sync estimation for a cue.
        
        Uses the translated text if available, otherwise the source.
        Takes into account the length of the original text as well.
        
        Args:
            cue: Cue object
            
        Returns:
            LipSyncResult with the estimation result
        """
        text = cue.translated_text or cue.source_text
        source = cue.source_text if cue.translated_text else ""
        return self.estimate(text, cue.duration_ms, source)
    
    def update_cue_ratio(self, cue: Cue) -> float:
        """
        Update cue lip_sync_ratio.
        
        Args:
            cue: Cue object (will be modified)
            
        Returns:
            New ratio value
        """
        result = self.estimate_cue(cue)
        cue.lip_sync_ratio = result.ratio
        return result.ratio
    
    def _prepare_text(self, text: str) -> str:
        """
        Prepare text for estimation.
        
        - Remove instructions in square brackets [e.g., sighs]
        - Replace newlines with spaces
        - Normalize multiple spaces
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
        Determine status based on ratio.
        """
        if ratio <= LIPSYNC_THRESHOLD_GOOD:
            return LipSyncStatus.GOOD
        elif ratio <= LIPSYNC_THRESHOLD_WARNING:
            return LipSyncStatus.WARNING
        else:
            return LipSyncStatus.TOO_LONG
    
    def calculate_max_chars(self, duration_ms: int) -> int:
        """
        Calculate maximum number of characters for a given duration.
        
        Args:
            duration_ms: Duration in milliseconds
            
        Returns:
            Maximum number of characters
        """
        seconds = duration_ms / 1000.0
        return int(seconds * self.chars_per_second)
    
    def calculate_min_duration(self, text: str) -> int:
        """
        Calculate minimum required duration for a given text.
        
        Args:
            text: Text
            
        Returns:
            Minimum duration in milliseconds
        """
        cleaned = self._prepare_text(text)
        if not cleaned:
            return 0
        
        seconds = len(cleaned) / self.chars_per_second
        return int(seconds * 1000)


def get_lipsync_color(status: LipSyncStatus) -> str:
    """
    Get color associated with lip-sync status.
    
    Args:
        status: LipSyncStatus enum value
        
    Returns:
        Hex color string
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
    Quick lip-sync estimation.
    """
    estimator = LipSyncEstimator()
    return estimator.estimate(text, duration_ms)


def check_cue_lipsync(cue: Cue) -> Tuple[LipSyncStatus, float]:
    """
    Check cue lip-sync.
    
    Returns:
        Tuple (status, ratio)
    """
    estimator = LipSyncEstimator()
    result = estimator.estimate_cue(cue)
    return result.status, result.ratio
