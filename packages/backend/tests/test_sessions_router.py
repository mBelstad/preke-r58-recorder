"""
Test recorder API endpoints
Priority: P0 - Customer-facing API
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime


class TestRecorderStatus:
    """Tests for GET /api/v1/recorder/status"""
    
    def test_status_when_idle(self, client, mock_pipeline_client):
        """Test status returns idle when not recording"""
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={"recording": False}
        )
        
        response = client.get("/api/v1/recorder/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["session_id"] is None
        assert data["duration_ms"] == 0
        assert data["inputs"] == []
    
    def test_status_while_recording(self, client, mock_pipeline_client):
        """Test status returns recording details when active"""
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={
                "recording": True,
                "session_id": "active-session-123",
                "duration_ms": 5000,
                "bytes_written": {"cam1": 1024, "cam2": 2048}
            }
        )
        
        response = client.get("/api/v1/recorder/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recording"
        assert data["session_id"] == "active-session-123"
        assert data["duration_ms"] == 5000
        assert "cam1" in data["inputs"]
        assert "cam2" in data["inputs"]
    
    def test_status_handles_pipeline_error(self, client, mock_pipeline_client):
        """Test status returns idle when pipeline reports error"""
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={"error": "Pipeline not connected"}
        )
        
        response = client.get("/api/v1/recorder/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"


class TestStartRecording:
    """Tests for POST /api/v1/recorder/start"""
    
    def test_start_recording_success(self, client, mock_pipeline_client):
        """Test successful recording start"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "new-session-001",
                "inputs": {"cam1": "/tmp/cam1.mp4", "cam2": "/tmp/cam2.mp4"},
                "status": "started"
            }
        )
        
        response = client.post(
            "/api/v1/recorder/start",
            json={"name": "Test Recording", "inputs": ["cam1", "cam2"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "new-session-001"
        assert data["status"] == "recording"
        assert "cam1" in data["inputs"]
        assert "cam2" in data["inputs"]
    
    def test_start_recording_minimal_request(self, client, mock_pipeline_client):
        """Test starting recording with minimal request (no name, default inputs)"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "default-session",
                "inputs": {"cam1": "/tmp/cam1.mp4"},
                "status": "started"
            }
        )
        
        response = client.post("/api/v1/recorder/start", json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "default-session"
        assert data["name"] is None
    
    def test_start_recording_already_recording(self, client, mock_pipeline_client):
        """Test starting recording when already recording returns 400"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={"error": "Already recording"}
        )
        
        response = client.post("/api/v1/recorder/start", json={})
        
        assert response.status_code == 400
        assert "Already recording" in response.json()["detail"]
    
    def test_start_recording_no_inputs_available(self, client, mock_pipeline_client):
        """Test starting recording with no inputs connected"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={"error": "No inputs available"}
        )
        
        response = client.post("/api/v1/recorder/start", json={"inputs": []})
        
        assert response.status_code == 400
    
    def test_start_recording_specific_inputs(self, client, mock_pipeline_client):
        """Test starting recording with specific input selection"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "single-input",
                "inputs": {"cam2": "/tmp/cam2.mp4"},
                "status": "started"
            }
        )
        
        response = client.post(
            "/api/v1/recorder/start",
            json={"inputs": ["cam2"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["inputs"]) == 1
        assert "cam2" in data["inputs"]


class TestStopRecording:
    """Tests for POST /api/v1/recorder/stop"""
    
    def test_stop_recording_success(self, client, mock_pipeline_client):
        """Test successful recording stop"""
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={
                "session_id": "stopped-session",
                "duration_ms": 60000,
                "files": {"cam1": "/tmp/cam1.mp4"},
                "status": "stopped"
            }
        )
        
        response = client.post("/api/v1/recorder/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "stopped-session"
        assert data["duration_ms"] == 60000
        assert data["status"] == "stopped"
        assert "cam1" in data["files"]
    
    def test_stop_recording_not_recording(self, client, mock_pipeline_client):
        """Test stopping when not recording returns 400"""
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={"error": "Not recording"}
        )
        
        response = client.post("/api/v1/recorder/stop")
        
        assert response.status_code == 400
        assert "Not recording" in response.json()["detail"]
    
    def test_stop_recording_with_session_id(self, client, mock_pipeline_client):
        """Test stopping recording with specific session_id"""
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={
                "session_id": "specific-session",
                "duration_ms": 30000,
                "files": {},
                "status": "stopped"
            }
        )
        
        response = client.post("/api/v1/recorder/stop?session_id=specific-session")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "specific-session"
    
    def test_stop_recording_wrong_session_id(self, client, mock_pipeline_client):
        """Test stopping with wrong session_id returns 400"""
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={"error": "Session ID mismatch"}
        )
        
        response = client.post("/api/v1/recorder/stop?session_id=wrong-session")
        
        assert response.status_code == 400


class TestSessionList:
    """Tests for GET /api/v1/recorder/sessions"""
    
    def test_list_sessions_empty(self, client):
        """Test listing sessions when none exist"""
        response = client.get("/api/v1/recorder/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
    
    def test_list_sessions_with_pagination(self, client):
        """Test listing sessions with pagination parameters"""
        response = client.get("/api/v1/recorder/sessions?limit=10&offset=0")
        
        assert response.status_code == 200


class TestSessionDetail:
    """Tests for GET /api/v1/recorder/sessions/{session_id}"""
    
    def test_get_session_not_found(self, client):
        """Test getting non-existent session returns 404"""
        response = client.get("/api/v1/recorder/sessions/nonexistent-session")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRecorderConcurrency:
    """Tests for concurrent recording operations"""
    
    def test_double_start_request(self, client, mock_pipeline_client):
        """Test two simultaneous start requests - second should fail"""
        # First request succeeds
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "first-session",
                "inputs": {"cam1": "/tmp/cam1.mp4"},
                "status": "started"
            }
        )
        
        response1 = client.post("/api/v1/recorder/start", json={})
        assert response1.status_code == 200
        
        # Second request fails (already recording)
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={"error": "Already recording"}
        )
        
        response2 = client.post("/api/v1/recorder/start", json={})
        assert response2.status_code == 400
    
    def test_stop_during_start(self, client, mock_pipeline_client):
        """Test stop request during start returns appropriate error"""
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={"error": "Recording is starting"}
        )
        
        response = client.post("/api/v1/recorder/stop")
        
        assert response.status_code == 400


class TestRecorderInputValidation:
    """Tests for request validation"""
    
    def test_start_with_invalid_json(self, client):
        """Test starting with invalid JSON returns 422"""
        response = client.post(
            "/api/v1/recorder/start",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_start_with_invalid_input_type(self, client):
        """Test starting with invalid inputs type returns 422"""
        response = client.post(
            "/api/v1/recorder/start",
            json={"inputs": "cam1"}  # Should be list, not string
        )
        
        assert response.status_code == 422

