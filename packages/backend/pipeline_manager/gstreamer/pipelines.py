"""GStreamer pipeline builders for R58 recording and streaming.

Ported from src/pipelines.py with adaptations for the new backend structure.
Provides hardware-accelerated H.264/H.265 encoding using Rockchip MPP.

Encoder Architecture:
---------------------
- **Preview (streaming to MediaMTX)**: Uses H.264 (mpph264enc)
  - Required for browser WebRTC compatibility (H.265 has limited browser support)
  - Stable with QP-based rate control: qp-init=26, qp-min=10, qp-max=51
  - Baseline profile (no B-frames) prevents DTS errors
  - Tested stable: 2025-12-28 (see docs/fix-log.md)

- **Recording**: Uses H.265 (mpph265enc)
  - Better compression efficiency (~30-40% smaller files)
  - Tested stable: 2025-12-19 (see docs/fix-log.md)
  - Used for local file storage only (not browser playback)

DO NOT use H.265 for preview - browsers cannot decode H.265 via WebRTC!
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from . import get_gst

logger = logging.getLogger(__name__)


def get_h264_hardware_encoder(bitrate: int) -> Tuple[str, str, str]:
    """Get H.264 hardware encoder using Rockchip MPP.

    USE THIS FOR: Preview/streaming to MediaMTX (browser WebRTC requires H.264)
    DO NOT USE FOR: Recording (use H.265 for better compression)

    Uses mpph264enc with QP-based rate control.
    Baseline profile (no B-frames) prevents DTS errors.

    Tested stable on 2025-12-28 with this exact configuration.
    Previous kernel panics were with different parameters.

    Args:
        bitrate: Target bitrate in kbps

    Returns:
        Tuple of (encoder_str, caps_str, parse_str)
    """
    bps = bitrate * 1000  # Convert kbps to bps
    encoder_str = (
        f"mpph264enc "
        f"qp-init=26 qp-min=10 qp-max=51 "
        f"gop=30 profile=baseline rc-mode=cbr bps={bps}"
    )
    caps_str = "video/x-h264,stream-format=byte-stream"
    parse_str = "h264parse"
    return encoder_str, caps_str, parse_str


def get_h265_encoder(bitrate: int) -> Tuple[str, str, str]:
    """Get H.265 hardware encoder using Rockchip MPP.

    USE THIS FOR: Recording to file (better compression, ~30-40% smaller)
    DO NOT USE FOR: Preview/streaming (browsers cannot decode H.265 via WebRTC)

    Uses mpph265enc for hardware acceleration.
    Tested stable on 2025-12-19 - no kernel panics, low CPU usage (~10% per stream).

    Args:
        bitrate: Target bitrate in kbps

    Returns:
        Tuple of (encoder_str, caps_str, parse_str)
    """
    bps = bitrate * 1000
    encoder_str = f"mpph265enc bps={bps} bps-max={bps * 2}"
    caps_str = "video/x-h265"
    parse_str = "h265parse"
    return encoder_str, caps_str, parse_str


def get_h264_software_encoder(bitrate: int) -> Tuple[str, str]:
    """Get H.264 software encoder for streaming compatibility.

    Note: mpph264enc (H.264 hardware) can cause issues.
    Use this for RTMP streaming (flvmux requires H.264).

    Args:
        bitrate: Target bitrate in kbps

    Returns:
        Tuple of (encoder_str, caps_str)
    """
    encoder_str = (
        f"x264enc tune=zerolatency bitrate={bitrate} speed-preset=superfast "
        f"key-int-max=30 bframes=0 threads=4 sliced-threads=true"
    )
    caps_str = "video/x-h264"
    return encoder_str, caps_str


def detect_device_type(device_path: str) -> str:
    """Detect the type of video device.

    Returns:
        'hdmirx' - RK3588 HDMI receiver (direct)
        'hdmi_rkcif' - HDMI input via rkcif (LT6911 bridge)
        'usb' - USB capture device
        'unknown' - Unknown device type
    """
    path = Path(device_path)
    if not path.exists():
        return "unknown"

    # R58 4x4 3S specific: Known HDMI port mappings
    hdmi_rkcif_devices = ["/dev/video0", "/dev/video11", "/dev/video22"]
    if str(path) in hdmi_rkcif_devices:
        return "hdmi_rkcif"

    # video60 is the direct hdmirx port
    if "video60" in str(path):
        return "hdmirx"

    # Check sysfs for more info
    try:
        sysfs_base = Path("/sys/class/video4linux")
        sysfs_path = sysfs_base / path.name

        if not sysfs_path.exists():
            return "unknown"

        name_path = sysfs_path / "name"
        if name_path.exists():
            name = name_path.read_text().strip().lower()
            if "hdmirx" in name:
                return "hdmirx"
            if "uvc" in name or "usb" in name:
                return "usb"

    except Exception as e:
        logger.warning(f"Error detecting device type for {device_path}: {e}")

    return "unknown"


def get_device_capabilities(device_path: str) -> Dict[str, Any]:
    """Get device capabilities using v4l2-ctl.

    Returns:
        Dictionary with format, width, height, framerate, has_signal, etc.
    """
    import subprocess

    result = {
        'format': 'NV16',
        'width': 1920,
        'height': 1080,
        'framerate': 30,
        'has_signal': True,
        'is_bayer': False,
        'bayer_format': None
    }

    try:
        # Get current format
        proc = subprocess.run(
            ["v4l2-ctl", "-d", device_path, "--get-fmt-video"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if proc.returncode == 0:
            output = proc.stdout
            # Parse width/height
            for line in output.splitlines():
                line = line.strip()
                if "Width/Height" in line:
                    # Format: "Width/Height      : 1920/1080"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        wh = parts[1].strip().split("/")
                        if len(wh) >= 2:
                            result['width'] = int(wh[0])
                            result['height'] = int(wh[1])
                elif "Pixel Format" in line:
                    # Format: "Pixel Format      : 'UYVY' (UYVY 4:2:2)"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        fmt_part = parts[1].strip()
                        # Extract format from quotes: 'UYVY' -> UYVY
                        if "'" in fmt_part:
                            fmt = fmt_part.split("'")[1]  # Get string between first two quotes
                        else:
                            fmt = fmt_part.split()[0]  # Fallback: get first word
                        result['format'] = fmt

            # Check for no signal (640x480 BGR typically means no signal)
            if result['width'] == 640 and result['height'] == 480:
                if result['format'] in ['BGR3', 'BGR']:
                    result['has_signal'] = False

    except Exception as e:
        logger.warning(f"Error getting device capabilities for {device_path}: {e}")

    return result


def build_source_pipeline(
    device: str,
    target_width: int = 1920,
    target_height: int = 1080,
    target_fps: int = 30
) -> str:
    """Build the video source portion of a pipeline.

    Handles device detection and format conversion.

    Args:
        device: V4L2 device path (e.g., /dev/video11)
        target_width: Target output width
        target_height: Target output height
        target_fps: Target framerate

    Returns:
        GStreamer pipeline string for video source
    """
    device_type = detect_device_type(device)
    caps = get_device_capabilities(device)

    logger.info(f"Building source pipeline: device={device}, type={device_type}, caps={caps}")

    if not caps['has_signal']:
        # No signal - use test pattern
        logger.warning(f"No signal on {device}, using black test pattern")
        return (
            f"videotestsrc pattern=black is-live=true ! "
            f"video/x-raw,width={target_width},height={target_height},framerate={target_fps}/1,format=NV12"
        )

    # Build source based on device type
    if device_type == "hdmirx":
        src_width = caps['width']
        src_height = caps['height']
        return (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,width={src_width},height={src_height} ! "
            f"videorate ! video/x-raw,framerate={target_fps}/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={target_width},height={target_height},format=NV12"
        )

    elif device_type == "hdmi_rkcif":
        src_format = caps['format'] or 'NV16'
        src_width = caps['width']
        src_height = caps['height']
        src_fps = caps['framerate'] or 60
        return (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format={src_format},width={src_width},height={src_height},framerate={src_fps}/1 ! "
            f"videorate ! video/x-raw,framerate={target_fps}/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={target_width},height={target_height},format=NV12"
        )

    elif device_type == "usb":
        return (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videorate ! video/x-raw,framerate={target_fps}/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={target_width},height={target_height},format=NV12"
        )

    else:
        # Generic fallback
        return (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={target_width},height={target_height},framerate={target_fps}/1,format=NV12"
        )


def build_preview_pipeline_string(
    cam_id: str,
    device: str,
    bitrate: int = 8000,
    resolution: str = "1920x1080"
) -> str:
    """Build GStreamer pipeline string for live preview streaming.

    Streams to MediaMTX via RTSP for WHEP preview.
    Uses H.264 hardware encoder with baseline profile.

    Args:
        cam_id: Camera identifier (used as RTSP path)
        device: V4L2 device path
        bitrate: Target bitrate in kbps
        resolution: Target resolution "WxH"

    Returns:
        GStreamer pipeline string
    """
    width, height = resolution.split("x")
    source_str = build_source_pipeline(device, int(width), int(height), 30)

    encoder_str, caps_str, parse_str = get_h264_hardware_encoder(bitrate)

    # Stream to MediaMTX via RTSP with TCP
    pipeline_str = (
        f"{source_str} ! "
        f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"{encoder_str} ! "
        f"{caps_str} ! "
        f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"{parse_str} config-interval=-1 ! "
        f"rtspclientsink location=rtsp://127.0.0.1:8554/{cam_id} protocols=tcp latency=0"
    )

    return pipeline_str


def build_recording_pipeline_string(
    cam_id: str,
    device: str,
    output_path: str,
    bitrate: int = 5000,
    resolution: str = "1920x1080",
    with_preview: bool = False
) -> str:
    """Build GStreamer pipeline string for recording.

    Uses H.265 hardware encoder for efficient recording.
    Optionally tees to MediaMTX for simultaneous preview.

    Args:
        cam_id: Camera identifier
        device: V4L2 device path
        output_path: Output file path
        bitrate: Target bitrate in kbps
        resolution: Target resolution "WxH"
        with_preview: Also stream preview to MediaMTX

    Returns:
        GStreamer pipeline string
    """
    width, height = resolution.split("x")
    source_str = build_source_pipeline(device, int(width), int(height), 30)

    # Use H.265 for recording (better compression)
    encoder_str, caps_str, parse_str = get_h265_encoder(bitrate)
    mux_str = "matroskamux"

    if with_preview:
        # Tee: H.265 recording + H.264 preview streaming via RTSP
        # Uses hardware H.264 encoder for preview (tested stable 2025-12-28)
        stream_encoder_str, stream_caps_str, stream_parse_str = get_h264_hardware_encoder(bitrate)
        pipeline_str = (
            f"{source_str} ! "
            f"timeoverlay ! "
            f"tee name=source_tee ! "
            # Recording branch (H.265 hardware for file storage)
            f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"{parse_str} ! "
            f"{mux_str} ! "
            f"filesink location={output_path} "
            # Preview branch (H.264 hardware for RTSP/MediaMTX - same path as preview pipeline)
            f"source_tee. ! "
            f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
            f"{stream_encoder_str} ! "
            f"{stream_caps_str} ! "
            f"{stream_parse_str} config-interval=-1 ! "
            f"rtspclientsink location=rtsp://127.0.0.1:8554/{cam_id} protocols=tcp latency=0"
        )
    else:
        # Recording only
        pipeline_str = (
            f"{source_str} ! "
            f"timeoverlay ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"{parse_str} ! "
            f"{mux_str} ! "
            f"filesink location={output_path}"
        )

    return pipeline_str


def build_subscriber_recording_pipeline_string(
    cam_id: str,
    source_url: str,
    output_path: str
) -> str:
    """Build pipeline to record from MediaMTX RTSP stream.

    Subscribes to existing MediaMTX stream and records to file.
    Uses H.264 because that's what the preview streams use.

    Args:
        cam_id: Camera identifier
        source_url: RTSP URL (e.g., rtsp://localhost:8554/cam0)
        output_path: Output file path

    Returns:
        GStreamer pipeline string
    """
    pipeline_str = (
        f"rtspsrc location={source_url} latency=100 protocols=tcp ! "
        f"rtph264depay ! "
        f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
        f"h264parse ! "
        f"mp4mux ! "
        f"filesink location={output_path}"
    )

    return pipeline_str


def create_pipeline(pipeline_string: str) -> Optional[Any]:
    """Create a GStreamer pipeline from a pipeline string.

    Args:
        pipeline_string: GStreamer pipeline description

    Returns:
        Gst.Pipeline object, or None if creation failed
    """
    Gst = get_gst()
    if Gst is None:
        logger.error("GStreamer not available")
        return None

    try:
        logger.info(f"Creating pipeline: {pipeline_string}")
        pipeline = Gst.parse_launch(pipeline_string)
        return pipeline
    except Exception as e:
        logger.error(f"Failed to create pipeline: {e}")
        return None

