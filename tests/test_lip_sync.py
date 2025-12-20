"""
DubSync Lip-Sync Estimator Tests

Lip-sync becslő tesztek.
"""

import pytest
from dubsync.services.lip_sync import (
    LipSyncEstimator, LipSyncResult, estimate_lipsync, check_cue_lipsync,
    get_lipsync_color
)
from dubsync.models.cue import Cue
from dubsync.utils.constants import (
    LipSyncStatus, CHARS_PER_SECOND_NORMAL,
    COLOR_LIPSYNC_GOOD, COLOR_LIPSYNC_WARNING, COLOR_LIPSYNC_TOO_LONG
)


class TestLipSyncEstimator:
    """LipSyncEstimator osztály tesztjei."""
    
    @pytest.fixture
    def estimator(self):
        return LipSyncEstimator()
    
    def test_estimate_empty_text(self, estimator):
        """Üres szöveg becslése."""
        result = estimator.estimate("", 5000)
        
        assert result.text_length == 0
        assert result.estimated_time_ms == 0
        assert result.status == LipSyncStatus.GOOD
    
    def test_estimate_short_text(self, estimator):
        """Rövid szöveg (jó lip-sync)."""
        # 5 seconds, ~65 chars would be max
        result = estimator.estimate("Hello", 5000)
        
        assert result.text_length == 5
        assert result.status == LipSyncStatus.GOOD
        assert result.is_ok
    
    def test_estimate_long_text(self, estimator):
        """Túl hosszú szöveg."""
        # 1 second, ~13 chars max
        long_text = "Ez egy nagyon-nagyon hosszú szöveg ami nem fér bele az időbe"
        result = estimator.estimate(long_text, 1000)
        
        assert result.status == LipSyncStatus.TOO_LONG
        assert not result.is_ok
        assert result.overflow_ms > 0
    
    def test_estimate_warning_range(self, estimator):
        """Határeset (warning)."""
        # Create text that's ~95% of available time
        duration_ms = 3000
        max_chars = int(duration_ms / 1000 * CHARS_PER_SECOND_NORMAL)
        text = "x" * int(max_chars * 0.95)
        
        result = estimator.estimate(text, duration_ms)
        
        # Should be GOOD or WARNING, not TOO_LONG
        assert result.status in (LipSyncStatus.GOOD, LipSyncStatus.WARNING)
    
    def test_estimate_normalizes_whitespace(self, estimator):
        """Szóközök normalizálása."""
        text_with_newlines = "Line one\nLine two\nLine three"
        text_with_spaces = "Line one Line two Line three"
        
        result1 = estimator.estimate(text_with_newlines, 5000)
        result2 = estimator.estimate(text_with_spaces, 5000)
        
        assert result1.text_length == result2.text_length
    
    def test_estimate_cue(self, estimator, sample_cues):
        """Cue becslése."""
        cue = sample_cues[0]  # Has translation
        result = estimator.estimate_cue(cue)
        
        assert result.text_length > 0
        assert result.available_time_ms == cue.duration_ms
    
    def test_estimate_cue_uses_translation(self, estimator):
        """Fordított szöveget használja."""
        self._extracted_from_test_estimate_cue_fallback_to_source_3(
            "Short",
            "Ez egy hosszabb fordított szöveg",
            estimator,
            "Ez egy hosszabb fordított szöveg",
        )
    
    def test_estimate_cue_fallback_to_source(self, estimator):
        """Visszaesés forrásra, ha nincs fordítás."""
        self._extracted_from_test_estimate_cue_fallback_to_source_3(
            "Source text only", "", estimator, "Source text only"
        )

    # TODO Rename this here and in `test_estimate_cue_uses_translation` and `test_estimate_cue_fallback_to_source`
    def _extracted_from_test_estimate_cue_fallback_to_source_3(self, source_text, translated_text, estimator, arg3):
        cue = Cue(
            time_in_ms=0,
            time_out_ms=5000,
            source_text=source_text,
            translated_text=translated_text,
        )
        result = estimator.estimate_cue(cue)
        assert result.text_length == len(arg3)
    
    def test_update_cue_ratio(self, estimator):
        """Cue ratio frissítése."""
        cue = Cue(
            time_in_ms=0,
            time_out_ms=5000,
            source_text="Test",
            translated_text="Teszt"
        )
        
        ratio = estimator.update_cue_ratio(cue)
        
        assert cue.lip_sync_ratio == ratio
        assert ratio > 0
    
    def test_calculate_max_chars(self, estimator):
        """Maximum karakterszám számítás."""
        # 5 seconds at 13 chars/sec = 65 chars
        max_chars = estimator.calculate_max_chars(5000)
        
        assert max_chars == int(5 * CHARS_PER_SECOND_NORMAL)
    
    def test_calculate_min_duration(self, estimator):
        """Minimum időtartam számítás."""
        text = "x" * 13  # 13 chars = 1 second at default rate
        min_duration = estimator.calculate_min_duration(text)
        
        assert min_duration == 1000


class TestLipSyncResult:
    """LipSyncResult tesztek."""
    
    def test_is_ok_good(self):
        """is_ok - jó státusznál."""
        result = LipSyncResult(
            text_length=10,
            available_time_ms=5000,
            estimated_time_ms=1000,
            ratio=0.2,
            status=LipSyncStatus.GOOD
        )
        assert result.is_ok
    
    def test_is_ok_warning(self):
        """is_ok - figyelmeztetésnél."""
        result = LipSyncResult(
            text_length=50,
            available_time_ms=5000,
            estimated_time_ms=4800,
            ratio=0.96,
            status=LipSyncStatus.WARNING
        )
        assert result.is_ok
    
    def test_is_ok_too_long(self):
        """is_ok - túl hosszúnál."""
        result = LipSyncResult(
            text_length=100,
            available_time_ms=5000,
            estimated_time_ms=8000,
            ratio=1.6,
            status=LipSyncStatus.TOO_LONG
        )
        assert not result.is_ok
    
    def test_overflow_ms(self):
        """Túlcsordulás számítás."""
        result = LipSyncResult(
            text_length=100,
            available_time_ms=5000,
            estimated_time_ms=8000,
            ratio=1.6,
            status=LipSyncStatus.TOO_LONG
        )
        assert result.overflow_ms == 3000
    
    def test_get_status_text(self):
        """Státusz szöveg."""
        result = LipSyncResult(
            text_length=10,
            available_time_ms=5000,
            estimated_time_ms=1000,
            ratio=0.2,
            status=LipSyncStatus.GOOD
        )
        assert result.get_status_text() == "Megfelelő"


class TestConvenienceFunctions:
    """Convenience function tesztek."""
    
    def test_estimate_lipsync(self):
        """estimate_lipsync function."""
        result = estimate_lipsync("Hello", 5000)
        
        assert isinstance(result, LipSyncResult)
        assert result.text_length == 5
    
    def test_check_cue_lipsync(self, sample_cues):
        """check_cue_lipsync function."""
        status, ratio = check_cue_lipsync(sample_cues[0])
        
        assert isinstance(status, LipSyncStatus)
        assert isinstance(ratio, float)
    
    def test_get_lipsync_color(self):
        """get_lipsync_color function."""
        assert get_lipsync_color(LipSyncStatus.GOOD) == COLOR_LIPSYNC_GOOD
        assert get_lipsync_color(LipSyncStatus.WARNING) == COLOR_LIPSYNC_WARNING
        assert get_lipsync_color(LipSyncStatus.TOO_LONG) == COLOR_LIPSYNC_TOO_LONG
