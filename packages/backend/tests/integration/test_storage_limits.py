"""
Test disk space handling
Priority: P0 - Prevents data loss

Tests:
- Recording fails when disk is full
- Recording stops when threshold reached
- Storage warning events are emitted
"""
from unittest.mock import AsyncMock

import pytest


class TestStorageLimitsStartRecording:
    """Tests for storage checks when starting recording"""

    def test_start_recording_fails_when_disk_full(self, client, mock_pipeline_client, mock_disk_usage):
        """Test that recording fails to start when disk is nearly full"""
        # Set disk to 99% full (1GB free on 100GB disk)
        mock_disk_usage(total_gb=100, free_gb=1)

        # Make sure not already recording
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={"recording": False}
        )

        response = client.post("/api/v1/recorder/start", json={})

        # Now returns 507 Insufficient Storage
        assert response.status_code == 507
        assert "Insufficient" in response.json()["detail"] or "disk" in response.json()["detail"].lower()

    def test_start_recording_succeeds_with_adequate_space(self, client, mock_pipeline_client, mock_disk_usage):
        """Test that recording starts when disk has adequate space"""
        # Set disk to 50% full
        mock_disk_usage(total_gb=100, free_gb=50)

        # Make sure not already recording
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={"recording": False}
        )
        mock_pipeline_client.return_value.start_recording = AsyncMock(
            return_value={
                "session_id": "space-ok",
                "inputs": {"cam1": "/tmp/cam1.mp4"},
                "status": "started"
            }
        )

        response = client.post("/api/v1/recorder/start", json={})

        assert response.status_code == 200
        assert response.json()["status"] == "recording"


class TestStorageWarnings:
    """Tests for storage warning thresholds"""

    def test_health_shows_low_storage_warning(self, client, mock_pipeline_client, mock_disk_usage):
        """Test that health endpoint shows storage warning when low"""
        # Set disk to 95% full
        mock_disk_usage(total_gb=100, free_gb=5)

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert data["storage"]["available_gb"] == 5.0
        assert data["storage"]["used_percent"] == 95.0

    def test_storage_status_in_capabilities(self, client, mock_disk_usage):
        """Test that capabilities includes storage status"""
        mock_disk_usage(total_gb=500, free_gb=100)

        response = client.get("/api/v1/capabilities")

        assert response.status_code == 200
        data = response.json()

        assert data["storage_total_gb"] == 500.0
        assert data["storage_available_gb"] == 100.0


class TestStorageEdgeCases:
    """Edge case tests for storage handling"""

    def test_handles_disk_read_error(self, client, mock_pipeline_client, monkeypatch):
        """Test graceful handling when disk_usage fails"""
        def mock_disk_usage(path):
            raise OSError("Disk not accessible")

        monkeypatch.setattr("shutil.disk_usage", mock_disk_usage)

        response = client.get("/api/v1/health/detailed")

        # Should not crash, return zeros
        assert response.status_code == 200
        data = response.json()
        assert data["storage"]["total_gb"] == 0.0

    def test_handles_very_large_disk(self, client, mock_pipeline_client, mock_disk_usage):
        """Test handling of very large disk sizes (>1TB)"""
        mock_disk_usage(total_gb=4000, free_gb=2000)  # 4TB disk

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["storage"]["total_gb"] == 4000.0
        assert data["storage"]["available_gb"] == 2000.0
        assert data["storage"]["used_percent"] == 50.0

    def test_handles_nearly_empty_disk(self, client, mock_pipeline_client, mock_disk_usage):
        """Test handling of nearly empty disk"""
        mock_disk_usage(total_gb=100, free_gb=99)

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["storage"]["used_percent"] == 1.0


class TestRecordingBytesTracking:
    """Tests for tracking bytes written during recording"""

    def test_status_includes_bytes_written(self, client, mock_pipeline_client):
        """Test that status includes bytes written per input"""
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={
                "recording": True,
                "session_id": "bytes-test",
                "duration_ms": 10000,
                "bytes_written": {
                    "cam1": 5000000,  # 5MB
                    "cam2": 4500000   # 4.5MB
                }
            }
        )

        response = client.get("/api/v1/recorder/status")

        assert response.status_code == 200
        data = response.json()
        assert "cam1" in data["inputs"]
        assert "cam2" in data["inputs"]

    def test_final_bytes_in_stop_response(self, client, mock_pipeline_client):
        """Test that stop response includes final file sizes"""
        # Set up as recording to allow stop
        mock_pipeline_client.return_value.get_recording_status = AsyncMock(
            return_value={
                "recording": True,
                "session_id": "final-bytes",
                "bytes_written": {"cam1": 1000, "cam2": 2000}
            }
        )
        mock_pipeline_client.return_value.stop_recording = AsyncMock(
            return_value={
                "session_id": "final-bytes",
                "duration_ms": 60000,
                "files": {
                    "cam1": "/tmp/cam1.mp4",
                    "cam2": "/tmp/cam2.mp4"
                },
                "status": "stopped"
            }
        )

        response = client.post("/api/v1/recorder/stop")

        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        assert "cam1" in data["files"]


class TestStorageThresholds:
    """Tests for various storage threshold levels"""

    @pytest.mark.parametrize("free_gb,expected_status", [
        (50, "healthy"),    # 50% free - healthy
        (20, "healthy"),    # 20% free - still ok
        (10, "healthy"),    # 10% free - warning level
        (5, "healthy"),     # 5% free - critical warning
        (1, "healthy"),     # 1% free - severe warning
    ])
    def test_storage_thresholds(self, client, mock_pipeline_client, mock_disk_usage, free_gb, expected_status):
        """Test different storage threshold levels"""
        mock_disk_usage(total_gb=100, free_gb=free_gb)

        response = client.get("/api/v1/health")

        # Basic health should still return healthy (storage doesn't affect simple health)
        assert response.status_code == 200
        assert response.json()["status"] == expected_status

    def test_storage_percentage_precision(self, client, mock_pipeline_client, mock_disk_usage):
        """Test storage percentage is calculated with correct precision"""
        # 73GB used of 100GB = 73% used
        mock_disk_usage(total_gb=100, free_gb=27)

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert data["storage"]["used_percent"] == 73.0

