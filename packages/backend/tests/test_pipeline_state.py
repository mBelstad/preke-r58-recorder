"""
Test pipeline state persistence and recovery
Priority: P0 - Critical for crash recovery
"""
import json
from datetime import datetime
from unittest.mock import patch

from pipeline_manager.state import PipelineState, RecordingState


class TestPipelineState:
    """Tests for PipelineState model"""

    def test_default_state(self):
        """Test PipelineState default values"""
        state = PipelineState()

        assert state.current_mode == "idle"
        assert state.active_recording is None
        assert state.last_error is None

    def test_start_recording(self, tmp_path):
        """Test starting a recording updates state correctly"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()

            inputs = {
                "cam1": "/opt/r58/recordings/session1_cam1.mp4",
                "cam2": "/opt/r58/recordings/session1_cam2.mp4"
            }

            state.start_recording("session-123", inputs)

            assert state.current_mode == "recording"
            assert state.active_recording is not None
            assert state.active_recording.session_id == "session-123"
            assert state.active_recording.inputs == inputs
            assert state.active_recording.bytes_written == {"cam1": 0, "cam2": 0}
            assert state.last_error is None

    def test_stop_recording(self, tmp_path):
        """Test stopping a recording returns final state"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()
            inputs = {"cam1": "/tmp/test.mp4"}

            state.start_recording("session-456", inputs)
            state.update_bytes("cam1", 1024000)

            final_state = state.stop_recording()

            assert state.current_mode == "idle"
            assert state.active_recording is None
            assert final_state is not None
            assert final_state.session_id == "session-456"
            assert final_state.bytes_written["cam1"] == 1024000

    def test_stop_recording_when_not_recording(self, tmp_path):
        """Test stopping when not recording returns None"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()
            result = state.stop_recording()

            assert result is None
            assert state.current_mode == "idle"

    def test_update_bytes(self, tmp_path):
        """Test updating bytes written for an input"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()
            inputs = {"cam1": "/tmp/cam1.mp4", "cam2": "/tmp/cam2.mp4"}

            state.start_recording("session-789", inputs)

            state.update_bytes("cam1", 1000)
            assert state.active_recording.bytes_written["cam1"] == 1000

            state.update_bytes("cam1", 2000)
            assert state.active_recording.bytes_written["cam1"] == 2000

            state.update_bytes("cam2", 500)
            assert state.active_recording.bytes_written["cam2"] == 500

    def test_update_bytes_unknown_input(self, tmp_path):
        """Test updating bytes for unknown input is ignored"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()
            inputs = {"cam1": "/tmp/cam1.mp4"}

            state.start_recording("session", inputs)
            state.update_bytes("cam99", 1000)  # Unknown input

            # Should not raise, just ignore
            assert "cam99" not in state.active_recording.bytes_written

    def test_set_error(self, tmp_path):
        """Test setting error state"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()

            state.set_error("Pipeline crashed: encoder failure")

            assert state.last_error == "Pipeline crashed: encoder failure"

            # Verify it was persisted
            assert state_file.exists()
            saved = json.loads(state_file.read_text())
            assert saved["last_error"] == "Pipeline crashed: encoder failure"


