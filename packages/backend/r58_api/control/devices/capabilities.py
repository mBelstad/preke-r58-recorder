"""Device capabilities endpoint - Critical for adaptive UI"""
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ...config import Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["Capabilities"])


class InputCapability(BaseModel):
    """Hardware input capability"""
    id: str
    type: str  # "hdmi", "sdi", "usb", "network"
    label: str
    max_resolution: str
    supports_audio: bool
    device_path: Optional[str] = None


class CodecCapability(BaseModel):
    """Codec capability"""
    id: str
    name: str
    hardware_accelerated: bool
    max_bitrate_kbps: int


class PreviewMode(BaseModel):
    """Preview mode capability"""
    id: str
    protocol: str  # "whep", "hls", "rtsp"
    latency_ms: int
    url_template: str


class VdoNinjaCapability(BaseModel):
    """VDO.ninja integration capability"""
    enabled: bool
    host: str
    port: int
    room: str


class DeviceCapabilities(BaseModel):
    """Complete device capabilities manifest"""
    device_id: str
    device_name: str
    platform: str  # "r58", "macos", "windows"
    api_version: str
    
    # Feature flags
    mixer_available: bool
    recorder_available: bool
    graphics_available: bool
    fleet_agent_connected: bool
    
    # Hardware
    inputs: List[InputCapability]
    codecs: List[CodecCapability]
    preview_modes: List[PreviewMode]
    
    # VDO.ninja (local)
    vdoninja: VdoNinjaCapability
    
    # Endpoints
    mediamtx_base_url: str
    
    # Limits
    max_simultaneous_recordings: int
    max_output_resolution: str
    storage_total_gb: float
    storage_available_gb: float


def detect_inputs(settings: Settings) -> List[InputCapability]:
    """Detect available hardware inputs"""
    # TODO: Implement actual hardware detection
    # For now, return configured inputs
    inputs = []
    for idx, input_id in enumerate(settings.enabled_inputs):
        inputs.append(InputCapability(
            id=input_id,
            type="hdmi",
            label=f"HDMI {idx + 1}",
            max_resolution="1920x1080",
            supports_audio=True,
            device_path=f"/dev/video{idx * 10}",
        ))
    return inputs


def detect_codecs() -> List[CodecCapability]:
    """Detect available codecs"""
    # TODO: Probe actual hardware encoders
    return [
        CodecCapability(
            id="h264_hw",
            name="H.264 (Hardware)",
            hardware_accelerated=True,
            max_bitrate_kbps=20000,
        ),
        CodecCapability(
            id="h265_hw",
            name="H.265 (Hardware)",
            hardware_accelerated=True,
            max_bitrate_kbps=15000,
        ),
    ]


def get_preview_modes(settings: Settings) -> List[PreviewMode]:
    """Get available preview modes"""
    return [
        PreviewMode(
            id="whep",
            protocol="whep",
            latency_ms=100,
            url_template=f"{settings.mediamtx_whep_base}/{{input_id}}/whep",
        ),
        PreviewMode(
            id="hls",
            protocol="hls",
            latency_ms=3000,
            url_template=f"{settings.mediamtx_whep_base}/{{input_id}}/hls.m3u8",
        ),
    ]


def get_storage_info() -> tuple[float, float]:
    """Get storage information.
    
    Prefers SD card mount at /mnt/sdcard for R58 recordings storage.
    Falls back to root filesystem if SD card is not available.
    """
    import shutil
    import os
    
    # Prefer SD card for R58 recordings
    paths_to_check = ["/mnt/sdcard", "/"]
    
    for path in paths_to_check:
        try:
            if os.path.exists(path):
                usage = shutil.disk_usage(path)
                if usage.total > 0:
                    total_gb = usage.total / (1024 ** 3)
                    available_gb = usage.free / (1024 ** 3)
                    return total_gb, available_gb
        except Exception:
            continue
    
    return 0.0, 0.0


@router.get("/capabilities", response_model=DeviceCapabilities)
async def get_capabilities(
    settings: Settings = Depends(get_settings)
) -> DeviceCapabilities:
    """
    Get device capabilities manifest.
    
    The UI uses this to adapt its features based on what the device supports.
    """
    storage_total, storage_available = get_storage_info()
    
    return DeviceCapabilities(
        device_id=settings.device_id,
        device_name="R58 Recorder",
        platform="r58",
        api_version="2.0.0",
        
        # Feature flags
        mixer_available=settings.vdoninja_enabled,
        recorder_available=True,
        graphics_available=True,
        fleet_agent_connected=settings.fleet_enabled,
        
        # Hardware
        inputs=detect_inputs(settings),
        codecs=detect_codecs(),
        preview_modes=get_preview_modes(settings),
        
        # VDO.ninja
        vdoninja=VdoNinjaCapability(
            enabled=settings.vdoninja_enabled,
            host="localhost",
            port=settings.vdoninja_port,
            room=settings.vdoninja_room,
        ),
        
        # Endpoints
        mediamtx_base_url=settings.mediamtx_whep_base,
        
        # Limits
        max_simultaneous_recordings=4,
        max_output_resolution="1920x1080",
        storage_total_gb=round(storage_total, 2),
        storage_available_gb=round(storage_available, 2),
    )

