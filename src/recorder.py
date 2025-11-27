"""Pipeline manager for camera recording."""
import logging
import subprocess
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

from .config import AppConfig, CameraConfig
from .pipelines import build_pipeline

logger = logging.getLogger(__name__)


class Recorder:
    """Manages recording pipelines for multiple cameras."""

    def __init__(self, config: AppConfig):
        """Initialize recorder with configuration."""
        self.config = config
        self.pipelines: Dict[str, Gst.Pipeline] = {}
        self.states: Dict[str, str] = {}  # 'idle', 'recording', 'error'
        self.loop: Optional[GLib.MainLoop] = None

        # Initialize GStreamer
        Gst.init(None)

        # Clean up any stuck GStreamer processes that might be holding video devices
        self._cleanup_stuck_pipelines()

        # Initialize states
        for cam_id in config.cameras.keys():
            self.states[cam_id] = "idle"

    def start_recording(self, cam_id: str) -> bool:
        """Start recording for a specific camera."""
        if cam_id not in self.config.cameras:
            logger.error(f"Camera {cam_id} not found in configuration")
            return False

        if self.states.get(cam_id) == "recording":
            logger.warning(f"Camera {cam_id} is already recording")
            return False

        # Stop existing pipeline if any
        if cam_id in self.pipelines:
            self._stop_pipeline(cam_id)
        
        # Stop preview pipeline if running (same device can't be used by both)
        # Import here to avoid circular dependency
        from .main import preview_manager
        if hasattr(preview_manager, 'preview_states') and preview_manager.preview_states.get(cam_id) == "preview":
            logger.info(f"Stopping preview for {cam_id} before starting recording")
            preview_manager.stop_preview(cam_id)
            # Give device time to release before starting recording
            import time
            time.sleep(0.5)

        # Get camera config
        cam_config: CameraConfig = self.config.cameras[cam_id]

        # Format output path with timestamp if needed
        output_path_str = cam_config.output_path
        if "%" in output_path_str:
            output_path_str = datetime.now().strftime(output_path_str)

        # Ensure output directory exists
        output_path = Path(output_path_str)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build MediaMTX path if enabled
        mediamtx_path = None
        if cam_config.mediamtx_enabled and self.config.mediamtx.enabled:
            if cam_config.mediamtx_path:
                mediamtx_path = cam_config.mediamtx_path
            else:
                mediamtx_path = f"rtsp://localhost:{self.config.mediamtx.rtsp_port}/{cam_id}"

        # Build pipeline
        try:
            pipeline = build_pipeline(
                platform=self.config.platform,
                cam_id=cam_id,
                device=cam_config.device,
                output_path=str(output_path),
                resolution=cam_config.resolution,
                bitrate=cam_config.bitrate,
                codec=cam_config.codec,
                mediamtx_path=mediamtx_path,
            )

            # Set up bus message handler
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message, cam_id)

            # Start pipeline
            pipeline.set_state(Gst.State.PLAYING)
            self.pipelines[cam_id] = pipeline
            self.states[cam_id] = "recording"

            # Streaming is now handled via tee in the main pipeline (no separate pipeline needed)
            # This avoids dual device access which caused system crashes

            logger.info(f"Started recording for camera {cam_id}")
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

        pipeline = self.pipelines[cam_id]
        try:
            # Send EOS to flush the pipeline (don't pause first - let it finish naturally)
            pipeline.send_event(Gst.Event.new_eos())

            # Wait for EOS or timeout (15 seconds max)
            bus = pipeline.get_bus()
            msg = bus.timed_pop_filtered(
                15 * Gst.SECOND,  # 15 second timeout
                Gst.MessageType.EOS | Gst.MessageType.ERROR,
            )

            if msg and msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                logger.error(f"Pipeline error during stop for {cam_id}: {err.message}")

            # Set to NULL state to finalize the file
            pipeline.set_state(Gst.State.NULL)
            
            # Wait for state change to ensure file is finalized
            ret = pipeline.get_state(Gst.CLOCK_TIME_NONE)
            if ret[0] == Gst.StateChangeReturn.ASYNC:
                pipeline.get_state(Gst.CLOCK_TIME_NONE)

            # Streaming is handled in the main pipeline via tee, no separate cleanup needed

            # Clean up
            del self.pipelines[cam_id]
            self.states[cam_id] = "idle"

            logger.info(f"Stopped recording for camera {cam_id}")
            return True

        except Exception as e:
            logger.error(f"Error stopping pipeline for {cam_id}: {e}")
            # Force stop even if there was an error
            try:
                pipeline.set_state(Gst.State.NULL)
                pipeline.get_state(Gst.CLOCK_TIME_NONE)
                del self.pipelines[cam_id]
            except:
                pass
            self.states[cam_id] = "error"
            return False

    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message, cam_id: str) -> None:
        """Handle GStreamer bus messages."""
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Pipeline error for {cam_id}: {err.message} - {debug}")
            self.states[cam_id] = "error"
            # Try to restart the pipeline if it's a recoverable error
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
            # Don't change state to idle here - let stop_pipeline handle it
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipelines.get(cam_id):
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.info(
                    f"State changed for {cam_id}: {old_state.value_nick} -> {new_state.value_nick}"
                )
                # If pipeline goes to NULL unexpectedly, mark as error
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

    def start_all_recordings(self) -> Dict[str, bool]:
        """Start recording for all cameras."""
        results = {}
        for cam_id in self.config.cameras.keys():
            results[cam_id] = self.start_recording(cam_id)
        return results

    def stop_all_recordings(self) -> Dict[str, bool]:
        """Stop recording for all cameras."""
        results = {}
        for cam_id in list(self.pipelines.keys()):
            results[cam_id] = self.stop_recording(cam_id)
        return results

    def _cleanup_stuck_pipelines(self) -> None:
        """Kill any stuck GStreamer processes that might be holding video devices."""
        import subprocess
        try:
            # Find and kill stuck gst-launch processes
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

