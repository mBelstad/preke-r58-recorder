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
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import get_gst

logger = logging.getLogger(__name__)


# =============================================================================
# RKCIF Device Initialization (LT6911 HDMI-to-MIPI Bridge Support)
# =============================================================================
# The LT6911UXE HDMI-to-MIPI bridge devices report 0x0 resolution until
# format is explicitly set. These functions initialize the devices by:
# 1. Querying the V4L2 subdev for the actual detected HDMI resolution
# 2. Setting that format on the video device using v4l2-ctl
# =============================================================================

# Mapping of rkcif video devices to their V4L2 subdevs
# These subdevs report the actual HDMI signal resolution from LT6911 bridges
RKCIF_SUBDEV_MAP = {
    "/dev/video0": "/dev/v4l-subdev2",   # HDMI N0 via LT6911 7-002b
    "/dev/video11": "/dev/v4l-subdev7",  # HDMI N11 via LT6911 4-002b
    "/dev/video22": "/dev/v4l-subdev12", # HDMI N21 via LT6911 2-002b
}


def get_subdev_resolution(device_path: str) -> Optional[Tuple[int, int]]:
    """Query subdev for current resolution without reinitializing device.
    
    This is a fast, read-only query that checks the current HDMI signal
    resolution from the LT6911 bridge without modifying any device state.
    
    Args:
        device_path: Path to video device (e.g., /dev/video11)
        
    Returns:
        Tuple of (width, height) if signal detected, None if no signal or error
    """
    import re
    
    subdev = RKCIF_SUBDEV_MAP.get(device_path)
    if not subdev:
        # Not an rkcif device, return None (caller should use get_device_capabilities)
        return None
    
    try:
        # Query subdev for actual resolution detected by LT6911 bridge
        result = subprocess.run(
            ["v4l2-ctl", "-d", subdev, "--get-subdev-fmt", "pad=0"],
            capture_output=True, text=True, timeout=2
        )
        
        if result.returncode != 0:
            logger.debug(f"Failed to query subdev {subdev}: {result.stderr}")
            return None
        
        # Parse width/height from subdev output
        # Format: "Width/Height      : 1920/1080"
        width_match = re.search(r"Width/Height\s*:\s*(\d+)/(\d+)", result.stdout)
        if width_match:
            width = int(width_match.group(1))
            height = int(width_match.group(2))
            
            # Check for valid signal (not 0x0 or very small)
            if width >= 640 and height >= 480:
                return (width, height)
        
        return None
        
    except subprocess.TimeoutExpired:
        logger.debug(f"Timeout querying subdev for {device_path}")
        return None
    except FileNotFoundError:
        logger.warning("v4l2-ctl not found")
        return None
    except Exception as e:
        logger.debug(f"Error querying subdev resolution for {device_path}: {e}")
        return None


