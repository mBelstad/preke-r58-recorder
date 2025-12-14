"""GStreamer utilities with lazy initialization and timeout protection."""
import logging
import threading
import signal
from typing import Optional

logger = logging.getLogger(__name__)

# Global state for GStreamer initialization
_gst_initialized = False
_gst_init_lock = threading.Lock()
_gst_init_error: Optional[str] = None


class GstInitTimeout(Exception):
    """Raised when GStreamer initialization times out."""
    pass


def _gst_init_thread():
    """Initialize GStreamer in a separate thread."""
    global _gst_initialized, _gst_init_error
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        Gst.init(None)
        _gst_initialized = True
        logger.info("GStreamer initialized successfully")
    except Exception as e:
        _gst_init_error = str(e)
        logger.error(f"GStreamer initialization failed: {e}")


def init_gstreamer(timeout: float = 10.0) -> bool:
    """
    Initialize GStreamer with timeout protection.
    
    Args:
        timeout: Maximum seconds to wait for initialization
        
    Returns:
        True if initialized successfully, False otherwise
    """
    global _gst_initialized, _gst_init_error
    
    with _gst_init_lock:
        if _gst_initialized:
            return True
        
        if _gst_init_error:
            logger.warning(f"GStreamer previously failed to initialize: {_gst_init_error}")
            return False
        
        logger.info(f"Initializing GStreamer (timeout: {timeout}s)...")
        
        # Run initialization in a thread with timeout
        init_thread = threading.Thread(target=_gst_init_thread, daemon=True)
        init_thread.start()
        init_thread.join(timeout=timeout)
        
        if init_thread.is_alive():
            # Thread is still running - initialization timed out
            _gst_init_error = f"Initialization timed out after {timeout}s"
            logger.error(f"GStreamer initialization timed out after {timeout}s")
            logger.error("This may indicate stuck gst-plugin-scanner processes - reboot may be required")
            return False
        
        return _gst_initialized


def is_gst_initialized() -> bool:
    """Check if GStreamer is initialized."""
    return _gst_initialized


def get_gst_init_error() -> Optional[str]:
    """Get the GStreamer initialization error, if any."""
    return _gst_init_error


def ensure_gst_initialized() -> bool:
    """
    Ensure GStreamer is initialized before using pipelines.
    
    Call this at the start of any function that needs GStreamer.
    Returns True if GStreamer is available, False otherwise.
    """
    if _gst_initialized:
        return True
    return init_gstreamer()


def get_gst():
    """
    Get the GStreamer module, initializing if needed.
    
    Returns:
        The Gst module, or None if initialization failed
    """
    if not ensure_gst_initialized():
        return None
    
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        return Gst
    except Exception as e:
        logger.error(f"Failed to import GStreamer: {e}")
        return None


def get_glib():
    """
    Get the GLib module for main loop.
    
    Returns:
        The GLib module, or None if not available
    """
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import GLib
        return GLib
    except Exception as e:
        logger.error(f"Failed to import GLib: {e}")
        return None

