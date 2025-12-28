"""Configuration loader for the pipeline manager.

Loads camera and recording settings from config.yml or environment.
"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Default paths to check for config file
CONFIG_PATHS = [
    Path("/opt/r58-app/current/config.yml"),
    Path("/etc/r58/config.yml"),
    Path("config.yml"),
]


@dataclass
class CameraConfig:
    """Configuration for a single camera input."""
    cam_id: str
    device: str
    resolution: str = "1920x1080"
    bitrate: int = 4000
    codec: str = "h264"
    enabled: bool = True
    mediamtx_enabled: bool = True
    mediamtx_path: Optional[str] = None
    output_path: str = "/opt/r58/recordings/{cam_id}_{timestamp}.mkv"


@dataclass
class PipelineConfig:
    """Configuration for the pipeline manager."""
    cameras: Dict[str, CameraConfig] = field(default_factory=dict)
    recordings_dir: Path = field(default_factory=lambda: Path("/opt/r58/recordings"))
    min_disk_space_gb: float = 10.0
    warning_disk_space_gb: float = 5.0
    mediamtx_rtsp_port: int = 8554
    mediamtx_rtmp_port: int = 1935


def load_config(config_path: Optional[Path] = None) -> PipelineConfig:
    """Load pipeline configuration from YAML file.
    
    Args:
        config_path: Optional explicit path to config file
        
    Returns:
        PipelineConfig instance
    """
    # Find config file
    if config_path and config_path.exists():
        path = config_path
    else:
        path = None
        for p in CONFIG_PATHS:
            if p.exists():
                path = p
                break
    
    if path is None:
        logger.warning("No config.yml found, using defaults")
        return _default_config()
    
    try:
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return _parse_config(data)
    except ImportError:
        logger.warning("PyYAML not installed, using defaults")
        return _default_config()
    except Exception as e:
        logger.error(f"Failed to load config from {path}: {e}")
        return _default_config()


def _default_config() -> PipelineConfig:
    """Create default configuration for R58 4x4 3S."""
    return PipelineConfig(
        cameras={
            "cam1": CameraConfig(
                cam_id="cam1",
                device="/dev/video60",
                enabled=True,
            ),
            "cam2": CameraConfig(
                cam_id="cam2",
                device="/dev/video11",
                enabled=True,
            ),
        }
    )


def _parse_config(data: Dict[str, Any]) -> PipelineConfig:
    """Parse configuration from YAML data."""
    config = PipelineConfig()
    
    # Parse cameras
    cameras_data = data.get("cameras", {})
    for cam_id, cam_data in cameras_data.items():
        if isinstance(cam_data, dict):
            config.cameras[cam_id] = CameraConfig(
                cam_id=cam_id,
                device=cam_data.get("device", f"/dev/video{len(config.cameras)}"),
                resolution=cam_data.get("resolution", "1920x1080"),
                bitrate=cam_data.get("bitrate", 4000),
                codec=cam_data.get("codec", "h264"),
                enabled=cam_data.get("enabled", True),
                mediamtx_enabled=cam_data.get("mediamtx_enabled", True),
                mediamtx_path=cam_data.get("mediamtx_path"),
                output_path=cam_data.get("output_path", f"/opt/r58/recordings/{cam_id}_{{timestamp}}.mkv"),
            )
    
    # Parse recording settings
    recording_data = data.get("recording", {})
    config.min_disk_space_gb = recording_data.get("min_disk_space_gb", 10.0)
    config.warning_disk_space_gb = recording_data.get("warning_disk_space_gb", 5.0)
    
    # Parse MediaMTX settings
    mediamtx_data = data.get("mediamtx", {})
    config.mediamtx_rtsp_port = mediamtx_data.get("rtsp_port", 8554)
    config.mediamtx_rtmp_port = mediamtx_data.get("rtmp_port", 1935)
    
    return config


def get_enabled_cameras(config: PipelineConfig) -> Dict[str, CameraConfig]:
    """Get only enabled cameras from config."""
    return {
        cam_id: cam_config
        for cam_id, cam_config in config.cameras.items()
        if cam_config.enabled
    }


# Singleton config instance
_config: Optional[PipelineConfig] = None


def get_config() -> PipelineConfig:
    """Get or load the configuration singleton."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

