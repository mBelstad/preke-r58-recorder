"""
Minimal VDO.ninja API router for Companion/Stream Deck integration

Provides HTTP endpoints that proxy to VDO.ninja's HTTP API.
Companion-compatible format for easy Stream Deck integration.
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...config import Settings, get_settings
from src.vdo_ninja.api_client import VdoNinjaApiClient, get_vdo_ninja_client_from_config

router = APIRouter(prefix="/api/v1/vdo-ninja", tags=["VDO.ninja"])
logger = logging.getLogger(__name__)

# Singleton client instance
_vdo_client: Optional[VdoNinjaApiClient] = None


def get_vdo_client(settings: Settings = Depends(get_settings)) -> Optional[VdoNinjaApiClient]:
    """Get or create VDO.ninja API client singleton"""
    global _vdo_client
    if _vdo_client is None:
        _vdo_client = get_vdo_ninja_client_from_config()
    return _vdo_client


# Request/Response models
class VolumeRequest(BaseModel):
    volume: int  # 0-200


class GuestInfo(BaseModel):
    id: str
    label: Optional[str] = None
    slot: Optional[int] = None


# Endpoints
@router.post("/scene/{scene_id}")
async def switch_scene(
    scene_id: int,
    client: Optional[VdoNinjaApiClient] = Depends(get_vdo_client)
) -> Dict[str, Any]:
    """Switch to scene (0-8 or custom scene name)"""
    if not client:
        raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
    
    success = await client.switch_scene(scene_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to switch scene")
    
    return {"success": True, "scene_id": scene_id}


@router.post("/guest/{guest_id}/mute")
async def toggle_mute(
    guest_id: str,
    client: Optional[VdoNinjaApiClient] = Depends(get_vdo_client)
) -> Dict[str, Any]:
    """Toggle microphone mute for a guest"""
    if not client:
        raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
    
    muted = await client.toggle_mute(guest_id)
    if muted is None:
        raise HTTPException(status_code=500, detail="Failed to toggle mute")
    
    return {"success": True, "guest_id": guest_id, "muted": muted}


@router.post("/guest/{guest_id}/volume")
async def set_volume(
    guest_id: str,
    request: VolumeRequest,
    client: Optional[VdoNinjaApiClient] = Depends(get_vdo_client)
) -> Dict[str, Any]:
    """Set volume for a guest (0-200)"""
    if not client:
        raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
    
    success = await client.set_volume(guest_id, request.volume)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set volume")
    
    return {"success": True, "guest_id": guest_id, "volume": request.volume}


@router.post("/recording/start")
async def start_recording(
    client: Optional[VdoNinjaApiClient] = Depends(get_vdo_client)
) -> Dict[str, Any]:
    """Start recording"""
    if not client:
        raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
    
    success = await client.start_recording()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start recording")
    
    return {"success": True, "recording": True}


@router.post("/recording/stop")
async def stop_recording(
    client: Optional[VdoNinjaApiClient] = Depends(get_vdo_client)
) -> Dict[str, Any]:
    """Stop recording"""
    if not client:
        raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
    
    success = await client.stop_recording()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop recording")
    
    return {"success": True, "recording": False}


@router.get("/guests", response_model=List[Dict[str, Any]])
async def list_guests(
    client: Optional[VdoNinjaApiClient] = Depends(get_vdo_client)
) -> List[Dict[str, Any]]:
    """List connected guests (for Companion feedback)"""
    if not client:
        raise HTTPException(status_code=503, detail="VDO.ninja API not configured")
    
    guests = await client.get_guests()
    return guests
