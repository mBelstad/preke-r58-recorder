"""
Test Pydantic models serialize/deserialize correctly
Priority: P0
"""
import pytest
from datetime import datetime
import json

from r58_api.models.session import (
    RecordingSession,
    RecordingSessionBase,
    RecordingSessionCreate,
    Recording,
    RecordingBase,
)
from r58_api.control.devices.capabilities import (
    DeviceCapabilities,
    InputCapability,
    CodecCapability,
    PreviewMode,
    VdoNinjaCapability,
)
from r58_api.realtime.events import (
    EventType,
    BaseEvent,
    ConnectedEvent,
    HeartbeatEvent,
    RecordingProgressEvent,
    InputSignalEvent,
)


class TestRecordingModels:
    """Tests for recording session models"""
    
    def test_recording_session_base_defaults(self):
        """Test RecordingSessionBase has correct defaults"""
        session = RecordingSessionBase(started_at=datetime.now())
        
        assert session.name is None
        assert session.ended_at is None
        assert session.status == "recording"
        assert session.total_bytes == 0
    
    def test_recording_session_create_minimal(self):
        """Test RecordingSessionCreate with minimal data"""
        create = RecordingSessionCreate()
        
        assert create.name is None
        assert create.inputs is None
    
    def test_recording_session_create_with_data(self):
        """Test RecordingSessionCreate with all fields"""
        create = RecordingSessionCreate(
            name="Test Session",
            inputs=["cam1", "cam2", "cam3"]
        )
        
        assert create.name == "Test Session"
        assert create.inputs == ["cam1", "cam2", "cam3"]
    
    def test_recording_base_defaults(self):
        """Test RecordingBase has correct defaults"""
        recording = RecordingBase(
            input_id="cam1",
            file_path="/opt/r58/recordings/test.mp4"
        )
        
        assert recording.input_id == "cam1"
        assert recording.duration_ms == 0
        assert recording.bytes == 0
        assert recording.codec == "h264"
        assert recording.resolution == "1920x1080"
    
    def test_recording_base_custom_values(self):
        """Test RecordingBase with custom values"""
        recording = RecordingBase(
            input_id="cam2",
            file_path="/opt/r58/recordings/cam2.mp4",
            duration_ms=60000,
            bytes=1024000,
            codec="h265",
            resolution="3840x2160"
        )
        
        assert recording.codec == "h265"
        assert recording.resolution == "3840x2160"
        assert recording.duration_ms == 60000


class TestCapabilityModels:
    """Tests for capability models"""
    
    def test_input_capability_serialization(self):
        """Test InputCapability serializes correctly"""
        input_cap = InputCapability(
            id="cam1",
            type="hdmi",
            label="HDMI 1",
            max_resolution="1920x1080",
            supports_audio=True,
            device_path="/dev/video0"
        )
        
        data = input_cap.model_dump()
        assert data["id"] == "cam1"
        assert data["type"] == "hdmi"
        assert data["supports_audio"] is True
        
        # Verify JSON roundtrip
        json_str = input_cap.model_dump_json()
        restored = InputCapability.model_validate_json(json_str)
        assert restored.id == input_cap.id
    
    def test_input_capability_optional_device_path(self):
        """Test InputCapability with no device_path"""
        input_cap = InputCapability(
            id="network1",
            type="network",
            label="Network Stream",
            max_resolution="1920x1080",
            supports_audio=True
        )
        
        assert input_cap.device_path is None
    
    def test_codec_capability_model(self):
        """Test CodecCapability model"""
        codec = CodecCapability(
            id="h264_hw",
            name="H.264 (Hardware)",
            hardware_accelerated=True,
            max_bitrate_kbps=20000
        )
        
        assert codec.hardware_accelerated is True
        assert codec.max_bitrate_kbps == 20000
    
    def test_preview_mode_model(self):
        """Test PreviewMode model"""
        preview = PreviewMode(
            id="whep",
            protocol="whep",
            latency_ms=100,
            url_template="http://localhost:8889/{input_id}/whep"
        )
        
        assert preview.protocol == "whep"
        assert preview.latency_ms == 100
    
    def test_vdoninja_capability_model(self):
        """Test VdoNinjaCapability model"""
        vdo = VdoNinjaCapability(
            enabled=True,
            host="localhost",
            port=8443,
            room="studio"
        )
        
        assert vdo.enabled is True
        assert vdo.port == 8443
    
    def test_device_capabilities_full(self):
        """Test full DeviceCapabilities model"""
        capabilities = DeviceCapabilities(
            device_id="r58-001",
            device_name="R58 Recorder",
            platform="r58",
            api_version="2.0.0",
            mixer_available=True,
            recorder_available=True,
            graphics_available=True,
            fleet_agent_connected=False,
            inputs=[
                InputCapability(
                    id="cam1",
                    type="hdmi",
                    label="HDMI 1",
                    max_resolution="1920x1080",
                    supports_audio=True
                )
            ],
            codecs=[
                CodecCapability(
                    id="h264_hw",
                    name="H.264",
                    hardware_accelerated=True,
                    max_bitrate_kbps=20000
                )
            ],
            preview_modes=[
                PreviewMode(
                    id="whep",
                    protocol="whep",
                    latency_ms=100,
                    url_template="http://localhost:8889/{input_id}/whep"
                )
            ],
            vdoninja=VdoNinjaCapability(
                enabled=True,
                host="localhost",
                port=8443,
                room="studio"
            ),
            mediamtx_base_url="http://localhost:8889",
            max_simultaneous_recordings=4,
            max_output_resolution="1920x1080",
            storage_total_gb=100.0,
            storage_available_gb=50.0
        )
        
        # Verify serialization
        data = capabilities.model_dump()
        assert len(data["inputs"]) == 1
        assert len(data["codecs"]) == 1
        assert data["vdoninja"]["enabled"] is True
        
        # Verify JSON roundtrip
        json_str = capabilities.model_dump_json()
        restored = DeviceCapabilities.model_validate_json(json_str)
        assert restored.device_id == capabilities.device_id


