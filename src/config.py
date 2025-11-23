"""Configuration management for the R58 recorder."""
from pathlib import Path
from typing import Optional
import yaml
from dataclasses import dataclass, field


@dataclass
class CameraConfig:
    """Configuration for a single camera."""
    device: str
    resolution: str
    bitrate: int
    codec: str  # 'h264' or 'h265'
    output_path: str
    mediamtx_enabled: bool = False
    mediamtx_path: Optional[str] = None


@dataclass
class MediaMTXConfig:
    """MediaMTX configuration."""
    enabled: bool = False
    rtsp_port: int = 8554
    rtmp_port: int = 1935
    srt_port: int = 8890


@dataclass
class MixerConfig:
    """Mixer configuration."""
    enabled: bool = False
    output_resolution: str = "1920x1080"
    output_bitrate: int = 8000
    output_codec: str = "h264"
    recording_enabled: bool = False
    recording_path: str = "/var/recordings/mixer/program_%Y%m%d_%H%M%S.mp4"
    mediamtx_enabled: bool = True
    mediamtx_path: str = "mixer_program"
    scenes_dir: str = "scenes"


@dataclass
class AppConfig:
    """Main application configuration."""
    platform: str  # 'macos' or 'r58'
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    mediamtx: MediaMTXConfig = field(default_factory=MediaMTXConfig)
    mixer: MixerConfig = field(default_factory=MixerConfig)
    log_level: str = "INFO"

    @classmethod
    def load(cls, config_path: str) -> "AppConfig":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        # Detect platform
        import platform
        system = platform.system().lower()
        if system == "darwin":
            platform_name = "macos"
        else:
            platform_name = data.get("platform", "r58")

        # Load MediaMTX config
        mediamtx_data = data.get("mediamtx", {})
        mediamtx = MediaMTXConfig(
            enabled=mediamtx_data.get("enabled", False),
            rtsp_port=mediamtx_data.get("rtsp_port", 8554),
            rtmp_port=mediamtx_data.get("rtmp_port", 1935),
            srt_port=mediamtx_data.get("srt_port", 8890),
        )

        # Load Mixer config
        mixer_data = data.get("mixer", {})
        mixer = MixerConfig(
            enabled=mixer_data.get("enabled", False),
            output_resolution=mixer_data.get("output_resolution", "1920x1080"),
            output_bitrate=mixer_data.get("output_bitrate", 8000),
            output_codec=mixer_data.get("output_codec", "h264"),
            recording_enabled=mixer_data.get("recording_enabled", False),
            recording_path=mixer_data.get("recording_path", "/var/recordings/mixer/program_%Y%m%d_%H%M%S.mp4"),
            mediamtx_enabled=mixer_data.get("mediamtx_enabled", True),
            mediamtx_path=mixer_data.get("mediamtx_path", "mixer_program"),
            scenes_dir=mixer_data.get("scenes_dir", "scenes"),
        )

        # Load cameras
        cameras = {}
        for cam_id, cam_data in data.get("cameras", {}).items():
            cameras[cam_id] = CameraConfig(
                device=cam_data.get("device", ""),
                resolution=cam_data.get("resolution", "1920x1080"),
                bitrate=cam_data.get("bitrate", 5000),
                codec=cam_data.get("codec", "h264"),
                output_path=cam_data.get("output_path", ""),
                mediamtx_enabled=cam_data.get("mediamtx_enabled", False),
                mediamtx_path=cam_data.get("mediamtx_path", None),
            )

        return cls(
            platform=platform_name,
            cameras=cameras,
            mediamtx=mediamtx,
            mixer=mixer,
            log_level=data.get("log_level", "INFO"),
        )

