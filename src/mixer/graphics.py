"""Graphics rendering for mixer sources (presentations, images, lower-thirds, etc.)."""
import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

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
        """Create a video source from a presentation.
        
        Args:
            source_id: Unique identifier for this source
            presentation_data: Presentation configuration
                - slides: List of slide content (HTML/Markdown)
                - current_slide: Current slide index
                - theme: Presentation theme
        
        Returns:
            GStreamer pipeline string or None if failed
        """
        # For now, use a simple HTML renderer approach
        # In production, this would use Reveal.js or similar
        logger.info(f"Creating presentation source: {source_id}")
        
        # This is a placeholder - full implementation would:
        # 1. Render HTML slides to images/video
        # 2. Create a GStreamer pipeline using textoverlay or cairooverlay
        # 3. Return pipeline string for mixer integration
        
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
    
    def create_lower_third_source(self, source_id: str, text_data: Dict[str, Any]) -> Optional[str]:
        """Create a lower-third graphics overlay.
        
        Args:
            source_id: Unique identifier
            text_data: Lower-third configuration
                - line1: Primary text
                - line2: Secondary text (optional)
                - background_color: Background color
                - text_color: Text color
        
        Returns:
            GStreamer pipeline string using textoverlay
        """
        line1 = text_data.get("line1", "")
        line2 = text_data.get("line2", "")
        bg_color = text_data.get("background_color", "#000000")
        text_color = text_data.get("text_color", "#FFFFFF")
        
        # Create text overlay pipeline
        # This is simplified - full implementation would use cairooverlay for better control
        text = f"{line1}\n{line2}" if line2 else line1
        
        pipeline = (
            f"videotestsrc pattern=solid-color ! "
            f"video/x-raw,width=1920,height=200 ! "
            f"textoverlay text=\"{text}\" valign=bottom halign=left "
            f"font-desc=\"Sans 24\" color={text_color} ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
        
        logger.info(f"Created lower-third source: {source_id}")
        return pipeline
    
    def create_graphics_source(self, source_id: str, graphics_data: Dict[str, Any]) -> Optional[str]:
        """Create a graphics/gamification overlay.
        
        Args:
            source_id: Unique identifier
            graphics_data: Graphics configuration
                - type: "scoreboard", "timer", "poll", etc.
                - data: Type-specific data
        
        Returns:
            GStreamer pipeline string
        """
        graphics_type = graphics_data.get("type", "scoreboard")
        
        # Placeholder for graphics rendering
        # Full implementation would render HTML/CSS graphics to video
        logger.info(f"Creating graphics source: {source_id} type={graphics_type}")
        
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

