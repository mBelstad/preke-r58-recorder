"""PTZ Controller API endpoints for hardware joystick/controller support."""
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Body, HTTPException
from pydantic import BaseModel

from ...realtime.manager import get_connection_manager
from ...realtime.events import CameraSettingsChangedEvent
from ..cameras.router import get_camera_control_manager

def get_camera_by_name(camera_name: str, manager):
    """Get camera instance by name."""
    if not manager or camera_name not in manager.cameras:
        return None
    return manager.cameras[camera_name]

router = APIRouter(prefix="/api/v1/ptz-controller", tags=["PTZ Controller"])
logger = logging.getLogger(__name__)


class PTZCommandRequest(BaseModel):
    """PTZ command from controller."""
    pan: float  # -1.0 to 1.0
    tilt: float  # -1.0 to 1.0
    zoom: float  # -1.0 to 1.0
    focus: Optional[float] = None
    speed: float = 1.0


@router.websocket("/ws")
async def ptz_controller_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time PTZ control from hardware controllers.
    
    Protocol:
    - Client sends PTZ commands continuously
    - Server executes commands on target camera
    - Optimized for low latency (< 10ms)
    """
    await websocket.accept()
    logger.info("PTZ controller WebSocket connected")
    
    manager = get_camera_control_manager()
    if manager is None:
        await websocket.send_json({
            "type": "error",
            "message": "Camera control not available"
        })
        await websocket.close()
        return
    
    current_camera: Optional[str] = None
    last_command_time = 0.0
    min_command_interval = 0.033  # ~30Hz max update rate
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "set_camera":
                # Set target camera
                current_camera = data.get("camera_name")
                await websocket.send_json({
                    "type": "camera_set",
                    "camera": current_camera
                })
                logger.info(f"PTZ controller targeting camera: {current_camera}")
            
            elif msg_type == "ptz_command":
                # Execute PTZ command (fast path)
                if not current_camera:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No camera selected"
                    })
                    continue
                
                try:
                    import time
                    now = time.time()
                    # Throttle commands for smooth control
                    if now - last_command_time < min_command_interval:
                        continue
                    last_command_time = now
                    
                    camera = get_camera_by_name(current_camera, manager)
                    if not camera:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Camera '{current_camera}' not found"
                        })
                        continue
                    
                    # Check if camera supports PTZ
                    if not hasattr(camera, "ptz_move"):
                        await websocket.send_json({
                            "type": "error",
                            "message": "Camera does not support PTZ"
                        })
                        continue
                    
                    # Execute PTZ command (fire-and-forget for speed)
                    pan = data.get("pan", 0.0)
                    tilt = data.get("tilt", 0.0)
                    zoom = data.get("zoom", 0.0)
                    speed = data.get("speed", 1.0)
                    
                    # Apply speed multiplier
                    pan *= speed
                    tilt *= speed
                    zoom *= speed
                    
                    # Execute (async, don't wait for response for speed)
                    asyncio.create_task(camera.ptz_move(pan, tilt, zoom))
                    
                    # Optional: Send focus command if provided
                    if "focus" in data and hasattr(camera, "set_focus"):
                        focus_value = data["focus"]
                        if focus_value != 0:
                            # Convert to focus value (0.0-1.0)
                            focus_normalized = (focus_value + 1.0) / 2.0
                            asyncio.create_task(camera.set_focus("manual", focus_normalized))
                    
                except Exception as e:
                    logger.error(f"Error executing PTZ command: {e}")
                    # Don't send error for every command (would spam)
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
    
    except WebSocketDisconnect:
        logger.info("PTZ controller WebSocket disconnected")
    except Exception as e:
        logger.error(f"PTZ controller WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


@router.put("/{camera_name}/ptz")
async def ptz_command(
    camera_name: str,
    request: PTZCommandRequest,
    manager = None
) -> Dict[str, Any]:
    """
    Execute PTZ command (REST endpoint for non-WebSocket clients).
    
    Optimized for speed - uses fire-and-forget for PTZ movements.
    """
    if manager is None:
        manager = get_camera_control_manager()
    
    if manager is None:
        raise HTTPException(status_code=503, detail="Camera control not available")
    
    camera = get_camera_by_name(camera_name, manager)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")
    
    if not hasattr(camera, "ptz_move"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ")
    
    # Apply speed multiplier
    pan = request.pan * request.speed
    tilt = request.tilt * request.speed
    zoom = request.zoom * request.speed
    
    # Execute PTZ (fire-and-forget for speed)
    asyncio.create_task(camera.ptz_move(pan, tilt, zoom))
    
    # Optional: Handle focus
    if request.focus is not None and hasattr(camera, "set_focus"):
        focus_normalized = (request.focus + 1.0) / 2.0
        asyncio.create_task(camera.set_focus("manual", focus_normalized))
    
    return {
        "success": True,
        "camera": camera_name,
        "command": {
            "pan": pan,
            "tilt": tilt,
            "zoom": zoom
        }
    }


@router.get("/cameras")
async def list_ptz_cameras(manager = None) -> Dict[str, Any]:
    """List cameras that support PTZ control."""
    if manager is None:
        manager = get_camera_control_manager()
    
    if manager is None:
        return {"cameras": []}
    
    ptz_cameras = []
    for name, camera in manager.cameras.items():
        if hasattr(camera, "ptz_move"):
            ptz_cameras.append({
                "name": name,
                "type": camera.__class__.__name__,
                "supports_focus": hasattr(camera, "set_focus")
            })
    
    return {"cameras": ptz_cameras}
