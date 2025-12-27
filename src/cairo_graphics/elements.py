"""Graphics elements for Cairo-based broadcast graphics.

Each element is a self-contained graphics object that can be shown, hidden,
updated, and animated independently.
"""
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from .animations import (
    ease_in_out_cubic,
    ease_out_bounce,
    lerp,
    hex_to_rgb,
    timestamp_to_seconds
)

logger = logging.getLogger(__name__)

# Try to import Cairo - will be available on R58
try:
    import cairo
    CAIRO_AVAILABLE = True
except ImportError:
    logger.warning("Cairo not available - graphics elements will not render")
    CAIRO_AVAILABLE = False


@dataclass
class GraphicsElement:
    """Base class for all Cairo graphics elements."""
    
    element_id: str
    visible: bool = False
    x: int = 0
    y: int = 0
    alpha: float = 1.0
    
    # Animation state
    show_time: Optional[int] = None  # GStreamer timestamp when shown
    hide_time: Optional[int] = None  # GStreamer timestamp when hidden
    animation_state: str = "hidden"  # hidden, entering, visible, exiting
    animation_duration: float = 0.5  # seconds
    
    def show(self, timestamp: int) -> None:
        """Show element with animation.
        
        Args:
            timestamp: GStreamer timestamp in nanoseconds
        """
        self.visible = True
        self.show_time = timestamp
        self.animation_state = "entering"
        logger.debug(f"Element {self.element_id} showing")
    
    def hide(self, timestamp: int) -> None:
        """Hide element with animation.
        
        Args:
            timestamp: GStreamer timestamp in nanoseconds
        """
        self.hide_time = timestamp
        self.animation_state = "exiting"
        logger.debug(f"Element {self.element_id} hiding")
    
    def get_animation_progress(self, timestamp: int) -> float:
        """Get current animation progress (0.0 to 1.0).
        
        Args:
            timestamp: Current GStreamer timestamp
        
        Returns:
            Progress from 0.0 (start) to 1.0 (complete)
        """
        if self.animation_state == "entering" and self.show_time is not None:
            elapsed = timestamp_to_seconds(timestamp - self.show_time)
            progress = min(elapsed / self.animation_duration, 1.0)
            if progress >= 1.0:
                self.animation_state = "visible"
            return progress
        
        elif self.animation_state == "exiting" and self.hide_time is not None:
            elapsed = timestamp_to_seconds(timestamp - self.hide_time)
            progress = min(elapsed / self.animation_duration, 1.0)
            if progress >= 1.0:
                self.animation_state = "hidden"
                self.visible = False
            return progress
        
        return 1.0  # Fully visible or hidden
    
    def draw(self, context, timestamp: int) -> None:
        """Draw the element. Override in subclasses.
        
        Args:
            context: Cairo context
            timestamp: GStreamer timestamp in nanoseconds
        """
        pass


