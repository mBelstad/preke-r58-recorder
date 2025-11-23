"""Graphics rendering for mixer sources (presentations, images, lower-thirds, etc.)."""
import logging
import subprocess
import threading
import time
import re
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .graphics_templates import (
    get_template,
    list_templates,
    get_position_config,
    GraphicsTemplate,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphicsSource:
    """Graphics source configuration."""
    source_id: str
    source_type: str  # "presentation", "image", "lower_third", "graphics"
    data: Dict[str, Any]
    output_path: Optional[str] = None


class GraphicsRenderer:
    """Renders graphics sources to video streams for mixer input."""
    
    def __init__(self, output_dir: str = "/tmp/mixer_graphics"):
        """Initialize graphics renderer.
        
        Args:
            output_dir: Directory for temporary graphics outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.active_sources: Dict[str, GraphicsSource] = {}
        self.pipelines: Dict[str, Any] = {}  # GStreamer pipelines
        self._lock = threading.Lock()
        
    def create_presentation_source(self, source_id: str, presentation_data: Dict[str, Any]) -> Optional[str]:
        """Create a video source from a Reveal.js presentation.
        
        Args:
            source_id: Unique identifier for this source
            presentation_data: Presentation configuration
                - id: Presentation ID
                - name: Presentation name
                - theme: Reveal.js theme (black, white, league, etc.)
                - slides: List of slide content (Markdown/HTML)
                - current_slide: Current slide index (optional)
        
        Returns:
            GStreamer pipeline string or None if failed
        """
        logger.info(f"Creating presentation source: {source_id}")
        
        # Store presentation data for later rendering
        graphics_source = GraphicsSource(
            source_id=source_id,
            source_type="presentation",
            data=presentation_data
        )
        
        with self._lock:
            self.active_sources[source_id] = graphics_source
        
        # Generate HTML file for Reveal.js presentation
        html_path = self._generate_reveal_html(source_id, presentation_data)
        if not html_path:
            logger.error(f"Failed to generate HTML for presentation {source_id}")
            return None
        
        # For now, use a simple approach: serve HTML via HTTP and capture with gst-launch
        # In production, this would use headless browser (Chromium) or similar
        # to render Reveal.js to video frames
        
        # Placeholder pipeline - full implementation would:
        # 1. Start a local web server serving the Reveal.js HTML
        # 2. Use gst-launch with souphttpsrc or similar to capture the rendered HTML
        # 3. Or use a headless browser (Chromium) with screen capture
        # 4. Return a proper GStreamer pipeline string
        
        # For now, return a test pattern that can be replaced later
        logger.warning(f"Presentation rendering not fully implemented - using placeholder for {source_id}")
        pipeline = (
            f"videotestsrc pattern=smpte ! "
            f"video/x-raw,width=1920,height=1080,framerate=30/1 ! "
            f"textoverlay text=\"Presentation: {presentation_data.get('name', source_id)}\" "
            f"valign=top halign=left font-desc=\"Sans 24\" color=0xFFFFFFFF ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
        
        return pipeline
    
    def _generate_reveal_html(self, source_id: str, presentation_data: Dict[str, Any]) -> Optional[Path]:
        """Generate Reveal.js HTML file from presentation data.
        
        Args:
            source_id: Source identifier
            presentation_data: Presentation configuration
        
        Returns:
            Path to generated HTML file or None if failed
        """
        try:
            html_path = self.output_dir / f"{source_id}.html"
            
            theme = presentation_data.get("theme", "black")
            slides = presentation_data.get("slides", [])
            
            # Generate Reveal.js HTML
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{presentation_data.get('name', 'Presentation')}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/theme/{theme}.css" id="theme">
</head>
<body>
    <div class="reveal">
        <div class="slides">
"""
            
            for slide in slides:
                content = slide.get("content", "")
                html_content += f"            <section data-markdown>\n"
                html_content += f"                <script type=\"text/template\">\n{content}\n                </script>\n"
                html_content += f"            </section>\n"
            
            html_content += """        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/dist/reveal.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.6.1/plugin/markdown/markdown.js"></script>
    <script>
        Reveal.initialize({
            hash: true,
            plugins: [ RevealMarkdown ]
        });
    </script>
</body>
</html>"""
            
            html_path.write_text(html_content)
            logger.info(f"Generated Reveal.js HTML: {html_path}")
            return html_path
            
        except Exception as e:
            logger.error(f"Failed to generate Reveal.js HTML for {source_id}: {e}")
            return None
    
    def create_image_source(self, source_id: str, image_path: str) -> Optional[str]:
        """Create a video source from an image.
        
        Args:
            source_id: Unique identifier
            image_path: Path to image file
        
        Returns:
            GStreamer pipeline string
        """
        if not Path(image_path).exists():
            logger.error(f"Image not found: {image_path}")
            return None
        
        # Create a looping video source from image
        pipeline = (
            f"multifilesrc location={image_path} loop=true ! "
            f"decodebin ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
        
        logger.info(f"Created image source: {source_id} from {image_path}")
        return pipeline
    
    def _hex_to_gstreamer_color(self, hex_color: str, alpha: float = 1.0) -> str:
        """Convert hex color to GStreamer color format (0xAARRGGBB)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # Round alpha to nearest integer (0.5 * 255 = 127.5 -> 128)
            a = int(round(alpha * 255))
            return f"0x{a:02X}{r:02X}{g:02X}{b:02X}"
        return "0xFFFFFFFF"
    
    def _escape_text(self, text: str) -> str:
        """Escape text for use in GStreamer pipeline."""
        # Escape quotes and backslashes
        text = text.replace("\\", "\\\\")
        text = text.replace('"', '\\"')
        return text
    
    def create_lower_third_source(self, source_id: str, text_data: Dict[str, Any]) -> Optional[str]:
        """Create a lower-third graphics overlay with enhanced features.
        
        Args:
            source_id: Unique identifier
            text_data: Lower-third configuration
                - line1: Primary text (required)
                - line2: Secondary text (optional)
                - background_color: Background color (hex, default: "#000000")
                - background_alpha: Background transparency (0.0-1.0, default: 0.8)
                - text_color: Text color (hex, default: "#FFFFFF")
                - line1_font: Font for line1 (default: "Sans Bold 32")
                - line2_font: Font for line2 (default: "Sans 24")
                - position: Position preset (default: "bottom-left")
                - width: Lower-third width (default: 600)
                - height: Lower-third height (default: 120)
                - padding: Padding dict with x, y (default: {"x": 20, "y": 15})
                - template_id: Template ID to apply (optional)
        
        Returns:
            GStreamer pipeline string using enhanced textoverlay with background
        """
        # Apply template if specified
        template_id = text_data.get("template_id")
        if template_id:
            template = get_template(template_id)
            if template:
                # Merge template defaults with provided data
                merged_data = template.default_config.copy()
                merged_data.update(text_data)
                text_data = merged_data
        
        # Extract configuration with defaults
        line1 = text_data.get("line1", "")
        line2 = text_data.get("line2", "")
        bg_color = text_data.get("background_color", "#000000")
        bg_alpha = text_data.get("background_alpha", 0.8)
        text_color = text_data.get("text_color", "#FFFFFF")
        line1_font = text_data.get("line1_font", "Sans Bold 32")
        line2_font = text_data.get("line2_font", "Sans 24")
        position = text_data.get("position", "bottom-left")
        width = text_data.get("width", 600)
        height = text_data.get("height", 120)
        padding = text_data.get("padding", {"x": 20, "y": 15})
        padding_x = padding.get("x", 20)
        padding_y = padding.get("y", 15)
        
        if not line1:
            logger.warning(f"Lower-third {source_id} has no line1 text")
            return None
        
        # Get position coordinates
        pos_config = get_position_config(position, width, height)
        x_pos = pos_config["x"]
        y_pos = pos_config["y"]
        
        # Convert colors
        bg_gst_color = self._hex_to_gstreamer_color(bg_color, bg_alpha)
        text_gst_color = self._hex_to_gstreamer_color(text_color, 1.0)
        
        # Escape text
        line1_escaped = self._escape_text(line1)
        line2_escaped = self._escape_text(line2) if line2 else ""
        
        # Calculate text positions within the lower-third
        line1_y = padding_y + 30  # Approximate baseline for line1
        line2_y = padding_y + 60 if line2 else line1_y  # Approximate baseline for line2
        
        # Create a pipeline with background and text
        # We'll use videotestsrc with alpha for background, then overlay text
        # For better control, we create a transparent video source and overlay text
        
        # Create background rectangle using videotestsrc with alpha
        # Note: GStreamer's textoverlay doesn't support background rectangles directly
        # We'll use a combination approach: create a colored background video and overlay text
        
        # Build text string
        if line2:
            # Two lines - we'll need to position them separately
            # Use newline for textoverlay (it supports multi-line)
            text_content = f"{line1_escaped}\\n{line2_escaped}"
        else:
            text_content = line1_escaped
        
        # Create pipeline with background and text overlay
        # Using videotestsrc for background, then textoverlay for text
        # The background will be a solid color with alpha channel
        
        # For now, use textoverlay with background color support
        # Note: textoverlay has limited background support, so we create a colored background
        # and overlay text on top
        
        # Create background video source with alpha
        bg_color_rgb = self._hex_to_gstreamer_color(bg_color, 1.0)  # Full opacity for background source
        
        # Build the pipeline
        # Create a full-frame transparent video, then overlay background and text
        # We'll use videotestsrc with alpha for the background rectangle
        # and textoverlay for the text
        
        # Create background color source (full frame, we'll crop/position later)
        # Use a solid color background at the lower-third position
        # For simplicity, create a video source sized to the lower-third with background color
        
        # Calculate text Y positions
        # Line 1 should be near the top of the lower-third
        # Line 2 should be below line 1
        
        # Build text overlay - textoverlay supports multi-line with \n
        # We'll position it within the lower-third bounds
        
        # Create pipeline: background video + text overlay
        # Note: textoverlay can draw on a video source, so we create a colored background
        # and overlay text on top
        
        # For the background, we use videotestsrc with the background color
        # Then overlay text using textoverlay
        # Finally, we need to position this on a 1920x1080 canvas
        
        # Simplified approach: Create lower-third sized video with background and text
        # Then use videobox to position it on full frame
        
        # Escape the background color for videotestsrc (it uses color format)
        bg_color_hex = bg_color.lstrip('#')
        if len(bg_color_hex) == 6:
            bg_r = int(bg_color_hex[0:2], 16)
            bg_g = int(bg_color_hex[2:4], 16)
            bg_b = int(bg_color_hex[4:6], 16)
            # videotestsrc uses 0xRRGGBB format
            bg_color_gst = f"0x{bg_r:02X}{bg_g:02X}{bg_b:02X}"
        else:
            bg_color_gst = "0x000000"
        
        # Build pipeline
        # Create background video source with the lower-third dimensions
        # Overlay text on top
        # Position on full 1920x1080 frame using videobox
        pipeline = (
            f"videotestsrc pattern=solid-color foreground-color={bg_color_gst} ! "
            f"video/x-raw,width={width},height={height},framerate=30/1 ! "
            f"textoverlay text=\"{text_content}\" "
            f"valign=top halign=left "
            f"xpad={padding_x} ypad={padding_y} "
            f"font-desc=\"{line1_font}\" "
            f"color={text_gst_color} ! "
            f"videobox border-alpha=0 left={x_pos} top={y_pos} ! "
            f"video/x-raw,width=1920,height=1080 ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
        
        # Note: This implementation uses textoverlay which has good support
        # For more advanced features (gradients, rounded corners, etc.), 
        # we would need to use cairooverlay with a custom draw script
        # Future enhancement: Generate cairo script for cairooverlay
        
        logger.info(f"Created enhanced lower-third source: {source_id} at {position} ({width}x{height})")
        return pipeline
    
    def create_graphics_source(self, source_id: str, graphics_data: Dict[str, Any]) -> Optional[str]:
        """Create a graphics/gamification overlay.
        
        Args:
            source_id: Unique identifier
            graphics_data: Graphics configuration
                - type: "stinger", "ticker", "timer", "scoreboard", "poll", etc.
                - Additional type-specific data
        
        Returns:
            GStreamer pipeline string
        """
        graphics_type = graphics_data.get("type", "scoreboard")
        
        if graphics_type == "timer":
            return self._create_timer_graphics(source_id, graphics_data)
        elif graphics_type == "ticker":
            return self._create_ticker_graphics(source_id, graphics_data)
        elif graphics_type == "stinger":
            return self._create_stinger_graphics(source_id, graphics_data)
        elif graphics_type == "scoreboard":
            return self._create_scoreboard_graphics(source_id, graphics_data)
        else:
            logger.warning(f"Unknown graphics type: {graphics_type}")
            return None
    
    def _create_timer_graphics(self, source_id: str, timer_data: Dict[str, Any]) -> Optional[str]:
        """Create a timer graphics overlay (countdown, clock, stopwatch).
        
        Args:
            source_id: Unique identifier
            timer_data: Timer configuration
                - timer_type: "countdown", "clock", "stopwatch"
                - duration: Countdown duration in seconds
                - position: Position on screen
                - text_color: Text color
                - font: Font description
        
        Returns:
            GStreamer pipeline string
        """
        timer_type = timer_data.get("timer_type", "clock")
        position = timer_data.get("position", "top-right")
        text_color = timer_data.get("text_color", "#FFFFFF")
        font = timer_data.get("font", "Sans 24")
        
        # Convert position
        if position == "top-right":
            halign = "right"
            valign = "top"
            xpad = 50
            ypad = 50
        elif position == "top-left":
            halign = "left"
            valign = "top"
            xpad = 50
            ypad = 50
        elif position == "bottom-right":
            halign = "right"
            valign = "bottom"
            xpad = 50
            ypad = 50
        else:  # bottom-left
            halign = "left"
            valign = "bottom"
            xpad = 50
            ypad = 50
        
        # Convert color
        text_color_hex = text_color.lstrip('#')
        if len(text_color_hex) == 6:
            r = int(text_color_hex[0:2], 16)
            g = int(text_color_hex[2:4], 16)
            b = int(text_color_hex[4:6], 16)
            color_gst = f"0xFFFFFFFF{r:02X}{g:02X}{b:02X}"
        else:
            color_gst = "0xFFFFFFFFFFFFFF"
        
        if timer_type == "clock":
            # Use timeoverlay for clock
            pipeline = (
                f"videotestsrc pattern=solid-color ! "
                f"video/x-raw,width=1920,height=1080,framerate=30/1 ! "
                f"timeoverlay halign={halign} valign={valign} "
                f"xpad={xpad} ypad={ypad} "
                f"font-desc=\"{font}\" color={color_gst} ! "
                f"videoconvert ! "
                f"video/x-raw,format=NV12"
            )
            logger.info(f"Created clock timer: {source_id}")
            return pipeline
        else:
            # Countdown and stopwatch require HTML/CSS or custom implementation
            logger.warning(f"Timer type {timer_type} requires HTML rendering, not yet fully implemented")
            return None
    
    def _create_ticker_graphics(self, source_id: str, ticker_data: Dict[str, Any]) -> Optional[str]:
        """Create a ticker (scrolling text) graphics overlay.
        
        Args:
            source_id: Unique identifier
            ticker_data: Ticker configuration
                - text: Text to scroll
                - direction: "left", "right", "up", "down"
                - speed: Scroll speed (pixels per second)
                - position: "top" or "bottom"
                - background_color: Background color
                - text_color: Text color
                - font: Font description
        
        Returns:
            GStreamer pipeline string
        """
        text = ticker_data.get("text", "")
        position = ticker_data.get("position", "bottom")
        background_color = ticker_data.get("background_color", "#000000")
        background_alpha = ticker_data.get("background_alpha", 0.8)
        text_color = ticker_data.get("text_color", "#FFFFFF")
        font = ticker_data.get("font", "Sans 20")
        
        if not text:
            logger.warning(f"Ticker {source_id} has no text")
            return None
        
        # For now, create a static ticker (scrolling requires HTML/CSS)
        # This creates a bottom ticker bar
        height = 60
        y_pos = 1020 if position == "bottom" else 0
        
        # Convert colors
        bg_gst_color = self._hex_to_gstreamer_color(background_color, background_alpha)
        text_gst_color = self._hex_to_gstreamer_color(text_color, 1.0)
        
        # Escape text
        text_escaped = self._escape_text(text)
        
        # Create ticker bar
        pipeline = (
            f"videotestsrc pattern=solid-color ! "
            f"video/x-raw,width=1920,height={height},framerate=30/1 ! "
            f"textoverlay text=\"{text_escaped}\" "
            f"valign=center halign=left "
            f"xpad=20 ypad=0 "
            f"font-desc=\"{font}\" color={text_gst_color} ! "
            f"videobox border-alpha=0 left=0 top={y_pos} ! "
            f"video/x-raw,width=1920,height=1080 ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
        
        logger.info(f"Created ticker: {source_id} (static, scrolling requires HTML)")
        return pipeline
    
    def _create_stinger_graphics(self, source_id: str, stinger_data: Dict[str, Any]) -> Optional[str]:
        """Create a stinger (transition animation) graphics overlay.
        
        Args:
            source_id: Unique identifier
            stinger_data: Stinger configuration
                - type: "wipe", "fade", "slide"
                - duration: Animation duration in seconds
                - logo_path: Path to logo image
                - background_color: Background color
                - text: Text to display
        
        Returns:
            GStreamer pipeline string
        """
        stinger_type = stinger_data.get("type", "fade")
        text = stinger_data.get("text", "")
        background_color = stinger_data.get("background_color", "#000000")
        text_color = stinger_data.get("text_color", "#FFFFFF")
        font = stinger_data.get("font", "Sans Bold 48")
        
        # For now, create a static stinger (animations require HTML/CSS)
        # This creates a full-screen overlay
        bg_gst_color = self._hex_to_gstreamer_color(background_color, 0.9)
        text_gst_color = self._hex_to_gstreamer_color(text_color, 1.0)
        
        text_escaped = self._escape_text(text) if text else ""
        
        pipeline = (
            f"videotestsrc pattern=solid-color ! "
            f"video/x-raw,width=1920,height=1080,framerate=30/1 ! "
        )
        
        if text_escaped:
            pipeline += (
                f"textoverlay text=\"{text_escaped}\" "
                f"valign=center halign=center "
                f"font-desc=\"{font}\" color={text_gst_color} ! "
            )
        
        pipeline += (
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
        
        logger.info(f"Created stinger: {source_id} (static, animations require HTML)")
        return pipeline
    
    def _create_scoreboard_graphics(self, source_id: str, scoreboard_data: Dict[str, Any]) -> Optional[str]:
        """Create a scoreboard graphics overlay.
        
        Args:
            source_id: Unique identifier
            scoreboard_data: Scoreboard configuration
                - team1_name: Team 1 name
                - team1_score: Team 1 score
                - team2_name: Team 2 name
                - team2_score: Team 2 score
                - position: Position on screen
                - background_color: Background color
                - text_color: Text color
        
        Returns:
            GStreamer pipeline string
        """
        # Scoreboards are complex and best done with HTML/CSS
        # For now, return None
        logger.warning(f"Scoreboard graphics require HTML rendering, not yet implemented")
        return None
    
    def get_source_pipeline(self, source: str) -> Optional[str]:
        """Get GStreamer pipeline string for a source.
        
        Args:
            source: Source identifier (e.g., "image:logo.png", "lower_third:name1")
        
        Returns:
            GStreamer pipeline string or None
        """
        if ":" not in source:
            return None  # Regular video source, handled by mixer
        
        source_type, source_id = source.split(":", 1)
        
        with self._lock:
            if source_id in self.active_sources:
                graphics_source = self.active_sources[source_id]
            else:
                # Create new graphics source
                # This would be populated from scene slot source_data
                graphics_source = GraphicsSource(
                    source_id=source_id,
                    source_type=source_type,
                    data={}
                )
                self.active_sources[source_id] = graphics_source
            
            if source_type == "image":
                return self.create_image_source(source_id, source_id)  # source_id is the path
            elif source_type == "lower_third":
                return self.create_lower_third_source(source_id, graphics_source.data)
            elif source_type == "presentation":
                return self.create_presentation_source(source_id, graphics_source.data)
            elif source_type == "graphics":
                return self.create_graphics_source(source_id, graphics_source.data)
            else:
                logger.warning(f"Unknown graphics source type: {source_type}")
                return None