def initialize_rkcif_device(device_path: str) -> Dict[str, Any]:
    """Initialize rkcif device by querying subdev resolution and setting format.
    
    The LT6911 HDMI-to-MIPI bridges report resolution via their V4L2 subdevs,
    but the video devices start with 0x0 resolution. This function:
    1. Queries the subdev for the actual detected HDMI resolution
    2. Sets that format on the video device using v4l2-ctl
    3. Returns the device capabilities
    
    CRITICAL: This must be called BEFORE get_device_capabilities() for rkcif devices,
    otherwise the device will report 0x0 resolution even when HDMI signal is present.
    
    Args:
        device_path: Path to video device (e.g., /dev/video11)
        
    Returns:
        Device capabilities dictionary from get_device_capabilities()
    """
    import re
    
    subdev = RKCIF_SUBDEV_MAP.get(device_path)
    if not subdev:
        # Not an rkcif device, just return capabilities
        logger.debug(f"{device_path}: Not an rkcif device, skipping initialization")
        return get_device_capabilities(device_path)
    
    logger.info(f"{device_path}: Initializing rkcif device via subdev {subdev}")
    
    try:
        # Query subdev for actual resolution detected by LT6911 bridge
        result = subprocess.run(
            ["v4l2-ctl", "-d", subdev, "--get-subdev-fmt", "pad=0"],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            logger.warning(f"Failed to query subdev {subdev}: {result.stderr}")
            return get_device_capabilities(device_path)
        
        # Parse width/height from subdev output
        # Format: "Width/Height      : 1920/1080"
        width_match = re.search(r"Width/Height\s*:\s*(\d+)/(\d+)", result.stdout)
        if width_match:
            width = int(width_match.group(1))
            height = int(width_match.group(2))
            
            if width > 0 and height > 0:
                logger.info(f"{device_path}: Subdev reports {width}x{height}, setting format")
                
                # Set format on video device - use NV12 which is supported by all devices
                # NV12 goes directly to encoder without needing videoconvert
                # All rkcif and hdmirx devices support NV12 (verified via v4l2-ctl --list-formats)
                set_result = subprocess.run(
                    ["v4l2-ctl", "-d", device_path,
                     f"--set-fmt-video=width={width},height={height},pixelformat=NV12"],
                    capture_output=True, text=True, timeout=5
                )
                
                if set_result.returncode != 0:
                    logger.warning(f"Failed to set format on {device_path}: {set_result.stderr}")
                else:
                    logger.info(f"{device_path}: Format set to {width}x{height} NV12")
            else:
                logger.warning(f"{device_path}: Subdev reports invalid resolution {width}x{height}")
        else:
            logger.warning(f"{device_path}: Could not parse resolution from subdev output")
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout initializing {device_path}")
    except FileNotFoundError:
        logger.warning("v4l2-ctl not found")
    except Exception as e:
        logger.error(f"Error initializing {device_path}: {e}")
    
    # Return current device capabilities after initialization
    return get_device_capabilities(device_path)


def is_device_busy(device_path: str) -> Tuple[bool, List[int]]:
    """Check if a V4L2 device is currently in use by another process.
    
    Uses fuser command to check for processes holding the device open.
    
    Args:
        device_path: Path to the device (e.g., /dev/video11)
        
    Returns:
        Tuple of (is_busy, list_of_pids_using_device)
    """
    try:
        # fuser returns 0 if processes are using the file, 1 if not
        result = subprocess.run(
            ["fuser", device_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Parse PIDs from output (format: "/dev/video11:  1234  5678")
            output = result.stdout.strip() + result.stderr.strip()
            pids = []
            for part in output.split():
                # Skip the device path and extract just numbers
                part = part.rstrip('m')  # Remove 'm' suffix (memory mapped)
                if part.isdigit():
                    pids.append(int(part))
            return (len(pids) > 0, pids)
        else:
            return (False, [])
            
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout checking if {device_path} is busy")
        return (False, [])
    except FileNotFoundError:
        # fuser not available
        logger.debug("fuser command not available, skipping device busy check")
        return (False, [])
    except Exception as e:
        logger.warning(f"Error checking device busy status for {device_path}: {e}")
        return (False, [])


def get_h264_hardware_encoder(bitrate: int) -> Tuple[str, str, str]:
    """Get H.264 hardware encoder using Rockchip MPP.

    USE THIS FOR: Preview/streaming to MediaMTX (browser WebRTC requires H.264)
    DO NOT USE FOR: Recording (use H.265 for better compression)

    Uses mpph264enc with QP-based rate control.
    Baseline profile (no B-frames) prevents DTS errors.
    
    NOTE: Do NOT use mpph264enc's width/height properties - they cause RGA crashes
    even with NV12 input. Use software videoscale instead.

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

    # All devices now use NV12 - supported by both rkcif and hdmirx
    # NV12 goes directly to encoder without needing videoconvert
    result = {
        'format': 'NV12',
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

            # Check for no signal indicators:
            # - 640x480 is the default fallback resolution when no HDMI is connected
            # - BGR3/BGR format often indicates test pattern (no real signal)
            # - 0x0 resolution means device not initialized or no signal
            if result['width'] == 0 or result['height'] == 0:
                result['has_signal'] = False
                logger.info(f"Device {device_path}: 0x0 resolution, treating as no signal")
            elif result['width'] == 640 and result['height'] == 480:
                result['has_signal'] = False
                logger.info(f"Device {device_path}: 640x480 detected, treating as no signal")
            elif result['format'] in ['BGR3', 'BGR']:
                result['has_signal'] = False
                logger.info(f"Device {device_path}: BGR format detected, treating as no signal")
            
            # For hdmirx devices, also check DV timings for signal presence
            if "video60" in device_path:
                try:
                    dv_proc = subprocess.run(
                        ["v4l2-ctl", "-d", device_path, "--query-dv-timings"],
                        capture_output=True, text=True, timeout=5
                    )
                    if dv_proc.returncode != 0 or "fail" in dv_proc.stderr.lower() or "no signal" in dv_proc.stdout.lower():
                        result['has_signal'] = False
                        logger.info(f"Device {device_path}: hdmirx DV timings check failed, treating as no signal")
                except Exception as e:
                    logger.debug(f"DV timings check failed for {device_path}: {e}")

    except Exception as e:
        logger.warning(f"Error getting device capabilities for {device_path}: {e}")
        result['has_signal'] = False  # Assume no signal on error

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
    
    # CRITICAL: Initialize rkcif devices BEFORE querying capabilities
    # The LT6911 bridge devices report 0x0 resolution until format is explicitly set
    if device in RKCIF_SUBDEV_MAP:
        caps = initialize_rkcif_device(device)
    else:
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
        
        # Don't force framerate in source caps - let v4l2src negotiate natively
        # hdmirx provides whatever the HDMI source sends
        is_4k = src_width > 1920 or src_height > 1080
        
        if is_4k:
            logger.info(f"4K hdmirx source {device}: native capture, downscaling to {target_width}x{target_height}")
        
        return (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,width={src_width},height={src_height} ! "
            f"queue max-size-buffers=3 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
            f"videorate ! video/x-raw,framerate={target_fps}/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={target_width},height={target_height},format=NV12"
        )

    elif device_type == "hdmi_rkcif":
        src_format = caps['format'] or 'UYVY'
        src_width = caps['width']
        src_height = caps['height']
        
        # Don't force framerate in source caps - let v4l2src negotiate natively
        # LT6911 bridges may provide various framerates depending on the HDMI source
        is_4k = src_width > 1920 or src_height > 1080
        
        if is_4k:
            logger.info(f"4K rkcif source {device}: native capture, downscaling to {target_width}x{target_height}")
        
        return (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format={src_format},width={src_width},height={src_height} ! "
            f"queue max-size-buffers=3 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
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


def build_ingest_pipeline_string(
    cam_id: str,
    device: str,
    resolution: str = "1920x1080",
    bitrate: int = 4000,
    rtsp_port: int = 8554
) -> str:
    """Build always-on ingest pipeline string (Publisher pattern).
    
    The ingest pipeline:
    - Captures from V4L2 device at native resolution
    - Encodes to H.264 using hardware encoder with internal scaling
    - Streams to MediaMTX via RTSP
    - Runs continuously (never stops during recording)
    
    OPTIMIZATION: Uses mpph264enc internal hardware scaling instead of 
    CPU-intensive videoconvert + videoscale. The MPP encoder accepts
    UYVY/NV16 directly and has width/height properties for hardware scaling.
    
    All consumers (preview, recording, mixer) subscribe to MediaMTX.
    
    Args:
        cam_id: Camera identifier (used as RTSP path)
        device: V4L2 device path
        resolution: Target resolution "WxH" (for preview/streaming)
        bitrate: Target bitrate in kbps
        rtsp_port: MediaMTX RTSP port
        
    Returns:
        GStreamer pipeline string
    """
    target_width, target_height = resolution.split("x")
    target_width = int(target_width)
    target_height = int(target_height)
    
    device_type = detect_device_type(device)
    
    # CRITICAL: Initialize rkcif devices BEFORE querying capabilities
    if device in RKCIF_SUBDEV_MAP:
        caps = initialize_rkcif_device(device)
    else:
        caps = get_device_capabilities(device)
    
    logger.info(f"Building ingest pipeline: cam_id={cam_id}, device={device}, type={device_type}, caps={caps}, target={target_width}x{target_height}")
    
    if not caps['has_signal']:
        # No signal - use test pattern
        logger.warning(f"No signal on {device}, using black test pattern")
        encoder_str, caps_str, parse_str = get_h264_hardware_encoder(bitrate)
        return (
            f"videotestsrc pattern=black is-live=true ! "
            f"video/x-raw,width={target_width},height={target_height},framerate=30/1,format=NV12 ! "
            f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
            f"{parse_str} config-interval=-1 ! "
            f"rtspclientsink location=rtsp://127.0.0.1:{rtsp_port}/{cam_id} protocols=tcp latency=0"
        )
    
    src_width = caps['width']
    src_height = caps['height']
    
    logger.info(f"{cam_id}: Source {src_width}x{src_height} -> target {target_width}x{target_height}")
    
    # OPTIMIZED: Request NV12 directly from V4L2 (all our devices support it!)
    # This skips CPU-intensive videoconvert entirely
    # Then use software videoscale (still needed, but lighter without format conversion)
    encoder_str, caps_str, parse_str = get_h264_hardware_encoder(bitrate)
    
    # Request NV12 directly from source - both rkcif and hdmirx support NV12!
    source_pipeline = (
        f"v4l2src device={device} io-mode=mmap ! "
        f"video/x-raw,format=NV12,width={src_width},height={src_height}"
    )
    
    # OPTIMIZED PIPELINE: NV12 from source -> scale only -> encode
    # No videoconvert needed! NV12 goes directly to videoscale and encoder
    pipeline_str = (
        f"{source_pipeline} ! "
        f"queue max-size-buffers=3 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"videoscale ! "
        f"video/x-raw,width={target_width},height={target_height} ! "
        f"queue max-size-buffers=3 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"{encoder_str} ! "
        f"{caps_str} ! "
        f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"{parse_str} config-interval=-1 ! "
        f"rtspclientsink location=rtsp://127.0.0.1:{rtsp_port}/{cam_id} protocols=tcp latency=0"
    )
    
    return pipeline_str


def build_tee_recording_pipeline(
    cam_id: str,
    device: str,
    recording_path: str,
    recording_bitrate: int = 18000,   # 18 Mbps for quality recording
    preview_bitrate: int = 6000,      # 6 Mbps for streaming
    resolution: str = "1920x1080",
    rtsp_port: int = 8554,
    use_valve: bool = True,           # Enable valve for recording control
) -> str:
    """Build TEE pipeline with independent recording + always-on preview.
    
    This is the optimized architecture for simultaneous recording and preview:
    - NV12 captured directly from source (no videoconvert needed)
    - RGA-accelerated videoscale (shared by both branches)
    - Recording can start/stop without affecting preview (via valve element)
    - .mkv container for edit-while-record (DaVinci Resolve compatible)
    - Dual VPU H.264 encoding (different bitrates/profiles)
    
    Pipeline structure:
        v4l2src (NV12) → [RGA: videoscale 1080p] → TEE
                                                    ├─→ Recording (18Mbps High) → .mkv
                                                    └─→ Preview (6Mbps Baseline) → RTSP
    
    Prerequisites:
    - GST_VIDEO_CONVERT_USE_RGA=1 set before GStreamer import
    - MediaMTX running on localhost:rtsp_port
    - Device initialized with NV12 format (via initialize_rkcif_device)
    
    Args:
        cam_id: Camera identifier (used as RTSP path, e.g., "cam2")
        device: V4L2 device path (e.g., "/dev/video11")
        recording_path: Output file path for recording (should end in .mkv)
        recording_bitrate: Bitrate for recording in kbps (default: 18000 = 18Mbps)
        preview_bitrate: Bitrate for preview stream in kbps (default: 6000 = 6Mbps)
        resolution: Target resolution "WxH" (default: 1920x1080)
        rtsp_port: MediaMTX RTSP port (default: 8554)
        use_valve: If True, include valve element to control recording (default: True)
        
    Returns:
        GStreamer pipeline string
        
    Note:
        When use_valve=True, recording starts paused (valve drop=true).
        To start recording: pipeline.get_by_name('rec_valve').set_property('drop', False)
        To stop recording: set drop=True, then send EOS to finalize the file
    """
    target_width, target_height = resolution.split("x")
    target_width = int(target_width)
    target_height = int(target_height)
    
    # Initialize device and get capabilities
    if device in RKCIF_SUBDEV_MAP:
        caps = initialize_rkcif_device(device)
    else:
        caps = get_device_capabilities(device)
    
    logger.info(f"Building TEE pipeline: {cam_id}, device={device}, caps={caps}, target={target_width}x{target_height}")
    
    if not caps.get('has_signal', False):
        # No signal - return a test pattern pipeline
        logger.warning(f"No signal on {device}, using black test pattern for TEE pipeline")
        return _build_tee_test_pattern_pipeline(
            cam_id, target_width, target_height,
            recording_path, recording_bitrate, preview_bitrate,
            rtsp_port, use_valve
        )
    
    src_width = caps['width']
    src_height = caps['height']
    # All devices now use NV12 directly - no videoconvert needed
    src_format = 'NV12'
    
    logger.info(f"{cam_id}: TEE pipeline source NV12 {src_width}x{src_height} -> target {target_width}x{target_height}")
    
    # === SOURCE + SCALE (NV12 DIRECT) ===
    # All devices capture NV12 directly, eliminating the videoconvert step
    # NV12 goes straight to encoder after RGA-accelerated scaling
    # 
    # Pipeline: v4l2src (NV12) → videorate (30fps) → videoscale (RGA) → encoder
    # This is simpler and more efficient than UYVY→NV12 conversion
    source_pipeline = (
        f"v4l2src device={device} io-mode=mmap ! "
        f"video/x-raw,format=NV12,width={src_width},height={src_height} ! "
        f"videorate ! video/x-raw,framerate=30/1 ! "
        f"videoscale ! "
        f"video/x-raw,format=NV12,width={target_width},height={target_height}"
    )
    
    # === RECORDING BRANCH ===
    # High bitrate H.264 High profile for quality recording
    # matroskamux for edit-while-record capability (DaVinci Resolve compatible)
    valve_element = "valve name=rec_valve drop=true ! " if use_valve else ""
    recording_branch = (
        f"queue name=rec_queue max-size-buffers=60 max-size-time=0 "
        f"max-size-bytes=0 leaky=downstream ! "
        f"{valve_element}"
        f"mpph264enc "
        f"qp-init=20 qp-min=10 qp-max=35 "
        f"gop=30 profile=high rc-mode=cbr "
        f"bps={recording_bitrate * 1000} ! "
        f"video/x-h264,stream-format=byte-stream ! "
        f"h264parse config-interval=1 ! "
        f"matroskamux streamable=true ! "
        f"filesink location={recording_path} sync=false"
    )
    
    # === PREVIEW BRANCH (Always On) ===
    # Lower bitrate H.264 Baseline for streaming efficiency (browser compatible)
    preview_branch = (
        f"queue name=preview_queue max-size-buffers=30 max-size-time=0 "
        f"max-size-bytes=0 leaky=downstream ! "
        f"mpph264enc "
        f"qp-init=26 qp-min=10 qp-max=51 "
        f"gop=30 profile=baseline rc-mode=cbr "
        f"bps={preview_bitrate * 1000} ! "
        f"video/x-h264,stream-format=byte-stream ! "
        f"h264parse config-interval=-1 ! "
        f"rtspclientsink location=rtsp://127.0.0.1:{rtsp_port}/{cam_id} "
        f"protocols=tcp latency=0"
    )
    
    # === COMBINED PIPELINE ===
    pipeline = (
        f"{source_pipeline} ! "
        f"tee name=t ! "
        f"{recording_branch} "
        f"t. ! {preview_branch}"
    )
    
    return pipeline


def _build_tee_test_pattern_pipeline(
    cam_id: str,
    width: int,
    height: int,
    recording_path: str,
    recording_bitrate: int,
    preview_bitrate: int,
    rtsp_port: int,
    use_valve: bool
) -> str:
    """Build TEE pipeline with test pattern when no signal is available."""
    valve_element = "valve name=rec_valve drop=true ! " if use_valve else ""
    
    return (
        f"videotestsrc pattern=black is-live=true ! "
        f"video/x-raw,format=NV12,width={width},height={height},framerate=30/1 ! "
        f"tee name=t ! "
        # Recording branch
        f"queue max-size-buffers=30 leaky=downstream ! "
        f"{valve_element}"
        f"mpph264enc qp-init=20 gop=30 profile=high bps={recording_bitrate * 1000} ! "
        f"video/x-h264,stream-format=byte-stream ! "
        f"h264parse config-interval=1 ! "
        f"matroskamux streamable=true ! "
        f"filesink location={recording_path} sync=false "
        # Preview branch
        f"t. ! queue max-size-buffers=30 leaky=downstream ! "
        f"mpph264enc qp-init=26 gop=30 profile=baseline bps={preview_bitrate * 1000} ! "
        f"video/x-h264,stream-format=byte-stream ! "
        f"h264parse config-interval=-1 ! "
        f"rtspclientsink location=rtsp://127.0.0.1:{rtsp_port}/{cam_id} protocols=tcp latency=0"
    )


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

