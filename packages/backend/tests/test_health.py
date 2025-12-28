"""
Test health check endpoints
Priority: P1
"""
import pytest
from unittest.mock import patch, Mock


class TestHealthCheck:
    """Tests for GET /api/v1/health"""
    
    def test_health_returns_healthy(self, client):
        """Test simple health check returns healthy"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestDetailedHealth:
    """Tests for GET /api/v1/health/detailed"""
    
    def test_detailed_health_includes_services(self, client):
        """Test detailed health includes all service statuses"""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "storage" in data
        assert "uptime_seconds" in data
        
        # Verify services are present
        service_names = [s["name"] for s in data["services"]]
        assert "api" in service_names
        assert "pipeline_manager" in service_names
        assert "mediamtx" in service_names
    
    def test_detailed_health_storage_info(self, client, mock_disk_usage):
        """Test detailed health includes storage information"""
        mock_disk_usage(total_gb=500, free_gb=250)
        
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["storage"]["total_gb"] == 500.0
        assert data["storage"]["available_gb"] == 250.0
        assert data["storage"]["used_percent"] == 50.0
    
    def test_detailed_health_low_storage_warning(self, client, mock_disk_usage):
        """Test detailed health with low storage"""
        mock_disk_usage(total_gb=100, free_gb=5)  # 5% free
        
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["storage"]["available_gb"] == 5.0
        assert data["storage"]["used_percent"] == 95.0
    
    def test_detailed_health_uptime(self, client):
        """Test detailed health includes uptime"""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["uptime_seconds"] >= 0
    
    def test_detailed_health_overall_status_healthy(self, client):
        """Test overall status is healthy when all services are healthy"""
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Default mock returns all healthy
        assert data["status"] == "healthy"


class TestStorageStatus:
    """Tests for storage status calculation"""
    
    def test_storage_handles_disk_error(self, client, monkeypatch):
        """Test storage gracefully handles disk_usage errors"""
        def mock_disk_usage(path):
            raise OSError("Disk not accessible")
        
        monkeypatch.setattr("shutil.disk_usage", mock_disk_usage)
        
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return zeros, not crash
        assert data["storage"]["total_gb"] == 0.0
        assert data["storage"]["available_gb"] == 0.0
        assert data["storage"]["used_percent"] == 0.0
    
    def test_storage_percentage_calculation(self, client, mock_disk_usage):
        """Test storage percentage is calculated correctly"""
        # 100GB total, 25GB free = 75% used
        mock_disk_usage(total_gb=100, free_gb=25)
        
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["storage"]["used_percent"] == 75.0


class TestServiceHealthChecks:
    """Tests for individual service health checks"""
    
    def test_includes_vdoninja_when_enabled(self, client, monkeypatch):
        """Test VDO.ninja service is included when enabled"""
        # Settings has vdoninja_enabled=True by default
        response = client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        service_names = [s["name"] for s in data["services"]]
        assert "vdoninja" in service_names

