"""
DubSync Time Utilities

Időkezelő segédfüggvények SRT és videó számára.
"""

import re
from typing import Optional, Tuple


def ms_to_timecode(milliseconds: int, use_comma: bool = True) -> str:
    """
    Milliszekundumot SRT formátumú időkóddá alakít.
    
    Args:
        milliseconds: Idő milliszekundumban
        use_comma: Ha True, vesszőt használ (SRT), egyébként pontot
        
    Returns:
        Időkód string (HH:MM:SS,mmm vagy HH:MM:SS.mmm)
        
    Example:
        >>> ms_to_timecode(3661500)
        '01:01:01,500'
    """
    milliseconds = max(milliseconds, 0)
    hours = milliseconds // 3600000
    minutes = (milliseconds % 3600000) // 60000
    seconds = (milliseconds % 60000) // 1000
    ms = milliseconds % 1000

    separator = "," if use_comma else "."
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{ms:03d}"


def timecode_to_ms(timecode: str) -> int:
    """
    SRT időkódot milliszekundummá alakít.
    
    Args:
        timecode: Időkód string (HH:MM:SS,mmm vagy HH:MM:SS.mmm)
        
    Returns:
        Idő milliszekundumban
        
    Raises:
        ValueError: Ha az időkód formátuma nem megfelelő
        
    Example:
        >>> timecode_to_ms("01:01:01,500")
        3661500
    """
    # Support both comma and dot as millisecond separator
    timecode = timecode.strip().replace(",", ".")

    pattern = r"^(\d{1,2}):(\d{2}):(\d{2})\.(\d{1,3})$"
    match = re.match(pattern, timecode)

    if not match:
        raise ValueError(f"Érvénytelen időkód formátum: {timecode}")

    hours, minutes, seconds, ms = match.groups()

    # Pad milliseconds if needed (e.g., "5" -> "500")
    ms = ms.ljust(3, "0")

    return (
        int(hours) * 3600000
        + int(minutes) * 60000
        + int(seconds) * 1000
        + int(ms)
    )


def format_duration(milliseconds: int) -> str:
    """
    Időtartamot formáz olvasható formába.
    
    Args:
        milliseconds: Időtartam milliszekundumban
        
    Returns:
        Formázott időtartam (pl. "1.5s" vagy "2m 30s")
        
    Example:
        >>> format_duration(1500)
        '1.5s'
        >>> format_duration(150000)
        '2m 30s'
    """
    if milliseconds < 0:
        return "0s"
    
    seconds = milliseconds / 1000.0
    
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def parse_srt_time_range(time_line: str) -> Tuple[int, int]:
    """
    SRT idősor elemzése (time_in --> time_out).
    
    Args:
        time_line: SRT idősor (pl. "00:00:01,000 --> 00:00:04,000")
        
    Returns:
        Tuple (time_in_ms, time_out_ms)
        
    Raises:
        ValueError: Ha a formátum nem megfelelő
    """
    parts = time_line.strip().split("-->")
    
    if len(parts) != 2:
        raise ValueError(f"Érvénytelen SRT idősor: {time_line}")
    
    time_in = timecode_to_ms(parts[0].strip())
    time_out = timecode_to_ms(parts[1].strip())
    
    return time_in, time_out


def frames_to_ms(frames: int, fps: float = 25.0) -> int:
    """
    Frame-számot milliszekundummá alakít.
    
    Args:
        frames: Frame-ek száma
        fps: Frame rate (alapértelmezett: 25 fps)
        
    Returns:
        Idő milliszekundumban
    """
    return int((frames / fps) * 1000)


def ms_to_frames(milliseconds: int, fps: float = 25.0) -> int:
    """
    Milliszekundumot frame-számmá alakít.
    
    Args:
        milliseconds: Idő milliszekundumban
        fps: Frame rate (alapértelmezett: 25 fps)
        
    Returns:
        Frame-ek száma
    """
    return int((milliseconds / 1000.0) * fps)


def get_duration_ms(time_in_ms: int, time_out_ms: int) -> int:
    """
    Két időpont közötti időtartam kiszámítása.
    
    Args:
        time_in_ms: Kezdő időpont milliszekundumban
        time_out_ms: Befejező időpont milliszekundumban
        
    Returns:
        Időtartam milliszekundumban (minimum 0)
    """
    return max(0, time_out_ms - time_in_ms)
