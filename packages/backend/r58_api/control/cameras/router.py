"""Camera control API endpoints"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...config import Settings, get_settings
from ...realtime.manager import get_connection_manager
from ...realtime.events import (
    BaseEvent, EventType, CameraSettingsChangedEvent
)

# Import camera control classes
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "src"))
from camera_control.manager import CameraControlManager
from camera_control.blackmagic import BlackmagicCamera
from camera_control.obsbot import ObsbotTail2

router = APIRouter(prefix="/api/v1/cameras", tags=["Cameras"])
logger = logging.getLogger(__name__)

# Camera control manager singleton
_camera_control_manager: Optional[CameraControlManager] = None


def get_camera_control_manager(settings: Settings = Depends(get_settings)) -> Optional[CameraControlManager]:
    """Get or create camera control manager singleton"""
    global _camera_control_manager
    
    if _camera_control_manager is not None:
        return _camera_control_manager
    
    # Load config from config.yml
    config_path = Path("/opt/preke-r58-recorder/config.yml")
    if not config_path.exists():
        config_path = Path(__file__).parent.parent.parent.parent.parent.parent / "config.yml"
    
    if not config_path.exists():
        logger.warning("config.yml not found, camera control disabled")
        return None
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        external_cameras = config_data.get("external_cameras", [])
        if not external_cameras:
            logger.info("No external cameras configured")
            return None
        
        _camera_control_manager = CameraControlManager(external_cameras)
        logger.info(f"Camera control manager initialized with {_camera_control_manager.get_camera_count()} camera(s)")
        return _camera_control_manager
    except Exception as e:
        logger.error(f"Failed to initialize camera control manager: {e}")
        return None


def get_camera_by_name(camera_name: str, manager: Optional[CameraControlManager] = None) -> Any:
    """Get camera instance by name"""
    if manager is None:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    if camera_name not in manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    return manager.cameras[camera_name]


# Request/Response models
class CameraStatusResponse(BaseModel):
    """Camera status response"""
    name: str
    type: str
    connected: bool
    settings: Optional[Dict[str, Any]] = None


class CameraSettingsResponse(BaseModel):
    """Camera settings response"""
    name: str
    settings: Dict[str, Any]


class SetFocusRequest(BaseModel):
    """Set focus request"""
    mode: str  # 'auto' or 'manual'
    value: Optional[float] = None  # 0.0-1.0 for manual mode


class SetWhiteBalanceRequest(BaseModel):
    """Set white balance request"""
    mode: str  # 'auto', 'manual', or 'preset'
    temperature: Optional[int] = None  # Kelvin for manual mode


class SetExposureRequest(BaseModel):
    """Set exposure request"""
    mode: str  # 'auto' or 'manual'
    value: Optional[float] = None  # Exposure value for manual mode


class SetPTZRequest(BaseModel):
    """PTZ move request"""
    pan: float  # -1.0 to 1.0
    tilt: float  # -1.0 to 1.0
    zoom: float  # -1.0 to 1.0


class SetColorCorrectionRequest(BaseModel):
    """Color correction request"""
    lift: Optional[List[float]] = None
    gamma: Optional[List[float]] = None
    gain: Optional[List[float]] = None
    offset: Optional[List[float]] = None


# API Endpoints
@router.get("/", response_model=List[str])
async def list_cameras(
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> List[str]:
    """List all configured external cameras"""
    if manager is None:
        return []
    return list(manager.cameras.keys())


@router.get("/{camera_name}/status", response_model=CameraStatusResponse)
async def get_camera_status(
    camera_name: str,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> CameraStatusResponse:
    """Get camera status and connection info"""
    camera = get_camera_by_name(camera_name, manager)
    
    connected = await camera.check_connection()
    camera_type = "blackmagic" if isinstance(camera, BlackmagicCamera) else "obsbot_tail2"
    
    settings = None
    if connected:
        try:
            settings = await camera.get_settings()
        except Exception as e:
            logger.warning(f"Failed to get settings from {camera_name}: {e}")
    
    return CameraStatusResponse(
        name=camera_name,
        type=camera_type,
        connected=connected,
        settings=settings
    )


@router.get("/{camera_name}/settings", response_model=CameraSettingsResponse)
async def get_camera_settings(
    camera_name: str,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> CameraSettingsResponse:
    """Get all camera settings"""
    camera = get_camera_by_name(camera_name, manager)
    
    settings = await camera.get_settings()
    if settings is None:
        raise HTTPException(status_code=503, detail="Failed to get camera settings")
    
    return CameraSettingsResponse(name=camera_name, settings=settings)


@router.put("/{camera_name}/settings/focus")
async def set_focus(
    camera_name: str,
    request: SetFocusRequest,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set camera focus"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, (BlackmagicCamera, ObsbotTail2)):
        raise HTTPException(status_code=400, detail="Camera does not support focus control")
    
    success = await camera.set_focus(request.mode, request.value)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set focus")
    
    # Broadcast event
    manager_ws = get_connection_manager()
    event = CameraSettingsChangedEvent.create(
        camera_name=camera_name,
        parameter="focus",
        value={"mode": request.mode, "value": request.value}
    )
    await manager_ws.broadcast(event)
    
    return {"success": True, "camera": camera_name, "parameter": "focus"}


@router.put("/{camera_name}/settings/whiteBalance")
async def set_white_balance(
    camera_name: str,
    request: SetWhiteBalanceRequest,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set camera white balance"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, (BlackmagicCamera, ObsbotTail2)):
        raise HTTPException(status_code=400, detail="Camera does not support white balance control")
    
    success = await camera.set_white_balance(request.mode, request.temperature)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set white balance")
    
    return {"success": True, "camera": camera_name, "parameter": "whiteBalance"}


@router.put("/{camera_name}/settings/exposure")
async def set_exposure(
    camera_name: str,
    request: SetExposureRequest,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set camera exposure (for OBSbot) or ISO/shutter (for BMD)"""
    camera = get_camera_by_name(camera_name, manager)
    
    if isinstance(camera, ObsbotTail2):
        success = await camera.set_exposure(request.mode, request.value)
    elif isinstance(camera, BlackmagicCamera):
        # For BMD, exposure is controlled via ISO and shutter separately
        raise HTTPException(status_code=400, detail="Use /settings/iso and /settings/shutter for Blackmagic cameras")
    else:
        raise HTTPException(status_code=400, detail="Camera does not support exposure control")
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set exposure")
    
    return {"success": True, "camera": camera_name, "parameter": "exposure"}


