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
class PreviewConfig:
    """Preview configuration."""
    health_check_interval: int = 10  # seconds
    stale_threshold: int = 15  # seconds
    restream_when_recording: bool = True  # Use restream mode when recording active


@dataclass
class GraphicsConfig:
    """Graphics plugin configuration."""
    enabled: bool = True
    templates_dir: str = "graphics_templates"
    output_dir: str = "/tmp/graphics_output"


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
class RecordingConfig:
    """Recording configuration."""
    enabled: bool = True
    gop: int = 30
    fragmented: bool = True
    fragment_duration: int = 1000
    filename_pattern: str = "{cam_id}_{timestamp}.mp4"
    min_disk_space_gb: float = 10.0
    warning_disk_space_gb: float = 5.0


@dataclass
class GuestConfig:
    """Remote guest configuration."""
    name: str
    enabled: bool = True


@dataclass
class CloudflareConfig:
    """Cloudflare Calls configuration for remote guests."""
    account_id: str
    calls_app_id: str
    calls_api_token: str
    calls_app_name: str = "r58-1"


@dataclass
class AppConfig:
    """Main application configuration."""
    platform: str  # 'macos' or 'r58'
    cameras: dict[str, CameraConfig] = field(default_factory=dict)
    guests: dict[str, GuestConfig] = field(default_factory=dict)
    cloudflare: CloudflareConfig = field(default_factory=lambda: CloudflareConfig("", "", ""))
    mediamtx: MediaMTXConfig = field(default_factory=MediaMTXConfig)
    graphics: GraphicsConfig = field(default_factory=GraphicsConfig)
    mixer: MixerConfig = field(default_factory=MixerConfig)
    preview: PreviewConfig = field(default_factory=PreviewConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    external_cameras: list = field(default_factory=list)
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

        # Load Preview config
        preview_data = data.get("preview", {})
        preview = PreviewConfig(
            health_check_interval=preview_data.get("health_check_interval", 10),
            stale_threshold=preview_data.get("stale_threshold", 15),
            restream_when_recording=preview_data.get("restream_when_recording", True),
        )

        # Load Graphics config
        graphics_data = data.get("graphics", {})
        graphics = GraphicsConfig(
            enabled=graphics_data.get("enabled", True),
            templates_dir=graphics_data.get("templates_dir", "graphics_templates"),
            output_dir=graphics_data.get("output_dir", "/tmp/graphics_output"),
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
        
        # Load recording config
        recording_data = data.get("recording", {})
        recording = RecordingConfig(
            enabled=recording_data.get("enabled", True),
            gop=recording_data.get("gop", 30),
            fragmented=recording_data.get("fragmented", True),
            fragment_duration=recording_data.get("fragment_duration", 1000),
            filename_pattern=recording_data.get("filename_pattern", "{cam_id}_{timestamp}.mp4"),
            min_disk_space_gb=recording_data.get("min_disk_space_gb", 10.0),
            warning_disk_space_gb=recording_data.get("warning_disk_space_gb", 5.0),
        )
        
        # Load guests
        guests = {}
        for guest_id, guest_data in data.get("guests", {}).items():
            guests[guest_id] = GuestConfig(
                name=guest_data.get("name", guest_id),
                enabled=guest_data.get("enabled", True),
            )
        
        # Load Cloudflare config (environment variables take priority over config file)
        import os
        cloudflare_data = data.get("cloudflare", {})
        cloudflare = CloudflareConfig(
            account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", cloudflare_data.get("account_id", "")),
            calls_app_id=os.environ.get("CLOUDFLARE_CALLS_APP_ID", cloudflare_data.get("calls_app_id", "")),
            calls_api_token=os.environ.get("CLOUDFLARE_CALLS_API_TOKEN", cloudflare_data.get("calls_api_token", "")),
            calls_app_name=cloudflare_data.get("calls_app_name", "r58-1"),
        )
        
        # Load external cameras
        external_cameras = data.get("external_cameras", [])

        return cls(
            platform=platform_name,
            cameras=cameras,
            guests=guests,
            cloudflare=cloudflare,
            mediamtx=mediamtx,
            graphics=graphics,
            mixer=mixer,
            preview=preview,
            recording=recording,
            external_cameras=external_cameras,
            log_level=data.get("log_level", "INFO"),
        )