class LowerThird(GraphicsElement):
    """Lower third graphic with name and title."""
    
    def __init__(
        self,
        element_id: str,
        name: str = "",
        title: str = "",
        x: int = 50,
        y: int = 900,
        width: int = 600,
        height: int = 120,
        bg_color: str = "#000000",
        bg_alpha: float = 0.8,
        text_color: str = "#FFFFFF",
        name_font_size: int = 48,
        title_font_size: int = 28,
        logo_path: Optional[str] = None,
        animation_duration: float = 0.5
    ):
        super().__init__(
            element_id=element_id,
            x=x,
            y=y,
            animation_duration=animation_duration
        )
        self.name = name
        self.title = title
        self.width = width
        self.height = height
        self.bg_color = hex_to_rgb(bg_color)
        self.bg_alpha = bg_alpha
        self.text_color = hex_to_rgb(text_color)
        self.name_font_size = name_font_size
        self.title_font_size = title_font_size
        self.logo_surface: Optional[Any] = None
        
        # Load logo if provided
        if logo_path and Path(logo_path).exists() and CAIRO_AVAILABLE:
            try:
                self.logo_surface = cairo.ImageSurface.create_from_png(logo_path)
            except Exception as e:
                logger.warning(f"Failed to load logo {logo_path}: {e}")
    
    def update(self, name: Optional[str] = None, title: Optional[str] = None) -> None:
        """Update text content.
        
        Args:
            name: New name (None to keep current)
            title: New title (None to keep current)
        """
        if name is not None:
            self.name = name
        if title is not None:
            self.title = title
    
    def draw(self, context, timestamp: int) -> None:
        """Draw lower third with animation."""
        if not CAIRO_AVAILABLE:
            return
        
        if self.animation_state == "hidden":
            return
        
        # Get animation progress
        progress = self.get_animation_progress(timestamp)
        
        # Calculate position based on animation
        if self.animation_state == "entering":
            eased = ease_in_out_cubic(progress)
            current_x = -self.width + (self.x + self.width) * eased
            current_alpha = self.alpha * eased
        elif self.animation_state == "exiting":
            eased = ease_in_out_cubic(progress)
            current_x = self.x - (self.x + self.width) * eased
            current_alpha = self.alpha * (1.0 - eased)
        else:  # visible
            current_x = self.x
            current_alpha = self.alpha
        
        # Draw background
        context.set_source_rgba(
            self.bg_color[0],
            self.bg_color[1],
            self.bg_color[2],
            self.bg_alpha * current_alpha
        )
        context.rectangle(current_x, self.y, self.width, self.height)
        context.fill()
        
        # Draw logo if available
        if self.logo_surface:
            logo_x = current_x + 10
            logo_y = self.y + (self.height - self.logo_surface.get_height()) / 2
            context.set_source_surface(self.logo_surface, logo_x, logo_y)
            context.paint_with_alpha(current_alpha)
            text_x = current_x + self.logo_surface.get_width() + 20
        else:
            text_x = current_x + 20
        
        # Draw name
        context.set_source_rgba(
            self.text_color[0],
            self.text_color[1],
            self.text_color[2],
            current_alpha
        )
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(self.name_font_size)
        context.move_to(text_x, self.y + 50)
        context.show_text(self.name)
        
        # Draw title
        if self.title:
            context.set_font_size(self.title_font_size)
            context.move_to(text_x, self.y + 85)
            context.show_text(self.title)


class Scoreboard(GraphicsElement):
    """Scoreboard graphic with two team scores."""
    
    def __init__(
        self,
        element_id: str,
        team1_name: str = "Team 1",
        team2_name: str = "Team 2",
        team1_score: int = 0,
        team2_score: int = 0,
        x: int = 1600,
        y: int = 50,
        width: int = 250,
        height: int = 150,
        bg_color: str = "#000000",
        bg_alpha: float = 0.9,
        text_color: str = "#FFFFFF",
        highlight_color: str = "#00FF00",
        highlight_duration: float = 2.0
    ):
        super().__init__(element_id=element_id, x=x, y=y)
        self.team1_name = team1_name
        self.team2_name = team2_name
        self.team1_score = team1_score
        self.team2_score = team2_score
        self.width = width
        self.height = height
        self.bg_color = hex_to_rgb(bg_color)
        self.bg_alpha = bg_alpha
        self.text_color = hex_to_rgb(text_color)
        self.highlight_color = hex_to_rgb(highlight_color)
        self.highlight_duration = highlight_duration
        
        # Highlight tracking
        self.highlight_team: Optional[int] = None  # 1 or 2
        self.highlight_start_time: float = 0.0
    
    def update_score(self, team1_score: Optional[int] = None, team2_score: Optional[int] = None) -> None:
        """Update scores with highlight on change.
        
        Args:
            team1_score: New team 1 score (None to keep current)
            team2_score: New team 2 score (None to keep current)
        """
        current_time = time.time()
        
        if team1_score is not None and team1_score != self.team1_score:
            self.team1_score = team1_score
            self.highlight_team = 1
            self.highlight_start_time = current_time
        
        if team2_score is not None and team2_score != self.team2_score:
            self.team2_score = team2_score
            self.highlight_team = 2
            self.highlight_start_time = current_time
    
    def draw(self, context, timestamp: int) -> None:
        """Draw scoreboard."""
        if not CAIRO_AVAILABLE or not self.visible:
            return
        
        # Check if highlight expired
        current_time = time.time()
        if self.highlight_team and (current_time - self.highlight_start_time) > self.highlight_duration:
            self.highlight_team = None
        
        # Draw background
        context.set_source_rgba(
            self.bg_color[0],
            self.bg_color[1],
            self.bg_color[2],
            self.bg_alpha * self.alpha
        )
        context.rectangle(self.x, self.y, self.width, self.height)
        context.fill()
        
        # Draw team 1 score
        if self.highlight_team == 1:
            context.set_source_rgba(
                self.highlight_color[0],
                self.highlight_color[1],
                self.highlight_color[2],
                self.alpha
            )
        else:
            context.set_source_rgba(
                self.text_color[0],
                self.text_color[1],
                self.text_color[2],
                self.alpha
            )
        
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(72)
        context.move_to(self.x + 50, self.y + 90)
        context.show_text(str(self.team1_score))
        
        # Draw separator
        context.set_source_rgba(0.5, 0.5, 0.5, self.alpha)
        context.set_font_size(48)
        context.move_to(self.x + 115, self.y + 90)
        context.show_text("-")
        
        # Draw team 2 score
        if self.highlight_team == 2:
            context.set_source_rgba(
                self.highlight_color[0],
                self.highlight_color[1],
                self.highlight_color[2],
                self.alpha
            )
        else:
            context.set_source_rgba(
                self.text_color[0],
                self.text_color[1],
                self.text_color[2],
                self.alpha
            )
        
        context.set_font_size(72)
        context.move_to(self.x + 150, self.y + 90)
        context.show_text(str(self.team2_score))
        
        # Draw team names (smaller)
        context.set_source_rgba(
            self.text_color[0],
            self.text_color[1],
            self.text_color[2],
            self.alpha * 0.7
        )
        context.set_font_size(16)
        context.move_to(self.x + 30, self.y + 130)
        context.show_text(self.team1_name)
        context.move_to(self.x + 130, self.y + 130)
        context.show_text(self.team2_name)


class Ticker(GraphicsElement):
    """Scrolling ticker text."""
    
    def __init__(
        self,
        element_id: str,
        text: str = "",
        x: int = 0,
        y: int = 0,
        width: int = 1920,
        height: int = 60,
        bg_color: str = "#CC0000",
        bg_alpha: float = 0.9,
        text_color: str = "#FFFFFF",
        font_size: int = 36,
        scroll_speed: float = 100.0  # pixels per second
    ):
        super().__init__(element_id=element_id, x=x, y=y)
        self.text = text
        self.width = width
        self.height = height
        self.bg_color = hex_to_rgb(bg_color)
        self.bg_alpha = bg_alpha
        self.text_color = hex_to_rgb(text_color)
        self.font_size = font_size
        self.scroll_speed = scroll_speed
        self.scroll_offset: float = 0.0
    
    def update_text(self, text: str) -> None:
        """Update ticker text.
        
        Args:
            text: New text to display
        """
        self.text = text
        self.scroll_offset = 0.0  # Reset scroll
    
    def draw(self, context, timestamp: int) -> None:
        """Draw scrolling ticker."""
        if not CAIRO_AVAILABLE or not self.visible:
            return
        
        # Draw background
        context.set_source_rgba(
            self.bg_color[0],
            self.bg_color[1],
            self.bg_color[2],
            self.bg_alpha * self.alpha
        )
        context.rectangle(self.x, self.y, self.width, self.height)
        context.fill()
        
        # Calculate scroll position
        time_sec = timestamp_to_seconds(timestamp)
        if self.show_time:
            elapsed = timestamp_to_seconds(timestamp - self.show_time)
            self.scroll_offset = elapsed * self.scroll_speed
        
        # Loop scroll (assuming text width ~10px per character)
        text_width = len(self.text) * 10
        scroll_x = self.x + self.width - (self.scroll_offset % (self.width + text_width))
        
        # Draw text
        context.set_source_rgba(
            self.text_color[0],
            self.text_color[1],
            self.text_color[2],
            self.alpha
        )
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(self.font_size)
        context.move_to(scroll_x, self.y + self.height - 15)
        context.show_text(self.text)


