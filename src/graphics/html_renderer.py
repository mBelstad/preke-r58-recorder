"""HTML/CSS graphics renderer for complex graphics that GStreamer can't handle natively."""
import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class HTMLGraphicsSource:
    """HTML graphics source configuration."""
    source_id: str
    template_id: str
    template_path: Path
    data: Dict[str, Any]
    output_path: Optional[Path] = None


class HTMLGraphicsRenderer:
    """Renders HTML/CSS graphics to video streams for mixer input."""
    
    def __init__(self, templates_dir: str = "graphics_templates", output_dir: str = "/tmp/mixer_graphics"):
        """Initialize HTML graphics renderer.
        
        Args:
            templates_dir: Directory containing HTML graphics templates
            output_dir: Directory for temporary graphics outputs
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.active_sources: Dict[str, HTMLGraphicsSource] = {}
        self._lock = threading.Lock()
        
        # Web server port for serving HTML templates
        self.web_port = 8001
        
    def _generate_html_from_template(self, template_path: Path, data: Dict[str, Any]) -> str:
        """Generate HTML from a template with data binding.
        
        Args:
            template_path: Path to HTML template file
            data: Data to bind to template
            
        Returns:
            Generated HTML content
        """
        try:
            template_content = template_path.read_text()
            
            # Simple template engine: replace {{variable}} with data values
            # For more complex templates, consider using Jinja2
            html_content = template_content
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                html_content = html_content.replace(placeholder, str(value))
            
            return html_content
        except Exception as e:
            logger.error(f"Failed to generate HTML from template {template_path}: {e}")
            return ""
    
    def create_stinger_source(self, source_id: str, stinger_data: Dict[str, Any]) -> Optional[str]:
        """Create a stinger (transition animation) graphics source.
        
        Args:
            source_id: Unique identifier
            stinger_data: Stinger configuration
                - template_id: Template ID (optional)
                - type: Stinger type ("wipe", "fade", "slide", etc.)
                - duration: Animation duration in seconds
                - logo_path: Path to logo image (optional)
                - background_color: Background color
                - text: Text to display (optional)
        
        Returns:
            GStreamer pipeline string or None
        """
        logger.info(f"Creating stinger source: {source_id}")
        
        # For now, return None as this requires HTML rendering
        # Future implementation would:
        # 1. Load HTML template for stinger type
        # 2. Generate HTML with data binding
        # 3. Serve via web server or render with headless browser
        # 4. Capture as video stream
        
        logger.warning(f"Stinger rendering not yet implemented for {source_id}")
        return None
    
    def create_ticker_source(self, source_id: str, ticker_data: Dict[str, Any]) -> Optional[str]:
        """Create a ticker (scrolling text) graphics source.
        
        Args:
            source_id: Unique identifier
            ticker_data: Ticker configuration
                - text: Text to scroll
                - direction: Scroll direction ("left", "right", "up", "down")
                - speed: Scroll speed (pixels per second)
                - background_color: Background color
                - text_color: Text color
                - font: Font description
                - position: Position on screen ("top", "bottom")
        
        Returns:
            GStreamer pipeline string or None
        """
        logger.info(f"Creating ticker source: {source_id}")
        
        # For now, return None as this requires HTML/CSS rendering
        # Future implementation would:
        # 1. Generate HTML with CSS animation for scrolling
        # 2. Serve via web server
        # 3. Capture with souphttpsrc or headless browser
        
        logger.warning(f"Ticker rendering not yet implemented for {source_id}")
        return None
    
    def create_timer_source(self, source_id: str, timer_data: Dict[str, Any]) -> Optional[str]:
        """Create a timer (countdown/clock) graphics source.
        
        Args:
            source_id: Unique identifier
            timer_data: Timer configuration
                - type: Timer type ("countdown", "clock", "stopwatch")
                - duration: Countdown duration in seconds (for countdown)
                - format: Time format (e.g., "MM:SS", "HH:MM:SS")
                - position: Position on screen
                - background_color: Background color
                - text_color: Text color
                - font: Font description
        
        Returns:
            GStreamer pipeline string or None
        """
        logger.info(f"Creating timer source: {source_id}")
        
        # For countdown/clock, we could use GStreamer's timeoverlay
        # For more complex timers, use HTML/CSS
        
        timer_type = timer_data.get("type", "countdown")
        
        if timer_type == "clock":
            # Use GStreamer's timeoverlay for simple clock
            position = timer_data.get("position", "top-right")
            text_color = timer_data.get("text_color", "#FFFFFF")
            font = timer_data.get("font", "Sans 24")
            
            # Convert position to GStreamer format
            if position == "top-right":
                halign = "right"
                valign = "top"
            elif position == "top-left":
                halign = "left"
                valign = "top"
            elif position == "bottom-right":
                halign = "right"
                valign = "bottom"
            else:  # bottom-left
                halign = "left"
                valign = "bottom"
            
            # Convert hex color to GStreamer format
            text_color_hex = text_color.lstrip('#')
            if len(text_color_hex) == 6:
                r = int(text_color_hex[0:2], 16)
                g = int(text_color_hex[2:4], 16)
                b = int(text_color_hex[4:6], 16)
                color_gst = f"0xFFFFFFFF{r:02X}{g:02X}{b:02X}"
            else:
                color_gst = "0xFFFFFFFFFFFFFF"
            
            pipeline = (
                f"videotestsrc pattern=solid-color ! "
                f"video/x-raw,width=1920,height=1080,framerate=30/1 ! "
                f"timeoverlay halign={halign} valign={valign} "
                f"font-desc=\"{font}\" color={color_gst} ! "
                f"videoconvert ! "
                f"video/x-raw,format=NV12"
            )
            
            return pipeline
        
        # For countdown and stopwatch, HTML/CSS would be better
        logger.warning(f"Timer type {timer_type} requires HTML rendering, not yet implemented")
        return None
    
    def get_source_pipeline(self, source: str) -> Optional[str]:
        """Get GStreamer pipeline string for an HTML graphics source.
        
        Args:
            source: Source identifier (e.g., "stinger:transition1", "ticker:news1")
        
        Returns:
            GStreamer pipeline string or None
        """
        if ":" not in source:
            return None
        
        source_type, source_id = source.split(":", 1)
        
        with self._lock:
            if source_id not in self.active_sources:
                return None
            
            graphics_source = self.active_sources[source_id]
            
            if source_type == "stinger":
                return self.create_stinger_source(source_id, graphics_source.data)
            elif source_type == "ticker":
                return self.create_ticker_source(source_id, graphics_source.data)
            elif source_type == "timer":
                return self.create_timer_source(source_id, graphics_source.data)
            else:
                logger.warning(f"Unknown HTML graphics source type: {source_type}")
                return None

