"""Cairo Graphics Manager - coordinates all Cairo-based graphics elements."""
import logging
import threading
from typing import Dict, Optional, Any
from pathlib import Path

from .elements import GraphicsElement

logger = logging.getLogger(__name__)

# Try to import Cairo
try:
    import cairo
    CAIRO_AVAILABLE = True
except ImportError:
    logger.warning("Cairo not available")
    CAIRO_AVAILABLE = False


class CairoGraphicsManager:
    """Manages all Cairo graphics elements and provides draw callback for GStreamer.
    
    This manager:
    - Maintains a registry of graphics elements (lower thirds, scoreboards, etc.)
    - Provides thread-safe access for API updates
    - Calls each element's draw() method every frame
    - Handles element lifecycle (show, hide, update)
    
    Usage:
        manager = CairoGraphicsManager()
        
        # Add elements
        lower_third = LowerThird("lt1", name="John Doe", title="CEO")
        manager.add_element("lt1", lower_third)
        
        # Connect to GStreamer
        overlay = pipeline.get_by_name("graphics_overlay")
        overlay.connect("draw", manager.draw_callback)
        
        # Control via API
        lower_third.show(timestamp)
        lower_third.update(name="Jane Smith", title="CTO")
    """
    
    def __init__(self):
        """Initialize Cairo graphics manager."""
        self._lock = threading.Lock()
        self._elements: Dict[str, GraphicsElement] = {}
        self._enabled = True
        
        if not CAIRO_AVAILABLE:
            logger.error("Cairo not available - graphics will not render")
            self._enabled = False
        else:
            logger.info("Cairo graphics manager initialized")
    
    @property
    def enabled(self) -> bool:
        """Check if Cairo is available."""
        return self._enabled
    
    def draw_callback(self, overlay, context, timestamp: int, duration: int) -> None:
        """GStreamer draw callback - called every frame.
        
        This method is called by GStreamer's cairooverlay element for each frame.
        It iterates through all elements and calls their draw() method.
        
        Args:
            overlay: GStreamer cairooverlay element
            context: Cairo context
            timestamp: Current timestamp in nanoseconds
            duration: Frame duration in nanoseconds
        """
        if not self._enabled:
            return
        
        with self._lock:
            for element in self._elements.values():
                try:
                    element.draw(context, timestamp)
                except Exception as e:
                    logger.error(f"Error drawing element {element.element_id}: {e}")
    
    def add_element(self, element_id: str, element: GraphicsElement) -> bool:
        """Add a graphics element to the manager.
        
        Args:
            element_id: Unique identifier
            element: GraphicsElement instance
        
        Returns:
            True if added successfully
        """
        with self._lock:
            if element_id in self._elements:
                logger.warning(f"Element {element_id} already exists, replacing")
            
            self._elements[element_id] = element
            logger.info(f"Added graphics element: {element_id} ({type(element).__name__})")
            return True
    
    def remove_element(self, element_id: str) -> bool:
        """Remove a graphics element.
        
        Args:
            element_id: Element identifier
        
        Returns:
            True if removed successfully
        """
        with self._lock:
            if element_id not in self._elements:
                logger.warning(f"Element {element_id} not found")
                return False
            
            del self._elements[element_id]
            logger.info(f"Removed graphics element: {element_id}")
            return True
    
    def get_element(self, element_id: str) -> Optional[GraphicsElement]:
        """Get a graphics element by ID.
        
        Args:
            element_id: Element identifier
        
        Returns:
            GraphicsElement instance or None
        """
        with self._lock:
            return self._elements.get(element_id)
    
    def list_elements(self) -> Dict[str, Dict[str, Any]]:
        """List all graphics elements with their status.
        
        Returns:
            Dictionary of element info
        """
        with self._lock:
            result = {}
            for element_id, element in self._elements.items():
                result[element_id] = {
                    "type": type(element).__name__,
                    "visible": element.visible,
                    "animation_state": element.animation_state,
                    "x": element.x,
                    "y": element.y,
                    "alpha": element.alpha
                }
            return result
    
    def clear_all(self) -> None:
        """Remove all graphics elements."""
        with self._lock:
            count = len(self._elements)
            self._elements.clear()
            logger.info(f"Cleared all graphics elements ({count} removed)")
    
    def show_element(self, element_id: str, timestamp: int) -> bool:
        """Show an element with animation.
        
        Args:
            element_id: Element identifier
            timestamp: GStreamer timestamp
        
        Returns:
            True if shown successfully
        """
        element = self.get_element(element_id)
        if not element:
            logger.warning(f"Element {element_id} not found")
            return False
        
        element.show(timestamp)
        return True
    
    def hide_element(self, element_id: str, timestamp: int) -> bool:
        """Hide an element with animation.
        
        Args:
            element_id: Element identifier
            timestamp: GStreamer timestamp
        
        Returns:
            True if hidden successfully
        """
        element = self.get_element(element_id)
        if not element:
            logger.warning(f"Element {element_id} not found")
            return False
        
        element.hide(timestamp)
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status.
        
        Returns:
            Status dictionary
        """
        with self._lock:
            return {
                "enabled": self._enabled,
                "cairo_available": CAIRO_AVAILABLE,
                "element_count": len(self._elements),
                "elements": self.list_elements()
            }

