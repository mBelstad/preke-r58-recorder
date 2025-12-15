"""Mixer Core - GStreamer compositor pipeline for scene-based mixing."""
import logging
import time
import threading
import subprocess
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime

from .scenes import SceneManager, Scene
from .watchdog import MixerWatchdog, HealthStatus
from .graphics import GraphicsRenderer
from ..gst_utils import ensure_gst_initialized, get_gst, get_glib

logger = logging.getLogger(__name__)

# Timeout for state transitions (seconds)
STATE_CHANGE_TIMEOUT = 10.0


class MixerCore:
    """Manages GStreamer compositor pipeline for mixing multiple video sources."""

    def __init__(
        self,
        config: Any,  # AppConfig from config.py
        scene_manager: SceneManager,
        output_resolution: str = "1920x1080",
        output_bitrate: int = 8000,
        output_codec: str = "h264",
        recording_enabled: bool = False,
        recording_path: Optional[str] = None,
        mediamtx_enabled: bool = True,
        mediamtx_path: Optional[str] = None,
    ):
        """Initialize mixer core.
        
        Args:
            config: Application configuration
            scene_manager: Scene manager instance
            output_resolution: Output resolution (e.g., "1920x1080")
            output_bitrate: Output bitrate in kbps
            output_codec: Codec ("h264" or "h265")
            recording_enabled: Enable program output recording
            recording_path: Path template for recordings (supports strftime)
            mediamtx_enabled: Enable MediaMTX streaming
            mediamtx_path: MediaMTX path (e.g., "mixer_program")
        """
        self.config = config
        self.scene_manager = scene_manager
        self.output_resolution = output_resolution
        self.output_bitrate = output_bitrate
        self.output_codec = output_codec
        self.recording_enabled = recording_enabled
        self.recording_path = recording_path
        self.mediamtx_enabled = mediamtx_enabled
        self.mediamtx_path = mediamtx_path or "mixer_program"

        # Pipeline state
        self.pipeline = None  # self.Gst.Pipeline
        self.current_scene: Optional[Scene] = None
        self.state: str = "NULL"
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()
        self._gst_ready = False
        
        # Watchdog
        self.watchdog = MixerWatchdog(
            on_unhealthy=self._handle_unhealthy
        )
        
        # Health check thread
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_running = False

        # Don't initialize GStreamer here - lazy load when needed
        self._Gst = None  # Will be set by _ensure_gst

        # Get camera devices from config
        self.camera_devices = {}
        for cam_id, cam_config in config.cameras.items():
            self.camera_devices[cam_id] = cam_config.device

        logger.info(f"MixerCore initialized: {len(self.camera_devices)} cameras, "
                   f"output={output_resolution}, bitrate={output_bitrate}kbps")
    
    @property
    def Gst(self):
        """Get GStreamer module (lazy initialization)."""
        if self._Gst is None:
            self._Gst = get_gst()
        return self._Gst
    
    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized before use."""
        if self._gst_ready:
            return True
        
        if ensure_gst_initialized():
            self._gst_ready = True
            self._Gst = get_gst()
            return True
        
        logger.error("GStreamer initialization failed - mixer not available")
        return False

    def start(self) -> bool:
        """Start the mixer pipeline."""
        if not self._ensure_gst():
            logger.error("Cannot start mixer - GStreamer not available")
            return False
        
        with self._lock:
            if self.pipeline and self.state == "PLAYING":
                logger.warning("Mixer pipeline already running")
                return True

            # Stop existing pipeline if any
            if self.pipeline:
                self._stop_pipeline_internal()

            # Apply default scene if none set
            if not self.current_scene:
                default_scene = self.scene_manager.get_scene("quad")
                if default_scene:
                    self.current_scene = default_scene
                else:
                    logger.error("No scene set and no default scene available")
                    return False

            # Build and start pipeline
            try:
                # Clean up any stuck GStreamer processes that might be holding video devices
                self._cleanup_stuck_pipelines()
                
                self.pipeline = self._build_pipeline()
                if not self.pipeline:
                    return False

                # Set up bus message handler BEFORE state change
                bus = self.pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message", self._on_bus_message)

                # Start pipeline with timeout (will check bus for errors)
                if not self._set_state_with_timeout(self.Gst.State.PLAYING):
                    # Check bus for error messages
                    msg = bus.timed_pop_filtered(
                        int(0.5 * self.Gst.SECOND),
                        self.Gst.MessageType.ERROR | self.Gst.MessageType.WARNING
                    )
                    if msg:
                        if msg.type == self.Gst.MessageType.ERROR:
                            err, debug = msg.parse_error()
                            error_msg = f"{err.message} - {debug}"
                            logger.error(f"Pipeline error during start: {error_msg}")
                            
                            # Provide user-friendly error message for common issues
                            if "no supported format" in error_msg.lower() or "TRY_FMT failed" in error_msg:
                                if "video60" in error_msg:
                                    self.last_error = "HDMI input (/dev/video60) cannot negotiate format. Check if HDMI cable is connected and source is active."
                                else:
                                    self.last_error = f"Video device format negotiation failed: {error_msg}"
                            else:
                                self.last_error = error_msg
                        elif msg.type == self.Gst.MessageType.WARNING:
                            warn, debug = msg.parse_warning()
                            logger.warning(f"Pipeline warning during start: {warn.message} - {debug}")
                    
                    logger.error("Failed to start mixer pipeline (timeout or format negotiation failure)")
                    self._stop_pipeline_internal()
                    return False

                self.state = "PLAYING"
                self.watchdog.start()
                self._start_health_check()
                logger.info(f"Mixer pipeline started with scene: {self.current_scene.id}")
                return True

            except Exception as e:
                logger.error(f"Failed to start mixer pipeline: {e}")
                self.last_error = str(e)
                if self.pipeline:
                    self._stop_pipeline_internal()
                return False

    def stop(self) -> bool:
        """Stop the mixer pipeline."""
        with self._lock:
            self._stop_health_check()
            self.watchdog.stop()
            return self._stop_pipeline_internal()

    def _stop_pipeline_internal(self) -> bool:
        """Internal method to stop pipeline (must be called with lock)."""
        if not self.pipeline:
            return True

        try:
            # Send EOS
            self.pipeline.send_event(self.Gst.Event.new_eos())
            
            # Wait for EOS with timeout
            bus = self.pipeline.get_bus()
            msg = bus.timed_pop_filtered(
                int(STATE_CHANGE_TIMEOUT * self.Gst.SECOND),
                self.Gst.MessageType.EOS | self.Gst.MessageType.ERROR
            )

            # Set to NULL state with timeout
            self._set_state_with_timeout(self.Gst.State.NULL)
            
            # Clean up
            if self.pipeline:
                self.pipeline = None
            self.state = "NULL"
            logger.info("Mixer pipeline stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping mixer pipeline: {e}")
            # Force cleanup
            try:
                if self.pipeline:
                    self.pipeline.set_state(self.Gst.State.NULL)
                    self.pipeline = None
            except:
                pass
            self.state = "NULL"
            return False

    def apply_scene(self, scene_id: str) -> bool:
        """Apply a scene to the mixer.
        
        Args:
            scene_id: Scene ID to apply
        
        Returns:
            True if scene was applied successfully
        """
        scene = self.scene_manager.get_scene(scene_id)
        if not scene:
            logger.error(f"Scene not found: {scene_id}")
            return False

        with self._lock:
            if not self.pipeline or self.state != "PLAYING":
                # Store scene for when pipeline starts
                self.current_scene = scene
                logger.info(f"Scene stored (will apply on start): {scene_id}")
                return True

            # Check if scene requires different sources (need pipeline rebuild)
            current_sources = {slot.source for slot in self.current_scene.slots} if self.current_scene else set()
            new_sources = {slot.source for slot in scene.slots}
            
            if current_sources != new_sources:
                # Different sources - need to rebuild pipeline
                logger.info(f"Scene {scene_id} uses different sources, rebuilding pipeline")
                was_playing = (self.state == "PLAYING")
                
                # Stop current pipeline
                self._stop_pipeline_internal()
                time.sleep(0.5)  # Give device time to release
                
                # Set new scene and rebuild
                self.current_scene = scene
                self.pipeline = self._build_pipeline()
                
                if not self.pipeline:
                    logger.error("Failed to rebuild pipeline for new scene")
                    return False
                
                # Restart pipeline
                bus = self.pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message", self._on_bus_message)
                
                if self._set_state_with_timeout(self.Gst.State.PLAYING):
                    self.state = "PLAYING"
                    logger.info(f"Pipeline rebuilt and started with scene: {scene_id}")
                    return True
                else:
                    logger.error("Failed to restart pipeline after scene change")
                    return False

            # Same sources - just update pad properties
            try:
                compositor = self.pipeline.get_by_name("compositor")
                if not compositor:
                    logger.error("Compositor element not found")
                    return False

                # Update compositor pad properties for each slot
                for i, slot in enumerate(scene.slots):
                    pad_name = f"sink_{i}"
                    pad = compositor.get_static_pad(pad_name)
                    if not pad:
                        logger.warning(f"Pad {pad_name} not found for source {slot.source}")
                        continue

                    coords = scene.get_absolute_coords(slot)
                    
                    # Set pad properties
                    pad.set_property("xpos", coords["x"])
                    pad.set_property("ypos", coords["y"])
                    pad.set_property("width", coords["w"])
                    pad.set_property("height", coords["h"])
                    pad.set_property("zorder", slot.z)
                    pad.set_property("alpha", slot.alpha)

                    logger.debug(f"Set pad {pad_name} ({slot.source}): "
                               f"x={coords['x']}, y={coords['y']}, "
                               f"w={coords['w']}, h={coords['h']}, z={slot.z}")

                self.current_scene = scene
                logger.info(f"Scene applied: {scene_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to apply scene {scene_id}: {e}")
                self.last_error = str(e)
                return False

    def get_status(self) -> Dict[str, Any]:
        """Get mixer status."""
        with self._lock:
            watchdog_status = self.watchdog.get_status()
            
            return {
                "state": self.state,
                "current_scene": self.current_scene.id if self.current_scene else None,
                "health": watchdog_status["health"],
                "last_error": self.last_error or watchdog_status["last_error"],
                "last_buffer_seconds_ago": watchdog_status["last_buffer_seconds_ago"],
                "recording_enabled": self.recording_enabled,
                "mediamtx_enabled": self.mediamtx_enabled,
            }

    def _build_pipeline(self):
        """Build the GStreamer compositor pipeline."""
        width, height = self.output_resolution.split("x")
        scene = self.current_scene

        # Build source branches for each slot
        source_branches = []
        for i, slot in enumerate(scene.slots):
            # Handle file sources (uploaded videos)
            if slot.source_type == "file" and slot.file_path:
                file_path = Path(slot.file_path)
                if not file_path.exists():
                    logger.warning(f"File source not found: {file_path}, skipping")
                    continue
                
                # Build file source pipeline
                if slot.loop:
                    # Looping video
                    source_str = (
                        f"filesrc location={file_path} loop=true ! "
                        f"decodebin ! "
                        f"videoconvert ! "
                        f"videoscale ! "
                        f"video/x-raw,width={width},height={height} ! "
                        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                    )
                else:
                    # Play once
                    source_str = (
                        f"filesrc location={file_path} ! "
                        f"decodebin ! "
                        f"videoconvert ! "
                        f"videoscale ! "
                        f"video/x-raw,width={width},height={height} ! "
                        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                    )
                
                # Apply crop if specified
                if slot.crop_w < 1.0 or slot.crop_h < 1.0 or slot.crop_x > 0.0 or slot.crop_y > 0.0:
                    crop_left = int(slot.crop_x * int(width))
                    crop_top = int(slot.crop_y * int(height))
                    crop_right = int((1.0 - slot.crop_x - slot.crop_w) * int(width))
                    crop_bottom = int((1.0 - slot.crop_y - slot.crop_h) * int(height))
                    source_str = source_str.replace(
                        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream",
                        f"videocrop left={crop_left} top={crop_top} right={crop_right} bottom={crop_bottom} ! queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                    )
                
                source_branches.append((i, source_str, slot))
                logger.info(f"Added file source branch: {file_path}")
                continue
            
            # Handle image sources (uploaded images)
            if slot.source_type == "image" and slot.file_path:
                file_path = Path(slot.file_path)
                if not file_path.exists():
                    logger.warning(f"Image source not found: {file_path}, skipping")
                    continue
                
                # Determine image decoder based on extension
                ext = file_path.suffix.lower()
                if ext in [".png"]:
                    decoder = "pngdec"
                elif ext in [".jpg", ".jpeg"]:
                    decoder = "jpegdec"
                else:
                    decoder = "decodebin"  # Fallback
                
                # Duration for image (default 10 seconds if not specified)
                duration = slot.duration if slot.duration else 10
                
                # Build image source pipeline
                source_str = (
                    f"filesrc location={file_path} ! "
                    f"{decoder} ! "
                    f"imagefreeze duration={duration} ! "
                    f"videoconvert ! "
                    f"videoscale ! "
                    f"video/x-raw,width={width},height={height} ! "
                    f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                )
                
                # Apply crop if specified
                if slot.crop_w < 1.0 or slot.crop_h < 1.0 or slot.crop_x > 0.0 or slot.crop_y > 0.0:
                    crop_left = int(slot.crop_x * int(width))
                    crop_top = int(slot.crop_y * int(height))
                    crop_right = int((1.0 - slot.crop_x - slot.crop_w) * int(width))
                    crop_bottom = int((1.0 - slot.crop_y - slot.crop_h) * int(height))
                    source_str = source_str.replace(
                        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream",
                        f"videocrop left={crop_left} top={crop_top} right={crop_right} bottom={crop_bottom} ! queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                    )
                
                source_branches.append((i, source_str, slot))
                logger.info(f"Added image source branch: {file_path}")
                continue
            
            # Handle graphics sources (image, presentation, lower_third, graphics)
            if slot.source_type not in ["camera", "file", "image"]:
                graphics_pipeline = self.graphics_renderer.get_source_pipeline(slot.source)
                if graphics_pipeline:
                    # Apply crop if specified
                    if slot.crop_w < 1.0 or slot.crop_h < 1.0 or slot.crop_x > 0.0 or slot.crop_y > 0.0:
                        # Add videocrop element
                        crop_x = int(slot.crop_x * int(width))
                        crop_y = int(slot.crop_y * int(height))
                        crop_w = int(slot.crop_w * int(width))
                        crop_h = int(slot.crop_h * int(height))
                        source_str = f"{graphics_pipeline} ! videocrop left={crop_x} top={crop_y} right={int(width) - crop_x - crop_w} bottom={int(height) - crop_y - crop_h} ! "
                    else:
                        source_str = f"{graphics_pipeline} ! "
                    
                    source_str += (
                        f"videoscale ! "
                        f"video/x-raw,width={width},height={height} ! "
                        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                    )
                    source_branches.append((i, source_str, slot))
                    logger.info(f"Added graphics source branch: {slot.source} (type: {slot.source_type})")
                else:
                    logger.warning(f"Failed to create graphics source for {slot.source}")
                continue
            
            # Handle camera sources
            if slot.source_type != "camera":
                logger.warning(f"Unknown source type: {slot.source_type}, skipping")
                continue
            
            cam_id = slot.source
            if cam_id not in self.camera_devices:
                logger.debug(f"Camera {cam_id} not found in config, skipping")
                continue

            device = self.camera_devices[cam_id]
            logger.debug(f"Processing camera {cam_id} with device {device}")
            
            # Use RTSP from MediaMTX preview streams to avoid device conflicts
            # Preview streams are already publishing to MediaMTX at camX_preview paths
            # This allows mixer and preview to run simultaneously
            if self.config.mediamtx.enabled:
                rtsp_port = self.config.mediamtx.rtsp_port
                preview_stream = f"{cam_id}_preview"
                rtsp_url = f"rtsp://127.0.0.1:{rtsp_port}/{preview_stream}"
                
                logger.info(f"Using RTSP source for {cam_id} from MediaMTX: {rtsp_url}")
                # Source from MediaMTX RTSP stream (preview stream)
                # Low latency settings for live mixing
                source_str = (
                    f"rtspsrc location={rtsp_url} latency=100 protocols=tcp ! "
                    f"rtph264depay ! "
                    f"h264parse ! "
                    f"avdec_h264 ! "
                    f"videoconvert ! "
                    f"videoscale ! "
                    f"video/x-raw,width={width},height={height} ! "
                    f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                )
            else:
                # Fallback to direct device access if MediaMTX is disabled
                # Skip if device doesn't exist (for non-connected cameras)
                if not Path(device).exists():
                    logger.debug(f"Device {device} for {cam_id} does not exist, skipping")
                    continue
                
                # Check if device is busy (being used by another process)
                try:
                    import fcntl
                    test_file = open(device, 'r')
                    fcntl.flock(test_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(test_file, fcntl.LOCK_UN)
                    test_file.close()
                except (IOError, OSError) as e:
                    logger.warning(f"Device {device} for {cam_id} is busy or not accessible, skipping: {e}")
                    continue
                
                # Build source pipeline (similar to existing R58 pipeline)
                if "video60" in device or "hdmirx" in device.lower():
                    # HDMI input (NV24 format)
                    source_str = (
                        f"v4l2src device={device} io-mode=mmap ! "
                        f"video/x-raw,format=NV24,width={width},height={height},framerate=60/1 ! "
                        f"videoconvert ! "
                        f"video/x-raw,format=NV12 ! "
                        f"videoscale ! "
                        f"video/x-raw,width={width},height={height} ! "
                        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
                        f"video/x-raw,format=NV12,width={width},height={height}"
                    )
                else:
                    # Other video devices
                    source_str = (
                        f"v4l2src device={device} ! "
                        f"videoconvert ! "
                        f"videoscale ! "
                        f"video/x-raw,width={width},height={height} ! "
                        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                    )
            
            # Apply crop if specified (for video sources)
            if slot.crop_w < 1.0 or slot.crop_h < 1.0 or slot.crop_x > 0.0 or slot.crop_y > 0.0:
                # Calculate crop values in pixels
                source_width = int(width)
                source_height = int(height)
                crop_left = int(slot.crop_x * source_width)
                crop_top = int(slot.crop_y * source_height)
                crop_right = int((1.0 - slot.crop_x - slot.crop_w) * source_width)
                crop_bottom = int((1.0 - slot.crop_y - slot.crop_h) * source_height)
                # Insert videocrop before the final queue
                source_str = source_str.replace(
                    f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream",
                    f"videocrop left={crop_left} top={crop_top} right={crop_right} bottom={crop_bottom} ! queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                )

            source_branches.append((i, source_str, slot))
            logger.info(f"Added source branch for {cam_id} ({device})")

        if not source_branches:
            logger.warning("No valid source branches to build - all cameras are unavailable or not configured")
            logger.info("Mixer cannot start without at least one valid video source")
            return None
        
        logger.info(f"Building mixer pipeline with {len(source_branches)} valid source(s) out of {len(scene.slots)} scene slot(s)")

        # Encoder
        if self.output_codec == "h265":
            encoder_str = f"mpph265enc bps={self.output_bitrate * 1000} bps-max={self.output_bitrate * 2000}"
            caps_str = "video/x-h265"
            parse_str = "h265parse"
            mux_str = "matroskamux"
        else:  # h264
            encoder_str = f"x264enc tune=zerolatency bitrate={self.output_bitrate} speed-preset=superfast"
            caps_str = "video/x-h264"
            parse_str = "h264parse"
            mux_str = "mp4mux"

        # Output branches
        output_branches = []
        
        # Recording branch
        if self.recording_enabled and self.recording_path:
            output_path = self.recording_path
            if "%" in output_path:
                output_path = datetime.now().strftime(output_path)
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            output_branches.append(
                f"queue ! {parse_str} ! {mux_str} ! filesink location={output_path}"
            )

        # MediaMTX branch
        if self.mediamtx_enabled:
            rtmp_url = f"rtmp://127.0.0.1:1935/{self.mediamtx_path}"
            output_branches.append(
                f"queue ! flvmux streamable=true ! rtmpsink location={rtmp_url} sync=false"
            )

        if not output_branches:
            logger.warning("No output branches configured")
            # Add fakesink as fallback
            output_branches.append("fakesink")

        # Build source branches connecting to compositor
        source_parts = []
        for i, (_, source_str, slot) in enumerate(source_branches):
            source_parts.append(f"{source_str} ! compositor.sink_{i}")

        # Build compositor with pad properties
        compositor_pad_props = []
        for i, (_, _, slot) in enumerate(source_branches):
            coords = scene.get_absolute_coords(slot)
            # Build pad properties with styling support
            pad_props = [
                f"sink_{i}::xpos={coords['x']}",
                f"sink_{i}::ypos={coords['y']}",
                f"sink_{i}::width={coords['w']}",
                f"sink_{i}::height={coords['h']}",
                f"sink_{i}::zorder={slot.z}",
                f"sink_{i}::alpha={slot.alpha}"
            ]
            
            # Note: GStreamer compositor doesn't natively support borders/border-radius
            # These would need to be applied via a separate overlay element or cairooverlay
            # For now, we store the values but don't apply them in the pipeline
            # TODO: Add cairooverlay or similar for border/border-radius rendering
            
            compositor_pad_props.append(" ".join(pad_props))

        # Build complete pipeline
        pipeline_str = (
            " ".join(source_parts) + " "
            f"compositor name=compositor {' '.join(compositor_pad_props)} ! "
            f"video/x-raw,width={width},height={height} ! "
            f"timeoverlay ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"tee name=t"
        )

        # Add output branches
        for branch in output_branches:
            pipeline_str += f" t. ! {branch}"

        logger.info(f"Building mixer pipeline: {len(source_branches)} sources")
        logger.debug(f"Pipeline string: {pipeline_str[:500]}...")

        try:
            pipeline = self.Gst.parse_launch(pipeline_str)
            return pipeline
        except Exception as e:
            logger.error(f"Failed to parse pipeline: {e}")
            return None

    def _set_state_with_timeout(self, state) -> bool:
        """Set pipeline state with timeout.
        
        Args:
            state: Target GStreamer state
        
        Returns:
            True if state change succeeded within timeout
        """
        if not self.pipeline:
            return False

        ret = self.pipeline.set_state(state)
        if ret == self.Gst.StateChangeReturn.FAILURE:
            logger.error(f"Failed to set pipeline state to {state.value_nick}")
            return False

        if ret == self.Gst.StateChangeReturn.SUCCESS:
            return True

        # Async state change - wait for completion
        # Also check bus for errors during state change
        bus = self.pipeline.get_bus() if self.pipeline else None
        start_time = time.time()
        while time.time() - start_time < STATE_CHANGE_TIMEOUT:
            # Check for bus messages (errors)
            if bus:
                msg = bus.pop_filtered(self.Gst.MessageType.ERROR | self.Gst.MessageType.WARNING)
                if msg:
                    if msg.type == self.Gst.MessageType.ERROR:
                        err, debug = msg.parse_error()
                        logger.error(f"Pipeline error during state change: {err.message} - {debug}")
                        return False
                    elif msg.type == self.Gst.MessageType.WARNING:
                        warn, debug = msg.parse_warning()
                        logger.warning(f"Pipeline warning during state change: {warn.message} - {debug}")
            
            ret = self.pipeline.get_state(self.Gst.CLOCK_TIME_NONE)
            if ret[0] == self.Gst.StateChangeReturn.SUCCESS:
                return True
            elif ret[0] == self.Gst.StateChangeReturn.FAILURE:
                logger.error(f"State change to {state.value_nick} failed")
                return False
            time.sleep(0.1)

        logger.error(f"State change to {state.value_nick} timed out")
        return False

    def _on_bus_message(self, bus, message) -> None:
        """Handle GStreamer bus messages."""
        if message.type == self.Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_msg = f"{err.message} - {debug}"
            logger.error(f"Mixer pipeline error: {error_msg}")
            self.last_error = error_msg
            self.watchdog.record_error(error_msg)
            
            # Check if recovery is needed
            health = self.watchdog.check_health(self.state)
            if health == HealthStatus.UNHEALTHY:
                logger.warning("Pipeline unhealthy, may need recovery")

        elif message.type == self.Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Mixer pipeline warning: {warn.message} - {debug}")

        elif message.type == self.Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(f"Mixer state changed: {old_state.value_nick} -> {new_state.value_nick}")
                self.state = new_state.value_nick

        elif message.type == self.Gst.MessageType.EOS:
            logger.info("Mixer pipeline EOS")

        elif message.type == self.Gst.MessageType.BUFFER:
            # Record buffer activity for health monitoring
            self.watchdog.record_buffer()

    def _start_health_check(self) -> None:
        """Start periodic health check thread."""
        if self._health_check_running:
            return
        
        self._health_check_running = True
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()
        logger.info("Mixer health check started")

    def _stop_health_check(self) -> None:
        """Stop health check thread."""
        self._health_check_running = False
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2.0)
        logger.info("Mixer health check stopped")

    def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._health_check_running:
            try:
                time.sleep(5.0)  # Check every 5 seconds
                
                with self._lock:
                    if not self.pipeline or self.state != "PLAYING":
                        continue
                    
                    # Check health
                    health = self.watchdog.check_health(self.state, expected_state="PLAYING")
                    
                    if health == HealthStatus.UNHEALTHY:
                        logger.error("Mixer pipeline unhealthy, attempting recovery")
                        self._recover_pipeline()
                        
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    def _recover_pipeline(self) -> None:
        """Attempt to recover from unhealthy state."""
        logger.info("Attempting pipeline recovery...")
        
        # Stop current pipeline
        self._stop_pipeline_internal()
        
        # Wait a moment
        time.sleep(1.0)
        
        # Restart pipeline
        if self.current_scene:
            try:
                self.pipeline = self._build_pipeline()
                if not self.pipeline:
                    logger.error("Failed to rebuild pipeline during recovery")
                    return
                
                bus = self.pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message", self._on_bus_message)
                
                if self._set_state_with_timeout(self.Gst.State.PLAYING):
                    self.state = "PLAYING"
                    logger.info("Pipeline recovered successfully")
                else:
                    logger.error("Failed to restart pipeline during recovery")
            except Exception as e:
                logger.error(f"Recovery failed: {e}")
                self.last_error = f"Recovery failed: {e}"

    def _cleanup_stuck_pipelines(self) -> None:
        """Kill any stuck GStreamer processes that might be holding video devices."""
        try:
            import os
            current_pid = os.getpid()
            
            # Find any gst-launch processes using video devices (but not our own process)
            # Only look for gst-launch processes, not python processes (to avoid killing ourselves)
            result = subprocess.run(
                ["pgrep", "-f", "gst-launch.*video60|gst-launch.*video[0-9]"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    if pid and pid.strip():
                        pid_int = int(pid.strip())
                        # Don't kill our own process
                        if pid_int != current_pid:
                            try:
                                logger.warning(f"Killing stuck GStreamer process: {pid}")
                                subprocess.run(["kill", "-9", pid], timeout=1, check=False)
                            except Exception as e:
                                logger.debug(f"Failed to kill process {pid}: {e}")
                if pids:
                    time.sleep(1.0)  # Give device time to release
                    
            # Additional check: try to open video60 to ensure it's released
            if Path("/dev/video60").exists():
                try:
                    import fcntl
                    with open("/dev/video60", 'r') as f:
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(f, fcntl.LOCK_UN)
                    logger.debug("Device /dev/video60 is available")
                except (IOError, OSError) as e:
                    logger.warning(f"Device /dev/video60 still appears busy: {e}")
                    time.sleep(0.5)  # Wait a bit more
        except Exception as e:
            logger.debug(f"Error cleaning up stuck pipelines: {e}")

    def _handle_unhealthy(self) -> None:
        """Handle unhealthy pipeline (called by watchdog)."""
        logger.warning("Mixer pipeline detected as unhealthy")
        # Recovery is handled by health check loop

