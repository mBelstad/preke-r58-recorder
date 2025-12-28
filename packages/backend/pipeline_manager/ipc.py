"""IPC server for pipeline manager communication"""
import asyncio
import concurrent.futures
import json
import logging
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from datetime import datetime
import uuid

from .state import PipelineState
from .watchdog import get_watchdog, RecordingWatchdog
from .config import get_config, get_enabled_cameras, CameraConfig
from .gstreamer.runner import get_runner, PipelineState as GstPipelineState
from .gstreamer.pipelines import (
    build_preview_pipeline_string,
    build_recording_pipeline_string,
)

logger = logging.getLogger(__name__)

SOCKET_PATH = Path("/run/r58/pipeline.sock")
RECORDINGS_DIR = Path("/opt/r58/recordings")

# Thread pool for GStreamer operations (blocking)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="gst_")


class IPCServer:
    """Unix socket IPC server for pipeline commands"""
    
    def __init__(self, state: PipelineState):
        self.state = state
        self.server = None
        self.running = False
        self.watchdog = get_watchdog()
        self.config = get_config()
        self.gst_runner = get_runner(on_state_change=self._on_pipeline_state_change)
        
        # Set up watchdog callbacks
        self.watchdog.on_stall = self._handle_stall
        self.watchdog.on_disk_low = self._handle_disk_low
    
    def _on_pipeline_state_change(self, pipeline_id: str, new_state: GstPipelineState, error: Optional[str] = None):
        """Handle GStreamer pipeline state changes."""
        logger.info(f"Pipeline {pipeline_id} state changed to {new_state.value}")
        
        if error:
            logger.error(f"Pipeline {pipeline_id} error: {error}")
            self.state.set_error(f"Pipeline {pipeline_id}: {error}")
        
        # TODO: Emit WebSocket event to notify UI
    
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
            RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            input_paths = {}
            started_pipelines = []
            
            enabled_cameras = get_enabled_cameras(self.config)
            
            for input_id in inputs:
                # Get camera config if available
                cam_config = enabled_cameras.get(input_id)
                if not cam_config:
                    logger.warning(f"Input {input_id} not found in config, skipping")
                    continue
                
                # Create output file path
                file_path = RECORDINGS_DIR / f"{session_id}_{input_id}_{timestamp}.mkv"
                input_paths[input_id] = str(file_path)
                
                # Build and start GStreamer pipeline
                try:
                    pipeline_str = build_recording_pipeline_string(
                        cam_id=input_id,
                        device=cam_config.device,
                        output_path=str(file_path),
                        bitrate=cam_config.bitrate,
                        resolution=cam_config.resolution,
                        with_preview=cam_config.mediamtx_enabled,
                    )
                    
                    pipeline_id = f"recording_{input_id}"
                    # Run GStreamer operation in thread pool to avoid blocking
                    loop = asyncio.get_event_loop()
                    success = await loop.run_in_executor(
                        _executor,
                        lambda pid=pipeline_id, pstr=pipeline_str, fp=str(file_path), dev=cam_config.device: self.gst_runner.start_pipeline(
                            pipeline_id=pid,
                            pipeline_string=pstr,
                            pipeline_type="recording",
                            output_path=fp,
                            device=dev,
                        )
                    )
                    
                    if success:
                        started_pipelines.append(input_id)
                        logger.info(f"Started recording pipeline for {input_id}")
                    else:
                        logger.error(f"Failed to start recording pipeline for {input_id}")
                        
                except Exception as e:
                    logger.error(f"Error starting pipeline for {input_id}: {e}")
            
            if not started_pipelines:
                return {"error": "Failed to start any recording pipelines"}
            
            # Start recording state
            self.state.start_recording(session_id, input_paths)
            
            # Start watchdog
            self.watchdog.start_watching(session_id, input_paths)
            
            logger.info(f"Recording started: session={session_id}, inputs={started_pipelines}")
            
            return {
                "session_id": session_id,
                "inputs": input_paths,
                "started_pipelines": started_pipelines,
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
            
            # Stop all recording GStreamer pipelines
            stopped_pipelines = []
            if self.state.active_recording:
                loop = asyncio.get_event_loop()
                for input_id in self.state.active_recording.inputs.keys():
                    pipeline_id = f"recording_{input_id}"
                    try:
                        # Run GStreamer operation in thread pool to avoid blocking
                        success = await loop.run_in_executor(
                            _executor,
                            lambda pid=pipeline_id: self.gst_runner.stop_pipeline(pid)
                        )
                        if success:
                            stopped_pipelines.append(input_id)
                            logger.info(f"Stopped recording pipeline for {input_id}")
                        else:
                            logger.warning(f"Failed to stop pipeline for {input_id}")
                    except Exception as e:
                        logger.error(f"Error stopping pipeline for {input_id}: {e}")
            
            # Stop recording state
            final_state = self.state.stop_recording()
            
            logger.info(f"Recording stopped: session={final_state.session_id if final_state else 'none'}")
            
            return {
                "session_id": final_state.session_id if final_state else None,
                "duration_ms": int((datetime.now() - final_state.started_at).total_seconds() * 1000) if final_state else 0,
                "files": final_state.inputs if final_state else {},
                "stopped_pipelines": stopped_pipelines,
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
        
        elif cmd == "preview.start":
            input_id = command.get("input_id")
            
            if not input_id:
                return {"error": "Missing input_id"}
            
            enabled_cameras = get_enabled_cameras(self.config)
            cam_config = enabled_cameras.get(input_id)
            
            if not cam_config:
                return {"error": f"Input {input_id} not found or not enabled"}
            
            pipeline_id = f"preview_{input_id}"
            
            # Check if already running
            if self.gst_runner.is_running(pipeline_id):
                return {"status": "already_running", "input_id": input_id}
            
            try:
                pipeline_str = build_preview_pipeline_string(
                    cam_id=input_id,
                    device=cam_config.device,
                    bitrate=cam_config.bitrate,
                    resolution=cam_config.resolution,
                )
                
                # Run GStreamer operation in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    _executor,
                    lambda: self.gst_runner.start_pipeline(
                        pipeline_id=pipeline_id,
                        pipeline_string=pipeline_str,
                        pipeline_type="preview",
                        device=cam_config.device,
                    )
                )
                
                if success:
                    logger.info(f"Started preview pipeline for {input_id}")
                    return {
                        "status": "started",
                        "input_id": input_id,
                        "rtsp_url": f"rtsp://127.0.0.1:{self.config.mediamtx_rtsp_port}/{input_id}",
                    }
                else:
                    return {"error": f"Failed to start preview pipeline for {input_id}"}
                    
            except Exception as e:
                logger.error(f"Error starting preview for {input_id}: {e}")
                return {"error": str(e)}
        
        elif cmd == "preview.stop":
            input_id = command.get("input_id")
            
            if not input_id:
                return {"error": "Missing input_id"}
            
            pipeline_id = f"preview_{input_id}"
            
            try:
                # Run GStreamer operation in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    _executor,
                    lambda: self.gst_runner.stop_pipeline(pipeline_id)
                )
                if success:
                    logger.info(f"Stopped preview pipeline for {input_id}")
                    return {"status": "stopped", "input_id": input_id}
                else:
                    return {"error": f"Failed to stop preview pipeline for {input_id}"}
            except Exception as e:
                logger.error(f"Error stopping preview for {input_id}: {e}")
                return {"error": str(e)}
        
        elif cmd == "preview.status":
            input_id = command.get("input_id")
            
            if input_id:
                # Status for single input
                pipeline_id = f"preview_{input_id}"
                info = self.gst_runner.get_pipeline_info(pipeline_id)
                return {"input_id": input_id, "pipeline": info}
            else:
                # Status for all previews
                all_pipelines = self.gst_runner.get_all_pipelines()
                previews = {
                    pid.replace("preview_", ""): info
                    for pid, info in all_pipelines.items()
                    if pid.startswith("preview_")
                }
                return {"previews": previews}
        
        elif cmd == "pipeline.status":
            # Get status of all pipelines
            return {"pipelines": self.gst_runner.get_all_pipelines()}
        
        else:
            return {"error": f"Unknown command: {cmd}"}

