"""Subscriber-based recorder for recording from MediaMTX streams.

The SubscriberRecorder is the SUBSCRIBER in the pub/sub architecture:
- It does NOT access V4L2 devices directly
- Subscribes to MediaMTX RTSP streams published by IngestManager
- Records by remuxing the already-encoded H.264 stream (NO re-encoding!)
- Independent of ingest - can start/stop without affecting preview

This decouples recording from device access, enabling:
- Preview during recording (both subscribe to same stream)
- Simultaneous multi-camera recording without VPU contention
- Recording start/stop without pipeline restart
"""
import asyncio
import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, List

from .config import get_config, get_enabled_cameras
from .gstreamer.pipelines import build_subscriber_recording_pipeline_string

logger = logging.getLogger(__name__)


# Default recording directory
RECORDINGS_DIR = Path("/mnt/sdcard/recordings")


@dataclass
class RecordingInfo:
    """Information about an active recording."""
    cam_id: str
    output_path: str
    start_time: datetime
    state: str = "recording"  # recording, stopped, error
    bytes_written: int = 0
    error_message: Optional[str] = None


@dataclass
class RecordingSession:
    """A recording session containing multiple camera recordings."""
    session_id: str
    started_at: datetime
    recordings: Dict[str, RecordingInfo] = field(default_factory=dict)
    state: str = "recording"  # recording, stopped, error


class SubscriberRecorder:
    """Records from MediaMTX RTSP streams (subscriber pattern).
    
    Key features:
    - NO device access: Subscribes to MediaMTX streams only
    - Zero re-encoding: Just remuxes existing H.264 stream
    - Independent of ingest: Start/stop without affecting preview
    - Session management: Groups recordings with session IDs
    - Disk space monitoring: Prevents recording when disk is full
    - Stall detection: Monitors file growth and reports issues
    """

    def __init__(
        self,
        on_status_change: Optional[Callable[[str, RecordingInfo], None]] = None,
        on_session_event: Optional[Callable[[str, str, dict], None]] = None,
    ):
        """Initialize subscriber recorder.
        
        Args:
            on_status_change: Callback when recording status changes
            on_session_event: Callback for session events (started, stopped, error)
        """
        self.config = get_config()
        self.on_status_change = on_status_change
        self.on_session_event = on_session_event
        
        self.pipelines: Dict[str, Any] = {}  # Gst.Pipeline objects
        self.recordings: Dict[str, RecordingInfo] = {}
        self.current_session: Optional[RecordingSession] = None
        
        self._gst = None
        self._gst_ready = False
        self._monitor_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized."""
        if self._gst_ready:
            return True
        
        try:
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst
            
            if not Gst.is_initialized():
                Gst.init(None)
            
            self._gst = Gst
            self._gst_ready = True
            return True
        except Exception as e:
            logger.error(f"GStreamer initialization failed: {e}")
            return False

    def _get_rtsp_url(self, cam_id: str) -> str:
        """Get RTSP URL for a camera stream."""
        rtsp_port = getattr(self.config, 'mediamtx_rtsp_port', 8554)
        return f"rtsp://127.0.0.1:{rtsp_port}/{cam_id}"

    def _check_disk_space(self, min_gb: float = 5.0) -> tuple[bool, float]:
        """Check if sufficient disk space is available.
        
        Args:
            min_gb: Minimum required GB
            
        Returns:
            Tuple of (sufficient, free_gb)
        """
        try:
            disk = shutil.disk_usage(RECORDINGS_DIR)
            free_gb = disk.free / (1024**3)
            return free_gb >= min_gb, free_gb
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            # Try parent directory
            try:
                disk = shutil.disk_usage("/mnt")
                free_gb = disk.free / (1024**3)
                return free_gb >= min_gb, free_gb
            except:
                return False, 0.0

    def _generate_output_path(self, cam_id: str, session_id: str) -> Path:
        """Generate output file path for a recording.
        
        Args:
            cam_id: Camera identifier
            session_id: Recording session ID
            
        Returns:
            Path to output file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        return RECORDINGS_DIR / f"{session_id}_{cam_id}_{timestamp}.mp4"

    def _notify_status_change(self, cam_id: str) -> None:
        """Notify listeners of status change."""
        if self.on_status_change:
            recording = self.recordings.get(cam_id)
            if recording:
                try:
                    self.on_status_change(cam_id, recording)
                except Exception as e:
                    logger.error(f"Error in status change callback: {e}")

    def _notify_session_event(self, event_type: str, data: dict) -> None:
        """Notify listeners of session event."""
        if self.on_session_event and self.current_session:
            try:
                self.on_session_event(self.current_session.session_id, event_type, data)
            except Exception as e:
                logger.error(f"Error in session event callback: {e}")

    def start_recording(self, cam_id: str, session_id: Optional[str] = None) -> bool:
        """Start recording for a camera by subscribing to its MediaMTX stream.
        
        Args:
            cam_id: Camera identifier
            session_id: Optional session ID (auto-generated if not provided)
            
        Returns:
            True if recording started successfully
        """
        if not self._ensure_gst():
            logger.error("Cannot start recording - GStreamer not available")
            return False
        
        # Check if already recording
        with self._lock:
            if cam_id in self.recordings and self.recordings[cam_id].state == "recording":
                logger.warning(f"Camera {cam_id} is already recording")
                return True
        
        # Check disk space
        ok, free_gb = self._check_disk_space(min_gb=5.0)
        if not ok:
            logger.error(f"Insufficient disk space: {free_gb:.1f}GB free")
            return False
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        
        # Create or update session
        with self._lock:
            if self.current_session is None or self.current_session.session_id != session_id:
                self.current_session = RecordingSession(
                    session_id=session_id,
                    started_at=datetime.now(),
                )
        
        # Generate output path
        output_path = self._generate_output_path(cam_id, session_id)
        
        # Get RTSP source URL
        source_url = self._get_rtsp_url(cam_id)
        
        try:
            # Build recording pipeline
            pipeline_str = build_subscriber_recording_pipeline_string(
                cam_id=cam_id,
                source_url=source_url,
                output_path=str(output_path),
            )
            
            logger.info(f"Starting recording for {cam_id}: {pipeline_str}")
            
            Gst = self._gst
            pipeline = Gst.parse_launch(pipeline_str)
            
            # Set up bus message handler
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message, cam_id)
            
            # Start pipeline
            ret = pipeline.set_state(Gst.State.PLAYING)
            
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error(f"Failed to start recording pipeline for {cam_id}")
                pipeline.set_state(Gst.State.NULL)
                return False
            
            # Wait briefly for pipeline to start
            time.sleep(0.3)
            
            # Create recording info
            recording = RecordingInfo(
                cam_id=cam_id,
                output_path=str(output_path),
                start_time=datetime.now(),
                state="recording",
            )
            
            with self._lock:
                self.pipelines[cam_id] = pipeline
                self.recordings[cam_id] = recording
                if self.current_session:
                    self.current_session.recordings[cam_id] = recording
            
            logger.info(f"Recording started for {cam_id}: {output_path}")
            self._notify_status_change(cam_id)
            
            # Start monitoring thread if not running
            self._start_monitor()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start recording for {cam_id}: {e}")
            with self._lock:
                if cam_id in self.recordings:
                    self.recordings[cam_id].state = "error"
                    self.recordings[cam_id].error_message = str(e)
            self._notify_status_change(cam_id)
            return False

    def stop_recording(self, cam_id: str) -> bool:
        """Stop recording for a camera.
        
        Args:
            cam_id: Camera identifier
            
        Returns:
            True if stopped successfully
        """
        with self._lock:
            recording = self.recordings.get(cam_id)
            if not recording or recording.state != "recording":
                logger.debug(f"Camera {cam_id} is not recording")
                return True
            
            pipeline = self.pipelines.get(cam_id)
            if not pipeline:
                recording.state = "stopped"
                return True
        
        try:
            Gst = self._gst
            if Gst:
                # Send EOS for clean file closure
                pipeline.send_event(Gst.Event.new_eos())
                
                # Wait for EOS or timeout
                bus = pipeline.get_bus()
                msg = bus.timed_pop_filtered(
                    10 * Gst.SECOND,
                    Gst.MessageType.EOS | Gst.MessageType.ERROR,
                )
                
                if msg and msg.type == Gst.MessageType.ERROR:
                    err, debug = msg.parse_error()
                    logger.warning(f"Error during recording stop for {cam_id}: {err.message}")
                
                # Stop pipeline
                pipeline.set_state(Gst.State.NULL)
                pipeline.get_state(Gst.CLOCK_TIME_NONE)
            
            with self._lock:
                del self.pipelines[cam_id]
                recording.state = "stopped"
            
            logger.info(f"Recording stopped for {cam_id}")
            self._notify_status_change(cam_id)
            return True
            
        except Exception as e:
            logger.error(f"Error stopping recording for {cam_id}: {e}")
            with self._lock:
                if cam_id in self.pipelines:
                    try:
                        self.pipelines[cam_id].set_state(self._gst.State.NULL)
                        del self.pipelines[cam_id]
                    except:
                        pass
                if cam_id in self.recordings:
                    self.recordings[cam_id].state = "error"
                    self.recordings[cam_id].error_message = str(e)
            return False

    def start_session(
        self,
        session_id: Optional[str] = None,
        camera_ids: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Start a recording session for multiple cameras.
        
        Args:
            session_id: Optional session ID
            camera_ids: List of camera IDs to record (default: all enabled)
            
        Returns:
            Dict mapping cam_id to success boolean
        """
        if session_id is None:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        
        # Get cameras to record
        if camera_ids is None:
            enabled_cameras = get_enabled_cameras(self.config)
            camera_ids = list(enabled_cameras.keys())
        
        # Create session
        with self._lock:
            self.current_session = RecordingSession(
                session_id=session_id,
                started_at=datetime.now(),
            )
        
        # Start recording for each camera
        results = {}
        for cam_id in camera_ids:
            results[cam_id] = self.start_recording(cam_id, session_id)
        
        # Notify session started
        self._notify_session_event("started", {
            "cameras": camera_ids,
            "results": results,
        })
        
        return results

    def stop_session(self) -> Dict[str, bool]:
        """Stop the current recording session.
        
        Returns:
            Dict mapping cam_id to success boolean
        """
        results = {}
        
        with self._lock:
            camera_ids = list(self.recordings.keys())
        
        for cam_id in camera_ids:
            results[cam_id] = self.stop_recording(cam_id)
        
        # Finalize session
        with self._lock:
            if self.current_session:
                self.current_session.state = "stopped"
                session_id = self.current_session.session_id
            else:
                session_id = None
        
        # Notify session stopped
        if session_id:
            self._notify_session_event("stopped", {
                "results": results,
            })
        
        # Stop monitor
        self._stop_monitor()
        
        return results

    def get_status(self) -> Dict[str, Any]:
        """Get current recording status.
        
        Returns:
            Dict with session and recording status
        """
        with self._lock:
            session_info = None
            if self.current_session:
                session_info = {
                    "session_id": self.current_session.session_id,
                    "started_at": self.current_session.started_at.isoformat(),
                    "state": self.current_session.state,
                }
            
            recordings = {}
            for cam_id, recording in self.recordings.items():
                recordings[cam_id] = {
                    "state": recording.state,
                    "output_path": recording.output_path,
                    "start_time": recording.start_time.isoformat(),
                    "bytes_written": recording.bytes_written,
                    "error_message": recording.error_message,
                }
            
            return {
                "session": session_info,
                "recordings": recordings,
                "recording": len([r for r in self.recordings.values() if r.state == "recording"]) > 0,
            }

    def _on_bus_message(self, bus, message, cam_id: str) -> None:
        """Handle GStreamer bus messages."""
        Gst = self._gst
        if not Gst:
            return
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Recording error for {cam_id}: {err.message} - {debug}")
            
            with self._lock:
                if cam_id in self.recordings:
                    self.recordings[cam_id].state = "error"
                    self.recordings[cam_id].error_message = err.message
                
                if cam_id in self.pipelines:
                    try:
                        self.pipelines[cam_id].set_state(Gst.State.NULL)
                    except:
                        pass
                    del self.pipelines[cam_id]
            
            self._notify_status_change(cam_id)
            
        elif message.type == Gst.MessageType.EOS:
            logger.info(f"Recording EOS for {cam_id}")
            
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Recording warning for {cam_id}: {warn.message}")

    def _start_monitor(self) -> None:
        """Start background monitor thread."""
        if self._monitor_running:
            return
        
        self._monitor_running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="recording-monitor"
        )
        self._monitor_thread.start()
        logger.debug("Started recording monitor thread")

    def _stop_monitor(self) -> None:
        """Stop background monitor thread."""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None

    def _monitor_loop(self) -> None:
        """Background thread that monitors recordings."""
        last_sizes: Dict[str, int] = {}
        stall_counts: Dict[str, int] = {}
        
        while self._monitor_running:
            try:
                # Check disk space
                ok, free_gb = self._check_disk_space(min_gb=1.0)
                if not ok:
                    logger.critical(f"Critical disk space: {free_gb:.1f}GB - stopping recordings")
                    self.stop_session()
                    break
                
                # Check file growth for each recording
                with self._lock:
                    recordings = list(self.recordings.items())
                
                for cam_id, recording in recordings:
                    if recording.state != "recording":
                        continue
                    
                    try:
                        current_size = os.path.getsize(recording.output_path)
                        recording.bytes_written = current_size
                        
                        last_size = last_sizes.get(cam_id, 0)
                        if current_size == last_size and last_size > 0:
                            # File not growing
                            stall_counts[cam_id] = stall_counts.get(cam_id, 0) + 1
                            if stall_counts[cam_id] >= 3:
                                logger.warning(f"Recording stalled for {cam_id}")
                                self._notify_session_event("stall", {"cam_id": cam_id})
                        else:
                            stall_counts[cam_id] = 0
                        
                        last_sizes[cam_id] = current_size
                        
                    except FileNotFoundError:
                        pass  # File not created yet
                    except Exception as e:
                        logger.debug(f"Error checking file size for {cam_id}: {e}")
                
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            
            time.sleep(5)


# Singleton instance
_subscriber_recorder: Optional[SubscriberRecorder] = None


def get_subscriber_recorder(
    on_status_change: Optional[Callable[[str, RecordingInfo], None]] = None,
    on_session_event: Optional[Callable[[str, str, dict], None]] = None,
) -> SubscriberRecorder:
    """Get or create the SubscriberRecorder singleton.
    
    Args:
        on_status_change: Optional callback for status changes
        on_session_event: Optional callback for session events
        
    Returns:
        SubscriberRecorder instance
    """
    global _subscriber_recorder
    if _subscriber_recorder is None:
        _subscriber_recorder = SubscriberRecorder(
            on_status_change=on_status_change,
            on_session_event=on_session_event,
        )
    else:
        if on_status_change:
            _subscriber_recorder.on_status_change = on_status_change
        if on_session_event:
            _subscriber_recorder.on_session_event = on_session_event
    return _subscriber_recorder

