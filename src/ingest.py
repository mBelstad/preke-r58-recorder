"""Ingest pipeline manager for always-on video capture."""
import logging
import threading
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass

from .config import AppConfig, CameraConfig
from .pipelines import build_ingest_pipeline
from .gst_utils import ensure_gst_initialized, get_gst

logger = logging.getLogger(__name__)


@dataclass
class IngestStatus:
    """Status information for an ingest pipeline."""
    status: str  # 'idle', 'streaming', 'no_signal', 'error'
    resolution: Optional[tuple[int, int]] = None
    has_signal: bool = False
    stream_url: Optional[str] = None
    error_message: Optional[str] = None


class IngestManager:
    """Manages always-on ingest pipelines for all cameras.
    
    The IngestManager owns the V4L2 devices and streams to MediaMTX.
    All consumers (preview, recording, mixer) subscribe to MediaMTX streams.
    """

    def __init__(self, config: AppConfig):
        """Initialize ingest manager."""
        self.config = config
        self.pipelines: Dict[str, Any] = {}  # Gst.Pipeline objects
        self.states: Dict[str, str] = {}  # 'idle', 'streaming', 'no_signal', 'error'
        self.pipeline_start_times: Dict[str, float] = {}
        self.last_health_check: Dict[str, float] = {}
        self.current_resolutions: Dict[str, tuple[int, int]] = {}
        self.signal_states: Dict[str, bool] = {}
        self.signal_loss_times: Dict[str, Optional[float]] = {}
        self.error_retry_count: Dict[str, int] = {}
        self._gst_ready = False
        self._health_check_running = False
        self._health_check_thread: Optional[threading.Thread] = None

        # Initialize states
        for cam_id in config.cameras.keys():
            self.states[cam_id] = "idle"
            self.signal_states[cam_id] = True
            self.signal_loss_times[cam_id] = None

    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized before use."""
        if self._gst_ready:
            return True
        
        if ensure_gst_initialized():
            self._gst_ready = True
            return True
        
        logger.error("GStreamer initialization failed - ingest not available")
        return False

    def start_ingest(self, cam_id: str) -> bool:
        """Start ingest pipeline for a camera."""
        if not self._ensure_gst():
            logger.error("Cannot start ingest - GStreamer not available")
            return False
        
        if cam_id not in self.config.cameras:
            logger.error(f"Camera {cam_id} not found in configuration")
            return False

        if self.states.get(cam_id) == "streaming":
            logger.warning(f"Camera {cam_id} is already streaming")
            return False

        # Stop existing pipeline if any
        if cam_id in self.pipelines:
            self._stop_ingest(cam_id)
        
        cam_config: CameraConfig = self.config.cameras[cam_id]

        # Check if device has an active signal before starting
        from .device_detection import get_device_capabilities
        caps = get_device_capabilities(cam_config.device)
        if not caps.get('has_signal', False):
            logger.info(f"Skipping ingest start for {cam_id} - no HDMI signal detected")
            self.states[cam_id] = "no_signal"
            self.signal_states[cam_id] = False
            self.signal_loss_times[cam_id] = time.time()
            return False

        # Build MediaMTX path
        mediamtx_path = f"rtsp://localhost:{self.config.mediamtx.rtsp_port}/{cam_id}"

        # Build ingest pipeline
        try:
            pipeline = build_ingest_pipeline(
                platform=self.config.platform,
                cam_id=cam_id,
                device=cam_config.device,
                resolution=cam_config.resolution,
                bitrate=18000,  # 18Mbps for high-quality recording via subscriber
                codec=cam_config.codec,
                mediamtx_path=mediamtx_path,
            )

            # Set up bus message handler
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message, cam_id)

            # Start pipeline
            Gst = get_gst()
            ret = pipeline.set_state(Gst.State.PLAYING)
            
            if ret == Gst.StateChangeReturn.FAILURE:
                logger.error(f"Failed to set pipeline to PLAYING state for {cam_id}")
                pipeline.set_state(Gst.State.NULL)
                self.states[cam_id] = "error"
                return False
            
            # Wait and verify
            time.sleep(0.5)
            state_ret, current_state, pending_state = pipeline.get_state(Gst.SECOND)
            
            if state_ret == Gst.StateChangeReturn.FAILURE:
                logger.error(f"Pipeline failed to reach PLAYING state for {cam_id}")
                bus = pipeline.get_bus()
                msg = bus.pop_filtered(Gst.MessageType.ERROR)
                if msg:
                    err, debug = msg.parse_error()
                    logger.error(f"Pipeline error for {cam_id}: {err.message} - {debug}")
                pipeline.set_state(Gst.State.NULL)
                self.states[cam_id] = "error"
                return False
            
            self.pipelines[cam_id] = pipeline
            self.states[cam_id] = "streaming"
            self.pipeline_start_times[cam_id] = time.time()
            self.last_health_check[cam_id] = time.time()
            self.signal_states[cam_id] = True
            self.signal_loss_times[cam_id] = None
            
            # Reset error retry count
            self.error_retry_count.pop(cam_id, None)
            
            # Store initial resolution
            try:
                from .device_detection import get_subdev_resolution
                initial_res = get_subdev_resolution(cam_config.device)
                if initial_res:
                    self.current_resolutions[cam_id] = initial_res
                    logger.info(f"Ingest started for {cam_id}: {initial_res[0]}x{initial_res[1]}")
            except Exception as e:
                logger.debug(f"Could not store initial resolution for {cam_id}: {e}")

            logger.info(f"Started ingest for camera {cam_id}")
            
            # Start health check thread if not running
            self._start_health_check()
            
            return True

        except Exception as e:
            logger.error(f"Failed to start ingest for {cam_id}: {e}")
            self.states[cam_id] = "error"
            return False

    def stop_ingest(self, cam_id: str) -> bool:
        """Stop ingest for a specific camera."""
        if cam_id not in self.states:
            return False

        state = self.states.get(cam_id)
        if state not in ("streaming", "no_signal"):
            return False

        # If in no_signal state, just update state
        if state == "no_signal":
            self.states[cam_id] = "idle"
            self.signal_states[cam_id] = True
            self.signal_loss_times[cam_id] = None
            logger.info(f"Stopped monitoring for camera {cam_id} (was in no_signal state)")
            return True

        return self._stop_ingest(cam_id)

    def _stop_ingest(self, cam_id: str) -> bool:
        """Internal method to stop an ingest pipeline."""
        if cam_id not in self.pipelines:
            return False

        Gst = get_gst()
        if not Gst:
            logger.error("GStreamer not available for stopping ingest")
            return False

        pipeline = self.pipelines[cam_id]
        try:
            pipeline.set_state(Gst.State.NULL)
            pipeline.get_state(Gst.CLOCK_TIME_NONE)
            del self.pipelines[cam_id]
            self.states[cam_id] = "idle"
            
            # Reset tracking
            self.error_retry_count.pop(cam_id, None)
            self.signal_states[cam_id] = True
            self.signal_loss_times[cam_id] = None
            
            logger.info(f"Stopped ingest for camera {cam_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping ingest for {cam_id}: {e}")
            try:
                pipeline.set_state(Gst.State.NULL)
                del self.pipelines[cam_id]
            except:
                pass
            self.states[cam_id] = "error"
            return False

    def start_all(self) -> Dict[str, bool]:
        """Start ingest for all cameras that have signal."""
        results = {}
        for cam_id, cam_config in self.config.cameras.items():
            # Skip disabled cameras
            if not cam_config.enabled:
                logger.info(f"Skipping {cam_id} - disabled in config")
                results[cam_id] = False
                self.states[cam_id] = "idle"
                continue
            
            # Check signal before attempting to start
            try:
                from .device_detection import get_device_capabilities
                caps = get_device_capabilities(cam_config.device)
                if not caps.get('has_signal', False):
                    logger.info(f"Skipping {cam_id} - no signal")
                    results[cam_id] = False
                    self.states[cam_id] = "no_signal"
                    self.signal_states[cam_id] = False
                    self.signal_loss_times[cam_id] = time.time()
                    continue
            except Exception as e:
                logger.debug(f"Could not check signal for {cam_id}: {e}")
            
            results[cam_id] = self.start_ingest(cam_id)
        return results

    def stop_all(self) -> Dict[str, bool]:
        """Stop ingest for all cameras."""
        results = {}
        for cam_id in list(self.pipelines.keys()):
            results[cam_id] = self.stop_ingest(cam_id)
        return results

    def get_status(self) -> Dict[str, IngestStatus]:
        """Get status for all cameras."""
        status_dict = {}
        for cam_id, cam_config in self.config.cameras.items():
            # Check if camera is disabled
            if not cam_config.enabled:
                status_dict[cam_id] = IngestStatus(
                    status="idle",
                    resolution=None,
                    has_signal=False,
                    stream_url=None,
                    error_message="Camera disabled in configuration"
                )
                continue
            
            state = self.states.get(cam_id, "idle")
            resolution = self.current_resolutions.get(cam_id)
            has_signal = self.signal_states.get(cam_id, False)

            stream_url = None
            if state == "streaming":
                # Use 127.0.0.1 instead of localhost to avoid IPv6 issues
                stream_url = f"rtsp://127.0.0.1:{self.config.mediamtx.rtsp_port}/{cam_id}"

            status_dict[cam_id] = IngestStatus(
                status=state,
                resolution=resolution,
                has_signal=has_signal,
                stream_url=stream_url,
            )
        return status_dict

    def get_camera_status(self, cam_id: str) -> Optional[IngestStatus]:
        """Get status of a specific camera."""
        if cam_id not in self.config.cameras:
            return None
        
        statuses = self.get_status()
        return statuses.get(cam_id)

    def _on_bus_message(self, bus, message, cam_id: str) -> None:
        """Handle GStreamer bus messages."""
        Gst = get_gst()
        if not Gst:
            return
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Ingest pipeline error for {cam_id}: {err.message} - {debug}")
            
            self.states[cam_id] = "error"
            
            # Clean up failed pipeline
            if cam_id in self.pipelines:
                try:
                    pipeline = self.pipelines[cam_id]
                    pipeline.set_state(Gst.State.NULL)
                    del self.pipelines[cam_id]
                except:
                    pass
            
            # Retry with exponential backoff
            if "Internal data stream error" in err.message or "device" in err.message.lower():
                retry_count = self.error_retry_count.get(cam_id, 0)
                if retry_count < 3:
                    self.error_retry_count[cam_id] = retry_count + 1
                    retry_delay = min(2.0 * (2 ** retry_count), 10.0)
                    logger.info(f"Retrying ingest for {cam_id} after error (attempt {retry_count + 1}/3) in {retry_delay}s")
                    
                    # Re-initialize rkcif device if needed
                    cam_config = self.config.cameras.get(cam_id)
                    if cam_config:
                        try:
                            from .device_detection import RKCIF_SUBDEV_MAP, initialize_rkcif_device
                            if cam_config.device in RKCIF_SUBDEV_MAP:
                                logger.info(f"Re-initializing rkcif device {cam_config.device}")
                                initialize_rkcif_device(cam_config.device)
                        except Exception as e:
                            logger.debug(f"Could not re-initialize device: {e}")
                    
                    # Retry after delay
                    threading.Timer(retry_delay, lambda: self.start_ingest(cam_id)).start()
                else:
                    logger.error(f"Max retries reached for {cam_id}")
                    self.error_retry_count.pop(cam_id, None)
                    
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Ingest pipeline warning for {cam_id}: {warn.message} - {debug}")
            
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipelines.get(cam_id):
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.debug(f"Ingest state changed for {cam_id}: {old_state.value_nick} -> {new_state.value_nick}")
                
                if new_state == Gst.State.NULL and old_state != Gst.State.NULL:
                    if self.states.get(cam_id) == "streaming":
                        logger.warning(f"Ingest pipeline for {cam_id} stopped unexpectedly")
                        self.states[cam_id] = "error"

    def _start_health_check(self):
        """Start the health check thread if not already running."""
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

    def _stop_health_check(self):
        """Stop the health check thread."""
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2)
            self._health_check_thread = None

    def _health_check_loop(self):
        """Background thread that monitors pipeline health."""
        check_interval = self.config.preview.health_check_interval
        
        while self._health_check_running:
            try:
                self._check_all_pipelines_health()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            # Sleep in small increments to allow quick shutdown
            for _ in range(int(check_interval)):
                if not self._health_check_running:
                    break
                time.sleep(1)

    def _check_all_pipelines_health(self):
        """Check health of all active pipelines and monitor signal status."""
        for cam_id, state in list(self.states.items()):
            # Skip disabled cameras entirely to save resources
            cam_config = self.config.cameras.get(cam_id)
            if not cam_config or not cam_config.enabled:
                continue
            
            # Check signal status for enabled cameras only
            signal_res = self._check_signal_status(cam_id)
            had_signal = self.signal_states.get(cam_id, True)
            
            if signal_res is None:
                # No signal
                if had_signal and state == "streaming":
                    self._handle_signal_loss(cam_id)
                continue
            else:
                # Signal present
                if not had_signal:
                    self._handle_signal_recovery(cam_id, signal_res[0], signal_res[1])
                    continue
                
                if state != "streaming":
                    continue
                
                # Check for resolution changes
                if self._check_resolution_change(cam_id):
                    continue

    def _check_signal_status(self, cam_id: str) -> Optional[tuple[int, int]]:
        """Check if camera has HDMI signal and return resolution."""
        if cam_id not in self.config.cameras:
            return None
        
        try:
            from .device_detection import get_subdev_resolution
            device = self.config.cameras[cam_id].device
            resolution = get_subdev_resolution(device)
            
            if not resolution or resolution == (0, 0):
                return None
            
            return resolution
            
        except Exception as e:
            logger.debug(f"Error checking signal status for {cam_id}: {e}")
            return None

    def _check_resolution_change(self, cam_id: str) -> bool:
        """Check if resolution changed for a camera."""
        if cam_id not in self.config.cameras:
            return False
        
        try:
            from .device_detection import get_subdev_resolution
            device = self.config.cameras[cam_id].device
            new_res = get_subdev_resolution(device)
            
            if not new_res or new_res == (0, 0):
                return False
            
            current_res = self.current_resolutions.get(cam_id)
            
            if current_res and current_res != new_res:
                logger.info(
                    f"{cam_id}: Resolution changed from {current_res[0]}x{current_res[1]} "
                    f"to {new_res[0]}x{new_res[1]}, restarting ingest..."
                )
                self._handle_resolution_change(cam_id, new_res[0], new_res[1])
                return True
            
            if not current_res:
                self.current_resolutions[cam_id] = new_res
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking resolution change for {cam_id}: {e}")
            return False

    def _handle_signal_loss(self, cam_id: str):
        """Handle HDMI signal loss gracefully."""
        logger.warning(f"{cam_id}: HDMI signal lost, stopping ingest")
        
        try:
            if cam_id in self.pipelines:
                Gst = get_gst()
                pipeline = self.pipelines[cam_id]
                pipeline.set_state(Gst.State.NULL)
                del self.pipelines[cam_id]
            
            self.states[cam_id] = "no_signal"
            self.signal_states[cam_id] = False
            self.signal_loss_times[cam_id] = time.time()
            
            if cam_id in self.current_resolutions:
                del self.current_resolutions[cam_id]
            
            logger.info(f"{cam_id}: Ingest stopped due to signal loss")
            
        except Exception as e:
            logger.error(f"Error handling signal loss for {cam_id}: {e}")
            self.states[cam_id] = "error"

    def _handle_signal_recovery(self, cam_id: str, width: int, height: int):
        """Handle HDMI signal return."""
        signal_loss_duration = None
        if self.signal_loss_times.get(cam_id):
            signal_loss_duration = time.time() - self.signal_loss_times[cam_id]
            logger.info(
                f"{cam_id}: HDMI signal recovered after {signal_loss_duration:.1f}s, "
                f"resolution {width}x{height}"
            )
        else:
            logger.info(f"{cam_id}: HDMI signal detected, resolution {width}x{height}")
        
        try:
            self.signal_states[cam_id] = True
            self.signal_loss_times[cam_id] = None
            
            time.sleep(0.5)
            
            # Re-initialize rkcif device if needed
            cam_config = self.config.cameras[cam_id]
            try:
                from .device_detection import initialize_rkcif_device, detect_device_type
                device_type = detect_device_type(cam_config.device)
                
                if device_type == "hdmi_rkcif":
                    logger.info(f"Re-initializing rkcif device {cam_config.device}")
                    initialize_rkcif_device(cam_config.device)
            except Exception as e:
                logger.warning(f"Could not re-initialize device {cam_config.device}: {e}")
            
            self.start_ingest(cam_id)
            
            logger.info(f"{cam_id}: Ingest restarted successfully after signal recovery")
            
        except Exception as e:
            logger.error(f"Error handling signal recovery for {cam_id}: {e}")
            self.states[cam_id] = "error"

    def _handle_resolution_change(self, cam_id: str, new_width: int, new_height: int):
        """Handle resolution change by gracefully restarting the ingest pipeline."""
        try:
            if cam_id in self.pipelines:
                Gst = get_gst()
                pipeline = self.pipelines[cam_id]
                pipeline.set_state(Gst.State.NULL)
                del self.pipelines[cam_id]
            
            self.current_resolutions[cam_id] = (new_width, new_height)
            
            time.sleep(0.5)
            
            # Re-initialize rkcif device if needed
            cam_config = self.config.cameras[cam_id]
            try:
                from .device_detection import initialize_rkcif_device, detect_device_type
                device_type = detect_device_type(cam_config.device)
                
                if device_type == "hdmi_rkcif":
                    logger.info(f"Re-initializing rkcif device {cam_config.device} with new resolution")
                    initialize_rkcif_device(cam_config.device)
            except Exception as e:
                logger.warning(f"Could not re-initialize device {cam_config.device}: {e}")
            
            self.start_ingest(cam_id)
            
            logger.info(
                f"Successfully restarted {cam_id} ingest with resolution "
                f"{new_width}x{new_height}"
            )
            
        except Exception as e:
            logger.error(f"Error handling resolution change for {cam_id}: {e}")
            self.states[cam_id] = "error"

