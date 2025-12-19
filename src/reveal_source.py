"""Reveal.js video source manager using WPE WebKit or Chromium for HTML rendering."""
import logging
import subprocess
import threading
import time
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from .gst_utils import ensure_gst_initialized, get_gst
    from .pipelines import get_h265_encoder
except ImportError:
    # Fallback for direct execution
    from gst_utils import ensure_gst_initialized, get_gst
    from pipelines import get_h265_encoder

logger = logging.getLogger(__name__)


class RevealSourceManager:
    """Manages Reveal.js rendering to video stream via WPE WebKit or Chromium.
    
    This class handles:
    - Detection of available HTML rendering backend (wpesrc or Chromium)
    - GStreamer pipeline creation for HTML-to-video conversion
    - Streaming to MediaMTX via RTSP
    - Slide navigation control via JavaScript injection
    """
    
    def __init__(
        self,
        resolution: str = "1920x1080",
        framerate: int = 30,
        bitrate: int = 4000,
        mediamtx_path: str = "slides",
        renderer: str = "auto"
    ):
        """Initialize Reveal.js source manager.
        
        Args:
            resolution: Output resolution (e.g., "1920x1080")
            framerate: Output framerate (fps)
            bitrate: Encoding bitrate in kbps
            mediamtx_path: MediaMTX path for RTSP streaming
            renderer: Renderer to use ("auto", "wpe", "chromium")
        """
        self.resolution = resolution
        self.framerate = framerate
        self.bitrate = bitrate
        self.mediamtx_path = mediamtx_path
        self.renderer_preference = renderer
        
        # State
        self.pipeline = None
        self.state = "idle"  # idle, starting, running, stopping, error
        self.current_url: Optional[str] = None
        self.current_presentation_id: Optional[str] = None
        self.renderer_type: Optional[str] = None  # "wpe" or "chromium"
        self._lock = threading.Lock()
        self._gst_ready = False
        
        # Detect available renderer
        self._detect_renderer()
    
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
    
    def start(self, presentation_id: str, url: str) -> bool:
        """Start rendering Reveal.js presentation to video stream.
        
        Args:
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
        
        with self._lock:
            if self.state == "running":
                logger.warning("Reveal.js source already running")
                return False
            
            if self.pipeline:
                self.stop()
            
            self.state = "starting"
            self.current_url = url
            self.current_presentation_id = presentation_id
            
            try:
                # Build pipeline based on renderer type
                if self.renderer_type == "wpe":
                    self.pipeline = self._build_wpe_pipeline(url)
                elif self.renderer_type == "chromium":
                    self.pipeline = self._build_chromium_pipeline(url)
                else:
                    logger.error(f"Unknown renderer type: {self.renderer_type}")
                    self.state = "error"
                    return False
                
                if not self.pipeline:
                    logger.error("Failed to build Reveal.js pipeline")
                    self.state = "error"
                    return False
                
                # Set up bus message handler
                bus = self.pipeline.get_bus()
                bus.add_signal_watch()
                bus.connect("message", self._on_bus_message)
                
                # Start pipeline
                Gst = get_gst()
                ret = self.pipeline.set_state(Gst.State.PLAYING)
                
                if ret == Gst.StateChangeReturn.FAILURE:
                    logger.error("Failed to start Reveal.js pipeline")
                    self.pipeline.set_state(Gst.State.NULL)
                    self.pipeline = None
                    self.state = "error"
                    return False
                
                # Wait for pipeline to reach PLAYING state
                time.sleep(0.5)
                state_ret, current_state, pending_state = self.pipeline.get_state(Gst.SECOND)
                
                if state_ret == Gst.StateChangeReturn.FAILURE:
                    logger.error("Reveal.js pipeline failed to reach PLAYING state")
                    self.pipeline.set_state(Gst.State.NULL)
                    self.pipeline = None
                    self.state = "error"
                    return False
                
                self.state = "running"
                logger.info(f"Started Reveal.js source: {presentation_id} at {url}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start Reveal.js source: {e}")
                self.state = "error"
                if self.pipeline:
                    try:
                        self.pipeline.set_state(get_gst().State.NULL)
                    except:
                        pass
                    self.pipeline = None
                return False
    
    def _build_wpe_pipeline(self, url: str) -> Any:
        """Build GStreamer pipeline using wpesrc.
        
        Args:
            url: URL to render
        
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
            f"rtspclientsink location=rtsp://127.0.0.1:8554/{self.mediamtx_path} protocols=udp latency=0"
        )
        
        logger.info(f"Building WPE pipeline: {pipeline_str}")
        Gst = get_gst()
        return Gst.parse_launch(pipeline_str)
    
    def _build_chromium_pipeline(self, url: str) -> Any:
        """Build GStreamer pipeline using Chromium headless + screen capture.
        
        Note: This requires X11/Wayland display server and is more resource-intensive.
        
        Args:
            url: URL to render
        
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
    
    def stop(self) -> bool:
        """Stop the Reveal.js video source.
        
        Returns:
            True if stopped successfully
        """
        with self._lock:
            if not self.pipeline:
                self.state = "idle"
                return True
            
            self.state = "stopping"
            
            try:
                Gst = get_gst()
                
                # Send EOS
                self.pipeline.send_event(Gst.Event.new_eos())
                
                # Wait for EOS
                bus = self.pipeline.get_bus()
                bus.timed_pop_filtered(
                    int(5 * Gst.SECOND),
                    Gst.MessageType.EOS | Gst.MessageType.ERROR
                )
                
                # Set to NULL
                self.pipeline.set_state(Gst.State.NULL)
                self.pipeline = None
                
                self.state = "idle"
                self.current_url = None
                self.current_presentation_id = None
                
                logger.info("Stopped Reveal.js source")
                return True
                
            except Exception as e:
                logger.error(f"Error stopping Reveal.js source: {e}")
                try:
                    if self.pipeline:
                        self.pipeline.set_state(get_gst().State.NULL)
                        self.pipeline = None
                except:
                    pass
                self.state = "error"
                return False
    
    def navigate(self, direction: str) -> bool:
        """Navigate slides in the presentation.
        
        Args:
            direction: Navigation direction ("next", "prev", "first", "last")
        
        Returns:
            True if navigation command sent successfully
        """
        if self.state != "running":
            logger.warning("Cannot navigate - Reveal.js source not running")
            return False
        
        # TODO: Implement slide navigation via JavaScript injection
        # This requires communication with the wpesrc element or the browser
        # For now, this is a placeholder
        logger.warning(f"Slide navigation not yet implemented: {direction}")
        return False
    
    def goto_slide(self, slide_index: int) -> bool:
        """Go to a specific slide.
        
        Args:
            slide_index: Slide index to navigate to
        
        Returns:
            True if navigation command sent successfully
        """
        if self.state != "running":
            logger.warning("Cannot navigate - Reveal.js source not running")
            return False
        
        # TODO: Implement goto slide via JavaScript injection
        logger.warning(f"Goto slide not yet implemented: {slide_index}")
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the Reveal.js source.
        
        Returns:
            Status dictionary
        """
        with self._lock:
            return {
                "state": self.state,
                "presentation_id": self.current_presentation_id,
                "url": self.current_url,
                "renderer": self.renderer_type,
                "resolution": self.resolution,
                "framerate": self.framerate,
                "bitrate": self.bitrate,
                "mediamtx_path": self.mediamtx_path,
                "stream_url": f"rtsp://127.0.0.1:8554/{self.mediamtx_path}" if self.state == "running" else None
            }
    
    def _on_bus_message(self, bus, message) -> None:
        """Handle GStreamer bus messages."""
        Gst = get_gst()
        
        if message.type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"Reveal.js pipeline error: {err.message} - {debug}")
            self.state = "error"
            
        elif message.type == Gst.MessageType.WARNING:
            warn, debug = message.parse_warning()
            logger.warning(f"Reveal.js pipeline warning: {warn.message} - {debug}")
            
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.debug(f"Reveal.js state changed: {old_state.value_nick} -> {new_state.value_nick}")
                
        elif message.type == Gst.MessageType.EOS:
            logger.info("Reveal.js pipeline EOS")
