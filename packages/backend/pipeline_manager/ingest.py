"""Ingest pipeline manager for always-on video capture and streaming.

The IngestManager is the PUBLISHER in the pub/sub architecture:
- It owns the V4L2 devices (camera inputs)
- Encodes video to H.264 using hardware encoders
- Streams to MediaMTX via RTSP
- Never stops during recording (always-on)

All consumers (preview, recording, mixer) SUBSCRIBE to MediaMTX streams.
This decouples device access from consumption.
"""
import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .config import CameraConfig, get_config, get_enabled_cameras
from .gstreamer.pipelines import (
    build_ingest_pipeline_string,
    get_device_capabilities,
    initialize_rkcif_device,
    RKCIF_SUBDEV_MAP,
    get_subdev_resolution,
)

logger = logging.getLogger(__name__)


@dataclass
class IngestStatus:
    """Status information for an ingest pipeline."""
    status: str  # 'idle', 'streaming', 'no_signal', 'error', 'starting'
    resolution: Optional[tuple[int, int]] = None
    framerate: Optional[int] = None
    has_signal: bool = False
    stream_url: Optional[str] = None
    error_message: Optional[str] = None
    uptime_seconds: float = 0


@dataclass
class IngestPipeline:
    """Holds state for a single ingest pipeline."""
    cam_id: str
    device: str
    pipeline: Any = None  # Gst.Pipeline
    state: str = "idle"  # idle, starting, streaming, no_signal, error
    resolution: Optional[tuple[int, int]] = None
    framerate: Optional[int] = None
    start_time: Optional[float] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    last_signal_check: float = 0


class IngestManager:
    """Manages always-on ingest pipelines for all cameras.
    
    The IngestManager owns the V4L2 devices and streams to MediaMTX.
    All consumers (preview, recording, mixer) subscribe to MediaMTX streams.
    
    Key features:
    - Always-on: Ingest pipelines never stop during recording
    - Hot-plug support: Handles signal loss/recovery gracefully
    - Resolution change detection: Restarts pipeline on resolution change
    - H.264-only: Uses hardware encoder for browser compatibility
    """

    def __init__(
        self,
        on_status_change: Optional[Callable[[str, IngestStatus], None]] = None,
    ):
        """Initialize ingest manager.
        
        Args:
            on_status_change: Callback when pipeline status changes
        """
        self.config = get_config()
        self.pipelines: Dict[str, IngestPipeline] = {}
        self.on_status_change = on_status_change
        
        self._gst = None
        self._gst_ready = False
        self._health_check_running = False
        self._health_check_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Initialize pipeline states for all enabled cameras
        enabled_cameras = get_enabled_cameras(self.config)
        for cam_id, cam_config in enabled_cameras.items():
            self.pipelines[cam_id] = IngestPipeline(
                cam_id=cam_id,
                device=cam_config.device,
            )

    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized."""
        if self._gst_ready:
            return True
        
        try:
            import os
            # Enable RGA hardware acceleration for videoscale/videoconvert
            # This MUST be set before GStreamer is initialized!
            os.environ['GST_VIDEO_CONVERT_USE_RGA'] = '1'
            
            import gi
            gi.require_version('Gst', '1.0')
            from gi.repository import Gst
            
            if not Gst.is_initialized():
                Gst.init(None)
            
            logger.info(f"GStreamer initialized with RGA enabled (GST_VIDEO_CONVERT_USE_RGA={os.environ.get('GST_VIDEO_CONVERT_USE_RGA')})")
            
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

    def _notify_status_change(self, cam_id: str) -> None:
        """Notify listeners of status change."""
        if self.on_status_change:
            status = self.get_pipeline_status(cam_id)
            if status:
                try:
                    self.on_status_change(cam_id, status)
                except Exception as e:
                    logger.error(f"Error in status change callback: {e}")

    def start_ingest(self, cam_id: str) -> bool:
        """Start ingest pipeline for a camera.
        
        Args:
            cam_id: Camera identifier (e.g., "cam0")
            
        Returns:
            True if pipeline started successfully
        """
        if not self._ensure_gst():
            logger.error("Cannot start ingest - GStreamer not available")
            return False
        
        enabled_cameras = get_enabled_cameras(self.config)
        if cam_id not in enabled_cameras:
            logger.error(f"Camera {cam_id} not found in configuration")
            return False
        
        with self._lock:
            pipeline_info = self.pipelines.get(cam_id)
            if not pipeline_info:
                cam_config = enabled_cameras[cam_id]
                pipeline_info = IngestPipeline(
                    cam_id=cam_id,
                    device=cam_config.device,
                )
                self.pipelines[cam_id] = pipeline_info
            
            if pipeline_info.state == "streaming":
                logger.warning(f"Camera {cam_id} is already streaming")
                return True
            
            pipeline_info.state = "starting"
        
        cam_config = enabled_cameras[cam_id]
        device = cam_config.device
        
        # Initialize rkcif devices (required for LT6911 HDMI bridges)
        try:
            if device in RKCIF_SUBDEV_MAP:
                caps = initialize_rkcif_device(device)
            else:
                caps = get_device_capabilities(device)
        except Exception as e:
            logger.error(f"Failed to get device capabilities for {cam_id}: {e}")
            with self._lock:
                pipeline_info.state = "error"
                pipeline_info.error_message = str(e)
            self._notify_status_change(cam_id)
            return False
        
        # Check for signal
        if not caps.get('has_signal', False):
            logger.info(f"No HDMI signal on {cam_id} ({device})")
            with self._lock:
                pipeline_info.state = "no_signal"
                pipeline_info.resolution = None
                pipeline_info.framerate = None
            self._notify_status_change(cam_id)
            return False
        
        # Build ingest pipeline
        try:
            rtsp_port = getattr(self.config, 'mediamtx_rtsp_port', 8554)
            pipeline_str = build_ingest_pipeline_string(
                cam_id=cam_id,
                device=device,
                resolution=cam_config.resolution,
                bitrate=cam_config.bitrate,
                rtsp_port=rtsp_port,
            )
            
            logger.info(f"Starting ingest for {cam_id}: {pipeline_str}")
            
            Gst = self._gst
            pipeline = Gst.parse_launch(pipeline_str)
            
            # Set up bus message handler
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message, cam_id)
            
            # Start pipeline
            ret = pipeline.set_state(Gst.State.PLAYING)
            
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error(f"Failed to set pipeline to PLAYING for {cam_id}")
                pipeline.set_state(Gst.State.NULL)
                with self._lock:
                    pipeline_info.state = "error"
                    pipeline_info.error_message = "Pipeline failed to start"
                self._notify_status_change(cam_id)
                return False
            
            # Wait briefly and verify state
            time.sleep(0.5)
            state_ret, current, pending = pipeline.get_state(Gst.SECOND)
            
            if state_ret == Gst.StateChangeReturn.FAILURE:
                logger.error(f"Pipeline failed to reach PLAYING for {cam_id}")
                # Check for error messages
                msg = bus.pop_filtered(Gst.MessageType.ERROR)
                if msg:
                    err, debug = msg.parse_error()
                    logger.error(f"Pipeline error: {err.message} - {debug}")
                    with self._lock:
                        pipeline_info.error_message = err.message
                pipeline.set_state(Gst.State.NULL)
                with self._lock:
                    pipeline_info.state = "error"
                self._notify_status_change(cam_id)
                return False
            
            # Success!
            with self._lock:
                pipeline_info.pipeline = pipeline
                pipeline_info.state = "streaming"
                pipeline_info.start_time = time.time()
                pipeline_info.error_message = None
                pipeline_info.retry_count = 0
                pipeline_info.resolution = (caps.get('width', 0), caps.get('height', 0))
                pipeline_info.framerate = caps.get('framerate', 30)
            
            logger.info(f"Ingest started for {cam_id}: {caps.get('width')}x{caps.get('height')}")
            self._notify_status_change(cam_id)
            
            # Start health check thread if not running
            self._start_health_check()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start ingest for {cam_id}: {e}")
            with self._lock:
                pipeline_info.state = "error"
                pipeline_info.error_message = str(e)
            self._notify_status_change(cam_id)
            return False

    def stop_ingest(self, cam_id: str) -> bool:
        """Stop ingest pipeline for a camera.
        
        Args:
            cam_id: Camera identifier
            
        Returns:
            True if pipeline stopped successfully
        """
        with self._lock:
            pipeline_info = self.pipelines.get(cam_id)
            if not pipeline_info:
                return False
            
            if pipeline_info.state not in ("streaming", "starting"):
                # Already stopped or in error state
                pipeline_info.state = "idle"
                return True
            
            pipeline = pipeline_info.pipeline
            if not pipeline:
                pipeline_info.state = "idle"
                return True
        
        try:
            Gst = self._gst
            if Gst:
                pipeline.set_state(Gst.State.NULL)
                pipeline.get_state(Gst.CLOCK_TIME_NONE)
            
            with self._lock:
                pipeline_info.pipeline = None
                pipeline_info.state = "idle"
                pipeline_info.start_time = None
            
            logger.info(f"Stopped ingest for {cam_id}")
            self._notify_status_change(cam_id)
            return True
            
        except Exception as e:
            logger.error(f"Error stopping ingest for {cam_id}: {e}")
            with self._lock:
                pipeline_info.state = "error"
                pipeline_info.error_message = str(e)
            return False

    def start_all(self) -> Dict[str, bool]:
        """Start ingest for all enabled cameras with signal.
        
        Returns:
            Dict mapping cam_id to success boolean
        """
        results = {}
        enabled_cameras = get_enabled_cameras(self.config)
        
        for cam_id in enabled_cameras.keys():
            results[cam_id] = self.start_ingest(cam_id)
            # Small delay between starts to avoid overwhelming the VPU
            time.sleep(0.2)
        
        return results

    def stop_all(self) -> Dict[str, bool]:
        """Stop ingest for all cameras.
        
        Returns:
            Dict mapping cam_id to success boolean
        """
        results = {}
        for cam_id in list(self.pipelines.keys()):
            results[cam_id] = self.stop_ingest(cam_id)
        return results

    def get_pipeline_status(self, cam_id: str) -> Optional[IngestStatus]:
        """Get status for a specific pipeline.
        
        Args:
            cam_id: Camera identifier
            
        Returns:
            IngestStatus or None if not found
        """
        with self._lock:
            pipeline_info = self.pipelines.get(cam_id)
            if not pipeline_info:
                return None
            
            uptime = 0.0
            if pipeline_info.state == "streaming" and pipeline_info.start_time:
                uptime = time.time() - pipeline_info.start_time
            
            stream_url = None
            if pipeline_info.state == "streaming":
                stream_url = self._get_rtsp_url(cam_id)
            
            return IngestStatus(
                status=pipeline_info.state,
                resolution=pipeline_info.resolution,
                framerate=pipeline_info.framerate,
                has_signal=pipeline_info.state not in ("no_signal", "idle"),
                stream_url=stream_url,
                error_message=pipeline_info.error_message,
                uptime_seconds=uptime,
            )

    def get_all_statuses(self) -> Dict[str, IngestStatus]:
        """Get status for all pipelines.
        
        Returns:
            Dict mapping cam_id to IngestStatus
        """
        statuses = {}
        for cam_id in self.pipelines.keys():
            status = self.get_pipeline_status(cam_id)
            if status:
                statuses[cam_id] = status
        return statuses

    def _on_bus_message(self, bus, message, cam_id: str) -> None:
        """Handle GStreamer bus messages."""
        Gst = self._gst
        if not Gst:
            return
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Ingest error for {cam_id}: {err.message} - {debug}")
            
            with self._lock:
                pipeline_info = self.pipelines.get(cam_id)
                if pipeline_info:
                    pipeline_info.state = "error"
                    pipeline_info.error_message = err.message
                    
                    # Clean up pipeline
                    if pipeline_info.pipeline:
                        try:
                            pipeline_info.pipeline.set_state(Gst.State.NULL)
                        except:
                            pass
                        pipeline_info.pipeline = None
                    
                    # Schedule retry with exponential backoff
                    retry_count = pipeline_info.retry_count
                    if retry_count < 3:
                        pipeline_info.retry_count = retry_count + 1
                        delay = min(2.0 * (2 ** retry_count), 10.0)
                        logger.info(f"Scheduling retry for {cam_id} in {delay}s (attempt {retry_count + 1}/3)")
                        threading.Timer(delay, lambda: self.start_ingest(cam_id)).start()
            
            self._notify_status_change(cam_id)
            
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Ingest warning for {cam_id}: {warn.message}")
            
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipelines.get(cam_id, IngestPipeline("", "")).pipeline:
                old, new, pending = message.parse_state_changed()
                logger.debug(f"Ingest state for {cam_id}: {old.value_nick} -> {new.value_nick}")

    def _start_health_check(self) -> None:
        """Start background health check thread."""
        if self._health_check_running:
            return
        
        self._health_check_running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="ingest-health-check"
        )
        self._health_check_thread.start()
        logger.info("Started ingest health check thread")

    def stop_health_check(self) -> None:
        """Stop background health check thread."""
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2)
            self._health_check_thread = None

    def _health_check_loop(self) -> None:
        """Background thread that monitors pipeline health."""
        check_interval = 5  # seconds
        
        while self._health_check_running:
            try:
                self._check_all_pipelines()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            # Sleep in small increments for quick shutdown
            for _ in range(check_interval):
                if not self._health_check_running:
                    break
                time.sleep(1)

    def _check_all_pipelines(self) -> None:
        """Check health of all pipelines and handle signal changes."""
        enabled_cameras = get_enabled_cameras(self.config)
        
        for cam_id, pipeline_info in list(self.pipelines.items()):
            cam_config = enabled_cameras.get(cam_id)
            if not cam_config:
                continue
            
            device = cam_config.device
            current_state = pipeline_info.state
            
            # Check signal status
            try:
                if device in RKCIF_SUBDEV_MAP:
                    resolution = get_subdev_resolution(device)
                    has_signal = resolution is not None and resolution != (0, 0)
                else:
                    caps = get_device_capabilities(device)
                    has_signal = caps.get('has_signal', False)
                    resolution = (caps.get('width', 0), caps.get('height', 0)) if has_signal else None
            except Exception as e:
                logger.debug(f"Error checking signal for {cam_id}: {e}")
                continue
            
            # Handle signal loss
            if current_state == "streaming" and not has_signal:
                logger.warning(f"{cam_id}: Signal lost, stopping ingest")
                self.stop_ingest(cam_id)
                with self._lock:
                    pipeline_info.state = "no_signal"
                self._notify_status_change(cam_id)
                continue
            
            # Handle signal recovery
            if current_state == "no_signal" and has_signal:
                logger.info(f"{cam_id}: Signal recovered ({resolution[0]}x{resolution[1]}), starting ingest")
                # Re-initialize device before starting
                if device in RKCIF_SUBDEV_MAP:
                    try:
                        initialize_rkcif_device(device)
                    except Exception as e:
                        logger.warning(f"Failed to reinitialize {device}: {e}")
                time.sleep(0.3)  # Brief delay for signal stability
                self.start_ingest(cam_id)
                continue
            
            # Handle resolution change
            if current_state == "streaming" and resolution:
                current_res = pipeline_info.resolution
                if current_res and current_res != resolution:
                    logger.info(f"{cam_id}: Resolution changed {current_res} -> {resolution}, restarting")
                    self.stop_ingest(cam_id)
                    if device in RKCIF_SUBDEV_MAP:
                        try:
                            initialize_rkcif_device(device)
                        except Exception as e:
                            logger.warning(f"Failed to reinitialize {device}: {e}")
                    time.sleep(0.3)
                    self.start_ingest(cam_id)


# Singleton instance
_ingest_manager: Optional[IngestManager] = None


def get_ingest_manager(
    on_status_change: Optional[Callable[[str, IngestStatus], None]] = None,
) -> IngestManager:
    """Get or create the IngestManager singleton.
    
    Args:
        on_status_change: Optional callback for status changes
        
    Returns:
        IngestManager instance
    """
    global _ingest_manager
    if _ingest_manager is None:
        _ingest_manager = IngestManager(on_status_change=on_status_change)
    elif on_status_change:
        _ingest_manager.on_status_change = on_status_change
    return _ingest_manager

