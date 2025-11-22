"""GStreamer pipeline builders for macOS and R58."""
import logging
from typing import Optional
import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst

logger = logging.getLogger(__name__)


def build_mock_pipeline(
    cam_id: str,
    output_path: str,
    resolution: str = "1920x1080",
    bitrate: int = 5000,
    mediamtx_path: Optional[str] = None,
) -> Gst.Pipeline:
    """Build a mock pipeline for macOS development using videotestsrc."""
    pipeline_str = (
        f"videotestsrc pattern=ball is-live=true ! "
        f"video/x-raw,width={resolution.split('x')[0]},height={resolution.split('x')[1]},framerate=30/1 ! "
        f"timeoverlay ! "
        f"x264enc bitrate={bitrate} speed-preset=ultrafast tune=zerolatency ! "
        f"video/x-h264,profile=baseline ! "
    )

    if mediamtx_path:
        # Tee to both file and MediaMTX
        pipeline_str += (
            f"tee name=t ! "
            f"queue ! "
            f"h264parse ! "
            f"mp4mux fragment-duration=1 ! "
            f"filesink location={output_path} "
            f"t. ! "
            f"queue ! "
            f"rtspclientsink location={mediamtx_path}"
        )
    else:
        # File only
        pipeline_str += (
            f"h264parse ! "
            f"mp4mux fragment-duration=1 ! "
            f"filesink location={output_path}"
        )

    logger.info(f"Building mock pipeline for {cam_id}: {pipeline_str}")
    pipeline = Gst.parse_launch(pipeline_str)
    return pipeline


def build_r58_pipeline(
    cam_id: str,
    device: str,
    output_path: str,
    resolution: str = "1920x1080",
    bitrate: int = 5000,
    codec: str = "h264",
    mediamtx_path: Optional[str] = None,
) -> Gst.Pipeline:
    """Build a real hardware-accelerated pipeline for R58."""
    width, height = resolution.split("x")

    # Video source for HDMI (rk_hdmirx) - must use io-mode=mmap and handle NV24 format
    # HDMI device is /dev/video60 with NV24 format (YUV 4:4:4)
    # Must convert NV24 before encoding
    if "video60" in device or "hdmirx" in device.lower():
        source_str = (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format=NV24,width={width},height={height} ! "
            f"videoconvert ! videoscale ! video/x-raw,width={width},height={height}"
        )
    else:
        # For other video devices (MIPI cameras, etc.)
        source_str = f"v4l2src device={device} ! videoconvert ! videoscale ! video/x-raw,width={width},height={height}"

    # Hardware encoder selection
    if codec == "h265":
        # bps is in bits per second (bitrate is in kbps, so multiply by 1000)
        bps = bitrate * 1000
        encoder_str = f"mpph265enc bps={bps} bps-max={bps * 2}"
        caps_str = "video/x-h265"
        parse_str = "h265parse"
        mux_str = "matroskamux"
    else:  # h264
        # Use mpph264enc (v4l2h264enc may not be available on all R58 systems)
        # bps is in bits per second (bitrate is in kbps, so multiply by 1000)
        bps = bitrate * 1000
        encoder_str = f"mpph264enc bps={bps} bps-max={bps * 2}"
        caps_str = "video/x-h264,profile=high"
        parse_str = "h264parse"
        mux_str = "mp4mux fragment-duration=1"

    # Build pipeline
    if mediamtx_path:
        # Tee to both file and MediaMTX
        pipeline_str = (
            f"{source_str} ! "
            f"timeoverlay ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"tee name=t ! "
            f"queue ! "
            f"{parse_str} ! "
            f"{mux_str} ! "
            f"filesink location={output_path} "
            f"t. ! "
            f"queue ! "
            f"rtspclientsink location={mediamtx_path}"
        )
    else:
        # File only - ensure proper format conversion for MPP encoder
        # videoconvert already handles format conversion, but we ensure NV12 for MPP
        pipeline_str = (
            f"{source_str} ! "
            f"timeoverlay ! "
            f"video/x-raw,format=NV12 ! "  # MPP encoder expects NV12
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"{parse_str} ! "
            f"{mux_str} ! "
            f"filesink location={output_path}"
        )

    logger.info(f"Building R58 pipeline for {cam_id} from {device}: {pipeline_str}")
    pipeline = Gst.parse_launch(pipeline_str)
    return pipeline


def build_pipeline(
    platform: str,
    cam_id: str,
    device: str,
    output_path: str,
    resolution: str = "1920x1080",
    bitrate: int = 5000,
    codec: str = "h264",
    mediamtx_path: Optional[str] = None,
) -> Gst.Pipeline:
    """Build pipeline based on platform."""
    if platform == "macos":
        return build_mock_pipeline(
            cam_id=cam_id,
            output_path=output_path,
            resolution=resolution,
            bitrate=bitrate,
            mediamtx_path=mediamtx_path,
        )
    else:  # r58
        return build_r58_pipeline(
            cam_id=cam_id,
            device=device,
            output_path=output_path,
            resolution=resolution,
            bitrate=bitrate,
            codec=codec,
            mediamtx_path=mediamtx_path,
        )