class Timer(GraphicsElement):
    """Countdown or countup timer."""
    
    def __init__(
        self,
        element_id: str,
        duration: float = 60.0,  # seconds
        mode: str = "countdown",  # countdown or countup
        x: int = 1700,
        y: int = 50,
        width: int = 180,
        height: int = 80,
        bg_color: str = "#000000",
        bg_alpha: float = 0.9,
        text_color: str = "#FFFFFF",
        warning_color: str = "#FF0000",
        warning_threshold: float = 10.0,  # seconds
        font_size: int = 60
    ):
        super().__init__(element_id=element_id, x=x, y=y)
        self.duration = duration
        self.mode = mode
        self.width = width
        self.height = height
        self.bg_color = hex_to_rgb(bg_color)
        self.bg_alpha = bg_alpha
        self.text_color = hex_to_rgb(text_color)
        self.warning_color = hex_to_rgb(warning_color)
        self.warning_threshold = warning_threshold
        self.font_size = font_size
        
        self.start_time: Optional[int] = None
        self.paused: bool = False
        self.pause_time: Optional[int] = None
        self.elapsed_at_pause: float = 0.0
    
    def start(self, timestamp: int) -> None:
        """Start timer.
        
        Args:
            timestamp: GStreamer timestamp
        """
        self.start_time = timestamp
        self.paused = False
        self.show(timestamp)
    
    def pause(self, timestamp: int) -> None:
        """Pause timer."""
        if not self.paused and self.start_time:
            self.paused = True
            self.pause_time = timestamp
            self.elapsed_at_pause = timestamp_to_seconds(timestamp - self.start_time)
    
    def resume(self, timestamp: int) -> None:
        """Resume timer."""
        if self.paused:
            self.paused = False
            self.start_time = timestamp - int(self.elapsed_at_pause * 1_000_000_000)
    
    def reset(self) -> None:
        """Reset timer."""
        self.start_time = None
        self.paused = False
        self.elapsed_at_pause = 0.0
    
    def get_current_time(self, timestamp: int) -> float:
        """Get current timer value in seconds."""
        if not self.start_time:
            return 0.0 if self.mode == "countup" else self.duration
        
        if self.paused:
            elapsed = self.elapsed_at_pause
        else:
            elapsed = timestamp_to_seconds(timestamp - self.start_time)
        
        if self.mode == "countdown":
            remaining = max(0.0, self.duration - elapsed)
            return remaining
        else:  # countup
            return elapsed
    
    def format_time(self, seconds: float) -> str:
        """Format time as MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def draw(self, context, timestamp: int) -> None:
        """Draw timer."""
        if not CAIRO_AVAILABLE or not self.visible:
            return
        
        # Get current time
        current_time = self.get_current_time(timestamp)
        time_str = self.format_time(current_time)
        
        # Determine color (warning if below threshold)
        if self.mode == "countdown" and current_time <= self.warning_threshold:
            color = self.warning_color
        else:
            color = self.text_color
        
        # Draw background
        context.set_source_rgba(
            self.bg_color[0],
            self.bg_color[1],
            self.bg_color[2],
            self.bg_alpha * self.alpha
        )
        context.rectangle(self.x, self.y, self.width, self.height)
        context.fill()
        
        # Draw time
        context.set_source_rgba(color[0], color[1], color[2], self.alpha)
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(self.font_size)
        
        # Center text
        extents = context.text_extents(time_str)
        text_x = self.x + (self.width - extents.width) / 2
        text_y = self.y + (self.height + extents.height) / 2
        
        context.move_to(text_x, text_y)
        context.show_text(time_str)


class LogoOverlay(GraphicsElement):
    """Logo overlay with optional pulse animation."""
    
    def __init__(
        self,
        element_id: str,
        logo_path: str,
        x: int = 1700,
        y: int = 50,
        scale: float = 1.0,
        pulse: bool = False,
        pulse_min: float = 0.9,
        pulse_max: float = 1.1,
        pulse_duration: float = 2.0
    ):
        super().__init__(element_id=element_id, x=x, y=y)
        self.scale = scale
        self.pulse = pulse
        self.pulse_min = pulse_min
        self.pulse_max = pulse_max
        self.pulse_duration = pulse_duration
        self.logo_surface: Optional[Any] = None
        
        # Load logo
        if Path(logo_path).exists() and CAIRO_AVAILABLE:
            try:
                self.logo_surface = cairo.ImageSurface.create_from_png(logo_path)
            except Exception as e:
                logger.error(f"Failed to load logo {logo_path}: {e}")
    
    def draw(self, context, timestamp: int) -> None:
        """Draw logo with optional pulse animation."""
        if not CAIRO_AVAILABLE or not self.visible or not self.logo_surface:
            return
        
        # Calculate scale (with pulse if enabled)
        current_scale = self.scale
        if self.pulse and self.show_time:
            elapsed = timestamp_to_seconds(timestamp - self.show_time)
            pulse_progress = (elapsed % self.pulse_duration) / self.pulse_duration
            pulse_value = self.pulse_min + (self.pulse_max - self.pulse_min) * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
            current_scale *= pulse_value
        
        # Get logo dimensions
        logo_width = self.logo_surface.get_width()
        logo_height = self.logo_surface.get_height()
        
        # Apply transform
        context.save()
        context.translate(self.x + logo_width / 2, self.y + logo_height / 2)
        context.scale(current_scale, current_scale)
        context.translate(-logo_width / 2, -logo_height / 2)
        
        # Draw logo
        context.set_source_surface(self.logo_surface, 0, 0)
        context.paint_with_alpha(self.alpha)
        
        context.restore()



