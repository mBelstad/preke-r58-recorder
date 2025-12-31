"""VDO.ninja integration endpoints (LOCAL R58 instance)"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import Settings, get_settings
from ..media.pipeline_client import get_pipeline_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/vdoninja", tags=["VDO.ninja"])


class VdoUrlRequest(BaseModel):
    """Request to generate a VDO.ninja URL"""
    profile: str  # director, scene, cameraContribution, guestInvite
    room: Optional[str] = None
    sources: Optional[List[str]] = None
    guest_name: Optional[str] = None


class VdoUrlResponse(BaseModel):
    """Generated VDO.ninja URL response"""
    url: str
    profile: str
    room: str
    css_url: str


class RoomStatus(BaseModel):
    """VDO.ninja room status"""
    room: str
    status: str
    sources: List[str]


class SourceInfo(BaseModel):
    """Information about a video source"""
    name: str
    stream: str
    type: str  # "camera" or "speaker"
    whep_url: str
    active: bool
    has_signal: Optional[bool] = None
    resolution: Optional[str] = None
    ingest_status: Optional[str] = None


class SourcesSummary(BaseModel):
    """Summary of available sources"""
    total: int
    active: int
    cameras: int
    speakers: int
    active_cameras: int
    active_speakers: int


class SourcesResponse(BaseModel):
    """Response containing all available sources"""
    sources: List[SourceInfo]
    summary: SourcesSummary


@router.post("/url", response_model=VdoUrlResponse)
async def generate_vdo_url(
    request: VdoUrlRequest,
    http_request: Request,
    settings: Settings = Depends(get_settings)
) -> VdoUrlResponse:
    """
    Generate a VDO.ninja URL for the specified profile.

    VDO.ninja runs LOCALLY on R58 - all URLs are local.
    """
    room = request.room or settings.vdoninja_room

    # Get the host that the client used to reach us
    # This ensures URLs work whether accessed via IP or hostname
    host = http_request.headers.get("host", "localhost:8000").split(":")[0]

    # VDO.ninja runs locally on R58
    vdo_host = f"{host}:{settings.vdoninja_port}"
    base = f"http://{vdo_host}"

    # CSS served from R58 API
    css_url = f"http://{host}:{settings.api_port}/static/css/vdo-theme.css"

    # Base params for all profiles (reskin + hide branding)
    params = {
        "css": css_url,
        "cleanoutput": "",
        "hideheader": "",
        "nologo": "",
        "darkmode": "",
    }

    if request.profile == "director":
        params.update({
            "director": room,
            "hidesolo": "",
        })

    elif request.profile == "scene":
        params.update({
            "scene": "",
            "room": room,
            "cover": "",
        })
        if request.sources:
            params["autoadd"] = ",".join(request.sources)

    elif request.profile == "cameraContribution":
        if request.sources:
            source = request.sources[0]  # One source per URL
            whep_url = f"http://{host}:{settings.mediamtx_whep_port}/{source}/whep"
            params.update({
                "push": source,
                "room": room,
                "whepshare": whep_url,  # urlencode handles encoding - don't double-encode
                "label": source.upper(),
                "videodevice": "0",
                "audiodevice": "0",
                "autostart": "",
            })

    elif request.profile == "guestInvite":
        params.update({
            "room": room,
            "push": request.guest_name or "guest",
            "label": request.guest_name or "Guest",
            "webcam": "",
        })

    elif request.profile == "multiview":
        params.update({
            "room": room,
            "scene": "",
            "grid": "",
            "autoadd": "*",
        })

    elif request.profile == "soloView":
        if request.sources:
            params.update({
                "view": request.sources[0],
                "room": room,
                "cover": "",
            })

    # Build URL with params
    url = f"{base}/?{urlencode(params, doseq=True)}"

    return VdoUrlResponse(
        url=url,
        profile=request.profile,
        room=room,
        css_url=css_url,
    )


async def _check_mediamtx_stream_ready(stream_id: str, settings: Settings) -> bool:
    """Check if a stream is ready in MediaMTX."""
    try:
        async with httpx.AsyncClient(timeout=2.0, verify=False) as client:
            url = f"{settings.mediamtx_api_url}/v3/paths/get/{stream_id}"
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                # MediaMTX v3 API uses "ready" field
                return data.get("ready", False)
    except Exception as e:
        logger.debug(f"MediaMTX check for {stream_id} failed: {e}")
    return False


@router.get("/sources", response_model=SourcesResponse)
async def get_sources(
    http_request: Request,
    settings: Settings = Depends(get_settings)
) -> SourcesResponse:
    """
    Get all available video sources (cameras + speakers) for VDO.ninja mixer.
    
    Returns a list of all sources with their status and WHEP URLs.
    Checks both pipeline manager state AND MediaMTX stream availability.
    """
    sources: List[SourceInfo] = []
    
    # Get the host for building WHEP URLs
    host = http_request.headers.get("host", "localhost:8000").split(":")[0]
    mediamtx_base = f"http://{host}:{settings.mediamtx_whep_port}"
    
    # Get pipeline status for camera information
    pipeline_client = get_pipeline_client()
    
    try:
        status = await pipeline_client.get_status()
        
        if "error" not in status:
            # Get camera sources from pipeline status
            inputs = status.get("inputs", {})
            for i, (input_id, input_status) in enumerate(sorted(inputs.items())):
                cam_number = i + 1
                
                has_signal = input_status.get("has_signal", False)
                is_streaming = input_status.get("preview_active", False)
                
                # Also check MediaMTX directly for stream availability
                mediamtx_ready = await _check_mediamtx_stream_ready(input_id, settings)
                
                # Stream is active if MediaMTX has the stream ready
                is_active = mediamtx_ready or is_streaming
                
                resolution_str = None
                resolution = input_status.get("resolution")
                if resolution:
                    if isinstance(resolution, list) and len(resolution) == 2:
                        resolution_str = f"{resolution[0]}x{resolution[1]}"
                    elif isinstance(resolution, str):
                        resolution_str = resolution
                
                sources.append(SourceInfo(
                    name=f"CAM{cam_number}",
                    stream=input_id,
                    type="camera",
                    whep_url=f"{mediamtx_base}/{input_id}/whep",
                    active=is_active,
                    ingest_status="streaming" if is_streaming else "idle",
                    has_signal=has_signal,
                    resolution=resolution_str
                ))
        else:
            # Pipeline manager not available - use configured inputs
            for i, input_id in enumerate(settings.enabled_inputs):
                cam_number = i + 1
                mediamtx_ready = await _check_mediamtx_stream_ready(input_id, settings)
                
                sources.append(SourceInfo(
                    name=f"CAM{cam_number}",
                    stream=input_id,
                    type="camera",
                    whep_url=f"{mediamtx_base}/{input_id}/whep",
                    active=mediamtx_ready,
                    ingest_status="unknown",
                    has_signal=None,
                    resolution=None
                ))
                
    except Exception as e:
        logger.warning(f"Failed to get pipeline status: {e}")
        # Fall back to configured inputs
        for i, input_id in enumerate(settings.enabled_inputs):
            cam_number = i + 1
            sources.append(SourceInfo(
                name=f"CAM{cam_number}",
                stream=input_id,
                type="camera",
                whep_url=f"{mediamtx_base}/{input_id}/whep",
                active=False,
                ingest_status="unknown",
                has_signal=None,
                resolution=None
            ))
    
    # Add speaker sources (check MediaMTX for availability)
    speaker_streams = ["speaker0", "speaker1", "speaker2"]
    for i, speaker_id in enumerate(speaker_streams):
        speaker_active = await _check_mediamtx_stream_ready(speaker_id, settings)
        
        sources.append(SourceInfo(
            name=f"Speaker {i + 1}",
            stream=speaker_id,
            type="speaker",
            whep_url=f"{mediamtx_base}/{speaker_id}/whep",
            active=speaker_active,
            resolution=None
        ))
    
    # Build summary
    cameras = [s for s in sources if s.type == "camera"]
    speakers = [s for s in sources if s.type == "speaker"]
    
    summary = SourcesSummary(
        total=len(sources),
        active=sum(1 for s in sources if s.active),
        cameras=len(cameras),
        speakers=len(speakers),
        active_cameras=sum(1 for s in cameras if s.active),
        active_speakers=sum(1 for s in speakers if s.active)
    )
    
    return SourcesResponse(sources=sources, summary=summary)


@router.get("/room-status", response_model=RoomStatus)
async def get_room_status(
    room: Optional[str] = None,
    settings: Settings = Depends(get_settings)
) -> RoomStatus:
    """
    Get current room status from local VDO.ninja signaling.

    Note: Requires integration with the custom signaling server on R58.
    """
    # TODO: Integrate with existing signaling server to get real-time room info
    return RoomStatus(
        room=room or settings.vdoninja_room,
        status="connected",
        sources=[],
    )


@router.get("/css")
async def get_vdo_css():
    """Serve VDO.ninja custom theme CSS"""
    css_path = Path(__file__).parent.parent / "static" / "css" / "vdo-theme.css"

    if css_path.exists():
        return FileResponse(
            css_path,
            media_type="text/css",
            headers={"Cache-Control": "public, max-age=3600"}
        )

    # Return empty CSS if file doesn't exist yet
    from fastapi.responses import Response
    return Response(
        content="/* VDO.ninja theme CSS placeholder */",
        media_type="text/css",
    )

