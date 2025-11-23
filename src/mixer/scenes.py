"""Scene management for video mixer."""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class SceneSlot:
    """A single source slot in a scene."""
    source: str  # e.g., "cam0", "cam1", "presentation:1", "image:logo.png", "lower_third:name"
    source_type: str = "video"  # "video", "image", "presentation", "graphics", "lower_third"
    x_rel: float  # 0.0-1.0
    y_rel: float  # 0.0-1.0
    w_rel: float  # 0.0-1.0
    h_rel: float  # 0.0-1.0
    z: int = 0  # z-order (higher = on top)
    alpha: float = 1.0  # 0.0-1.0
    # Styling options
    border_width: int = 0  # pixels
    border_color: str = "#000000"  # hex color
    border_radius: int = 0  # pixels
    # Crop (relative to source, 0.0-1.0)
    crop_x: float = 0.0
    crop_y: float = 0.0
    crop_w: float = 1.0
    crop_h: float = 1.0
    # Source-specific data (for presentations, images, etc.)
    source_data: Optional[Dict[str, Any]] = field(default=None)  # Additional data for source type


@dataclass
class Scene:
    """Scene definition with layout information."""
    id: str
    label: str
    resolution: Dict[str, int]  # {"width": 1920, "height": 1080}
    slots: List[SceneSlot]

    def to_dict(self) -> Dict[str, Any]:
        """Convert scene to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "label": self.label,
            "resolution": self.resolution,
            "slots": [asdict(slot) for slot in self.slots]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        """Create scene from dictionary."""
        slots = []
        for slot_data in data.get("slots", []):
            # Handle backward compatibility - old scenes don't have new fields
            slot = SceneSlot(
                source=slot_data.get("source", ""),
                source_type=slot_data.get("source_type", "video"),
                x_rel=slot_data.get("x_rel", 0.0),
                y_rel=slot_data.get("y_rel", 0.0),
                w_rel=slot_data.get("w_rel", 1.0),
                h_rel=slot_data.get("h_rel", 1.0),
                z=slot_data.get("z", 0),
                alpha=slot_data.get("alpha", 1.0),
                border_width=slot_data.get("border_width", 0),
                border_color=slot_data.get("border_color", "#000000"),
                border_radius=slot_data.get("border_radius", 0),
                crop_x=slot_data.get("crop_x", 0.0),
                crop_y=slot_data.get("crop_y", 0.0),
                crop_w=slot_data.get("crop_w", 1.0),
                crop_h=slot_data.get("crop_h", 1.0),
                source_data=slot_data.get("source_data")
            )
            slots.append(slot)
        return cls(
            id=data["id"],
            label=data["label"],
            resolution=data["resolution"],
            slots=slots
        )

    def get_absolute_coords(self, slot: SceneSlot) -> Dict[str, int]:
        """Convert relative coordinates to absolute pixels."""
        width = self.resolution["width"]
        height = self.resolution["height"]
        return {
            "x": int(slot.x_rel * width),
            "y": int(slot.y_rel * height),
            "w": int(slot.w_rel * width),
            "h": int(slot.h_rel * height),
        }


class SceneManager:
    """Manages scene definitions and loading."""

    def __init__(self, scenes_dir: str = "scenes"):
        """Initialize scene manager.
        
        Args:
            scenes_dir: Directory containing JSON scene files
        """
        self.scenes_dir = Path(scenes_dir)
        self.scenes: Dict[str, Scene] = {}
        self._load_scenes()

    def _load_scenes(self) -> None:
        """Load all scene definitions from JSON files."""
        if not self.scenes_dir.exists():
            logger.warning(f"Scenes directory not found: {self.scenes_dir}, creating it")
            self.scenes_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_scenes()
            return

        scene_files = list(self.scenes_dir.glob("*.json"))
        if not scene_files:
            logger.info("No scene files found, creating default scenes")
            self._create_default_scenes()
            return

        for scene_file in scene_files:
            try:
                with open(scene_file, "r") as f:
                    data = json.load(f)
                    scene = Scene.from_dict(data)
                    self.scenes[scene.id] = scene
                    logger.info(f"Loaded scene: {scene.id} - {scene.label}")
            except Exception as e:
                logger.error(f"Failed to load scene from {scene_file}: {e}")

    def _create_default_scenes(self) -> None:
        """Create default scene definitions."""
        default_resolution = {"width": 1920, "height": 1080}
        
        default_scenes = [
            {
                "id": "quad",
                "label": "4-up grid",
                "resolution": default_resolution,
                "slots": [
                    {"source": "cam0", "x_rel": 0.0, "y_rel": 0.0, "w_rel": 0.5, "h_rel": 0.5, "z": 0},
                    {"source": "cam1", "x_rel": 0.5, "y_rel": 0.0, "w_rel": 0.5, "h_rel": 0.5, "z": 0},
                    {"source": "cam2", "x_rel": 0.0, "y_rel": 0.5, "w_rel": 0.5, "h_rel": 0.5, "z": 0},
                    {"source": "cam3", "x_rel": 0.5, "y_rel": 0.5, "w_rel": 0.5, "h_rel": 0.5, "z": 0},
                ]
            },
            {
                "id": "two_up",
                "label": "2-up side-by-side",
                "resolution": default_resolution,
                "slots": [
                    {"source": "cam0", "x_rel": 0.0, "y_rel": 0.0, "w_rel": 0.5, "h_rel": 1.0, "z": 0},
                    {"source": "cam1", "x_rel": 0.5, "y_rel": 0.0, "w_rel": 0.5, "h_rel": 1.0, "z": 0},
                ]
            },
            {
                "id": "cam0_full",
                "label": "CAM 1 fullscreen",
                "resolution": default_resolution,
                "slots": [
                    {"source": "cam0", "x_rel": 0.0, "y_rel": 0.0, "w_rel": 1.0, "h_rel": 1.0, "z": 0},
                ]
            },
            {
                "id": "cam1_full",
                "label": "CAM 2 fullscreen",
                "resolution": default_resolution,
                "slots": [
                    {"source": "cam1", "x_rel": 0.0, "y_rel": 0.0, "w_rel": 1.0, "h_rel": 1.0, "z": 0},
                ]
            },
            {
                "id": "cam2_full",
                "label": "CAM 3 fullscreen",
                "resolution": default_resolution,
                "slots": [
                    {"source": "cam2", "x_rel": 0.0, "y_rel": 0.0, "w_rel": 1.0, "h_rel": 1.0, "z": 0},
                ]
            },
            {
                "id": "cam3_full",
                "label": "CAM 4 fullscreen",
                "resolution": default_resolution,
                "slots": [
                    {"source": "cam3", "x_rel": 0.0, "y_rel": 0.0, "w_rel": 1.0, "h_rel": 1.0, "z": 0},
                ]
            },
            {
                "id": "pip_cam1_over_cam0",
                "label": "PiP: CAM 2 over CAM 1",
                "resolution": default_resolution,
                "slots": [
                    {"source": "cam0", "x_rel": 0.0, "y_rel": 0.0, "w_rel": 1.0, "h_rel": 1.0, "z": 0},
                    {"source": "cam1", "x_rel": 0.7, "y_rel": 0.7, "w_rel": 0.3, "h_rel": 0.3, "z": 1},
                ]
            },
        ]

        for scene_data in default_scenes:
            scene = Scene.from_dict(scene_data)
            self.scenes[scene.id] = scene
            # Save to file
            scene_file = self.scenes_dir / f"{scene.id}.json"
            with open(scene_file, "w") as f:
                json.dump(scene.to_dict(), f, indent=2)
            logger.info(f"Created default scene: {scene.id}")

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        """Get a scene by ID."""
        return self.scenes.get(scene_id)

    def list_scenes(self) -> List[Dict[str, Any]]:
        """List all available scenes."""
        return [
            {
                "id": scene.id,
                "label": scene.label,
                "resolution": scene.resolution,
                "slot_count": len(scene.slots)
            }
            for scene in self.scenes.values()
        ]

    def create_scene(self, scene: Scene) -> bool:
        """Create or update a scene."""
        try:
            self.scenes[scene.id] = scene
            scene_file = self.scenes_dir / f"{scene.id}.json"
            with open(scene_file, "w") as f:
                json.dump(scene.to_dict(), f, indent=2)
            logger.info(f"Created/updated scene: {scene.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create scene {scene.id}: {e}")
            return False

    def delete_scene(self, scene_id: str) -> bool:
        """Delete a scene."""
        if scene_id not in self.scenes:
            return False
        
        try:
            scene_file = self.scenes_dir / f"{scene_id}.json"
            if scene_file.exists():
                scene_file.unlink()
            del self.scenes[scene_id]
            logger.info(f"Deleted scene: {scene_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete scene {scene_id}: {e}")
            return False

