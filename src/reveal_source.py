"""Reveal.js video source manager using WPE WebKit or Chromium for HTML rendering.

Supports multiple independent video outputs that can run simultaneously.
Each output has its own pipeline streaming to a unique MediaMTX path.
"""
import logging
import subprocess
import threading
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field

try:
    from .gst_utils import ensure_gst_initialized, get_gst
    from .pipelines import get_h265_encoder
except ImportError:
    # Fallback for direct execution
    from gst_utils import ensure_gst_initialized, get_gst
    from pipelines import get_h265_encoder

logger = logging.getLogger(__name__)


@dataclass
class RevealOutput:
    """Represents a single Reveal.js video output instance."""
    output_id: str
    mediamtx_path: str
    pipeline: Any = None
    state: str = "idle"  # idle, starting, running, stopping, error
    current_url: Optional[str] = None
    current_presentation_id: Optional[str] = None


class RevealSourceManager:
    """Manages multiple Reveal.js video outputs via WPE WebKit or Chromium.
    
    This class handles:
    - Detection of available HTML rendering backend (wpesrc or Chromium)
    - GStreamer pipeline creation for HTML-to-video conversion
    - Streaming to MediaMTX via RTSP
    - Multiple independent outputs (e.g., "slides" and "slides_overlay")
    - Slide navigation control via JavaScript injection
    
    Usage:
        manager = RevealSourceManager(outputs=["slides", "slides_overlay"])
        manager.start("slides", "demo", "http://localhost:8000/presentation")
        manager.start("slides_overlay", "overlay", "http://localhost:8000/overlay")
        # Both outputs run independently
    """
    
    def __init__(
        self,
        resolution: str = "1920x1080",
        framerate: int = 30,
        bitrate: int = 4000,
        mediamtx_path: str = "slides",  # Kept for backward compatibility
        renderer: str = "auto",
        outputs: Optional[List[str]] = None
    ):
        """Initialize Reveal.js source manager.
        
        Args:
            resolution: Output resolution (e.g., "1920x1080")
            framerate: Output framerate (fps)
            bitrate: Encoding bitrate in kbps
            mediamtx_path: Default MediaMTX path (used if outputs not specified)
            renderer: Renderer to use ("auto", "wpe", "chromium")
            outputs: List of output IDs (e.g., ["slides", "slides_overlay"])
                     Each output gets its own pipeline streaming to mediamtx_path=output_id
        """
        self.resolution = resolution
        self.framerate = framerate
        self.bitrate = bitrate
        self.renderer_preference = renderer
        
        # Multiple outputs support
        # If outputs not specified, use single output with mediamtx_path
        if outputs is None:
            outputs = [mediamtx_path]
        
        # Initialize output instances
        self._outputs: Dict[str, RevealOutput] = {}
        for output_id in outputs:
            self._outputs[output_id] = RevealOutput(
                output_id=output_id,
                mediamtx_path=output_id  # Use output_id as MediaMTX path
            )
        
        # Backward compatibility: keep track of default output
        self.mediamtx_path = outputs[0] if outputs else mediamtx_path
        
        self.renderer_type: Optional[str] = None  # "wpe" or "chromium"
        self._lock = threading.Lock()
        self._gst_ready = False
        
        # Detect available renderer
        self._detect_renderer()
        
        logger.info(f"RevealSourceManager initialized with outputs: {list(self._outputs.keys())}")
    
    def _detect_renderer(self) -> None:
        """Detect which HTML renderer is available."""
        if self.renderer_preference == "wpe":
            if self._check_wpesrc():
                self.renderer_type = "wpe"
                logger.info("Using WPE WebKit renderer (wpesrc)")
            else:
                logger.error("WPE WebKit requested but not available")
                self.renderer_type = None
        elif self.renderer_preference == "chromium":
            if self._check_chromium():
                self.renderer_type = "chromium"
                logger.info("Using Chromium headless renderer")
            else:
                logger.error("Chromium requested but not available")
                self.renderer_type = None
        else:  # auto
            if self._check_wpesrc():
                self.renderer_type = "wpe"
                logger.info("Auto-detected WPE WebKit renderer (wpesrc)")
            elif self._check_chromium():
                self.renderer_type = "chromium"
                logger.info("Auto-detected Chromium headless renderer")
            else:
                logger.warning("No HTML renderer available (wpesrc or chromium)")
                self.renderer_type = None
    
    def _check_wpesrc(self) -> bool:
        """Check if wpesrc GStreamer element is available."""
        try:
            result = subprocess.run(
                ["gst-inspect-1.0", "wpesrc"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"wpesrc check failed: {e}")
            return False
    
    def _check_chromium(self) -> bool:
        """Check if Chromium/Chrome is available."""
        for cmd in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
            try:
                result = subprocess.run(
                    ["which", cmd],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    return True
            except Exception:
                continue
        return False
    
    def _ensure_gst(self) -> bool:
        """Ensure GStreamer is initialized."""
        if self._gst_ready:
            return True
        
        if ensure_gst_initialized():
            self._gst_ready = True
            return True
        
        logger.error("GStreamer initialization failed")
        return False
    
    def get_output_ids(self) -> List[str]:
        """Get list of available output IDs."""
        return list(self._outputs.keys())
    
    def start(self, output_id: str, presentation_id: str, url: str) -> bool:
        """Start rendering Reveal.js presentation to a specific video output.
        
        Args:
            output_id: Output identifier (e.g., "slides" or "slides_overlay")
            presentation_id: Unique identifier for the presentation
            url: URL to render (e.g., "http://localhost:8000/graphics?presentation=demo")
        
        Returns:
            True if started successfully
        """
        if not self._ensure_gst():
            logger.error("Cannot start Reveal.js source - GStreamer not available")
            return False
        
        if not self.renderer_type:
            logger.error("Cannot start Reveal.js source - no renderer available")
            return False
        
        # Validate output_id
        if output_id not in self._outputs:
            logger.error(f"Unknown output_id: {output_id}. Available: {list(self._outputs.keys())}")
            return False
        
        with self._lock:
            output = self._outputs[output_id]
            
            if output.state == "running":
                logger.warning(f"Reveal.js output '{output_id}' already running")
                return False
            
            if output.pipeline:
                self._stop_output(output)
            
            output.state = "starting"
            output.current_url = url
            output.current_presentation_id = presentation_id
            
            try:
                # Build pipeline based on renderer type
                if self.renderer_type == "wpe":
                    output.pipeline = self._build_wpe_pipeline(url, output.mediamtx_path)
                elif self.renderer_type == "chromium":
                    output.pipeline = self._build_chromium_pipeline(url, output.mediamtx_path)
                else:
                    logger.error(f"Unknown renderer type: {self.renderer_type}")
                    output.state = "error"
                    return False
                
                if not output.pipeline:
                    logger.error(f"Failed to build Reveal.js pipeline for output '{output_id}'")
                    output.state = "error"
                    return False
                
                # Set up bus message handler with output reference
                bus = output.pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message", lambda bus, msg: self._on_bus_message(bus, msg, output))
                
                # Start pipeline
                Gst = get_gst()
                ret = output.pipeline.set_state(Gst.State.PLAYING)
                
                if ret == Gst.StateChangeReturn.FAILURE:
                    logger.error(f"Failed to start Reveal.js pipeline for output '{output_id}'")
                    output.pipeline.set_state(Gst.State.NULL)
                    output.pipeline = None
                    output.state = "error"
                    return False
                
                # Wait for pipeline to reach PLAYING state
                time.sleep(0.5)
                state_ret, current_state, pending_state = output.pipeline.get_state(Gst.SECOND)
                
                if state_ret == Gst.StateChangeReturn.FAILURE:
                    logger.error(f"Reveal.js pipeline for '{output_id}' failed to reach PLAYING state")
                    output.pipeline.set_state(Gst.State.NULL)
                    output.pipeline = None
                    output.state = "error"
                    return False
                
                output.state = "running"
                logger.info(f"Started Reveal.js output '{output_id}': {presentation_id} at {url}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start Reveal.js output '{output_id}': {e}")
                output.state = "error"
                if output.pipeline:
                    try:
                        output.pipeline.set_state(get_gst().State.NULL)
                    except:
                        pass
                    output.pipeline = None
                return False
    
    def _build_wpe_pipeline(self, url: str, mediamtx_path: str) -> Any:
        """Build GStreamer pipeline using wpesrc.
        
        Args:
            url: URL to render
            mediamtx_path: MediaMTX path for this output
        
        Returns:
            GStreamer pipeline object
        """
        width, height = self.resolution.split("x")
        
        # Get H.265 encoder for hardware acceleration
        encoder_str, caps_str, parse_str = get_h265_encoder(self.bitrate)
        
        # Build wpesrc pipeline
        # wpesrc renders HTML to video frames
        # draw-background=false makes background transparent (useful for overlays)
        pipeline_str = (
            f"wpesrc location=\"{url}\" draw-background=false ! "
            f"video/x-raw,width={width},height={height},framerate={self.framerate}/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,format=NV12 ! "
            f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
            f"{parse_str} ! "
            f"rtspclientsink location=rtsp://127.0.0.1:8554/{mediamtx_path} protocols=udp latency=0"
        )
        
        logger.info(f"Building WPE pipeline for output '{mediamtx_path}': {pipeline_str}")
        Gst = get_gst()
        return Gst.parse_launch(pipeline_str)
    
    def _build_chromium_pipeline(self, url: str, mediamtx_path: str) -> Any:
        """Build GStreamer pipeline using Chromium headless + screen capture.
        
        Note: This requires X11/Wayland display server and is more resource-intensive.
        
        Args:
            url: URL to render
            mediamtx_path: MediaMTX path for this output
        
        Returns:
            GStreamer pipeline object or None if not implemented
        """
        logger.warning("Chromium renderer not yet fully implemented")
        # TODO: Implement Chromium + ximagesrc/waylandsrc pipeline
        # This would require:
        # 1. Start Xvfb virtual display
        # 2. Launch Chromium headless on that display
        # 3. Use ximagesrc to capture the display
        # 4. Encode and stream to MediaMTX
        return None
    
    def _stop_pipeline_async(self, pipeline, output_id: str) -> None:
        """Stop pipeline in background thread to avoid blocking."""
        try:
            Gst = get_gst()
            logger.debug(f"Background stop for output '{output_id}'")
            pipeline.set_state(Gst.State.NULL)
            logger.debug(f"Background stop completed for '{output_id}'")
        except Exception as e:
            logger.warning(f"Background stop error for '{output_id}': {e}")
    
    def _stop_output(self, output: RevealOutput) -> bool:
        """Stop a specific output pipeline (internal helper).
        
        For live sources like wpesrc, we skip EOS and run set_state(NULL)
        in a background thread to avoid blocking the event loop.
        
        Args:
            output: RevealOutput instance to stop
        
        Returns:
            True if stop was initiated successfully
        """
        if not output.pipeline:
            output.state = "idle"
            return True
        
        output.state = "stopping"
        pipeline = output.pipeline
        output.pipeline = None  # Clear reference immediately
        output_id = output.output_id
        
        # Update state immediately - don't wait for pipeline
        output.state = "idle"
        output.current_url = None
        output.current_presentation_id = None
        
        # Stop pipeline in background thread to avoid blocking
        stop_thread = threading.Thread(
            target=self._stop_pipeline_async,
            args=(pipeline, output_id),
            daemon=True
        )
        stop_thread.start()
        
        logger.info(f"Initiated stop for Reveal.js output '{output_id}'")
        return True
    
    def stop(self, output_id: Optional[str] = None) -> bool:
        """Stop Reveal.js video output(s).
        
        Args:
            output_id: Specific output to stop, or None to stop all outputs
        
        Returns:
            True if stopped successfully
        """
        with self._lock:
            if output_id is not None:
                # Stop specific output
                if output_id not in self._outputs:
                    logger.error(f"Unknown output_id: {output_id}")
                    return False
                return self._stop_output(self._outputs[output_id])
            else:
                # Stop all outputs
                success = True
                for output in self._outputs.values():
                    if output.state != "idle":
                        if not self._stop_output(output):
                            success = False
                return success
    
    def stop_all(self) -> bool:
        """Stop all running outputs.
        
        Returns:
            True if all stopped successfully
        """
        return self.stop(output_id=None)
    
    def navigate(self, output_id: str, direction: str) -> bool:
        """Navigate slides in a specific presentation output.
        
        Args:
            output_id: Output identifier
            direction: Navigation direction ("next", "prev", "first", "last")
        
        Returns:
            True if navigation command sent successfully
        """
        if output_id not in self._outputs:
            logger.error(f"Unknown output_id: {output_id}")
            return False
        
        output = self._outputs[output_id]
        if output.state != "running":
            logger.warning(f"Cannot navigate - output '{output_id}' not running")
            return False
        
        # TODO: Implement slide navigation via JavaScript injection
        # This requires communication with the wpesrc element or the browser
        # For now, this is a placeholder
        logger.warning(f"Slide navigation not yet implemented: {direction} on output '{output_id}'")
        return False
    
    def goto_slide(self, output_id: str, slide_index: int) -> bool:
        """Go to a specific slide on a specific output.
        
        Args:
            output_id: Output identifier
            slide_index: Slide index to navigate to
        
        Returns:
            True if navigation command sent successfully
        """
        if output_id not in self._outputs:
            logger.error(f"Unknown output_id: {output_id}")
            return False
        
        output = self._outputs[output_id]
        if output.state != "running":
            logger.warning(f"Cannot navigate - output '{output_id}' not running")
            return False
        
        # TODO: Implement goto slide via JavaScript injection
        logger.warning(f"Goto slide not yet implemented: {slide_index} on output '{output_id}'")
        return False
    
    def get_output_status(self, output_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific output.
        
        Args:
            output_id: Output identifier
        
        Returns:
            Status dictionary or None if output doesn't exist
        """
        if output_id not in self._outputs:
            return None
        
        with self._lock:
            output = self._outputs[output_id]
            return {
                "output_id": output.output_id,
                "state": output.state,
                "presentation_id": output.current_presentation_id,
                "url": output.current_url,
                "mediamtx_path": output.mediamtx_path,
                "stream_url": f"rtsp://127.0.0.1:8554/{output.mediamtx_path}" if output.state == "running" else None
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all Reveal.js outputs.
        
        Returns:
            Status dictionary with global info and per-output status
        """
        with self._lock:
            # Build per-output status
            outputs_status = {}
            any_running = False
            for output_id, output in self._outputs.items():
                is_running = output.state == "running"
                if is_running:
                    any_running = True
                outputs_status[output_id] = {
                    "state": output.state,
                    "presentation_id": output.current_presentation_id,
                    "url": output.current_url,
                    "mediamtx_path": output.mediamtx_path,
                    "stream_url": f"rtsp://127.0.0.1:8554/{output.mediamtx_path}" if is_running else None
                }
            
            return {
                "renderer": self.renderer_type,
                "resolution": self.resolution,
                "framerate": self.framerate,
                "bitrate": self.bitrate,
                "available_outputs": list(self._outputs.keys()),
                "any_running": any_running,
                "outputs": outputs_status
            }
    
    def _on_bus_message(self, bus, message, output: RevealOutput) -> None:
        """Handle GStreamer bus messages for a specific output.
        
        Args:
            bus: GStreamer bus
            message: GStreamer message
            output: The RevealOutput instance this message belongs to
        """
        Gst = get_gst()
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Reveal.js output '{output.output_id}' error: {err.message} - {debug}")
            output.state = "error"
            
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Reveal.js output '{output.output_id}' warning: {warn.message} - {debug}")
            
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == output.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.debug(f"Reveal.js output '{output.output_id}' state: {old_state.value_nick} -> {new_state.value_nick}")
                
        elif message.type == Gst.MessageType.EOS:
            logger.info(f"Reveal.js output '{output.output_id}' EOS")

