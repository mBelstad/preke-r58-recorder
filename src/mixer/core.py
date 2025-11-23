"""Mixer Core - GStreamer compositor pipeline for scene-based mixing."""
import logging
import time
import threading
import subprocess
from typing import Dict, Optional, Any
from pathlib import Path
from datetime import datetime
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

from .scenes import SceneManager, Scene
from .watchdog import MixerWatchdog, HealthStatus

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
        self.pipeline: Optional[Gst.Pipeline] = None
        self.current_scene: Optional[Scene] = None
        self.state: str = "NULL"
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()
        
        # Watchdog
        self.watchdog = MixerWatchdog(
            on_unhealthy=self._handle_unhealthy
        )
        
        # Health check thread
        self._health_check_thread: Optional[threading.Thread] = None
        self._health_check_running = False

        # Initialize GStreamer if not already done
        if not Gst.is_initialized():
            Gst.init(None)

        # Get camera devices from config
        self.camera_devices = {}
        for cam_id, cam_config in config.cameras.items():
            self.camera_devices[cam_id] = cam_config.device

        logger.info(f"MixerCore initialized: {len(self.camera_devices)} cameras, "
                   f"output={output_resolution}, bitrate={output_bitrate}kbps")

    def start(self) -> bool:
        """Start the mixer pipeline."""
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
                if not self._set_state_with_timeout(Gst.State.PLAYING):
                    # Check bus for error messages
                    msg = bus.timed_pop_filtered(
                        int(0.5 * Gst.SECOND),
                        Gst.MessageType.ERROR | Gst.MessageType.WARNING
                    )
                    if msg:
                        if msg.type == Gst.MessageType.ERROR:
                            err, debug = msg.parse_error()
                            logger.error(f"Pipeline error during start: {err.message} - {debug}")
                            self.last_error = f"{err.message} - {debug}"
                        elif msg.type == Gst.MessageType.WARNING:
                            warn, debug = msg.parse_warning()
                            logger.warning(f"Pipeline warning during start: {warn.message} - {debug}")
                    
                    logger.error("Failed to start mixer pipeline (timeout)")
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
            self.pipeline.send_event(Gst.Event.new_eos())
            
            # Wait for EOS with timeout
            bus = self.pipeline.get_bus()
            msg = bus.timed_pop_filtered(
                int(STATE_CHANGE_TIMEOUT * Gst.SECOND),
                Gst.MessageType.EOS | Gst.MessageType.ERROR
            )

            # Set to NULL state with timeout
            self._set_state_with_timeout(Gst.State.NULL)
            
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
                    self.pipeline.set_state(Gst.State.NULL)
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
                
                if self._set_state_with_timeout(Gst.State.PLAYING):
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

    def _build_pipeline(self) -> Optional[Gst.Pipeline]:
        """Build the GStreamer compositor pipeline."""
        width, height = self.output_resolution.split("x")
        scene = self.current_scene

        # Build source branches for each camera
        source_branches = []
        for i, slot in enumerate(scene.slots):
            cam_id = slot.source
            if cam_id not in self.camera_devices:
                logger.warning(f"Camera {cam_id} not found in config, skipping")
                continue

            device = self.camera_devices[cam_id]
            
            # Skip if device doesn't exist (for non-connected cameras)
            if not Path(device).exists():
                logger.warning(f"Device {device} for {cam_id} does not exist, skipping")
                continue
            
            # Check if device is busy (being used by another process)
            # Only check for non-video60 devices (video60 is the main HDMI input)
            if "video60" not in device:
                try:
                    import fcntl
                    with open(device, 'r') as f:
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(f, fcntl.LOCK_UN)
                except (IOError, OSError):
                    logger.warning(f"Device {device} for {cam_id} is busy or not accessible, skipping")
                    continue
            
            # Build source pipeline (similar to existing R58 pipeline)
            if "video60" in device or "hdmirx" in device.lower():
                # HDMI input (NV24 format) - use EXACT same approach as working recorder pipeline
                # Match the working pipeline exactly: format=NV24,width={width},height={height},framerate=60/1
                # Then convert to NV12 and scale to match compositor input requirements
                # Add explicit caps after queue to prevent compositor from negotiating upstream
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
                # Other video devices - check if they exist first
                if not Path(device).exists():
                    logger.warning(f"Device {device} does not exist, skipping")
                    continue
                source_str = (
                    f"v4l2src device={device} ! "
                    f"videoconvert ! "
                    f"videoscale ! "
                    f"video/x-raw,width={width},height={height} ! "
                    f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream"
                )

            source_branches.append((i, source_str, slot))

        if not source_branches:
            logger.error("No valid source branches to build")
            return None

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
            compositor_pad_props.append(
                f"sink_{i}::xpos={coords['x']} "
                f"sink_{i}::ypos={coords['y']} "
                f"sink_{i}::width={coords['w']} "
                f"sink_{i}::height={coords['h']} "
                f"sink_{i}::zorder={slot.z} "
                f"sink_{i}::alpha={slot.alpha}"
            )

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
            pipeline = Gst.parse_launch(pipeline_str)
            return pipeline
        except Exception as e:
            logger.error(f"Failed to parse pipeline: {e}")
            return None

    def _set_state_with_timeout(self, state: Gst.State) -> bool:
        """Set pipeline state with timeout.
        
        Args:
            state: Target GStreamer state
        
        Returns:
            True if state change succeeded within timeout
        """
        if not self.pipeline:
            return False

        ret = self.pipeline.set_state(state)
        if ret == Gst.StateChangeReturn.FAILURE:
            logger.error(f"Failed to set pipeline state to {state.value_nick}")
            return False

        if ret == Gst.StateChangeReturn.SUCCESS:
            return True

        # Async state change - wait for completion
        # Also check bus for errors during state change
        bus = self.pipeline.get_bus() if self.pipeline else None
        start_time = time.time()
        while time.time() - start_time < STATE_CHANGE_TIMEOUT:
            # Check for bus messages (errors)
            if bus:
                msg = bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.WARNING)
                if msg:
                    if msg.type == Gst.MessageType.ERROR:
                        err, debug = msg.parse_error()
                        logger.error(f"Pipeline error during state change: {err.message} - {debug}")
                        return False
                    elif msg.type == Gst.MessageType.WARNING:
                        warn, debug = msg.parse_warning()
                        logger.warning(f"Pipeline warning during state change: {warn.message} - {debug}")
            
            ret = self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
            if ret[0] == Gst.StateChangeReturn.SUCCESS:
                return True
            elif ret[0] == Gst.StateChangeReturn.FAILURE:
                logger.error(f"State change to {state.value_nick} failed")
                return False
            time.sleep(0.1)

        logger.error(f"State change to {state.value_nick} timed out")
        return False

    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message) -> None:
        """Handle GStreamer bus messages."""
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_msg = f"{err.message} - {debug}"
            logger.error(f"Mixer pipeline error: {error_msg}")
            self.last_error = error_msg
            self.watchdog.record_error(error_msg)
            
            # Check if recovery is needed
            health = self.watchdog.check_health(self.state)
            if health == HealthStatus.UNHEALTHY:
                logger.warning("Pipeline unhealthy, may need recovery")

        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Mixer pipeline warning: {warn.message} - {debug}")

        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(f"Mixer state changed: {old_state.value_nick} -> {new_state.value_nick}")
                self.state = new_state.value_nick

        elif message.type == Gst.MessageType.EOS:
            logger.info("Mixer pipeline EOS")

        elif message.type == Gst.MessageType.BUFFER:
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
                
                if self._set_state_with_timeout(Gst.State.PLAYING):
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
            # Find any gst-launch or python processes using video devices
            # Also check for any process using video60 specifically
            result = subprocess.run(
                ["pgrep", "-f", "gst.*video60|gst.*video[0-9]|python.*recorder|python.*preview"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    if pid:
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

