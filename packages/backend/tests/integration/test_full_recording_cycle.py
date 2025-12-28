"""
Test complete recording workflow via API
Priority: P0

Tests the full recording lifecycle:
- Start recording
- Progress updates
- Stop recording
- Verify session created
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, AsyncMock
from pathlib import Path


class TestFullRecordingLifecycle:
    """Integration tests for complete recording workflow"""
    
    def test_start_status_stop_cycle(self, client, mock_pipeline_client):
        """Test complete start -> status -> stop cycle"""
        # 1. Verify initial state is idle
        response = client.get("/api/v1/recorder/status")
        assert response.status_code == 200
        assert response.json()["status"] == "idle"
        
        # 2. Start recording
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "integration-test-001",
                "inputs": {"cam1": "/tmp/cam1.mp4", "cam2": "/tmp/cam2.mp4"},
                "status": "started"
            }
        )
        
        response = client.post(
            "/api/v1/recorder/start",
            json={"name": "Integration Test Session", "inputs": ["cam1", "cam2"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "integration-test-001"
        assert data["status"] == "recording"
        
        # 3. Check status while recording
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={
                "recording": True,
                "session_id": "integration-test-001",
                "duration_ms": 5000,
                "bytes_written": {"cam1": 1000, "cam2": 2000}
            }
        )
        
        response = client.get("/api/v1/recorder/status")
        assert response.status_code == 200
        status = response.json()
        assert status["status"] == "recording"
        assert status["session_id"] == "integration-test-001"
        assert status["duration_ms"] == 5000
        
        # 4. Stop recording
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={
                "session_id": "integration-test-001",
                "duration_ms": 10000,
                "files": {"cam1": "/tmp/cam1.mp4", "cam2": "/tmp/cam2.mp4"},
                "status": "stopped"
            }
        )
        
        response = client.post("/api/v1/recorder/stop")
        assert response.status_code == 200
        stop_data = response.json()
        assert stop_data["session_id"] == "integration-test-001"
        assert stop_data["duration_ms"] == 10000
        assert stop_data["status"] == "stopped"
        
        # 5. Verify final state is idle
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={"recording": False}
        )
        
        response = client.get("/api/v1/recorder/status")
        assert response.status_code == 200
        assert response.json()["status"] == "idle"
    
    def test_start_with_single_input(self, client, mock_pipeline_client):
        """Test recording with single input"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "single-input-test",
                "inputs": {"cam1": "/tmp/cam1.mp4"},
                "status": "started"
            }
        )
        
        response = client.post(
            "/api/v1/recorder/start",
            json={"inputs": ["cam1"]}
        )
        
        assert response.status_code == 200
        assert len(response.json()["inputs"]) == 1
    
    def test_start_with_all_available_inputs(self, client, mock_pipeline_client):
        """Test recording with all available inputs (default)"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "all-inputs-test",
                "inputs": {
                    "cam1": "/tmp/cam1.mp4",
                    "cam2": "/tmp/cam2.mp4"
                },
                "status": "started"
            }
        )
        
        # Empty inputs list should use defaults
        response = client.post("/api/v1/recorder/start", json={})
        
        assert response.status_code == 200
        # Should use configured inputs


class TestRecordingWithPipelineState:
    """Integration tests that verify pipeline state is managed correctly"""
    
    def test_state_persists_across_status_checks(self, client, mock_pipeline_client):
        """Test that state is consistent across multiple status checks"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "persist-test",
                "inputs": {"cam1": "/tmp/cam1.mp4"},
                "status": "started"
            }
        )
        
        # Start recording
        client.post("/api/v1/recorder/start", json={})
        
        # Multiple status checks should return consistent data
        for i in range(3):
            mock_pipeline_client.return_value.get_recording_status = AsyncMock(
                return_value={
                    "recording": True,
                    "session_id": "persist-test",
                    "duration_ms": 1000 * (i + 1),
                    "bytes_written": {"cam1": 1000 * (i + 1)}
                }
            )
            
            response = client.get("/api/v1/recorder/status")
            assert response.status_code == 200
            assert response.json()["session_id"] == "persist-test"


class TestRecordingErrorHandling:
    """Integration tests for error handling during recording"""
    
    def test_handles_pipeline_disconnect(self, client, mock_pipeline_client):
        """Test handling when pipeline manager disconnects"""
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={"error": "Connection refused"}
        )
        
        response = client.get("/api/v1/recorder/status")
        
        # Should return idle, not error to client
        assert response.status_code == 200
        assert response.json()["status"] == "idle"
    
    def test_handles_start_timeout(self, client, mock_pipeline_client):
        """Test handling when start takes too long"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={"error": "Timeout waiting for pipeline"}
        )
        
        response = client.post("/api/v1/recorder/start", json={})
        
        assert response.status_code == 400
    
    def test_handles_stop_while_finalizing(self, client, mock_pipeline_client):
        """Test stopping while file is being finalized"""
        # Set up as recording to allow stop attempt
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={
                "recording": True,
                "session_id": "finalizing-session",
                "bytes_written": {"cam1": 1000}
            }
        )
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={"error": "Finalization in progress, please wait"}
        )
        
        response = client.post("/api/v1/recorder/stop")
        
        assert response.status_code == 400


class TestHealthDuringRecording:
    """Test health checks during recording operations"""
    
    def test_health_check_during_recording(self, client, mock_pipeline_client):
        """Test that health check works during active recording"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "health-test",
                "inputs": {"cam1": "/tmp/cam1.mp4"},
                "status": "started"
            }
        )
        
        # Start recording
        client.post("/api/v1/recorder/start", json={})
        
        # Health check should still work
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Detailed health should also work
        response = client.get("/api/v1/health/detailed")
        assert response.status_code == 200


class TestCapabilitiesDuringRecording:
    """Test capabilities endpoint during recording"""
    
    def test_capabilities_available_during_recording(self, client, mock_pipeline_client):
        """Test that capabilities endpoint works during recording"""
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "caps-test",
                "inputs": {"cam1": "/tmp/cam1.mp4"},
                "status": "started"
            }
        )
        
        # Start recording
        client.post("/api/v1/recorder/start", json={})
        
        # Capabilities should still be available
        response = client.get("/api/v1/capabilities")
        assert response.status_code == 200
        
        data = response.json()
        assert data["recorder_available"] is True

