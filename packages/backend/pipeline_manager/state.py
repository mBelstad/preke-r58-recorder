"""Pipeline state persistence"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel

STATE_FILE = Path("/var/lib/r58/pipeline_state.json")


class RecordingState(BaseModel):
    """Active recording state"""
    session_id: str
    started_at: datetime
    inputs: Dict[str, str]  # input_id -> file_path
    bytes_written: Dict[str, int]  # input_id -> bytes


class PipelineState(BaseModel):
    """Complete pipeline state"""
    current_mode: str = "idle"  # "idle", "recording", "mixing"
    active_recording: Optional[RecordingState] = None
    last_error: Optional[str] = None

    def save(self):
        """Persist state to disk"""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(self.model_dump_json(indent=2))
        print(f"[Pipeline State] Saved to {STATE_FILE}")

    @classmethod
    def load(cls) -> "PipelineState":
        """Load state from disk or create new"""
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                return cls.model_validate(data)
            except Exception as e:
                print(f"[Pipeline State] Failed to load: {e}")
        return cls()

    def start_recording(self, session_id: str, inputs: Dict[str, str]) -> None:
        """Start a new recording session"""
        self.current_mode = "recording"
        self.active_recording = RecordingState(
            session_id=session_id,
            started_at=datetime.now(timezone.utc),
            inputs=inputs,
            bytes_written={input_id: 0 for input_id in inputs},
        )
        self.last_error = None
        self.save()

    def stop_recording(self) -> Optional[RecordingState]:
        """Stop current recording and return final state"""
        recording = self.active_recording
        self.current_mode = "idle"
        self.active_recording = None
        self.save()
        return recording

    def update_bytes(self, input_id: str, bytes_written: int) -> None:
        """Update bytes written for an input"""
        if self.active_recording and input_id in self.active_recording.bytes_written:
            self.active_recording.bytes_written[input_id] = bytes_written

    def set_error(self, error: str) -> None:
        """Record an error"""
        self.last_error = error
        self.save()

