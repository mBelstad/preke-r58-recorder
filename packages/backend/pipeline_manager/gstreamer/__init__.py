"""GStreamer utilities with lazy initialization and timeout protection.

This module provides GStreamer initialization and access for the pipeline manager.
Ported from src/gst_utils.py with adaptations for the new backend structure.
"""
import logging
import threading
import platform
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Global state for GStreamer initialization
_gst_initialized = False
_gst_init_lock = threading.Lock()
_gst_init_error: Optional[str] = None

# Cached module references
_Gst: Optional[Any] = None
_GLib: Optional[Any] = None


def _gst_init_thread():
    """Initialize GStreamer in a separate thread."""
    global _gst_initialized, _gst_init_error, _Gst, _GLib
    try:
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst, GLib
        Gst.init(None)
        _Gst = Gst
        _GLib = GLib
        _gst_initialized = True
        logger.info("GStreamer initialized successfully")
    except ImportError as e:
        error_msg = f"GStreamer Python bindings not found: {e}"
        _gst_init_error = error_msg
        logger.error(error_msg)
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
            _gst_init_error = f"Initialization timed out after {timeout}s"
            logger.error(f"GStreamer initialization timed out after {timeout}s")
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
    
    Returns True if GStreamer is available, False otherwise.
    """
    if _gst_initialized:
        return True
    return init_gstreamer()


def get_gst() -> Optional[Any]:
    """
    Get the GStreamer module, initializing if needed.
    
    Returns:
        The Gst module, or None if initialization failed
    """
    if not ensure_gst_initialized():
        return None
    return _Gst


def get_glib() -> Optional[Any]:
    """
    Get the GLib module for main loop.
    
    Returns:
        The GLib module, or None if not available
    """
    if not ensure_gst_initialized():
        return None
    return _GLib