class TestEventModels:
    """Tests for WebSocket event models"""
    
    def test_event_type_enum(self):
        """Test EventType enum values"""
        assert EventType.CONNECTED == "connected"
        assert EventType.RECORDING_STARTED == "recorder.started"
        assert EventType.INPUT_SIGNAL_CHANGED == "input.signal_changed"
    
    def test_base_event_defaults(self):
        """Test BaseEvent has correct defaults"""
        event = BaseEvent(type=EventType.HEARTBEAT)
        
        assert event.v == 1
        assert event.seq == 0
        assert event.device_id == ""
        assert event.payload is None
        assert event.ts is not None
    
    def test_connected_event(self):
        """Test ConnectedEvent structure"""
        event = ConnectedEvent()
        
        assert event.type == EventType.CONNECTED
        assert event.payload["api_version"] == "2.0.0"
        assert "message" in event.payload
    
    def test_heartbeat_event(self):
        """Test HeartbeatEvent structure"""
        event = HeartbeatEvent()
        
        assert event.type == EventType.HEARTBEAT
    
    def test_recording_progress_event_create(self):
        """Test RecordingProgressEvent factory method"""
        event = RecordingProgressEvent.create(
            session_id="test-123",
            duration_ms=5000,
            bytes_written={"cam1": 1024, "cam2": 2048},
            device_id="r58-001",
            seq=42
        )
        
        assert event.type == EventType.RECORDING_PROGRESS
        assert event.seq == 42
        assert event.device_id == "r58-001"
        assert event.payload["session_id"] == "test-123"
        assert event.payload["duration_ms"] == 5000
        assert event.payload["bytes_written"]["cam1"] == 1024
    
    def test_input_signal_event_create(self):
        """Test InputSignalEvent factory method"""
        event = InputSignalEvent.create(
            input_id="cam1",
            has_signal=True,
            resolution="1920x1080",
            framerate=30,
            device_id="r58-001",
            seq=10
        )
        
        assert event.type == EventType.INPUT_SIGNAL_CHANGED
        assert event.payload["input_id"] == "cam1"
        assert event.payload["has_signal"] is True
        assert event.payload["resolution"] == "1920x1080"
        assert event.payload["framerate"] == 30
    
    def test_input_signal_event_no_signal(self):
        """Test InputSignalEvent for signal loss"""
        event = InputSignalEvent.create(
            input_id="cam2",
            has_signal=False,
            device_id="r58-001",
            seq=11
        )
        
        assert event.payload["has_signal"] is False
        assert event.payload["resolution"] is None
        assert event.payload["framerate"] is None
    
    def test_event_serialization(self):
        """Test event JSON serialization"""
        event = RecordingProgressEvent.create(
            session_id="test-456",
            duration_ms=10000,
            bytes_written={"cam1": 5000},
            device_id="r58-001",
            seq=100
        )
        
        json_str = event.model_dump_json()
        data = json.loads(json_str)
        
        assert data["type"] == "recorder.progress"
        assert data["v"] == 1
        assert data["seq"] == 100

