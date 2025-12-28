"""Pipeline manager for camera recording (subscribes to MediaMTX streams)."""
import logging
import subprocess
import shutil
import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

import httpx

from .config import AppConfig, CameraConfig
from .pipelines import build_recording_subscriber_pipeline
from .gst_utils import ensure_gst_initialized, get_gst, get_glib

logger = logging.getLogger(__name__)


class Recorder:
    """Manages recording pipelines for multiple cameras.
    
    Records by subscribing to MediaMTX streams from IngestManager.
    Does NOT access V4L2 devices directly - completely independent of ingest.
    """

    def __init__(self, config: AppConfig, ingest_manager=None):
        """Initialize recorder with configuration."""
        self.config = config
        self.ingest_manager = ingest_manager  # Reference to IngestManager for status checks
        self.pipelines: Dict[str, Any] = {}  # Gst.Pipeline objects
        self.states: Dict[str, str] = {}  # 'idle', 'recording', 'error'
        self.recording_files: Dict[str, str] = {}  # Track output file paths
        self.loop = None
        self._gst_ready = False
        
        # Session management
        self.current_session_id: Optional[str] = None
        self.session_start_time: Optional[datetime] = None
        self.session_metadata: Dict[str, Any] = {}
        
        # Monitoring threads
        self._recording_active = False
        self._disk_monitor_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None

        # Initialize states (don't init GStreamer yet - lazy load)
        for cam_id in config.cameras.keys():
            self.states[cam_id] = "idle"
    
    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized before use."""
        if self._gst_ready:
            return True
        
        if ensure_gst_initialized():
            self._gst_ready = True
            # Clean up any stuck GStreamer processes
            self._cleanup_stuck_pipelines()
            return True
        
        logger.error("GStreamer initialization failed - recording not available")
        return False
    
    def _check_disk_space(self, min_gb: float = 10.0) -> tuple[bool, float]:
        """Check if sufficient disk space is available."""
        try:
            disk = shutil.disk_usage("/mnt/sdcard")
            free_gb = disk.free / (1024**3)
            return free_gb >= min_gb, free_gb
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return False, 0.0
    
    def _check_mediamtx_alive(self) -> bool:
        """Check if MediaMTX is responding."""
        try:
            # Check WebRTC endpoint (MediaMTX health indicator)
            response = httpx.get(
                f"http://localhost:8889/",
                timeout=2.0
            )
            return response.status_code < 500
        except Exception:
            logger.error("MediaMTX not responding")
            return False
    
    def _monitor_disk_space(self):
        """Background thread to monitor disk space during recording."""
        while self._recording_active:
            ok, free_gb = self._check_disk_space(min_gb=5.0)
            if not ok:
                logger.critical(f"Low disk space ({free_gb:.1f}GB) - stopping all recordings")
                self.stop_all_recordings()
                break
            time.sleep(30)  # Check every 30 seconds
    
    def _recording_watchdog(self):
        """Monitor recording health - detect stalled recordings."""
        last_sizes = {}
        stall_counts = {}
        
        while self._recording_active:
            for cam_id in list(self.pipelines.keys()):
                if self.states.get(cam_id) != "recording":
                    continue
                
                # Get current file size
                file_path = self.recording_files.get(cam_id)
                if not file_path or not os.path.exists(file_path):
                    continue
                
                try:
                    current_size = os.path.getsize(file_path)
                    last_size = last_sizes.get(cam_id, 0)
                    
                    if current_size == last_size and last_size > 0:
                        # File not growing
                        stall_counts[cam_id] = stall_counts.get(cam_id, 0) + 1
                        if stall_counts[cam_id] >= 3:  # 30 seconds of no growth
                            logger.warning(f"Recording stalled for {cam_id}, restarting...")
                            self._restart_recording(cam_id)
                            stall_counts[cam_id] = 0
                    else:
                        stall_counts[cam_id] = 0
                    
                    last_sizes[cam_id] = current_size
                except Exception as e:
                    logger.error(f"Error checking file size for {cam_id}: {e}")
            
            time.sleep(10)  # Check every 10 seconds
    
    def _restart_recording(self, cam_id: str):
        """Restart recording for a specific camera."""
        logger.info(f"Restarting recording for {cam_id}")
        try:
            self.stop_recording(cam_id)
            time.sleep(1)
            self.start_recording(cam_id)
        except Exception as e:
            logger.error(f"Failed to restart recording for {cam_id}: {e}")
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _create_session_metadata(self):
        """Create session metadata file."""
        if not self.current_session_id:
            return
        
        # Ensure sessions directory exists
        sessions_dir = Path("data/sessions")
        sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Create metadata
        self.session_metadata = {
            "session_id": self.current_session_id,
            "start_time": int(self.session_start_time.timestamp()) if self.session_start_time else None,
            "start_iso": self.session_start_time.isoformat() if self.session_start_time else None,
            "end_time": None,
            "status": "recording",
            "cameras": {},
            "external_cameras": {}
        }
        
        # Add camera info
        for cam_id, file_path in self.recording_files.items():
            self.session_metadata["cameras"][cam_id] = {
                "file": file_path,
                "status": self.states.get(cam_id, "unknown")
            }
        
        # Write to file
        metadata_path = sessions_dir / f"{self.current_session_id}.json"
        try:
            with open(metadata_path, 'w') as f:
                json.dump(self.session_metadata, f, indent=2)
            logger.info(f"Created session metadata: {metadata_path}")
        except Exception as e:
            logger.error(f"Failed to create session metadata: {e}")
    
    def _update_session_metadata(self):
        """Update session metadata file."""
        if not self.current_session_id:
            return
        
        sessions_dir = Path("data/sessions")
        metadata_path = sessions_dir / f"{self.current_session_id}.json"
        
        # Update camera statuses
        for cam_id in self.session_metadata.get("cameras", {}).keys():
            self.session_metadata["cameras"][cam_id]["status"] = self.states.get(cam_id, "unknown")
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(self.session_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update session metadata: {e}")
    
    def _finalize_session_metadata(self):
        """Finalize session metadata when recording stops."""
        if not self.current_session_id:
            return
        
        self.session_metadata["end_time"] = int(datetime.now().timestamp())
        self.session_metadata["status"] = "completed"
        
        # Update all camera statuses
        for cam_id in self.session_metadata.get("cameras", {}).keys():
            self.session_metadata["cameras"][cam_id]["status"] = "completed"
        
        sessions_dir = Path("data/sessions")
        metadata_path = sessions_dir / f"{self.current_session_id}.json"
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(self.session_metadata, f, indent=2)
            logger.info(f"Finalized session metadata: {metadata_path}")
        except Exception as e:
            logger.error(f"Failed to finalize session metadata: {e}")

    def start_recording(self, cam_id: str) -> bool:
        """Start recording for a specific camera by subscribing to its MediaMTX stream."""
        if not self._ensure_gst():
            logger.error("Cannot start recording - GStreamer not available")
            return False
        
        if cam_id not in self.config.cameras:
            logger.error(f"Camera {cam_id} not found in configuration")
            return False

        if self.states.get(cam_id) == "recording":
            logger.warning(f"Camera {cam_id} is already recording")
            return False
        
        # Check disk space before starting
        min_disk_gb = 10.0
        if hasattr(self.config, 'recording') and hasattr(self.config.recording, 'min_disk_space_gb'):
            min_disk_gb = self.config.recording.min_disk_space_gb
        ok, free_gb = self._check_disk_space(min_gb=min_disk_gb)
        if not ok:
            logger.error(f"Insufficient disk space: {free_gb:.1f}GB free, need {min_disk_gb}GB")
            return False
        
        # Check MediaMTX before starting
        if not self._check_mediamtx_alive():
            logger.error("Cannot start recording - MediaMTX not available")
            return False

        # Check if ingest is streaming for this camera
        if self.ingest_manager:
            ingest_status = self.ingest_manager.states.get(cam_id)
            if ingest_status != "streaming":
                logger.warning(
                    f"Cannot start recording for {cam_id} - ingest not streaming "
                    f"(status: {ingest_status})"
                )
                return False
        else:
            logger.warning(f"No ingest_manager available - cannot verify stream status for {cam_id}")

        # Stop existing pipeline if any
        if cam_id in self.pipelines:
            self._stop_pipeline(cam_id)
        
        # NO LONGER NEEDED: Device contention removed
        # Recording now subscribes to MediaMTX stream from ingest pipeline
        # Preview and recording can run simultaneously

        # Get camera config
        cam_config: CameraConfig = self.config.cameras[cam_id]

        # Format output path with timestamp if needed
        output_path_str = cam_config.output_path
        if "%" in output_path_str:
            output_path_str = datetime.now().strftime(output_path_str)

        # Ensure output directory exists
        output_path = Path(output_path_str)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build MediaMTX source URL (subscribe to ingest stream)
        # Use 127.0.0.1 instead of localhost to avoid IPv6 issues
        source_url = f"rtsp://127.0.0.1:{self.config.mediamtx.rtsp_port}/{cam_id}"

        # Build recording subscriber pipeline (reads from MediaMTX, not device)
        try:
            pipeline = build_recording_subscriber_pipeline(
                cam_id=cam_id,
                source_url=source_url,
                output_path=str(output_path),
                codec=cam_config.codec,
            )

            # Set up bus message handler
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message, cam_id)

            # Start pipeline
            Gst = get_gst()
            pipeline.set_state(Gst.State.PLAYING)
            self.pipelines[cam_id] = pipeline
            self.states[cam_id] = "recording"
            self.recording_files[cam_id] = str(output_path)

            # Recording now subscribes to MediaMTX ingest stream
            # No device access needed - completely independent of ingest

            logger.info(f"Started recording for camera {cam_id} (subscribing to {source_url})")
            return True

        except Exception as e:
            logger.error(f"Failed to start recording for {cam_id}: {e}")
            self.states[cam_id] = "error"
            return False

    def stop_recording(self, cam_id: str) -> bool:
        """Stop recording for a specific camera."""
        if cam_id not in self.states:
            logger.error(f"Camera {cam_id} not found")
            return False

        # If already idle, consider it successful (idempotent operation)
        if self.states.get(cam_id) != "recording":
            logger.debug(f"Camera {cam_id} is not recording (already idle)")
            # Clean up any orphaned pipeline references
            if cam_id in self.pipelines:
                try:
                    Gst = get_gst()
                    if Gst:
                        pipeline = self.pipelines[cam_id]
                        pipeline.set_state(Gst.State.NULL)
                    del self.pipelines[cam_id]
                except:
                    pass
            return True

        return self._stop_pipeline(cam_id)

    def _stop_pipeline(self, cam_id: str) -> bool:
        """Internal method to stop a pipeline."""
        if cam_id not in self.pipelines:
            return False

        Gst = get_gst()
        if not Gst:
            logger.error("GStreamer not available for stopping pipeline")
            return False

        pipeline = self.pipelines[cam_id]
        try:
            # Send EOS to flush the pipeline
            pipeline.send_event(Gst.Event.new_eos())

            # Wait for EOS or timeout
            bus = pipeline.get_bus()
            msg = bus.timed_pop_filtered(
                15 * Gst.SECOND,
                Gst.MessageType.EOS | Gst.MessageType.ERROR,
            )

            if msg and msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                logger.error(f"Pipeline error during stop for {cam_id}: {err.message}")

            # Set to NULL state
            pipeline.set_state(Gst.State.NULL)
            
            # Wait for state change
            ret = pipeline.get_state(Gst.CLOCK_TIME_NONE)
            if ret[0] == Gst.StateChangeReturn.ASYNC:
                pipeline.get_state(Gst.CLOCK_TIME_NONE)

            # Clean up
            del self.pipelines[cam_id]
            self.states[cam_id] = "idle"

            logger.info(f"Stopped recording for camera {cam_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping pipeline for {cam_id}: {e}")
            # Force stop
            try:
                pipeline.set_state(Gst.State.NULL)
                pipeline.get_state(Gst.CLOCK_TIME_NONE)
                del self.pipelines[cam_id]
            except:
                pass
            self.states[cam_id] = "error"
            return False

    def _on_bus_message(self, bus, message, cam_id: str) -> None:
        """Handle GStreamer bus messages."""
        Gst = get_gst()
        if not Gst:
            return
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Pipeline error for {cam_id}: {err.message} - {debug}")
            self.states[cam_id] = "error"
            # Try to restart if recoverable
            if "busy" not in err.message.lower() and "device" not in err.message.lower():
                logger.info(f"Attempting to restart pipeline for {cam_id} after error")
                try:
                    if cam_id in self.pipelines:
                        self._stop_pipeline(cam_id)
                    import time
                    time.sleep(1)
                    self.start_recording(cam_id)
                except Exception as e:
                    logger.error(f"Failed to restart pipeline for {cam_id}: {e}")
        elif message.type == Gst.MessageType.EOS:
            logger.info(f"End of stream for {cam_id}")
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipelines.get(cam_id):
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(
                    f"State changed for {cam_id}: {old_state.value_nick} -> {new_state.value_nick}"
                )
                if new_state == Gst.State.NULL and old_state == Gst.State.PLAYING:
                    if self.states.get(cam_id) == "recording":
                        logger.warning(f"Pipeline for {cam_id} unexpectedly went to NULL state during recording")
                        self.states[cam_id] = "error"
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Pipeline warning for {cam_id}: {warn.message} - {debug}")

    def get_status(self) -> Dict[str, str]:
        """Get status of all cameras."""
        return self.states.copy()

    def get_camera_status(self, cam_id: str) -> Optional[str]:
        """Get status of a specific camera."""
        return self.states.get(cam_id)
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current session status."""
        if not self.current_session_id:
            return {
                "active": False,
                "session_id": None,
                "start_time": None,
                "duration": 0,
                "cameras": {}
            }
        
        duration = (datetime.now() - self.session_start_time).total_seconds() if self.session_start_time else 0
        
        return {
            "active": True,
            "session_id": self.current_session_id,
            "start_time": self.session_start_time.isoformat() if self.session_start_time else None,
            "duration": int(duration),
            "cameras": {
                cam_id: {
                    "status": self.states.get(cam_id, "unknown"),
                    "file": self.recording_files.get(cam_id)
                }
                for cam_id in self.config.cameras.keys()
            }
        }

    def start_all_recordings(self) -> Dict[str, bool]:
        """Start recording for all cameras with session management."""
        # Generate session ID
        self.current_session_id = self._generate_session_id()
        self.session_start_time = datetime.now()
        logger.info(f"Starting recording session: {self.current_session_id}")
        
        # Start recording for all cameras
        results = {}
        for cam_id in self.config.cameras.keys():
            results[cam_id] = self.start_recording(cam_id)
        
        # Create session metadata
        self._create_session_metadata()
        
        # Start monitoring threads
        self._recording_active = True
        self._disk_monitor_thread = threading.Thread(target=self._monitor_disk_space, daemon=True)
        self._disk_monitor_thread.start()
        
        self._watchdog_thread = threading.Thread(target=self._recording_watchdog, daemon=True)
        self._watchdog_thread.start()
        
        return results

    def stop_all_recordings(self) -> Dict[str, bool]:
        """Stop recording for all cameras and finalize session."""
        logger.info(f"Stopping recording session: {self.current_session_id}")
        
        # Stop monitoring threads
        self._recording_active = False
        
        # Stop all recordings
        results = {}
        for cam_id in list(self.pipelines.keys()):
            results[cam_id] = self.stop_recording(cam_id)
        
        # Finalize session metadata
        self._finalize_session_metadata()
        
        # Clear session info
        self.current_session_id = None
        self.session_start_time = None
        self.recording_files.clear()
        
        return results

    def _cleanup_stuck_pipelines(self) -> None:
        """Kill any stuck GStreamer processes."""
        import subprocess
        try:
            result = subprocess.run(
                ["pgrep", "-f", "gst-launch.*video60"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    if pid:
                        try:
                            subprocess.run(["kill", "-9", pid], check=False)
                            logger.info(f"Killed stuck GStreamer process: {pid}")
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Could not cleanup stuck pipelines: {e}")
