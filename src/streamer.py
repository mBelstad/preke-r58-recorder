"""Separate streaming pipeline for MediaMTX."""
import logging
from typing import Optional
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

logger = logging.getLogger(__name__)


def build_streaming_pipeline(
    device: str,
    cam_id: str,
    resolution: str = "1920x1080",
    bitrate: int = 5000,
    mediamtx_rtsp_url: str = "rtsp://localhost:8554",
) -> Optional[Gst.Pipeline]:
    """Build a separate streaming pipeline for MediaMTX.
    
    Uses rtph264pay + udpsink to send RTP stream to MediaMTX.
    MediaMTX will accept this as an RTSP source.
    """
    width, height = resolution.split("x")
    
    # For HDMI (video60), use the same pipeline structure
    if "video60" in device:
        source_str = (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format=NV24,width={width},height={height},framerate=60/1 ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
    else:
        source_str = f"v4l2src device={device} ! videoconvert ! video/x-raw,width={width},height={height}"
    
    # Streaming pipeline: encode and send via RTP
    # MediaMTX accepts RTP streams on UDP port 8000 (RTP) and 8001 (RTCP)
    pipeline_str = (
        f"{source_str} ! "
        f"timeoverlay ! "
        f"x264enc tune=zerolatency bitrate={bitrate} speed-preset=superfast ! "
        f"video/x-h264 ! "
        f"rtph264pay config-interval=1 pt=96 ! "
        f"udpsink host=127.0.0.1 port=8000"
    )
    
    try:
        logger.info(f"Building streaming pipeline for {cam_id}: {pipeline_str}")
        pipeline = Gst.parse_launch(pipeline_str)
        return pipeline
    except Exception as e:
        logger.error(f"Failed to build streaming pipeline: {e}")
        return None

