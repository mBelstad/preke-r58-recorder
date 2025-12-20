"""Cairo-based broadcast graphics for real-time overlays.

This package provides high-performance graphics rendering using Cairo,
integrated with GStreamer's cairooverlay element.

Components:
- CairoGraphicsManager: Main manager coordinating all graphics elements
- GraphicsElement: Base class for all graphics (lower thirds, scoreboards, etc.)
- Animation helpers: Easing functions and timing utilities

Features:
- Real-time updates (0-33ms latency)
- Smooth animations (30/60fps)
- Low CPU usage (5-15% for all graphics)
- Thread-safe API control
- Multiple simultaneous elements

Usage:
    from cairo_graphics import CairoGraphicsManager, LowerThird, Scoreboard
    
    manager = CairoGraphicsManager()
    lower_third = LowerThird("lt1", name="John Doe", title="CEO")
    manager.add_element("lt1", lower_third)
    lower_third.show()
"""

from .manager import CairoGraphicsManager
from .elements import (
    GraphicsElement,
    LowerThird,
    Scoreboard,
    Ticker,
    Timer,
    LogoOverlay
)
from .animations import (
    ease_in_out_cubic,
    ease_out_bounce,
    ease_in_cubic,
    ease_out_cubic,
    lerp
)

__all__ = [
    "CairoGraphicsManager",
    "GraphicsElement",
    "LowerThird",
    "Scoreboard",
    "Ticker",
    "Timer",
    "LogoOverlay",
    "ease_in_out_cubic",
    "ease_out_bounce",
    "ease_in_cubic",
    "ease_out_cubic",
    "lerp"
]

