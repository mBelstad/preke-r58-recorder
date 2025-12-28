"""IPC server for pipeline manager communication"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from datetime import datetime
import uuid

from .state import PipelineState
from .watchdog import get_watchdog, RecordingWatchdog

logger = logging.getLogger(__name__)

SOCKET_PATH = Path("/run/r58/pipeline.sock")


class IPCServer:
    """Unix socket IPC server for pipeline commands"""
    
    def __init__(self, state: PipelineState):
        self.state = state
        self.server = None
        self.running = False
        self.watchdog = get_watchdog()
        
        # Set up watchdog callbacks
        self.watchdog.on_stall = self._handle_stall
        self.watchdog.on_disk_low = self._handle_disk_low
    
    async def _handle_stall(self, session_id: str, input_id: str) -> None:
        """Handle a stalled recording input"""
        logger.error(f"Recording stall detected: session={session_id}, input={input_id}")
        
        # Record error in state
        self.state.set_error(f"Recording stall: {input_id} stopped writing")
        
        # TODO: Emit WebSocket event to notify UI
        # TODO: Consider auto-recovery (restart pipeline) or auto-stop
    
    async def _handle_disk_low(self, available_gb: float) -> None:
        """Handle low disk space condition"""
        logger.error(f"Low disk space: {available_gb:.2f}GB remaining")
        
        # If critically low and recording, stop to prevent data loss
        if available_gb < 0.5 and self.state.current_mode == "recording":
            logger.critical("Emergency stop: disk space critical")
            self.state.set_error(f"Emergency stop: disk space critical ({available_gb:.2f}GB)")
            
            # Stop recording to save what we have
            self.watchdog.stop_watching()
            final_state = self.state.stop_recording()
            
            # TODO: Emit WebSocket event to notify UI
            # TODO: Stop GStreamer pipelines
    
    async def start(self):
        """Start the IPC server"""
        # Ensure socket directory exists
        SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing socket if present
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        
        self.server = await asyncio.start_unix_server(
            self.handle_connection,
            path=str(SOCKET_PATH)
        )
        self.running = True
        
        # Make socket accessible
        SOCKET_PATH.chmod(0o666)
        
        print(f"[IPC Server] Listening on {SOCKET_PATH}")
    
    def stop(self):
        """Stop the IPC server"""
        self.running = False
        if self.server:
            self.server.close()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
    
    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming connection"""
        try:
            data = await reader.readline()
            if not data:
                return
            
            command = json.loads(data.decode())
            response = await self.handle_command(command)
            
            writer.write(json.dumps(response).encode() + b"\n")
            await writer.drain()
        except Exception as e:
            error_response = {"error": str(e)}
            writer.write(json.dumps(error_response).encode() + b"\n")
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def handle_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a command and return response"""
        cmd = command.get("cmd")
        
        if cmd == "status":
            return {
                "mode": self.state.current_mode,
                "recording": self.state.active_recording.model_dump() if self.state.active_recording else None,
                "last_error": self.state.last_error,
            }
        
        elif cmd == "recording.start":
            session_id = command.get("session_id") or str(uuid.uuid4())
            inputs = command.get("inputs", [])
            
            if self.state.current_mode == "recording":
                return {"error": "Already recording"}
            
            # Create file paths for each input
            recordings_dir = Path("/opt/r58/recordings")
            recordings_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            input_paths = {}
            for input_id in inputs:
                file_path = recordings_dir / f"{session_id}_{input_id}_{timestamp}.mp4"
                input_paths[input_id] = str(file_path)
            
            # Start recording
            self.state.start_recording(session_id, input_paths)
            
            # Start watchdog
            self.watchdog.start_watching(session_id, input_paths)
            
            # TODO: Actually start GStreamer pipelines here
            
            logger.info(f"Recording started: session={session_id}, inputs={list(input_paths.keys())}")
            
            return {
                "session_id": session_id,
                "inputs": input_paths,
                "status": "started",
            }
        
        elif cmd == "recording.stop":
            session_id = command.get("session_id")
            
            if self.state.current_mode != "recording":
                return {"error": "Not recording"}
            
            if session_id and self.state.active_recording and \
               self.state.active_recording.session_id != session_id:
                return {"error": "Session ID mismatch"}
            
            # Stop watchdog
            self.watchdog.stop_watching()
            
            # Stop recording
            final_state = self.state.stop_recording()
            
            # TODO: Actually stop GStreamer pipelines here
            
            logger.info(f"Recording stopped: session={final_state.session_id if final_state else 'none'}")
            
            return {
                "session_id": final_state.session_id if final_state else None,
                "duration_ms": int((datetime.now() - final_state.started_at).total_seconds() * 1000) if final_state else 0,
                "files": final_state.inputs if final_state else {},
                "status": "stopped",
            }
        
        elif cmd == "recording.status":
            if not self.state.active_recording:
                return {"recording": False}
            
            return {
                "recording": True,
                "session_id": self.state.active_recording.session_id,
                "duration_ms": int((datetime.now() - self.state.active_recording.started_at).total_seconds() * 1000),
                "bytes_written": self.state.active_recording.bytes_written,
            }
        
        elif cmd == "recording.update_bytes":
            # Called by GStreamer pipeline to report progress
            input_id = command.get("input_id")
            bytes_written = command.get("bytes")
            
            if not input_id or bytes_written is None:
                return {"error": "Missing input_id or bytes"}
            
            if not self.state.active_recording:
                return {"error": "Not recording"}
            
            # Update state
            self.state.update_bytes(input_id, bytes_written)
            
            # Notify watchdog
            self.watchdog.update_bytes(input_id, bytes_written)
            
            return {"ok": True}
        
        elif cmd == "watchdog.status":
            # Get watchdog status for diagnostics
            return {
                "watching": self.watchdog._running,
                "session_id": self.watchdog._session_id,
                "input_state": {
                    input_id: {
                        "bytes": bytes_val,
                        "last_change": ts.isoformat(),
                    }
                    for input_id, (bytes_val, ts) in self.watchdog._input_state.items()
                },
            }
        
        else:
            return {"error": f"Unknown command: {cmd}"}

