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
    # Must convert NV24 before encoding - always use videoconvert
    if "video60" in device or "hdmirx" in device.lower():
        # HDMI input: use NV24 format explicitly with framerate, then convert to NV12
        source_str = (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format=NV24,width={width},height={height},framerate=60/1 ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
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
        # Use x264enc (software encoder) - more reliable than mpph264enc for HDMI
        # bitrate is in kbps for x264enc
        encoder_str = f"x264enc tune=zerolatency bitrate={bitrate} speed-preset=superfast"
        caps_str = "video/x-h264"
        parse_str = "h264parse"
        mux_str = "mp4mux"

    # Build pipeline with optional tee for MediaMTX streaming
    # CRITICAL: Use tee in single pipeline to avoid dual device access crashes
    if mediamtx_path:
        # Tee to both file recording and RTMP streaming (single pipeline, single device access)
        # Stream goes to MediaMTX via RTMP on port 1935
        # Extract path from mediamtx_path (e.g., rtsp://localhost:8554/cam0 -> cam0)
        stream_path = mediamtx_path.split("/")[-1] if "/" in mediamtx_path else cam_id
        rtmp_url = f"rtmp://127.0.0.1:1935/{stream_path}"
        
        pipeline_str = (
            f"{source_str} ! "
            f"timeoverlay ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"tee name=t ! "
            f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
            f"{parse_str} ! "
            f"{mux_str} ! "
            f"filesink location={output_path} "
            f"t. ! "
            f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
            f"flvmux streamable=true ! "
            f"rtmpsink location={rtmp_url}"
        )
    else:
        # Recording only - no streaming
        pipeline_str = (
            f"{source_str} ! "
            f"timeoverlay ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"{parse_str} ! "
            f"{mux_str} ! "
            f"filesink location={output_path}"
        )

    logger.info(f"Building R58 pipeline for {cam_id} from {device}: {pipeline_str}")
    pipeline = Gst.parse_launch(pipeline_str)
    return pipeline


def build_preview_pipeline(
    platform: str,
    cam_id: str,
    device: str,
    resolution: str = "1920x1080",
    bitrate: int = 5000,
    codec: str = "h264",
    mediamtx_path: Optional[str] = None,
) -> Gst.Pipeline:
    """Build preview-only pipeline (streaming, no recording) for multiview."""
    if platform == "macos":
        # Mock preview pipeline
        width, height = resolution.split("x")
        pipeline_str = (
            f"videotestsrc pattern=ball is-live=true ! "
            f"video/x-raw,width={width},height={height},framerate=30/1 ! "
            f"x264enc bitrate={bitrate} speed-preset=ultrafast tune=zerolatency ! "
            f"video/x-h264,profile=baseline ! "
            f"flvmux streamable=true ! "
            f"rtmpsink location={mediamtx_path or f'rtmp://127.0.0.1:1935/{cam_id}_preview'}"
        )
        return Gst.parse_launch(pipeline_str)
    else:  # r58
        return build_r58_preview_pipeline(
            cam_id=cam_id,
            device=device,
            resolution=resolution,
            bitrate=bitrate,
            codec=codec,
            mediamtx_path=mediamtx_path,
        )


def build_r58_preview_pipeline(
    cam_id: str,
    device: str,
    resolution: str = "1920x1080",
    bitrate: int = 5000,
    codec: str = "h264",
    mediamtx_path: Optional[str] = None,
) -> Gst.Pipeline:
    """Build preview-only pipeline for R58 (streaming to MediaMTX, no recording)."""
    width, height = resolution.split("x")

    # Video source - use 30fps for preview to reduce encoding latency
    if "video60" in device or "hdmirx" in device.lower():
        source_str = (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format=NV24,width={width},height={height},framerate=60/1 ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"video/x-raw,format=NV12"
        )
    else:
        source_str = f"v4l2src device={device} ! videoconvert ! videoscale ! video/x-raw,width={width},height={height},framerate=30/1"

    # Encoder - ALWAYS use H.264 for preview (flvmux doesn't support H.265)
    # Balanced settings: good quality with low latency
    # Use 80% of recording bitrate for preview (better quality)
    preview_bitrate = max(4000, int(bitrate * 0.8))  # 80% of recording bitrate
    # key-int-max=60 = keyframe every 2s at 30fps (good quality, acceptable latency)
    # speed-preset=veryfast = best balance of quality and latency
    # threads=2 = slight threading for better quality without much latency
    # sync-lookahead=1 = minimal lookahead for better quality
    # dct8x8=true = better quality for 1080p
    encoder_str = f"x264enc tune=zerolatency bitrate={preview_bitrate} speed-preset=veryfast key-int-max=60 threads=2 sync-lookahead=1 dct8x8=true"
    caps_str = "video/x-h264"

    # Preview pipeline: stream to MediaMTX only (no recording)
    if mediamtx_path:
        stream_path = mediamtx_path.split("/")[-1] if "/" in mediamtx_path else f"{cam_id}_preview"
        rtmp_url = f"rtmp://127.0.0.1:1935/{stream_path}"
    else:
        rtmp_url = f"rtmp://127.0.0.1:1935/{cam_id}_preview"

    # Low-latency pipeline: minimal queues for stability, leaky downstream, no sync
    # Small queues prevent frame drops while maintaining low latency
    pipeline_str = (
        f"{source_str} ! "
        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"{encoder_str} ! "
        f"{caps_str} ! "
        f"queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"flvmux streamable=true ! "
        f"rtmpsink location={rtmp_url} sync=false"
    )

    logger.info(f"Building preview pipeline for {cam_id}: {pipeline_str}")
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

