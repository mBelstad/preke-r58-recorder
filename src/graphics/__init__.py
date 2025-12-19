"""Graphics plugin for presentations, lower thirds, and broadcast graphics.

Components:
- GraphicsRenderer: Renders presentations and graphics to video
- GraphicsTemplates: Predefined broadcast graphics templates
- HTMLGraphicsRenderer: HTML/CSS based graphics rendering

Usage:
    from .graphics import create_graphics_plugin
    graphics_plugin = create_graphics_plugin()
    graphics_plugin.initialize(config)
"""

from typing import TYPE_CHECKING, Optional, Any
import logging

if TYPE_CHECKING:
    from ..config import AppConfig

logger = logging.getLogger(__name__)


class GraphicsPlugin:
    """Lazy-loaded container for graphics components."""
    
    def __init__(self):
        self.renderer: Optional[Any] = None
        self.html_renderer: Optional[Any] = None
        self._initialized = False
    
    def initialize(self, config: "AppConfig") -> bool:
        """Initialize graphics components."""
        if self._initialized:
            return True
        
        # Import lazily
        from .renderer import GraphicsRenderer
        from .html_renderer import HTMLGraphicsRenderer
        
        self.renderer = GraphicsRenderer(
            output_dir=config.graphics.output_dir
        )
        self.html_renderer = HTMLGraphicsRenderer(
            templates_dir=config.graphics.templates_dir,
            output_dir=config.graphics.output_dir
        )
        
        self._initialized = True
        logger.info("Graphics plugin initialized")
        return True
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    # Expose template functions
    def get_template(self, template_id: str):
        from .templates import get_template
        return get_template(template_id)
    
    def list_templates(self, template_type: Optional[str] = None):
        from .templates import list_templates
        return list_templates(template_type)


def create_graphics_plugin() -> GraphicsPlugin:
    """Create a new graphics plugin instance."""
    return GraphicsPlugin()

