"""WebSocket endpoint handlers"""
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from .manager import get_connection_manager
from .events import EventType, BaseEvent

router = APIRouter()


@router.websocket("/api/v1/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
):
    """
    WebSocket endpoint for real-time events.
    
    Connect with: ws://host:8000/api/v1/ws?token=jwt_token
    """
    # TODO: Validate JWT token
    # For now, accept all connections
    
    client_id = str(uuid.uuid4())
    manager = get_connection_manager()
    
    try:
        await manager.connect(websocket, client_id)
        
        while True:
            # Wait for client messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(websocket, client_id, message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"}
                })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        manager.disconnect(client_id)


async def handle_client_message(
    websocket: WebSocket,
    client_id: str,
    message: dict
) -> None:
    """Handle incoming client messages"""
    msg_type = message.get("type")
    
    if msg_type == "sync_request":
        # Client is requesting state sync
        last_seq = message.get("last_seq", 0)
        
        # TODO: Send any events since last_seq
        # For now, just send current state
        await websocket.send_json({
            "type": "sync_response",
            "payload": {
                "last_seq": last_seq,
                "events": [],  # Would include missed events
            }
        })
    
    elif msg_type == "ping":
        # Respond to ping
        await websocket.send_json({"type": "pong"})
    
    else:
        # Unknown message type
        await websocket.send_json({
            "type": "error",
            "payload": {"message": f"Unknown message type: {msg_type}"}
        })

