"""WebSocket connection manager"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

from .events import BaseEvent, EventType, ConnectedEvent, HeartbeatEvent
from ..config import get_settings


class ConnectionManager:
    """Manages WebSocket connections and event broadcasting"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sequence: int = 0
        self.settings = get_settings()
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # Send connected event
        event = ConnectedEvent(
            seq=self._next_seq(),
            device_id=self.settings.device_id,
        )
        await self._send_event(websocket, event)
        
        # Start heartbeat if first connection
        if len(self.active_connections) == 1:
            self._start_heartbeat()
    
    def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # Stop heartbeat if no connections
        if not self.active_connections and self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
    
    async def broadcast(self, event: BaseEvent) -> None:
        """Broadcast an event to all connected clients"""
        event.seq = self._next_seq()
        event.device_id = self.settings.device_id
        
        disconnected = []
        for client_id, ws in self.active_connections.items():
            try:
                await self._send_event(ws, event)
            except Exception:
                disconnected.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def send_to(self, client_id: str, event: BaseEvent) -> bool:
        """Send an event to a specific client"""
        if client_id not in self.active_connections:
            return False
        
        event.seq = self._next_seq()
        event.device_id = self.settings.device_id
        
        try:
            await self._send_event(self.active_connections[client_id], event)
            return True
        except Exception:
            self.disconnect(client_id)
            return False
    
    async def _send_event(self, ws: WebSocket, event: BaseEvent) -> None:
        """Send an event to a WebSocket"""
        data = event.model_dump(mode="json")
        await ws.send_json(data)
    
    def _next_seq(self) -> int:
        """Get next sequence number"""
        self.sequence += 1
        return self.sequence
    
    def _start_heartbeat(self) -> None:
        """Start the heartbeat background task"""
        async def heartbeat_loop():
            while self.active_connections:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                event = HeartbeatEvent(
                    seq=self._next_seq(),
                    device_id=self.settings.device_id,
                )
                await self.broadcast(event)
        
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())


# Singleton instance
_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create connection manager singleton"""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager

