"""VDO.ninja integration endpoints (LOCAL R58 instance)"""
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..config import Settings, get_settings

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
                "whepshare": quote(whep_url, safe=''),
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

