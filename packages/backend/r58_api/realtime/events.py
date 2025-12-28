"""WebSocket event schema definitions"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types for WebSocket communication"""

    # System
    CONNECTED = "connected"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    SYNC_RESPONSE = "sync_response"

    # Mode
    MODE_CHANGED = "mode.changed"

    # Recorder
    RECORDING_STARTED = "recorder.started"
    RECORDING_STOPPED = "recorder.stopped"
    RECORDING_PROGRESS = "recorder.progress"

    # Pipeline/Preview
    PREVIEW_STARTED = "preview.started"
    PREVIEW_STOPPED = "preview.stopped"
    PIPELINE_ERROR = "pipeline.error"

    # Mixer
    SCENE_CHANGED = "mixer.scene_changed"
    SOURCE_UPDATED = "mixer.source_updated"

    # Inputs
    INPUT_SIGNAL_CHANGED = "input.signal_changed"
    INPUT_ERROR = "input.error"

    # Graphics
    OVERLAY_SHOWN = "graphics.overlay_shown"
    OVERLAY_HIDDEN = "graphics.overlay_hidden"

    # System
    HEALTH_CHANGED = "health.changed"
    STORAGE_WARNING = "storage.warning"


class BaseEvent(BaseModel):
    """Base event structure"""
    v: int = 1  # Schema version
    type: EventType
    ts: datetime = Field(default_factory=datetime.now)
    seq: int = 0  # Sequence number
    device_id: str = ""
    payload: Optional[Dict[str, Any]] = None


class ConnectedEvent(BaseEvent):
    """Sent when client connects"""
    type: EventType = EventType.CONNECTED
    payload: Dict[str, Any] = Field(default_factory=lambda: {
        "message": "Connected to R58 API",
        "api_version": "2.0.0",
    })


class HeartbeatEvent(BaseEvent):
    """Keep-alive heartbeat"""
    type: EventType = EventType.HEARTBEAT


class RecordingProgressEvent(BaseEvent):
    """Recording progress update"""
    type: EventType = EventType.RECORDING_PROGRESS

    @classmethod
    def create(
        cls,
        session_id: str,
        duration_ms: int,
        bytes_written: Dict[str, int],
        device_id: str,
        seq: int
    ) -> "RecordingProgressEvent":
        return cls(
            seq=seq,
            device_id=device_id,
            payload={
                "session_id": session_id,
                "duration_ms": duration_ms,
                "bytes_written": bytes_written,
            }
        )


class InputSignalEvent(BaseEvent):
    """Input signal status change"""
    type: EventType = EventType.INPUT_SIGNAL_CHANGED

    @classmethod
    def create(
        cls,
        input_id: str,
        has_signal: bool,
        resolution: Optional[str] = None,
        framerate: Optional[int] = None,
        device_id: str = "",
        seq: int = 0
    ) -> "InputSignalEvent":
        return cls(
            seq=seq,
            device_id=device_id,
            payload={
                "input_id": input_id,
                "has_signal": has_signal,
                "resolution": resolution,
                "framerate": framerate,
            }
        )


class PreviewStartedEvent(BaseEvent):
    """Preview pipeline started"""
    type: EventType = EventType.PREVIEW_STARTED

    @classmethod
    def create(
        cls,
        input_id: str,
        rtsp_url: Optional[str] = None,
        device_id: str = "",
        seq: int = 0
    ) -> "PreviewStartedEvent":
        return cls(
            seq=seq,
            device_id=device_id,
            payload={
                "input_id": input_id,
                "rtsp_url": rtsp_url,
            }
        )


class PreviewStoppedEvent(BaseEvent):
    """Preview pipeline stopped"""
    type: EventType = EventType.PREVIEW_STOPPED

    @classmethod
    def create(
        cls,
        input_id: str,
        device_id: str = "",
        seq: int = 0
    ) -> "PreviewStoppedEvent":
        return cls(
            seq=seq,
            device_id=device_id,
            payload={
                "input_id": input_id,
            }
        )


class PipelineErrorEvent(BaseEvent):
    """Pipeline error occurred"""
    type: EventType = EventType.PIPELINE_ERROR

    @classmethod
    def create(
        cls,
        pipeline_id: str,
        error: str,
        input_id: Optional[str] = None,
        device_id: str = "",
        seq: int = 0
    ) -> "PipelineErrorEvent":
        return cls(
            seq=seq,
            device_id=device_id,
            payload={
                "pipeline_id": pipeline_id,
                "error": error,
                "input_id": input_id,
            }
        )