@router.put("/{camera_name}/settings/iso")
async def set_iso(
    camera_name: str,
    value: int,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set camera ISO (Blackmagic only)"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support ISO control")
    
    success = await camera.set_iso(value)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set ISO")
    
    return {"success": True, "camera": camera_name, "parameter": "iso", "value": value}


@router.put("/{camera_name}/settings/shutter")
async def set_shutter(
    camera_name: str,
    value: float,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set camera shutter speed (Blackmagic only)"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support shutter control")
    
    success = await camera.set_shutter(value)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set shutter")
    
    return {"success": True, "camera": camera_name, "parameter": "shutter", "value": value}


@router.put("/{camera_name}/settings/iris")
async def set_iris(
    camera_name: str,
    mode: str,
    value: Optional[float] = None,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set camera iris (Blackmagic only)"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support iris control")
    
    success = await camera.set_iris(mode, value)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set iris")
    
    return {"success": True, "camera": camera_name, "parameter": "iris"}


@router.put("/{camera_name}/settings/gain")
async def set_gain(
    camera_name: str,
    value: float,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set camera gain (Blackmagic only)"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support gain control")
    
    success = await camera.set_gain(value)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set gain")
    
    return {"success": True, "camera": camera_name, "parameter": "gain", "value": value}


@router.put("/{camera_name}/settings/ptz")
async def set_ptz(
    camera_name: str,
    request: SetPTZRequest,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Move PTZ camera (OBSbot only)"""
    camera = get_camera_by_name(camera_name, manager)
    
    # Check if camera supports PTZ (OBSbot, Sony, etc.)
    if not hasattr(camera, "ptz_move"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ control")
    
    success = await camera.ptz_move(request.pan, request.tilt, request.zoom)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to move PTZ")
    
    return {"success": True, "camera": camera_name, "parameter": "ptz"}


@router.put("/{camera_name}/settings/ptz/preset/{preset_id}")
async def recall_ptz_preset(
    camera_name: str,
    preset_id: int,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Recall PTZ preset (OBSbot only)"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, ObsbotTail2):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ presets")
    
    success = await camera.ptz_preset(preset_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to recall preset")
    
    return {"success": True, "camera": camera_name, "preset_id": preset_id}


@router.put("/{camera_name}/settings/colorCorrection")
async def set_color_correction(
    camera_name: str,
    request: SetColorCorrectionRequest,
    manager: Optional[CameraControlManager] = Depends(get_camera_control_manager)
) -> Dict[str, Any]:
    """Set color correction (Blackmagic only)"""
    camera = get_camera_by_name(camera_name, manager)
    
    if not isinstance(camera, BlackmagicCamera):
        raise HTTPException(status_code=400, detail="Camera does not support color correction")
    
    settings = {}
    if request.lift:
        settings["lift"] = request.lift
    if request.gamma:
        settings["gamma"] = request.gamma
    if request.gain:
        settings["gain"] = request.gain
    if request.offset:
        settings["offset"] = request.offset
    
    success = await camera.set_color_correction(settings)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set color correction")
    
    return {"success": True, "camera": camera_name, "parameter": "colorCorrection"}
