"""
Test IPC server commands
Priority: P1
"""
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock
from datetime import datetime

from pipeline_manager.ipc import IPCServer, SOCKET_PATH
from pipeline_manager.state import PipelineState


class TestIPCServer:
    """Tests for IPC server initialization"""
    
    @pytest.mark.asyncio
    async def test_ipc_server_creates_socket(self, tmp_path):
        """Test IPC server creates socket file"""
        socket_path = tmp_path / "test.sock"
        
        with patch('pipeline_manager.ipc.SOCKET_PATH', socket_path):
            state = PipelineState()
            server = IPCServer(state)
            
            await server.start()
            
            assert socket_path.exists()
            
            server.stop()
    
    @pytest.mark.asyncio
    async def test_ipc_server_removes_existing_socket(self, tmp_path):
        """Test IPC server removes existing socket file on start"""
        socket_path = tmp_path / "existing.sock"
        socket_path.touch()  # Create existing file
        
        with patch('pipeline_manager.ipc.SOCKET_PATH', socket_path):
            state = PipelineState()
            server = IPCServer(state)
            
            await server.start()
            
            # Socket should still exist (recreated)
            assert socket_path.exists()
            
            server.stop()
    
    @pytest.mark.asyncio
    async def test_ipc_server_stop_removes_socket(self, tmp_path):
        """Test IPC server removes socket on stop"""
        socket_path = tmp_path / "cleanup.sock"
        
        with patch('pipeline_manager.ipc.SOCKET_PATH', socket_path):
            state = PipelineState()
            server = IPCServer(state)
            
            await server.start()
            assert socket_path.exists()
            
            server.stop()
            assert not socket_path.exists()


class TestIPCCommands:
    """Tests for IPC command handling"""
    
    @pytest.fixture
    def ipc_server(self, tmp_path):
        """Create IPC server with test state"""
        state_file = tmp_path / "state.json"
        socket_path = tmp_path / "ipc.sock"
        
        with patch('pipeline_manager.state.STATE_FILE', state_file), \
             patch('pipeline_manager.ipc.SOCKET_PATH', socket_path):
            state = PipelineState()
            server = IPCServer(state)
            yield server, state
    
    @pytest.mark.asyncio
    async def test_status_command_idle(self, ipc_server):
        """Test status command when idle"""
        server, state = ipc_server
        
        result = await server.handle_command({"cmd": "status"})
        
        assert result["mode"] == "idle"
        assert result["recording"] is None
        assert result["last_error"] is None
    
    @pytest.mark.asyncio
    async def test_status_command_recording(self, ipc_server):
        """Test status command when recording"""
        server, state = ipc_server
        
        # Start recording first
        state.start_recording("test-session", {"cam1": "/tmp/test.mp4"})
        
        result = await server.handle_command({"cmd": "status"})
        
        assert result["mode"] == "recording"
        assert result["recording"] is not None
        assert result["recording"]["session_id"] == "test-session"
    
    @pytest.mark.asyncio
    async def test_start_recording_command(self, ipc_server):
        """Test recording.start command"""
        server, state = ipc_server
        
        result = await server.handle_command({
            "cmd": "recording.start",
            "session_id": "new-session",
            "inputs": ["cam1", "cam2"]
        })
        
        assert result["status"] == "started"
        assert result["session_id"] == "new-session"
        assert "cam1" in result["inputs"]
        assert "cam2" in result["inputs"]
        
        # Verify state was updated
        assert state.current_mode == "recording"
    
    @pytest.mark.asyncio
    async def test_start_recording_generates_session_id(self, ipc_server):
        """Test recording.start generates session_id if not provided"""
        server, state = ipc_server
        
        result = await server.handle_command({
            "cmd": "recording.start",
            "inputs": ["cam1"]
        })
        
        assert result["status"] == "started"
        assert result["session_id"] is not None
        assert len(result["session_id"]) > 0
    
    @pytest.mark.asyncio
    async def test_start_recording_already_recording_error(self, ipc_server):
        """Test recording.start returns error if already recording"""
        server, state = ipc_server
        
        # Start first recording
        await server.handle_command({
            "cmd": "recording.start",
            "inputs": ["cam1"]
        })
        
        # Try to start second recording
        result = await server.handle_command({
            "cmd": "recording.start",
            "inputs": ["cam2"]
        })
        
        assert "error" in result
        assert "Already recording" in result["error"]
    
    @pytest.mark.asyncio
    async def test_stop_recording_command(self, ipc_server):
        """Test recording.stop command"""
        server, state = ipc_server
        
        # Start recording first
        await server.handle_command({
            "cmd": "recording.start",
            "session_id": "stop-test",
            "inputs": ["cam1"]
        })
        
        result = await server.handle_command({"cmd": "recording.stop"})
        
        assert result["status"] == "stopped"
        assert result["session_id"] == "stop-test"
        assert "duration_ms" in result
        
        # Verify state was updated
        assert state.current_mode == "idle"
    
    @pytest.mark.asyncio
    async def test_stop_recording_not_recording_error(self, ipc_server):
        """Test recording.stop returns error when not recording"""
        server, state = ipc_server
        
        result = await server.handle_command({"cmd": "recording.stop"})
        
        assert "error" in result
        assert "Not recording" in result["error"]
    
    @pytest.mark.asyncio
    async def test_stop_recording_session_id_mismatch(self, ipc_server):
        """Test recording.stop returns error on session_id mismatch"""
        server, state = ipc_server
        
        # Start recording
        await server.handle_command({
            "cmd": "recording.start",
            "session_id": "correct-session",
            "inputs": ["cam1"]
        })
        
        # Try to stop with wrong session_id
        result = await server.handle_command({
            "cmd": "recording.stop",
            "session_id": "wrong-session"
        })
        
        assert "error" in result
        assert "mismatch" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_recording_status_command_idle(self, ipc_server):
        """Test recording.status command when idle"""
        server, state = ipc_server
        
        result = await server.handle_command({"cmd": "recording.status"})
        
        assert result["recording"] is False
    
    @pytest.mark.asyncio
    async def test_recording_status_command_active(self, ipc_server):
        """Test recording.status command when recording"""
        server, state = ipc_server
        
        # Start recording
        await server.handle_command({
            "cmd": "recording.start",
            "session_id": "status-test",
            "inputs": ["cam1"]
        })
        
        result = await server.handle_command({"cmd": "recording.status"})
        
        assert result["recording"] is True
        assert result["session_id"] == "status-test"
        assert "duration_ms" in result
        assert "bytes_written" in result
    
    @pytest.mark.asyncio
    async def test_unknown_command_returns_error(self, ipc_server):
        """Test unknown command returns error"""
        server, state = ipc_server
        
        result = await server.handle_command({"cmd": "unknown.command"})
        
        assert "error" in result
        assert "Unknown command" in result["error"]
    
    @pytest.mark.asyncio
    async def test_missing_cmd_returns_error(self, ipc_server):
        """Test missing cmd field returns error"""
        server, state = ipc_server
        
        result = await server.handle_command({"not_cmd": "value"})
        
        assert "error" in result


