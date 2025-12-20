"""Animation easing functions and timing utilities for Cairo graphics."""
import math
from typing import Tuple


def ease_in_out_cubic(t: float) -> float:
    """Cubic easing in/out - smooth acceleration and deceleration.
    
    Args:
        t: Progress from 0.0 to 1.0
    
    Returns:
        Eased value from 0.0 to 1.0
    """
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2


def ease_in_cubic(t: float) -> float:
    """Cubic easing in - smooth acceleration.
    
    Args:
        t: Progress from 0.0 to 1.0
    
    Returns:
        Eased value from 0.0 to 1.0
    """
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """Cubic easing out - smooth deceleration.
    
    Args:
        t: Progress from 0.0 to 1.0
    
    Returns:
        Eased value from 0.0 to 1.0
    """
    return 1 - pow(1 - t, 3)


def ease_out_bounce(t: float) -> float:
    """Bounce easing out - bouncy ending.
    
    Args:
        t: Progress from 0.0 to 1.0
    
    Returns:
        Eased value from 0.0 to 1.0 with bounce
    """
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


def ease_in_out_sine(t: float) -> float:
    """Sine easing in/out - very smooth.
    
    Args:
        t: Progress from 0.0 to 1.0
    
    Returns:
        Eased value from 0.0 to 1.0
    """
    return -(math.cos(math.pi * t) - 1) / 2


def lerp(start: float, end: float, t: float) -> float:
    """Linear interpolation between two values.
    
    Args:
        start: Start value
        end: End value
        t: Progress from 0.0 to 1.0
    
    Returns:
        Interpolated value
    """
    return start + (end - start) * t


def lerp_color(start_rgb: Tuple[float, float, float], 
               end_rgb: Tuple[float, float, float], 
               t: float) -> Tuple[float, float, float]:
    """Linear interpolation between two RGB colors.
    
    Args:
        start_rgb: Start color (r, g, b) in 0.0-1.0 range
        end_rgb: End color (r, g, b) in 0.0-1.0 range
        t: Progress from 0.0 to 1.0
    
    Returns:
        Interpolated color (r, g, b)
    """
    return (
        lerp(start_rgb[0], end_rgb[0], t),
        lerp(start_rgb[1], end_rgb[1], t),
        lerp(start_rgb[2], end_rgb[2], t)
    )


def hex_to_rgb(hex_color: str) -> Tuple[float, float, float]:
    """Convert hex color to RGB tuple (0.0-1.0 range).
    
    Args:
        hex_color: Hex color string (e.g., "#FF0000" or "FF0000")
    
    Returns:
        RGB tuple (r, g, b) in 0.0-1.0 range
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0
    return (r, g, b)


def timestamp_to_seconds(timestamp: int) -> float:
    """Convert GStreamer timestamp (nanoseconds) to seconds.
    
    Args:
        timestamp: GStreamer timestamp in nanoseconds
    
    Returns:
        Time in seconds
    """
    return timestamp / 1_000_000_000.0

