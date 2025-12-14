"""
DubSync Time Utils Tests

Időkezelő segédfüggvények tesztjei.
"""

import pytest
from dubsync.utils.time_utils import (
    ms_to_timecode,
    timecode_to_ms,
    format_duration,
    parse_srt_time_range,
    frames_to_ms,
    ms_to_frames,
    get_duration_ms
)


class TestMsToTimecode:
    """ms_to_timecode tesztek."""
    
    def test_zero(self):
        """0 ms konvertálása."""
        assert ms_to_timecode(0) == "00:00:00,000"
    
    def test_milliseconds_only(self):
        """Csak ezredmásodpercek."""
        assert ms_to_timecode(500) == "00:00:00,500"
    
    def test_seconds(self):
        """Másodpercek."""
        assert ms_to_timecode(5000) == "00:00:05,000"
    
    def test_minutes(self):
        """Percek."""
        assert ms_to_timecode(65000) == "00:01:05,000"
    
    def test_hours(self):
        """Órák."""
        assert ms_to_timecode(3661500) == "01:01:01,500"
    
    def test_use_dot_separator(self):
        """Pont szeparátor."""
        assert ms_to_timecode(1500, use_comma=False) == "00:00:01.500"
    
    def test_negative_returns_zero(self):
        """Negatív érték 0-t ad."""
        assert ms_to_timecode(-100) == "00:00:00,000"


class TestTimecodeToMs:
    """timecode_to_ms tesztek."""
    
    def test_zero(self):
        """0 időkód."""
        assert timecode_to_ms("00:00:00,000") == 0
    
    def test_milliseconds(self):
        """Ezredmásodpercek."""
        assert timecode_to_ms("00:00:00,500") == 500
    
    def test_seconds(self):
        """Másodpercek."""
        assert timecode_to_ms("00:00:05,000") == 5000
    
    def test_minutes(self):
        """Percek."""
        assert timecode_to_ms("00:01:05,000") == 65000
    
    def test_hours(self):
        """Órák."""
        assert timecode_to_ms("01:01:01,500") == 3661500
    
    def test_dot_separator(self):
        """Pont szeparátor támogatása."""
        assert timecode_to_ms("00:00:01.500") == 1500
    
    def test_short_ms(self):
        """Rövid ezredmásodperc (pl. ,5 -> 500)."""
        assert timecode_to_ms("00:00:01,5") == 1500
    
    def test_invalid_format(self):
        """Érvénytelen formátum."""
        with pytest.raises(ValueError):
            timecode_to_ms("invalid")
    
    def test_roundtrip(self):
        """Oda-vissza konverzió."""
        original = 3661500
        timecode = ms_to_timecode(original)
        result = timecode_to_ms(timecode)
        assert result == original


class TestFormatDuration:
    """format_duration tesztek."""
    
    def test_seconds(self):
        """Másodpercek."""
        assert format_duration(1500) == "1.5s"
    
    def test_minutes(self):
        """Percek."""
        assert format_duration(150000) == "2m 30s"
    
    def test_hours(self):
        """Órák."""
        assert format_duration(7200000) == "2h 0m"
    
    def test_zero(self):
        """0 időtartam."""
        assert format_duration(0) == "0.0s"
    
    def test_negative(self):
        """Negatív érték."""
        assert format_duration(-100) == "0s"


class TestParseSrtTimeRange:
    """parse_srt_time_range tesztek."""
    
    def test_standard_format(self):
        """Standard SRT formátum."""
        time_in, time_out = parse_srt_time_range("00:00:01,000 --> 00:00:04,000")
        assert time_in == 1000
        assert time_out == 4000
    
    def test_with_extra_spaces(self):
        """Extra szóközökkel."""
        time_in, time_out = parse_srt_time_range("00:00:01,000  -->  00:00:04,000")
        assert time_in == 1000
        assert time_out == 4000
    
    def test_invalid_format(self):
        """Érvénytelen formátum."""
        with pytest.raises(ValueError):
            parse_srt_time_range("invalid time range")


class TestFrameConversion:
    """Frame konverziós tesztek."""
    
    def test_frames_to_ms_default_fps(self):
        """Frame -> ms 25 fps-nél."""
        assert frames_to_ms(25) == 1000
    
    def test_frames_to_ms_custom_fps(self):
        """Frame -> ms egyedi fps-nél."""
        assert frames_to_ms(30, fps=30.0) == 1000
    
    def test_ms_to_frames_default_fps(self):
        """Ms -> frame 25 fps-nél."""
        assert ms_to_frames(1000) == 25
    
    def test_ms_to_frames_custom_fps(self):
        """Ms -> frame egyedi fps-nél."""
        assert ms_to_frames(1000, fps=30.0) == 30


class TestGetDurationMs:
    """get_duration_ms tesztek."""
    
    def test_normal(self):
        """Normál időtartam."""
        assert get_duration_ms(1000, 5000) == 4000
    
    def test_zero_duration(self):
        """Nulla időtartam."""
        assert get_duration_ms(1000, 1000) == 0
    
    def test_negative_returns_zero(self):
        """Negatív érték 0-t ad."""
        assert get_duration_ms(5000, 1000) == 0
