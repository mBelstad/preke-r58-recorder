"""
R58 Backend Test Fixtures
Shared fixtures for pytest tests
"""
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Generator, AsyncGenerator

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport


# Test environment setup
@pytest.fixture(autouse=True)
def test_env(monkeypatch, tmp_path):
    """Set up test environment variables"""
    monkeypatch.setenv("R58_JWT_SECRET", "test-secret-do-not-use-in-prod")
    monkeypatch.setenv("R58_DEVICE_ID", "test-device-001")
    monkeypatch.setenv("R58_DEBUG", "true")
    monkeypatch.setenv("R58_DB_PATH", str(tmp_path / "r58_test.db"))
    monkeypatch.setenv("R58_MEDIAMTX_API_URL", "http://localhost:9997")
    monkeypatch.setenv("R58_VDONINJA_HOST", "localhost:8443")
    return tmp_path


@pytest.fixture
def settings(test_env):
    """Create test settings instance"""
    from r58_api.config import Settings
    return Settings(
        jwt_secret="test-secret-do-not-use-in-prod",
        device_id="test-device-001",
        db_path=test_env / "r58_test.db",
        debug=True,
    )


@pytest.fixture
def app(settings):
    """Create FastAPI test application"""
    from r58_api.main import create_app
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Synchronous test client"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async test client for async endpoints"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_pipeline_client(monkeypatch):
    """Mock pipeline client for API tests without real IPC"""
    mock_client = Mock()
    mock_client.get_recording_status = AsyncMock(return_value={"recording": False})
    mock_client.start_recording = AsyncMock(return_value={
        "session_id": "test-session-123",
        "inputs": {"cam1": "/tmp/test_cam1.mp4", "cam2": "/tmp/test_cam2.mp4"},
        "status": "started",
    })
    mock_client.stop_recording = AsyncMock(return_value={
        "session_id": "test-session-123",
        "duration_ms": 10000,
        "files": {"cam1": "/tmp/test_cam1.mp4", "cam2": "/tmp/test_cam2.mp4"},
        "status": "stopped",
    })
    mock_client._send_command = AsyncMock(return_value={"mode": "idle"})
    mock_client.is_healthy = True
    mock_client._consecutive_failures = 0
    
    # Create a mock function that returns the client
    mock_get_client = Mock(return_value=mock_client)
    
    # Patch at multiple locations to ensure it works regardless of import order
    monkeypatch.setattr(
        "r58_api.media.pipeline_client.get_pipeline_client",
        mock_get_client
    )
    monkeypatch.setattr(
        "r58_api.observability.health.get_pipeline_client",
        mock_get_client
    )
    monkeypatch.setattr(
        "r58_api.control.sessions.router.get_pipeline_client",
        mock_get_client
    )
    return mock_get_client


@pytest.fixture
def temp_state_dir(tmp_path):
    """Temporary directory for pipeline state tests"""
    state_file = tmp_path / "pipeline_state.json"
    return tmp_path, state_file


@pytest.fixture
def temp_socket_path(tmp_path):
    """Temporary socket path for IPC tests (avoids macOS path length limits)"""
    # macOS has a 104-char limit for Unix socket paths
    # Use a short path in /tmp to avoid issues
    import os
    short_tmp = Path("/tmp/r58test")
    short_tmp.mkdir(exist_ok=True)
    socket_path = short_tmp / f"test_{os.getpid()}.sock"
    yield socket_path
    # Cleanup
    if socket_path.exists():
        socket_path.unlink()


@pytest.fixture
def temp_recordings_dir(tmp_path):
    """Temporary recordings directory for tests"""
    recordings = tmp_path / "recordings"
    recordings.mkdir(exist_ok=True)
    return recordings


@pytest.fixture
def sample_pipeline_state():
    """Sample pipeline state for testing"""
    return {
        "current_mode": "idle",
        "active_recording": None,
        "last_error": None,
    }


@pytest.fixture
def sample_recording_state():
    """Sample active recording state"""
    from datetime import datetime
    return {
        "current_mode": "recording",
        "active_recording": {
            "session_id": "test-session-123",
            "started_at": datetime.now().isoformat(),
            "inputs": {
                "cam1": "/opt/r58/recordings/test_cam1.mp4",
                "cam2": "/opt/r58/recordings/test_cam2.mp4",
            },
            "bytes_written": {
                "cam1": 1024000,
                "cam2": 1024000,
            },
        },
        "last_error": None,
    }


@pytest.fixture
def mock_disk_usage(monkeypatch):
    """Mock disk usage for storage tests"""
    class MockUsage:
        def __init__(self, total, used, free):
            self.total = total
            self.used = used
            self.free = free
    
    def set_disk_space(total_gb=100, free_gb=50):
        total = int(total_gb * 1024**3)
        free = int(free_gb * 1024**3)
        used = total - free
        monkeypatch.setattr(
            "shutil.disk_usage",
            lambda path: MockUsage(total, used, free)
        )
    
    return set_disk_space


@pytest.fixture
def auth_headers():
    """Generate valid JWT auth headers for testing"""
    from datetime import datetime, timedelta
    from jose import jwt
    
    payload = {
        "sub": "test-user",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "role": "admin",
    }
    token = jwt.encode(payload, "test-secret-do-not-use-in-prod", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def websocket_messages():
    """Capture WebSocket messages for testing"""
    messages = []
    
    class MessageCapture:
        def append(self, msg):
            messages.append(msg)
        
        def clear(self):
            messages.clear()
        
        @property
        def all(self):
            return messages.copy()
        
        @property
        def last(self):
            return messages[-1] if messages else None
    
    return MessageCapture()

