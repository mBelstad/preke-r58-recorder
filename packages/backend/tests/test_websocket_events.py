"""
Test WebSocket event handling
Priority: P1
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from r58_api.realtime.events import (
    EventType,
    BaseEvent,
    ConnectedEvent,
    HeartbeatEvent,
    RecordingProgressEvent,
    InputSignalEvent,
)


class TestEventSerialization:
    """Tests for event serialization"""
    
    def test_connected_event_serialization(self):
        """Test ConnectedEvent serializes correctly for WebSocket"""
        event = ConnectedEvent()
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        
        assert data["type"] == "connected"
        assert data["v"] == 1
        assert "ts" in data
        assert "api_version" in data["payload"]
    
    def test_heartbeat_event_serialization(self):
        """Test HeartbeatEvent serializes correctly"""
        event = HeartbeatEvent(seq=42, device_id="r58-001")
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        
        assert data["type"] == "heartbeat"
        assert data["seq"] == 42
        assert data["device_id"] == "r58-001"
    
    def test_recording_progress_serialization(self):
        """Test RecordingProgressEvent serializes correctly"""
        event = RecordingProgressEvent.create(
            session_id="test-123",
            duration_ms=5000,
            bytes_written={"cam1": 1024, "cam2": 2048},
            device_id="r58-001",
            seq=10
        )
        
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        
        assert data["type"] == "recorder.progress"
        assert data["payload"]["duration_ms"] == 5000
        assert data["payload"]["bytes_written"]["cam1"] == 1024
    
    def test_input_signal_serialization(self):
        """Test InputSignalEvent serializes correctly"""
        event = InputSignalEvent.create(
            input_id="cam1",
            has_signal=True,
            resolution="1920x1080",
            framerate=30,
            device_id="r58-001",
            seq=5
        )
        
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        
        assert data["type"] == "input.signal_changed"
        assert data["payload"]["input_id"] == "cam1"
        assert data["payload"]["has_signal"] is True


class TestEventCreation:
    """Tests for event factory methods"""
    
    def test_recording_progress_with_multiple_inputs(self):
        """Test RecordingProgressEvent with multiple inputs"""
        bytes_written = {
            "cam1": 1000000,
            "cam2": 2000000,
            "cam3": 1500000,
            "cam4": 1800000
        }
        
        event = RecordingProgressEvent.create(
            session_id="multi-input-session",
            duration_ms=60000,
            bytes_written=bytes_written,
            device_id="r58-001",
            seq=100
        )
        
        assert len(event.payload["bytes_written"]) == 4
        assert event.payload["duration_ms"] == 60000
    
    def test_input_signal_loss_event(self):
        """Test InputSignalEvent for signal loss (no resolution/framerate)"""
        event = InputSignalEvent.create(
            input_id="cam2",
            has_signal=False,
            device_id="r58-001",
            seq=15
        )
        
        assert event.payload["has_signal"] is False
        assert event.payload["resolution"] is None
        assert event.payload["framerate"] is None
    
    def test_event_sequence_numbers_increment(self):
        """Test that sequence numbers are properly tracked"""
        events = []
        for i in range(5):
            event = HeartbeatEvent(seq=i, device_id="r58-001")
            events.append(event)
        
        for i, event in enumerate(events):
            assert event.seq == i


class TestEventTypeEnum:
    """Tests for EventType enum"""
    
    def test_all_event_types_are_strings(self):
        """Test all EventType values are strings"""
        for event_type in EventType:
            assert isinstance(event_type.value, str)
    
    def test_recorder_event_types(self):
        """Test recorder-related event types"""
        assert EventType.RECORDING_STARTED.value == "recorder.started"
        assert EventType.RECORDING_STOPPED.value == "recorder.stopped"
        assert EventType.RECORDING_PROGRESS.value == "recorder.progress"
    
    def test_mixer_event_types(self):
        """Test mixer-related event types"""
        assert EventType.SCENE_CHANGED.value == "mixer.scene_changed"
        assert EventType.SOURCE_UPDATED.value == "mixer.source_updated"
    
    def test_input_event_types(self):
        """Test input-related event types"""
        assert EventType.INPUT_SIGNAL_CHANGED.value == "input.signal_changed"
        assert EventType.INPUT_ERROR.value == "input.error"
    
    def test_system_event_types(self):
        """Test system event types"""
        assert EventType.CONNECTED.value == "connected"
        assert EventType.HEARTBEAT.value == "heartbeat"
        assert EventType.ERROR.value == "error"
        assert EventType.HEALTH_CHANGED.value == "health.changed"
        assert EventType.STORAGE_WARNING.value == "storage.warning"


class TestBaseEvent:
    """Tests for BaseEvent base class"""
    
    def test_base_event_defaults(self):
        """Test BaseEvent has sensible defaults"""
        event = BaseEvent(type=EventType.HEARTBEAT)
        
        assert event.v == 1
        assert event.seq == 0
        assert event.device_id == ""
        assert event.payload is None
        assert isinstance(event.ts, datetime)
    
    def test_base_event_with_payload(self):
        """Test BaseEvent with custom payload"""
        event = BaseEvent(
            type=EventType.ERROR,
            payload={"message": "Something went wrong", "code": 500}
        )
        
        assert event.payload["message"] == "Something went wrong"
        assert event.payload["code"] == 500
    
    def test_base_event_timestamp_is_recent(self):
        """Test BaseEvent timestamp is close to now"""
        before = datetime.now()
        event = BaseEvent(type=EventType.HEARTBEAT)
        after = datetime.now()
        
        assert before <= event.ts <= after


class TestMalformedEvents:
    """Tests for handling malformed event data"""
    
    def test_parse_valid_event_json(self):
        """Test parsing valid event JSON"""
        json_data = {
            "v": 1,
            "type": "heartbeat",
            "ts": datetime.now().isoformat(),
            "seq": 10,
            "device_id": "r58-001",
            "payload": None
        }
        
        event = BaseEvent.model_validate(json_data)
        assert event.type == EventType.HEARTBEAT
        assert event.seq == 10
    
    def test_parse_event_with_extra_fields(self):
        """Test parsing event with extra fields (should be ignored)"""
        json_data = {
            "v": 1,
            "type": "heartbeat",
            "ts": datetime.now().isoformat(),
            "seq": 10,
            "device_id": "r58-001",
            "payload": None,
            "extra_field": "should be ignored"
        }
        
        # Should not raise, extra fields are ignored
        event = BaseEvent.model_validate(json_data)
        assert event.type == EventType.HEARTBEAT
    
    def test_parse_event_missing_required_fields(self):
        """Test parsing event with missing required fields raises error"""
        json_data = {
            "v": 1,
            # Missing "type" field
            "ts": datetime.now().isoformat(),
        }
        
        with pytest.raises(Exception):
            BaseEvent.model_validate(json_data)

