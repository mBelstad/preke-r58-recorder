"""Preview pipeline manager for live multiview."""
import logging
from typing import Dict, Optional, Any

from .config import AppConfig, CameraConfig
from .pipelines import build_preview_pipeline
from .gst_utils import ensure_gst_initialized, get_gst

logger = logging.getLogger(__name__)


class PreviewManager:
    """Manages preview pipelines for multiview (no recording, just streaming)."""

    def __init__(self, config: AppConfig):
        """Initialize preview manager."""
        self.config = config
        self.preview_pipelines: Dict[str, Any] = {}  # Gst.Pipeline objects
        self.preview_states: Dict[str, str] = {}  # 'idle', 'preview', 'error'
        self._gst_ready = False

        # Initialize states (don't init GStreamer yet - lazy load)
        for cam_id in config.cameras.keys():
            self.preview_states[cam_id] = "idle"
    
    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized before use."""
        if self._gst_ready:
            return True
        
        if ensure_gst_initialized():
            self._gst_ready = True
            return True
        
        logger.error("GStreamer initialization failed - preview not available")
        return False

    def start_preview(self, cam_id: str) -> bool:
        """Start preview stream for a camera (no recording)."""
        if not self._ensure_gst():
            logger.error("Cannot start preview - GStreamer not available")
            return False
        
        if cam_id not in self.config.cameras:
            logger.error(f"Camera {cam_id} not found in configuration")
            return False

        if self.preview_states.get(cam_id) == "preview":
            logger.warning(f"Camera {cam_id} is already in preview mode")
            return False

        # Stop existing preview pipeline if any
        if cam_id in self.preview_pipelines:
            self._stop_preview(cam_id)
        
        # Stop recording pipeline if running (same device can't be used by both)
        # Import here to avoid circular dependency
        from .main import recorder
        if hasattr(recorder, 'states') and recorder.states.get(cam_id) == "recording":
            logger.info(f"Stopping recording for {cam_id} before starting preview")
            recorder.stop_recording(cam_id)
            # Give device time to release before starting preview
            import time
            time.sleep(0.5)

        cam_config: CameraConfig = self.config.cameras[cam_id]

        # Check if device has an active signal before starting preview
        # Devices with no signal may report minimum resolution (64x64) or 0x0
        # We'll let the pipeline start but it may not produce frames
        # The pipeline will handle this gracefully with format negotiation

        # Build MediaMTX path for preview
        preview_path = None
        if self.config.mediamtx.enabled:
            preview_path = f"rtsp://localhost:{self.config.mediamtx.rtsp_port}/{cam_id}_preview"

        # Build preview pipeline (streaming only, no recording)
        try:
            pipeline = build_preview_pipeline(
                platform=self.config.platform,
                cam_id=cam_id,
                device=cam_config.device,
                resolution=cam_config.resolution,
                bitrate=cam_config.bitrate,
                codec=cam_config.codec,
                mediamtx_path=preview_path,
            )

            # Set up bus message handler
            bus = pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message, cam_id)

            # Start pipeline
            Gst = get_gst()
            pipeline.set_state(Gst.State.PLAYING)
            self.preview_pipelines[cam_id] = pipeline
            self.preview_states[cam_id] = "preview"

            logger.info(f"Started preview for camera {cam_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to start preview for {cam_id}: {e}")
            self.preview_states[cam_id] = "error"
            return False

    def stop_preview(self, cam_id: str) -> bool:
        """Stop preview for a specific camera."""
        if cam_id not in self.preview_states:
            return False

        if self.preview_states.get(cam_id) != "preview":
            return False

        return self._stop_preview(cam_id)

    def _stop_preview(self, cam_id: str) -> bool:
        """Internal method to stop a preview pipeline."""
        if cam_id not in self.preview_pipelines:
            return False

        Gst = get_gst()
        if not Gst:
            logger.error("GStreamer not available for stopping preview")
            return False

        pipeline = self.preview_pipelines[cam_id]
        try:
            pipeline.set_state(Gst.State.NULL)
            pipeline.get_state(Gst.CLOCK_TIME_NONE)
            del self.preview_pipelines[cam_id]
            self.preview_states[cam_id] = "idle"
            logger.info(f"Stopped preview for camera {cam_id}")
            return True
        except Exception as e:
            logger.error(f"Error stopping preview for {cam_id}: {e}")
            try:
                pipeline.set_state(Gst.State.NULL)
                del self.preview_pipelines[cam_id]
            except:
                pass
            self.preview_states[cam_id] = "error"
            return False

    def start_all_previews(self) -> Dict[str, bool]:
        """Start preview for all cameras."""
        results = {}
        for cam_id in self.config.cameras.keys():
            results[cam_id] = self.start_preview(cam_id)
        return results

    def stop_all_previews(self) -> Dict[str, bool]:
        """Stop preview for all cameras."""
        results = {}
        for cam_id in list(self.preview_pipelines.keys()):
            results[cam_id] = self.stop_preview(cam_id)
        return results

    def _on_bus_message(self, bus, message, cam_id: str) -> None:
        """Handle GStreamer bus messages."""
        Gst = get_gst()
        if not Gst:
            return
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Preview pipeline error for {cam_id}: {err.message} - {debug}")
            self.preview_states[cam_id] = "error"
            # Try to clean up the failed pipeline
            if cam_id in self.preview_pipelines:
                try:
                    pipeline = self.preview_pipelines[cam_id]
                    pipeline.set_state(Gst.State.NULL)
                    del self.preview_pipelines[cam_id]
                except:
                    pass
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Preview pipeline warning for {cam_id}: {warn.message} - {debug}")
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.preview_pipelines.get(cam_id):
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.debug(
                    f"Preview state changed for {cam_id}: {old_state.value_nick} -> {new_state.value_nick}"
                )
                # If pipeline failed to start, mark as error
                if new_state == Gst.State.NULL and old_state != Gst.State.NULL:
                    if self.preview_states.get(cam_id) == "preview":
                        logger.warning(f"Preview pipeline for {cam_id} stopped unexpectedly")
                        self.preview_states[cam_id] = "error"

    def get_preview_status(self) -> Dict[str, str]:
        """Get preview status for all cameras."""
        return self.preview_states.copy()

    def get_camera_preview_status(self, cam_id: str) -> Optional[str]:
        """Get preview status for a specific camera."""
        return self.preview_states.get(cam_id)

