"""Video mixer plugin for scene-based compositing.

Components:
- MixerCore: GStreamer compositor pipeline
- SceneManager: Scene configuration management
- SceneQueue: Automated scene queue with auto-advance

Optional dependency on Graphics plugin for presentation/graphics sources.

Usage:
    from .mixer import create_mixer_plugin
    mixer_plugin = create_mixer_plugin()
    mixer_plugin.initialize(config, ingest_manager, database, graphics_plugin)
"""

from typing import TYPE_CHECKING, Optional, Any
import logging

if TYPE_CHECKING:
    from ..config import AppConfig
    from ..ingest import IngestManager
    from ..database import Database
    from ..graphics import GraphicsPlugin

logger = logging.getLogger(__name__)


class MixerPlugin:
    """Lazy-loaded container for mixer components."""
    
    def __init__(self):
        self.core: Optional[Any] = None
        self.scene_manager: Optional[Any] = None
        self.scene_queue: Optional[Any] = None
        self.graphics_plugin: Optional[Any] = None  # Optional dependency
        self._initialized = False
    
    def initialize(
        self, 
        config: "AppConfig", 
        ingest_manager: "IngestManager",
        database: "Database",
        graphics_plugin: Optional["GraphicsPlugin"] = None
    ) -> bool:
        """Initialize mixer components.
        
        Args:
            config: Application configuration
            ingest_manager: Ingest manager for stream status
            database: Shared database instance
            graphics_plugin: Optional graphics plugin for presentation sources
        """
        if self._initialized:
            return True
        
        # Store graphics plugin reference (optional)
        self.graphics_plugin = graphics_plugin
        
        # Import mixer modules lazily
        from .scenes import SceneManager
        from .core import MixerCore
        from .queue import SceneQueue
        
        # Migrate scenes from JSON to database
        database.migrate_json_scenes(config.mixer.scenes_dir)
        
        # Initialize scene manager
        self.scene_manager = SceneManager(scenes_dir=config.mixer.scenes_dir)
        
        # Initialize queue with advance callback
        def queue_advance_callback(scene_id: str):
            if self.core:
                self.core.apply_scene(scene_id)
        
        self.scene_queue = SceneQueue(
            database=database, 
            on_advance=queue_advance_callback
        )
        
        # Initialize core mixer with optional graphics
        graphics_renderer = None
        if graphics_plugin and graphics_plugin.is_initialized:
            graphics_renderer = graphics_plugin.renderer
            logger.info("Mixer using graphics plugin for presentations/overlays")
        else:
            logger.info("Mixer running without graphics plugin")
        
        self.core = MixerCore(
            config=config,
            scene_manager=self.scene_manager,
            ingest_manager=ingest_manager,
            graphics_renderer=graphics_renderer,  # Pass graphics renderer
            output_resolution=config.mixer.output_resolution,
            output_bitrate=config.mixer.output_bitrate,
            output_codec=config.mixer.output_codec,
            recording_enabled=config.mixer.recording_enabled,
            recording_path=config.mixer.recording_path,
            mediamtx_enabled=config.mixer.mediamtx_enabled,
            mediamtx_path=config.mixer.mediamtx_path,
        )
        
        self._initialized = True
        logger.info("Mixer plugin initialized")
        return True
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized


def create_mixer_plugin() -> MixerPlugin:
    """Create a new mixer plugin instance."""
    return MixerPlugin()