class TestIPCConcurrency:
    """Tests for concurrent IPC operations"""
    
    @pytest.mark.asyncio
    async def test_concurrent_status_requests(self, tmp_path):
        """Test multiple concurrent status requests"""
        state_file = tmp_path / "state.json"
        socket_path = tmp_path / "concurrent.sock"
        
        with patch('pipeline_manager.state.STATE_FILE', state_file), \
             patch('pipeline_manager.ipc.SOCKET_PATH', socket_path):
            state = PipelineState()
            server = IPCServer(state)
            
            # Run 10 concurrent status requests
            tasks = [
                server.handle_command({"cmd": "status"})
                for _ in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert len(results) == 10
            for result in results:
                assert result["mode"] == "idle"
    
    @pytest.mark.asyncio
    async def test_rapid_start_stop_via_ipc(self, tmp_path):
        """Test rapid start/stop cycles via IPC"""
        state_file = tmp_path / "state.json"
        socket_path = tmp_path / "rapid.sock"
        
        with patch('pipeline_manager.state.STATE_FILE', state_file), \
             patch('pipeline_manager.ipc.SOCKET_PATH', socket_path):
            state = PipelineState()
            server = IPCServer(state)
            
            for i in range(5):
                start_result = await server.handle_command({
                    "cmd": "recording.start",
                    "session_id": f"rapid-{i}",
                    "inputs": ["cam1"]
                })
                assert start_result["status"] == "started"
                
                stop_result = await server.handle_command({
                    "cmd": "recording.stop"
                })
                assert stop_result["status"] == "stopped"
            
            # Final state should be idle
            status = await server.handle_command({"cmd": "status"})
            assert status["mode"] == "idle"


class TestIPCFilePaths:
    """Tests for IPC file path generation"""
    
    @pytest.mark.asyncio
    async def test_recording_creates_file_paths(self, tmp_path):
        """Test recording.start creates proper file paths"""
        state_file = tmp_path / "state.json"
        socket_path = tmp_path / "paths.sock"
        
        with patch('pipeline_manager.state.STATE_FILE', state_file), \
             patch('pipeline_manager.ipc.SOCKET_PATH', socket_path):
            state = PipelineState()
            server = IPCServer(state)
            
            result = await server.handle_command({
                "cmd": "recording.start",
                "session_id": "path-test",
                "inputs": ["cam1", "cam2"]
            })
            
            # Verify file paths were created
            assert "cam1" in result["inputs"]
            assert "cam2" in result["inputs"]
            assert result["inputs"]["cam1"].endswith(".mp4")
            assert result["inputs"]["cam2"].endswith(".mp4")
            assert "path-test" in result["inputs"]["cam1"]