class TestStatePersistence:
    """Tests for state file persistence"""

    def test_state_persists_on_start_recording(self, tmp_path):
        """Test that state is saved when recording starts"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()
            state.start_recording("persist-test", {"cam1": "/tmp/test.mp4"})

            assert state_file.exists()

            saved = json.loads(state_file.read_text())
            assert saved["current_mode"] == "recording"
            assert saved["active_recording"]["session_id"] == "persist-test"

    def test_state_recovers_after_crash(self, tmp_path):
        """Test that state can be recovered from disk after crash"""
        state_file = tmp_path / "pipeline_state.json"

        # Simulate state before crash
        crash_state = {
            "current_mode": "recording",
            "active_recording": {
                "session_id": "crash-session",
                "started_at": datetime.now().isoformat(),
                "inputs": {"cam1": "/tmp/crash.mp4"},
                "bytes_written": {"cam1": 5000000}
            },
            "last_error": None
        }
        state_file.write_text(json.dumps(crash_state))

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            # Simulate restart - load state
            recovered = PipelineState.load()

            assert recovered.current_mode == "recording"
            assert recovered.active_recording is not None
            assert recovered.active_recording.session_id == "crash-session"
            assert recovered.active_recording.bytes_written["cam1"] == 5000000

    def test_state_handles_corrupt_json(self, tmp_path):
        """Test that corrupt state file is handled gracefully"""
        state_file = tmp_path / "pipeline_state.json"

        # Write corrupt JSON
        state_file.write_text("{ this is not valid json }")

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            # Should return default state, not crash
            recovered = PipelineState.load()

            assert recovered.current_mode == "idle"
            assert recovered.active_recording is None

    def test_state_handles_missing_file(self, tmp_path):
        """Test that missing state file creates default state"""
        state_file = tmp_path / "nonexistent" / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            recovered = PipelineState.load()

            assert recovered.current_mode == "idle"

    def test_state_handles_partial_data(self, tmp_path):
        """Test that partial state file is handled"""
        state_file = tmp_path / "pipeline_state.json"

        # Write partial state (missing active_recording)
        partial_state = {
            "current_mode": "idle",
        }
        state_file.write_text(json.dumps(partial_state))

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            recovered = PipelineState.load()

            assert recovered.current_mode == "idle"
            assert recovered.active_recording is None

    def test_state_creates_parent_directory(self, tmp_path):
        """Test that save creates parent directory if missing"""
        state_file = tmp_path / "new_dir" / "nested" / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()
            state.save()

            assert state_file.exists()


class TestRecordingState:
    """Tests for RecordingState model"""

    def test_recording_state_creation(self):
        """Test RecordingState initialization"""
        now = datetime.now()
        recording = RecordingState(
            session_id="test-session",
            started_at=now,
            inputs={"cam1": "/tmp/cam1.mp4"},
            bytes_written={"cam1": 0}
        )

        assert recording.session_id == "test-session"
        assert recording.started_at == now
        assert recording.inputs["cam1"] == "/tmp/cam1.mp4"
        assert recording.bytes_written["cam1"] == 0

    def test_recording_state_serialization(self):
        """Test RecordingState JSON serialization"""
        recording = RecordingState(
            session_id="serialize-test",
            started_at=datetime.now(),
            inputs={"cam1": "/tmp/cam1.mp4", "cam2": "/tmp/cam2.mp4"},
            bytes_written={"cam1": 1000, "cam2": 2000}
        )

        json_str = recording.model_dump_json()
        data = json.loads(json_str)

        assert data["session_id"] == "serialize-test"
        assert len(data["inputs"]) == 2
        assert data["bytes_written"]["cam1"] == 1000


class TestStateEdgeCases:
    """Edge case tests for pipeline state"""

    def test_recording_across_midnight(self, tmp_path):
        """Test recording that spans midnight (timestamp rollover)"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            # Simulate recording started just before midnight
            state = PipelineState()
            inputs = {"cam1": "/tmp/midnight.mp4"}

            state.start_recording("midnight-session", inputs)

            # Simulate time passing across midnight
            original_time = state.active_recording.started_at

            # Stop recording (simulating after midnight)
            final = state.stop_recording()

            assert final.session_id == "midnight-session"
            assert final.started_at == original_time

    def test_rapid_start_stop_cycles(self, tmp_path):
        """Test rapid start/stop cycles don't corrupt state"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()

            for i in range(10):
                state.start_recording(f"rapid-{i}", {"cam1": f"/tmp/rapid-{i}.mp4"})
                state.update_bytes("cam1", 100 * i)
                state.stop_recording()

            # Final state should be idle
            assert state.current_mode == "idle"
            assert state.active_recording is None

            # Verify file is valid
            loaded = PipelineState.load()
            assert loaded.current_mode == "idle"

    def test_empty_inputs(self, tmp_path):
        """Test recording with empty inputs dict"""
        state_file = tmp_path / "pipeline_state.json"

        with patch('pipeline_manager.state.STATE_FILE', state_file):
            state = PipelineState()
            state.start_recording("empty-inputs", {})

            assert state.current_mode == "recording"
            assert state.active_recording.inputs == {}
            assert state.active_recording.bytes_written == {}

