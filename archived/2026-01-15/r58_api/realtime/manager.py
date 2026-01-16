"""WebSocket connection manager"""
import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from fastapi import WebSocket

from ..config import get_settings
from .events import BaseEvent, ConnectedEvent, EventType, HeartbeatEvent

logger = logging.getLogger(__name__)

# Maximum number of events to buffer for replay
EVENT_BUFFER_SIZE = 100


class EventBuffer:
    """Circular buffer for event replay on reconnection"""

    def __init__(self, max_size: int = EVENT_BUFFER_SIZE):
        self._buffer: Deque[dict] = deque(maxlen=max_size)
        self._min_seq: int = 0

    def add(self, event_data: dict) -> None:
        """Add an event to the buffer"""
        self._buffer.append(event_data)
        # Track the minimum sequence we have
        if self._buffer:
            self._min_seq = self._buffer[0].get("seq", 0)

    def get_events_since(self, last_seq: int) -> List[dict]:
        """Get all events with seq > last_seq"""
        if last_seq < self._min_seq:
            # Client is too far behind, they need full state
            return []

        return [
            event for event in self._buffer
            if event.get("seq", 0) > last_seq
        ]

    def can_replay_from(self, last_seq: int) -> bool:
        """Check if we have events from last_seq onwards"""
        if not self._buffer:
            return last_seq == 0
        return last_seq >= self._min_seq - 1

    @property
    def latest_seq(self) -> int:
        """Get the latest sequence number in buffer"""
        if not self._buffer:
            return 0
        return self._buffer[-1].get("seq", 0)


class ConnectionManager:
    """Manages WebSocket connections and event broadcasting"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sequence: int = 0
        self.settings = get_settings()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._event_buffer = EventBuffer()

        # Current state cache for quick sync
        self._current_state: Dict[str, Any] = {
            "mode": "idle",
            "recording": None,
            "inputs": {},
        }

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

        # Serialize event for buffer and sending
        event_data = event.model_dump(mode="json")

        # Add to event buffer for replay
        self._event_buffer.add(event_data)

        # Update current state cache based on event type
        self._update_state_from_event(event)

        disconnected = []
        for client_id, ws in self.active_connections.items():
            try:
                await ws.send_json(event_data)
            except Exception:
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    def _update_state_from_event(self, event: BaseEvent) -> None:
        """Update current state cache based on event"""
        if event.type == EventType.RECORDING_STARTED:
            self._current_state["mode"] = "recording"
            self._current_state["recording"] = event.payload

        elif event.type == EventType.RECORDING_STOPPED:
            self._current_state["mode"] = "idle"
            self._current_state["recording"] = None

        elif event.type == EventType.RECORDING_PROGRESS:
            if event.payload:
                self._current_state["recording"] = {
                    **self._current_state.get("recording", {}),
                    **event.payload,
                }

        elif event.type == EventType.MODE_CHANGED:
            if event.payload:
                self._current_state["mode"] = event.payload.get("mode", "idle")

        elif event.type == EventType.INPUT_SIGNAL_CHANGED:
            if event.payload:
                input_id = event.payload.get("input_id")
                if input_id:
                    self._current_state["inputs"][input_id] = event.payload

        elif event.type == EventType.PREVIEW_STARTED:
            if event.payload:
                input_id = event.payload.get("input_id")
                if input_id:
                    if "previews" not in self._current_state:
                        self._current_state["previews"] = {}
                    self._current_state["previews"][input_id] = {
                        "running": True,
                        "rtsp_url": event.payload.get("rtsp_url"),
                    }

        elif event.type == EventType.PREVIEW_STOPPED:
            if event.payload:
                input_id = event.payload.get("input_id")
                if input_id and "previews" in self._current_state:
                    self._current_state["previews"][input_id] = {"running": False}

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

    async def get_sync_response(self, last_seq: int) -> dict:
        """
        Build a sync response for a reconnecting client.

        Args:
            last_seq: The last sequence number the client received

        Returns:
            Sync response with current state and any missed events
        """
        # Get current authoritative state from pipeline
        current_state = await self._fetch_authoritative_state()

        # Check if we can replay missed events
        can_replay = self._event_buffer.can_replay_from(last_seq)
        missed_events = []

        if can_replay:
            missed_events = self._event_buffer.get_events_since(last_seq)

        return {
            "type": "sync_response",
            "seq": self._next_seq(),
            "ts": datetime.now().isoformat(),
            "payload": {
                "last_seq": last_seq,
                "current_seq": self.sequence,
                "can_replay": can_replay,
                "missed_event_count": len(missed_events),
                "events": missed_events,
                "state": current_state,
            }
        }

    async def _fetch_authoritative_state(self) -> dict:
        """Fetch current authoritative state from pipeline manager"""
        from ..media.pipeline_client import get_pipeline_client

        try:
            client = get_pipeline_client()
            recording_status = await client.get_recording_status()

            return {
                "mode": "recording" if recording_status.get("recording") else "idle",
                "recording": {
                    "session_id": recording_status.get("session_id"),
                    "duration_ms": recording_status.get("duration_ms", 0),
                    "bytes_written": recording_status.get("bytes_written", {}),
                    "inputs": list(recording_status.get("bytes_written", {}).keys()),
                } if recording_status.get("recording") else None,
                "inputs": self._current_state.get("inputs", {}),
            }
        except Exception as e:
            logger.error(f"Failed to fetch authoritative state: {e}")
            # Fall back to cached state
            return self._current_state

    def update_input_state(self, input_id: str, state: dict) -> None:
        """Update cached input state"""
        self._current_state["inputs"][input_id] = state

    @property
    def current_state(self) -> dict:
        """Get current cached state"""
        return self._current_state.copy()

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

