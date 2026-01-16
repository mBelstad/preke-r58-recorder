"""Companion WebSocket handler for Stream Deck integration"""
import json
import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from ...realtime.manager import get_connection_manager
from ...realtime.events import CameraSettingsChangedEvent
from ..cameras.router import get_camera_control_manager, get_camera_by_name

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/api/v1/companion/ws")
async def companion_websocket(
    websocket: WebSocket,
    instance_id: Optional[str] = Query(None),
):
    """
    Companion WebSocket endpoint for Stream Deck integration.
    
    Protocol:
    - Companion sends button press events
    - Server responds with state updates
    - Server can send button feedback updates
    """
    await websocket.accept()
    logger.info(f"Companion connected (instance: {instance_id})")
    
    manager = get_camera_control_manager()
    if manager is None:
        await websocket.send_json({
            "type": "error",
            "message": "Camera control not available"
        })
        await websocket.close()
        return
    
    try:
        while True:
            # Receive message from Companion
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_companion_message(websocket, message, manager)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                logger.error(f"Error handling Companion message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
    
    except WebSocketDisconnect:
        logger.info(f"Companion disconnected (instance: {instance_id})")
    except Exception as e:
        logger.error(f"Companion WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass


async def handle_companion_message(
    websocket: WebSocket,
    message: Dict[str, Any],
    manager: Any
) -> None:
    """Handle incoming message from Companion"""
    msg_type = message.get("type")
    action = message.get("action")
    
    if msg_type == "button_press" or action == "camera_control":
        # Button press event
        payload = message.get("payload", {})
        camera_name = payload.get("camera_id") or payload.get("camera")
        parameter = payload.get("parameter")
        value = payload.get("value")
        mode = payload.get("mode")
        
        if not camera_name or not parameter:
            await websocket.send_json({
                "type": "error",
                "message": "Missing camera_id or parameter"
            })
            return
        
        try:
            camera = get_camera_by_name(camera_name, manager)
            
            # Execute camera control action
            success = False
            if parameter == "focus":
                success = await camera.set_focus(mode, value)
            elif parameter == "whiteBalance":
                success = await camera.set_white_balance(mode, payload.get("temperature"))
            elif parameter == "exposure":
                if hasattr(camera, "set_exposure"):
                    success = await camera.set_exposure(mode, value)
            elif parameter == "iso":
                if hasattr(camera, "set_iso"):
                    success = await camera.set_iso(value)
            elif parameter == "shutter":
                if hasattr(camera, "set_shutter"):
                    success = await camera.set_shutter(value)
            elif parameter == "iris":
                if hasattr(camera, "set_iris"):
                    success = await camera.set_iris(mode, value)
            elif parameter == "gain":
                if hasattr(camera, "set_gain"):
                    success = await camera.set_gain(value)
            elif parameter == "ptz":
                if hasattr(camera, "ptz_move"):
                    success = await camera.ptz_move(
                        payload.get("pan", 0),
                        payload.get("tilt", 0),
                        payload.get("zoom", 0)
                    )
            elif parameter == "ptz_preset":
                if hasattr(camera, "ptz_preset"):
                    success = await camera.ptz_preset(payload.get("preset_id", 0))
            
            # Send response
            await websocket.send_json({
                "type": "button_feedback",
                "button_id": message.get("button_id"),
                "success": success,
                "camera": camera_name,
                "parameter": parameter
            })
            
            # Broadcast event to WebSocket clients
            if success:
                ws_manager = get_connection_manager()
                event = CameraSettingsChangedEvent.create(
                    camera_name=camera_name,
                    parameter=parameter,
                    value={"mode": mode, "value": value}
                )
                await ws_manager.broadcast(event)
        
        except Exception as e:
            logger.error(f"Error executing camera control: {e}")
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
    
    elif msg_type == "get_state":
        # Companion requesting current state
        cameras = {}
        for name in manager.cameras.keys():
            try:
                camera = manager.cameras[name]
                connected = await camera.check_connection()
                settings = await camera.get_settings() if connected else None
                cameras[name] = {
                    "connected": connected,
                    "settings": settings
                }
            except Exception as e:
                logger.warning(f"Error getting state for {name}: {e}")
                cameras[name] = {"connected": False, "settings": None}
        
        await websocket.send_json({
            "type": "state",
            "cameras": cameras
        })
    
    elif msg_type == "ping":
        # Heartbeat
        await websocket.send_json({
            "type": "pong",
            "ts": message.get("ts")
        })
    
    else:
        await websocket.send_json({
            "type": "error",
            "message": f"Unknown message type: {msg_type}"
        })
