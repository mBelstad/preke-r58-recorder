"""IPC server for pipeline manager communication"""
import asyncio
import concurrent.futures
import functools
import json
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional

from .config import check_resource_limits, get_config, get_enabled_cameras
from .device_monitor import DeviceMonitor, get_device_monitor
from .gstreamer.pipelines import (
    build_preview_pipeline_string,
    build_recording_pipeline_string,
    build_ingest_pipeline_string,
    get_device_capabilities,
    is_device_busy,
)
from .gstreamer.runner import PipelineState as GstPipelineState
from .gstreamer.runner import get_runner
from .state import PipelineState
from .watchdog import get_watchdog
from .ingest import IngestManager, IngestStatus, get_ingest_manager
from .subscriber_recorder import SubscriberRecorder, get_subscriber_recorder
from .integrity import RecordingIntegrityChecker

logger = logging.getLogger(__name__)

SOCKET_PATH = Path("/run/r58/pipeline.sock")
RECORDINGS_DIR = Path("/mnt/sdcard/recordings")

# Thread pool for GStreamer operations (blocking)
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="gst_")

# Maximum number of events to buffer for API polling
EVENT_BUFFER_SIZE = 100


class IPCServer:
    """Unix socket IPC server for pipeline commands
    
    Supports two architectures:
    1. Legacy: Direct V4L2 access for preview/recording (original)
    2. Pub/Sub: IngestManager (publisher) + SubscriberRecorder (subscriber)
    
    The pub/sub architecture is preferred as it:
    - Allows preview during recording
    - Reduces VPU load (single encoder per camera)
    - Supports hot-plug without stopping recording
    """

    def __init__(self, state: PipelineState, use_pubsub: bool = True):
        self.state = state
        self.server = None
        self.running = False
        self.watchdog = get_watchdog()
        self.config = get_config()
        self.gst_runner = get_runner(on_state_change=self._on_pipeline_state_change)
        self.use_pubsub = use_pubsub
        
        # Pub/Sub architecture components
        self.ingest_manager = get_ingest_manager(on_status_change=self._on_ingest_status_change)
        self.subscriber_recorder = get_subscriber_recorder(
            on_status_change=self._on_recording_status_change,
            on_session_event=self._on_session_event,
        )
        
        # Device monitor for hot-plug detection
        self.device_monitor = get_device_monitor()
        self.device_monitor.on_connected = self._handle_device_connected
        self.device_monitor.on_disconnected = self._handle_device_disconnected

        # Event queue for async events that need to be sent to the API
        self._event_queue: Deque[Dict[str, Any]] = deque(maxlen=EVENT_BUFFER_SIZE)
        self._event_seq = 0

        # Set up watchdog callbacks
        self.watchdog.on_stall = self._handle_stall
        self.watchdog.on_disk_low = self._handle_disk_low
        self.watchdog.on_progress = self._handle_progress
        
        # Recording integrity checker
        self.integrity_checker = RecordingIntegrityChecker()

    def _on_ingest_status_change(self, cam_id: str, status: IngestStatus) -> None:
        """Handle ingest pipeline status changes."""
        logger.info(f"Ingest {cam_id} status: {status.status}")
        self._queue_event("ingest.status", {
            "input_id": cam_id,
            "status": status.status,
            "resolution": f"{status.resolution[0]}x{status.resolution[1]}" if status.resolution else None,
            "has_signal": status.has_signal,
            "stream_url": status.stream_url,
            "error": status.error_message,
        })

    def _on_recording_status_change(self, cam_id: str, recording) -> None:
        """Handle recording status changes."""
        logger.info(f"Recording {cam_id} status: {recording.state}")
        self._queue_event("recording.status", {
            "input_id": cam_id,
            "state": recording.state,
            "output_path": recording.output_path,
            "error": recording.error_message,
        })

    def _on_session_event(self, session_id: str, event_type: str, data: dict) -> None:
        """Handle recording session events."""
        logger.info(f"Session {session_id} event: {event_type}")
        self._queue_event(f"session.{event_type}", {
            "session_id": session_id,
            **data,
        })

    def _queue_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Add an event to the queue for API polling"""
        self._event_seq += 1
        event = {
            "seq": self._event_seq,
            "type": event_type,
            "ts": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        self._event_queue.append(event)
        logger.debug(f"Queued event: {event_type} (seq={self._event_seq})")

    def _on_pipeline_state_change(self, pipeline_id: str, new_state: GstPipelineState, error: Optional[str] = None):
        """Handle GStreamer pipeline state changes."""
        logger.info(f"Pipeline {pipeline_id} state changed to {new_state.value}")

        if error:
            logger.error(f"Pipeline {pipeline_id} error: {error}")
            self.state.set_error(f"Pipeline {pipeline_id}: {error}")

        # Queue event for API to broadcast to WebSocket clients
        # Extract input_id from pipeline_id (e.g., "preview_cam1" -> "cam1")
        input_id = None
        if "_" in pipeline_id:
            parts = pipeline_id.split("_", 1)
            if len(parts) > 1:
                input_id = parts[1]

        if error:
            self._queue_event("pipeline.error", {
                "pipeline_id": pipeline_id,
                "input_id": input_id,
                "error": error,
            })
        
        # Queue preview started/stopped events
        if pipeline_id.startswith("preview_"):
            if new_state == GstPipelineState.RUNNING:
                self._queue_event("preview.started", {
                    "input_id": input_id,
                    "pipeline_id": pipeline_id,
                })
            elif new_state == GstPipelineState.IDLE:
                self._queue_event("preview.stopped", {
                    "input_id": input_id,
                    "pipeline_id": pipeline_id,
                })

    async def _handle_stall(self, session_id: str, input_id: str) -> None:
        """Handle a stalled recording input"""
        logger.error(f"Recording stall detected: session={session_id}, input={input_id}")

        # Record error in state
        self.state.set_error(f"Recording stall: {input_id} stopped writing")

        # Queue event for API to broadcast to WebSocket clients
        self._queue_event("recording.stall", {
            "session_id": session_id,
            "input_id": input_id,
            "message": f"Recording stall: {input_id} stopped writing",
        })
        
        # Auto-recovery: attempt to restart the stalled pipeline
        logger.info(f"Attempting auto-recovery for stalled input: {input_id}")
        pipeline_id = f"recording_{input_id}"
        
        try:
            # Try to stop and restart the pipeline
            loop = asyncio.get_event_loop()
            
            # Stop the stalled pipeline
            await loop.run_in_executor(
                _executor,
                lambda pid=pipeline_id: self.gst_runner.stop_pipeline(pid)
            )
            
            # Get camera config for restart
            enabled_cameras = get_enabled_cameras(self.config)
            cam_config = enabled_cameras.get(input_id)
            
            if cam_config and self.state.active_recording:
                file_path = self.state.active_recording.inputs.get(input_id)
                if file_path:
                    # Restart the recording pipeline (with_preview=False for stability)
                    pipeline_str = build_recording_pipeline_string(
                        cam_id=input_id,
                        device=cam_config.device,
                        output_path=file_path,
                        bitrate=cam_config.bitrate,
                        resolution=cam_config.resolution,
                        with_preview=False,  # Disabled to prevent VPU overload
                    )
                    
                    success = await loop.run_in_executor(
                        _executor,
                        lambda pid=pipeline_id, pstr=pipeline_str, fp=file_path, dev=cam_config.device: self.gst_runner.start_pipeline(
                            pipeline_id=pid,
                            pipeline_string=pstr,
                            pipeline_type="recording",
                            output_path=fp,
                            device=dev,
                        )
                    )
                    
                    if success:
                        logger.info(f"Successfully restarted stalled pipeline for {input_id}")
                        self._queue_event("recording.recovered", {
                            "session_id": session_id,
                            "input_id": input_id,
                            "message": f"Pipeline {input_id} recovered from stall",
                        })
                    else:
                        logger.error(f"Failed to restart stalled pipeline for {input_id}")
        except Exception as e:
            logger.error(f"Auto-recovery failed for {input_id}: {e}")

    async def _handle_disk_low(self, available_gb: float) -> None:
        """Handle low disk space condition"""
        logger.error(f"Low disk space: {available_gb:.2f}GB remaining")

        # Queue storage warning event
        self._queue_event("storage.warning", {
            "available_gb": available_gb,
            "warning": f"Low disk space: {available_gb:.2f}GB remaining",
            "critical": available_gb < 0.5,
        })

        # If critically low and recording, stop to prevent data loss
        if available_gb < 0.5 and self.state.current_mode == "recording":
            logger.critical("Emergency stop: disk space critical")
            self.state.set_error(f"Emergency stop: disk space critical ({available_gb:.2f}GB)")

            # Queue emergency stop event
            session_id = self.state.active_recording.session_id if self.state.active_recording else None
            self._queue_event("recording.emergency_stop", {
                "session_id": session_id,
                "reason": "disk_space_critical",
                "available_gb": available_gb,
            })

            # Stop recording to save what we have
            self.watchdog.stop_watching()
            
            # Stop all recording GStreamer pipelines
            if self.state.active_recording:
                loop = asyncio.get_event_loop()
                for input_id in self.state.active_recording.inputs.keys():
                    pipeline_id = f"recording_{input_id}"
                    try:
                        await loop.run_in_executor(
                            _executor,
                            lambda pid=pipeline_id: self.gst_runner.stop_pipeline(pid)
                        )
                        logger.info(f"Emergency stopped recording pipeline for {input_id}")
                    except Exception as e:
                        logger.error(f"Error stopping pipeline for {input_id}: {e}")
            
            self.state.stop_recording()

    async def _handle_progress(self, session_id: str, bytes_written: Dict[str, int]) -> None:
        """Handle recording progress update from watchdog."""
        if not self.state.active_recording:
            return
        
        # Update state with current bytes written
        for input_id, bytes_val in bytes_written.items():
            self.state.update_bytes(input_id, bytes_val)
        
        # Calculate duration from recording start
        duration_ms = int((datetime.now(timezone.utc) - self.state.active_recording.started_at).total_seconds() * 1000)
        
        # Queue progress event for API to broadcast
        self._queue_event("recording.progress", {
            "session_id": session_id,
            "duration_ms": duration_ms,
            "bytes_written": bytes_written,
        })
        
        logger.info(f"[IPC] Queued recording.progress event: duration={duration_ms}ms, bytes={bytes_written}")

    async def _handle_device_connected(self, input_id: str, capabilities: Dict[str, Any]) -> None:
        """Handle a device being connected (signal detected).
        
        Auto-starts preview pipeline for the newly connected device.
        """
        logger.info(f"Device connected: {input_id} ({capabilities.get('width')}x{capabilities.get('height')})")
        
        # Queue event for API to broadcast to WebSocket clients
        self._queue_event("input.connected", {
            "input_id": input_id,
            "width": capabilities.get('width', 0),
            "height": capabilities.get('height', 0),
            "format": capabilities.get('format', ''),
        })
        
        # Auto-start preview if not recording
        if self.state.current_mode != "recording":
            enabled_cameras = get_enabled_cameras(self.config)
            cam_config = enabled_cameras.get(input_id)
            
            if cam_config:
                pipeline_id = f"preview_{input_id}"
                
                if not self.gst_runner.is_running(pipeline_id):
                    try:
                        pipeline_str = build_preview_pipeline_string(
                            cam_id=input_id,
                            device=cam_config.device,
                            bitrate=cam_config.bitrate,
                            resolution=cam_config.resolution,
                        )
                        
                        loop = asyncio.get_event_loop()
                        success = await loop.run_in_executor(
                            _executor,
                            functools.partial(
                                self.gst_runner.start_pipeline,
                                pipeline_id=pipeline_id,
                                pipeline_string=pipeline_str,
                                pipeline_type="preview",
                                device=cam_config.device,
                            )
                        )
                        
                        if success:
                            logger.info(f"Auto-started preview for newly connected {input_id}")
                        else:
                            logger.warning(f"Failed to auto-start preview for {input_id}")
                            
                    except Exception as e:
                        logger.error(f"Error auto-starting preview for connected device {input_id}: {e}")

    async def _handle_device_disconnected(self, input_id: str) -> None:
        """Handle a device being disconnected (signal lost).
        
        Stops any running pipelines for the disconnected device.
        """
        logger.info(f"Device disconnected: {input_id}")
        
        # Queue event for API to broadcast to WebSocket clients
        self._queue_event("input.disconnected", {
            "input_id": input_id,
        })
        
        # Stop preview pipeline if running
        preview_pipeline_id = f"preview_{input_id}"
        if self.gst_runner.is_running(preview_pipeline_id):
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    _executor,
                    lambda: self.gst_runner.stop_pipeline(preview_pipeline_id)
                )
                logger.info(f"Stopped preview pipeline for disconnected {input_id}")
            except Exception as e:
                logger.error(f"Error stopping preview for disconnected device {input_id}: {e}")
        
        # If recording, mark this input as having an issue
        if self.state.current_mode == "recording":
            recording_pipeline_id = f"recording_{input_id}"
            if self.gst_runner.is_running(recording_pipeline_id):
                logger.warning(f"Device {input_id} disconnected during recording!")
                self._queue_event("recording.input_lost", {
                    "session_id": self.state.active_recording.session_id if self.state.active_recording else None,
                    "input_id": input_id,
                })

    async def _auto_start_previews(self) -> None:
        """Start preview/ingest pipelines for all enabled cameras on startup.

        This ensures WHEP preview streams are immediately available
        when the pipeline manager starts. Only starts previews for
        cameras that have an active signal.
        
        In pub/sub mode, uses IngestManager for always-on streaming.
        In legacy mode, uses direct preview pipelines.
        """
        enabled_cameras = get_enabled_cameras(self.config)
        loop = asyncio.get_event_loop()

        logger.info(f"Auto-starting {'ingest' if self.use_pubsub else 'previews'} for {len(enabled_cameras)} enabled cameras")

        started = 0
        skipped_no_signal = 0

        if self.use_pubsub:
            # Pub/Sub mode: Use IngestManager for always-on streams
            for input_id in enabled_cameras.keys():
                try:
                    success = await loop.run_in_executor(
                        _executor,
                        lambda cam_id=input_id: self.ingest_manager.start_ingest(cam_id)
                    )
                    if success:
                        logger.info(f"Auto-started ingest for {input_id}")
                        started += 1
                    else:
                        # Check if it's no_signal vs error
                        status = self.ingest_manager.get_pipeline_status(input_id)
                        if status and status.status == "no_signal":
                            skipped_no_signal += 1
                except Exception as e:
                    logger.error(f"Error auto-starting ingest for {input_id}: {e}")
        else:
            # Legacy mode: Direct preview pipelines
            for input_id, cam_config in enabled_cameras.items():
                pipeline_id = f"preview_{input_id}"

                # Skip if already running
                if self.gst_runner.is_running(pipeline_id):
                    logger.info(f"Preview for {input_id} already running, skipping")
                    continue

                # Check for signal before starting preview
                try:
                    caps = get_device_capabilities(cam_config.device)
                    if not caps.get('has_signal', False):
                        logger.info(f"Skipping preview for {input_id}: no signal detected on {cam_config.device}")
                        skipped_no_signal += 1
                        continue
                except Exception as e:
                    logger.warning(f"Could not check signal for {input_id}: {e}, will attempt preview anyway")

                try:
                    pipeline_str = build_preview_pipeline_string(
                        cam_id=input_id,
                        device=cam_config.device,
                        bitrate=cam_config.bitrate,
                        resolution=cam_config.resolution,
                    )

                    success = await loop.run_in_executor(
                        _executor,
                        functools.partial(
                            self.gst_runner.start_pipeline,
                            pipeline_id=pipeline_id,
                            pipeline_string=pipeline_str,
                            pipeline_type="preview",
                            device=cam_config.device,
                        )
                    )

                    if success:
                        logger.info(f"Auto-started preview for {input_id}")
                        started += 1
                    else:
                        logger.warning(f"Failed to auto-start preview for {input_id}")

                except Exception as e:
                    logger.error(f"Error auto-starting preview for {input_id}: {e}")
                    # Continue with other cameras even if one fails
        
        logger.info(f"Auto-start complete: {started} started, {skipped_no_signal} skipped (no signal)")

    def _reconcile_state(self) -> None:
        """Reconcile persisted state with actual pipeline state on startup.
        
        If the persisted state shows recording but no recording pipelines are
        actually running (e.g., after crash/reboot), reset to idle.
        """
        if self.state.current_mode == "recording":
            # Check if any recording pipelines are actually running
            all_pipelines = self.gst_runner.get_all_pipelines()
            recording_pipelines = [
                pid for pid in all_pipelines.keys()
                if pid.startswith("recording_")
            ]
            
            if not recording_pipelines:
                logger.warning(
                    f"Stale recording state detected (session: {self.state.active_recording.session_id if self.state.active_recording else 'unknown'}), "
                    "resetting to idle"
                )
                self.state.current_mode = "idle"
                self.state.active_recording = None
                self.state.save()
            else:
                logger.info(f"Resuming recording with {len(recording_pipelines)} active pipelines")

    async def start(self):
        """Start the IPC server"""
        # Reconcile state with actual pipelines before starting
        self._reconcile_state()
        
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

        # Auto-start preview pipelines for all enabled cameras
        await self._auto_start_previews()
        
        # Start device monitor for hot-plug detection
        self.device_monitor.start()
        logger.info("Device monitor started for hot-plug detection")

    def stop(self):
        """Stop the IPC server"""
        self.running = False
        
        # Stop device monitor
        self.device_monitor.stop()
        
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
                "recording": self.state.active_recording.model_dump(mode="json") if self.state.active_recording else None,
                "last_error": self.state.last_error,
            }

        elif cmd == "recording.start":
            session_id = command.get("session_id") or str(uuid.uuid4())
            inputs = command.get("inputs", [])

            if self.state.current_mode == "recording":
                return {"error": "Already recording"}

            # Check resource limits before starting
            resources_ok, resource_reason = check_resource_limits(self.config)
            if not resources_ok:
                logger.warning(f"Recording blocked by resource limits: {resource_reason}")
                return {"error": f"Cannot start recording: {resource_reason}"}

            # TEE Pipeline Architecture:
            # The ingest pipelines are already running with TEE (preview + recording branches).
            # Recording is controlled by a valve element in the recording branch.
            # We just need to open the valves for the requested cameras.
            
            enabled_cameras = get_enabled_cameras(self.config)
            started_recordings = []
            skipped_inputs = []
            input_paths = {}
            
            loop = asyncio.get_event_loop()
            
            # If no inputs specified, record all streaming cameras
            if not inputs:
                inputs = list(enabled_cameras.keys())
            
            for input_id in inputs:
                if input_id not in enabled_cameras:
                    skipped_inputs.append({"id": input_id, "reason": "not in config"})
                    continue
                
                # Check if camera is streaming with TEE pipeline
                recording_status = self.ingest_manager.get_recording_status(input_id)
                if not recording_status.get("is_tee_pipeline"):
                    skipped_inputs.append({"id": input_id, "reason": "not using TEE pipeline"})
                    continue
                
                # Start recording via valve control
                try:
                    success = await loop.run_in_executor(
                        _executor,
                        lambda cam_id=input_id: self.ingest_manager.start_recording(cam_id)
                    )
                    
                    if success:
                        started_recordings.append(input_id)
                        # Get the recording path from ingest manager
                        rec_status = self.ingest_manager.get_recording_status(input_id)
                        input_paths[input_id] = rec_status.get("path", "")
                        logger.info(f"Started recording for {input_id}")
                    else:
                        skipped_inputs.append({"id": input_id, "reason": "valve control failed"})
                except Exception as e:
                    logger.error(f"Error starting recording for {input_id}: {e}")
                    skipped_inputs.append({"id": input_id, "reason": str(e)})
            
            if not started_recordings:
                return {"error": "Failed to start any recordings", "skipped": skipped_inputs}

            # Start recording state
            self.state.start_recording(session_id, input_paths)

            # Start watchdog
            self.watchdog.start_watching(session_id, input_paths)

            logger.info(f"Recording started: session={session_id}, inputs={started_recordings}, skipped={len(skipped_inputs)}")

            return {
                "session_id": session_id,
                "inputs": input_paths,
                "started_recordings": started_recordings,
                "skipped_inputs": skipped_inputs,
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

            # TEE Pipeline Architecture:
            # Stop recordings by closing the valves (preview continues running)
            stopped_recordings = []
            loop = asyncio.get_event_loop()
            
            if self.state.active_recording:
                for input_id in self.state.active_recording.inputs.keys():
                    try:
                        success = await loop.run_in_executor(
                            _executor,
                            lambda cam_id=input_id: self.ingest_manager.stop_recording(cam_id)
                        )
                        if success:
                            stopped_recordings.append(input_id)
                            logger.info(f"Stopped recording for {input_id}")
                        else:
                            logger.warning(f"Failed to stop recording for {input_id}")
                    except Exception as e:
                        logger.error(f"Error stopping recording for {input_id}: {e}")

            # Stop recording state
            final_state = self.state.stop_recording()

            logger.info(f"Recording stopped: session={final_state.session_id if final_state else 'none'}")

            # Run integrity checks on recorded files (async, don't block response)
            if final_state and final_state.inputs:
                asyncio.create_task(self._check_recording_integrity(final_state))

            # Note: With TEE pipeline, preview is always running (no need to restart)
            # The valve just stops the recording branch, preview continues unaffected
            
            return {
                "session_id": final_state.session_id if final_state else session_id,
                "stopped_recordings": stopped_recordings,
                "status": "stopped",
            }

        # Legacy code path for backward compatibility (disabled)
        elif cmd == "recording.stop.legacy":
            session_id = command.get("session_id")

            if self.state.current_mode != "recording":
                return {"error": "Not recording"}

            if session_id and self.state.active_recording and \
               self.state.active_recording.session_id != session_id:
                return {"error": "Session ID mismatch"}

            # Stop watchdog
            self.watchdog.stop_watching()

            # Stop all recording GStreamer pipelines (OLD way - before TEE)
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

            # Restart preview pipelines for recorded inputs
            restarted_previews = []
            if final_state:
                enabled_cameras = get_enabled_cameras(self.config)
                for input_id in final_state.inputs.keys():
                    cam_config = enabled_cameras.get(input_id)
                    if cam_config and cam_config.mediamtx_enabled:
                        try:
                            pipeline_str = build_preview_pipeline_string(
                                cam_id=input_id,
                                device=cam_config.device,
                                bitrate=cam_config.bitrate,
                                resolution=cam_config.resolution,
                            )
                            preview_pipeline_id = f"preview_{input_id}"
                            success = await loop.run_in_executor(
                                _executor,
                                lambda pid=preview_pipeline_id, pstr=pipeline_str, dev=cam_config.device: self.gst_runner.start_pipeline(
                                    pipeline_id=pid,
                                    pipeline_string=pstr,
                                    pipeline_type="preview",
                                    device=dev,
                                )
                            )
                            if success:
                                restarted_previews.append(input_id)
                                logger.info(f"Restarted preview pipeline for {input_id}")
                        except Exception as e:
                            logger.warning(f"Failed to restart preview for {input_id}: {e}")

            return {
                "session_id": final_state.session_id if final_state else None,
                "duration_ms": int((datetime.now(timezone.utc) - final_state.started_at).total_seconds() * 1000) if final_state else 0,
                "files": final_state.inputs if final_state else {},
                "stopped_pipelines": stopped_pipelines,
                "restarted_previews": restarted_previews,
                "status": "stopped",
            }

        elif cmd == "recording.status":
            if not self.state.active_recording:
                return {"recording": False}

            return {
                "recording": True,
                "session_id": self.state.active_recording.session_id,
                "duration_ms": int((datetime.now(timezone.utc) - self.state.active_recording.started_at).total_seconds() * 1000),
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

            # Check for signal before starting preview
            caps = get_device_capabilities(cam_config.device)
            if not caps.get('has_signal', False):
                logger.info(f"Skipping preview for {input_id}: no signal on {cam_config.device}")
                return {"status": "no_signal", "input_id": input_id}

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

        elif cmd == "device.check":
            # Check device capabilities and signal status for diagnostics
            device = command.get("device")

            if not device:
                # Return status for all configured devices
                enabled_cameras = get_enabled_cameras(self.config)
                devices = {}
                for input_id, cam_config in enabled_cameras.items():
                    try:
                        caps = get_device_capabilities(cam_config.device)
                        devices[input_id] = {
                            "device": cam_config.device,
                            "capabilities": caps,
                        }
                    except Exception as e:
                        devices[input_id] = {
                            "device": cam_config.device,
                            "error": str(e),
                        }
                return {"devices": devices}

            # Return status for specific device
            try:
                caps = get_device_capabilities(device)
                return {"device": device, "capabilities": caps}
            except Exception as e:
                return {"device": device, "error": str(e)}

        elif cmd == "events.poll":
            # Return pending events for the API to broadcast
            last_seq = command.get("last_seq", 0)
            
            # Get events since last_seq
            events: List[Dict[str, Any]] = []
            for event in self._event_queue:
                if event.get("seq", 0) > last_seq:
                    events.append(event)
            
            return {
                "events": events,
                "latest_seq": self._event_seq,
                "count": len(events),
            }

        elif cmd == "pipelines.list":
            # Return information about all running pipelines
            all_pipelines = self.gst_runner.get_all_pipelines()
            return {"pipelines": all_pipelines}

        elif cmd == "pipeline.stop":
            # Stop a specific pipeline
            pipeline_id = command.get("pipeline_id")
            if not pipeline_id:
                return {"error": "Missing pipeline_id"}
            
            try:
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    _executor,
                    lambda pid=pipeline_id: self.gst_runner.stop_pipeline(pid)
                )
                
                if success:
                    logger.info(f"Stopped pipeline: {pipeline_id}")
                    return {"success": True, "pipeline_id": pipeline_id}
                else:
                    return {"error": f"Failed to stop pipeline: {pipeline_id}"}
            except Exception as e:
                logger.error(f"Error stopping pipeline {pipeline_id}: {e}")
                return {"error": str(e)}

        # =================================================================
        # PUB/SUB ARCHITECTURE COMMANDS
        # =================================================================
        
        elif cmd == "ingest.start":
            # Start ingest for a specific camera
            input_id = command.get("input_id")
            if not input_id:
                return {"error": "Missing input_id"}
            
            try:
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    _executor,
                    lambda: self.ingest_manager.start_ingest(input_id)
                )
                
                if success:
                    status = self.ingest_manager.get_pipeline_status(input_id)
                    return {
                        "status": "started",
                        "input_id": input_id,
                        "stream_url": status.stream_url if status else None,
                    }
                else:
                    status = self.ingest_manager.get_pipeline_status(input_id)
                    return {
                        "status": status.status if status else "error",
                        "input_id": input_id,
                        "error": status.error_message if status else "Unknown error",
                    }
            except Exception as e:
                logger.error(f"Error starting ingest for {input_id}: {e}")
                return {"error": str(e)}

        elif cmd == "ingest.stop":
            # Stop ingest for a specific camera
            input_id = command.get("input_id")
            if not input_id:
                return {"error": "Missing input_id"}
            
            try:
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    _executor,
                    lambda: self.ingest_manager.stop_ingest(input_id)
                )
                
                return {"status": "stopped" if success else "error", "input_id": input_id}
            except Exception as e:
                logger.error(f"Error stopping ingest for {input_id}: {e}")
                return {"error": str(e)}

        elif cmd == "ingest.start_all":
            # Start ingest for all enabled cameras
            try:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    _executor,
                    lambda: self.ingest_manager.start_all()
                )
                
                return {"status": "started", "results": results}
            except Exception as e:
                logger.error(f"Error starting all ingests: {e}")
                return {"error": str(e)}

        elif cmd == "ingest.stop_all":
            # Stop ingest for all cameras
            try:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    _executor,
                    lambda: self.ingest_manager.stop_all()
                )
                
                return {"status": "stopped", "results": results}
            except Exception as e:
                logger.error(f"Error stopping all ingests: {e}")
                return {"error": str(e)}

        elif cmd == "ingest.status":
            # Get ingest status
            input_id = command.get("input_id")
            
            if input_id:
                status = self.ingest_manager.get_pipeline_status(input_id)
                if status:
                    return {
                        "input_id": input_id,
                        "status": status.status,
                        "resolution": f"{status.resolution[0]}x{status.resolution[1]}" if status.resolution else None,
                        "has_signal": status.has_signal,
                        "stream_url": status.stream_url,
                        "uptime_seconds": status.uptime_seconds,
                        "error": status.error_message,
                    }
                else:
                    return {"error": f"Camera {input_id} not found"}
            else:
                # Return all ingest statuses
                statuses = self.ingest_manager.get_all_statuses()
                result = {}
                for cam_id, status in statuses.items():
                    result[cam_id] = {
                        "status": status.status,
                        "resolution": f"{status.resolution[0]}x{status.resolution[1]}" if status.resolution else None,
                        "has_signal": status.has_signal,
                        "stream_url": status.stream_url,
                        "uptime_seconds": status.uptime_seconds,
                        "error": status.error_message,
                    }
                return {"ingests": result}

        elif cmd == "subscriber.record.start":
            # Start recording using subscriber pattern
            input_id = command.get("input_id")
            session_id = command.get("session_id")
            
            if not input_id:
                return {"error": "Missing input_id"}
            
            try:
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    _executor,
                    lambda: self.subscriber_recorder.start_recording(input_id, session_id)
                )
                
                if success:
                    status = self.subscriber_recorder.get_status()
                    recording = status.get("recordings", {}).get(input_id, {})
                    return {
                        "status": "started",
                        "input_id": input_id,
                        "output_path": recording.get("output_path"),
                        "session_id": status.get("session", {}).get("session_id"),
                    }
                else:
                    return {"error": f"Failed to start recording for {input_id}"}
            except Exception as e:
                logger.error(f"Error starting subscriber recording for {input_id}: {e}")
                return {"error": str(e)}

        elif cmd == "subscriber.record.stop":
            # Stop recording for a specific camera
            input_id = command.get("input_id")
            
            if not input_id:
                return {"error": "Missing input_id"}
            
            try:
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    _executor,
                    lambda: self.subscriber_recorder.stop_recording(input_id)
                )
                
                return {"status": "stopped" if success else "error", "input_id": input_id}
            except Exception as e:
                logger.error(f"Error stopping subscriber recording for {input_id}: {e}")
                return {"error": str(e)}

        elif cmd == "subscriber.session.start":
            # Start a recording session for multiple cameras
            session_id = command.get("session_id")
            camera_ids = command.get("camera_ids")  # Optional: list of camera IDs
            
            try:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    _executor,
                    lambda: self.subscriber_recorder.start_session(session_id, camera_ids)
                )
                
                status = self.subscriber_recorder.get_status()
                return {
                    "status": "started",
                    "session_id": status.get("session", {}).get("session_id"),
                    "results": results,
                }
            except Exception as e:
                logger.error(f"Error starting recording session: {e}")
                return {"error": str(e)}

        elif cmd == "subscriber.session.stop":
            # Stop the current recording session
            try:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    _executor,
                    lambda: self.subscriber_recorder.stop_session()
                )
                
                return {"status": "stopped", "results": results}
            except Exception as e:
                logger.error(f"Error stopping recording session: {e}")
                return {"error": str(e)}

        elif cmd == "subscriber.status":
            # Get subscriber recorder status
            return self.subscriber_recorder.get_status()

        else:
            return {"error": f"Unknown command: {cmd}"}
    
    async def _check_recording_integrity(self, recording_state) -> None:
        """Check integrity of recorded files after recording stops.
        
        This runs asynchronously and doesn't block the stop response.
        Results are logged for monitoring.
        
        Args:
            recording_state: RecordingState with file paths
        """
        try:
            # Wait a bit for files to be fully flushed
            await asyncio.sleep(2.0)
            
            # Calculate expected duration
            if recording_state.started_at:
                from datetime import datetime, timezone
                duration = (datetime.now(timezone.utc) - recording_state.started_at).total_seconds()
            else:
                duration = None
            
            # Check each recording file
            for input_id, file_path_str in recording_state.inputs.items():
                file_path = Path(file_path_str)
                
                if not file_path.exists():
                    logger.warning(f"Recording file not found for integrity check: {file_path}")
                    continue
                
                logger.info(f"Checking integrity of {file_path.name}...")
                result = await self.integrity_checker.validate(
                    file_path,
                    expected_duration=duration,
                    duration_tolerance=5.0,  # Allow 5 second difference
                )
                
                # Log the result
                self.integrity_checker.log_result(result)
                
                # Queue event for API
                self._queue_event("recording.integrity", {
                    "input_id": input_id,
                    "file_path": str(file_path),
                    "valid": result.valid,
                    "file_size_mb": round(result.file_size_bytes / 1024 / 1024, 2),
                    "duration_seconds": result.duration_seconds,
                    "has_video": result.has_video,
                    "has_audio": result.has_audio,
                    "video_codec": result.video_codec,
                    "audio_codec": result.audio_codec,
                    "error": result.error_message,
                })
        
        except Exception as e:
            logger.error(f"Error during integrity check: {e}")

