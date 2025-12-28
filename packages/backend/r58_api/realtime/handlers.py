"""WebSocket endpoint handlers"""
import json
import logging
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from .manager import get_connection_manager
from .events import EventType, BaseEvent

router = APIRouter()
logger = logging.getLogger(__name__)


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
    manager = get_connection_manager()
    
    if msg_type == "sync_request":
        # Client is requesting state sync (typically after reconnection)
        last_seq = message.get("last_seq", 0)
        
        logger.info(f"[WS] Client {client_id[:8]} requesting sync from seq {last_seq}")
        
        # Get full sync response with state and missed events
        sync_response = await manager.get_sync_response(last_seq)
        
        await websocket.send_json(sync_response)
        
        missed_count = sync_response["payload"]["missed_event_count"]
        if missed_count > 0:
            logger.info(f"[WS] Sent {missed_count} missed events to client {client_id[:8]}")
        else:
            logger.debug(f"[WS] No missed events for client {client_id[:8]}")
    
    elif msg_type == "ping":
        # Respond to ping
        await websocket.send_json({"type": "pong", "ts": message.get("ts")})
    
    elif msg_type == "get_state":
        # Client requesting current state without event replay
        state = manager.current_state
        await websocket.send_json({
            "type": "state",
            "seq": manager.sequence,
            "payload": state,
        })
    
    elif msg_type == "subscribe":
        # Client wants to subscribe to specific event types
        event_types = message.get("events", [])
        logger.info(f"[WS] Client {client_id[:8]} subscribing to: {event_types}")
        # TODO: Implement per-client event filtering
        await websocket.send_json({
            "type": "subscribed",
            "payload": {"events": event_types}
        })
    
    else:
        # Unknown message type
        logger.warning(f"[WS] Unknown message type from {client_id[:8]}: {msg_type}")
        await websocket.send_json({
            "type": "error",
            "payload": {"message": f"Unknown message type: {msg_type}"}
        })

