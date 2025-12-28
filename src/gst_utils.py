"""GStreamer utilities with lazy initialization and timeout protection."""
import logging
import threading
import signal
import sys
import platform
from typing import Optional

logger = logging.getLogger(__name__)

# Global state for GStreamer initialization
_gst_initialized = False
_gst_init_lock = threading.Lock()
_gst_init_error: Optional[str] = None


class GstInitTimeout(Exception):
    """Raised when GStreamer initialization times out."""
    pass


def _get_gstreamer_install_instructions() -> str:
    """Get platform-specific GStreamer installation instructions."""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return """
GStreamer is not installed or not found on macOS.

To install GStreamer:
1. Install Homebrew (if not already installed):
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

2. Install GStreamer:
   brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav

3. Install Python GObject bindings:
   brew install pygobject3

4. Restart your terminal and try again.

For more info: https://gstreamer.freedesktop.org/documentation/installing/on-mac-osx.html
"""
    elif system == "Linux":
        return """
GStreamer is not installed or not found on Linux.

To install GStreamer on Ubuntu/Debian:
   sudo apt-get update
   sudo apt-get install -y gstreamer1.0-tools gstreamer1.0-plugins-base \\
       gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \\
       gstreamer1.0-plugins-ugly gstreamer1.0-libav \\
       python3-gi python3-gi-cairo gir1.2-gstreamer-1.0

For other distributions, consult: https://gstreamer.freedesktop.org/documentation/installing/on-linux.html
"""
    else:
        return f"GStreamer installation instructions not available for {system}. Please visit https://gstreamer.freedesktop.org"


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
    except ImportError as e:
        error_msg = f"GStreamer Python bindings not found: {e}"
        _gst_init_error = error_msg
        logger.error(error_msg)
        logger.error(_get_gstreamer_install_instructions())
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
            # On macOS, provide helpful installation instructions
            if platform.system() == "Darwin":
                logger.warning("=" * 70)
                logger.warning("GStreamer is required for video capture and processing.")
                logger.warning("On macOS, you can install it with:")
                logger.warning("  brew install gstreamer gst-plugins-base gst-plugins-good")
                logger.warning("  brew install pygobject3")
                logger.warning("=" * 70)
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
        
        if not _gst_initialized and _gst_init_error:
            # Provide helpful error message based on platform
            if platform.system() == "Darwin":
                logger.error("=" * 70)
                logger.error("GStreamer failed to initialize on macOS.")
                logger.error(_get_gstreamer_install_instructions())
                logger.error("=" * 70)
        
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

