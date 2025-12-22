"""GStreamer pipeline builders for macOS and R58."""
import logging
from typing import Optional

from .gst_utils import get_gst, ensure_gst_initialized

logger = logging.getLogger(__name__)

# Note: Previously used RTP_PORT_MAP for raw UDP streaming
# Now using rtspclientsink which handles RTSP publishing automatically


def get_h264_hardware_encoder(bitrate: int) -> tuple[str, str, str]:
    """Get H.264 hardware encoder using raspberry.ninja-proven config.
    
    Uses mpph264enc (Rockchip MPP H.264 encoder) with QP-based rate control.
    This configuration was proven stable in raspberry.ninja tests on 2025-12-18.
    
    Args:
        bitrate: Target bitrate in kbps
        
    Returns:
        Tuple of (encoder_str, caps_str, parse_str)
    """
    bps = bitrate * 1000  # Convert kbps to bps
    encoder_str = (
        f"mpph264enc "
        f"qp-init=26 qp-min=10 qp-max=51 "
        f"gop=30 profile=baseline rc-mode=cbr bps={bps}"  # baseline profile has no B-frames, prevents DTS errors
    )
    caps_str = "video/x-h264,stream-format=byte-stream"
    parse_str = "h264parse"
    return encoder_str, caps_str, parse_str


def get_h265_encoder(bitrate: int) -> tuple[str, str, str]:
    """Get H.265 hardware encoder string for R58 VPU.
    
    Uses mpph265enc (Rockchip MPP H.265 encoder) for hardware acceleration.
    Tested stable on 2025-12-19 - no kernel panics, low CPU usage (~10% per stream).
    
    Args:
        bitrate: Target bitrate in kbps
        
    Returns:
        Tuple of (encoder_str, caps_str, parse_str)
    """
    bps = bitrate * 1000  # Convert kbps to bps
    encoder_str = f"mpph265enc bps={bps} bps-max={bps * 2}"
    caps_str = "video/x-h265"
    parse_str = "h265parse"
    return encoder_str, caps_str, parse_str


def get_h264_encoder_for_streaming(bitrate: int) -> tuple[str, str]:
    """Get H.264 software encoder for streaming compatibility.
    
    Note: mpph264enc (H.264 hardware) causes kernel panics - DO NOT USE.
    This is only used for streaming to MediaMTX via RTMP (flvmux requires H.264).
    
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


def build_mock_pipeline(
    cam_id: str,
    output_path: str,
    resolution: str = "1920x1080",
    bitrate: int = 5000,
    mediamtx_path: Optional[str] = None,
):
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
    Gst = get_gst()
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
):
    """Build a real hardware-accelerated pipeline for R58."""
    width, height = resolution.split("x")

    # Video source detection and pipeline setup
    # Import device detection (lazy import to avoid circular dependencies)
    try:
        from .device_detection import detect_device_type, get_device_capabilities, initialize_rkcif_device, RKCIF_SUBDEV_MAP
        device_type = detect_device_type(device)
        
        # For rkcif devices (LT6911 bridges), initialize format from subdev first
        if device in RKCIF_SUBDEV_MAP:
            caps = initialize_rkcif_device(device)
        else:
            caps = get_device_capabilities(device)
    except ImportError:
        # Fallback to simple detection
        device_type = "hdmirx" if ("video60" in device or "hdmirx" in device.lower()) else "unknown"
        caps = {'format': 'NV16', 'width': int(width), 'height': int(height), 'framerate': 60, 'has_signal': True, 'is_bayer': False, 'bayer_format': None}
    
    logger.info(f"Building recording pipeline for {cam_id}: device_type={device_type}, caps={caps}")
    
    if device_type == "hdmirx":
        # HDMI input: RK hdmirx currently exposes NV16 (4:2:2); convert to NV12 for encoders
        # Must use io-mode=mmap for hdmirx
        # Use actual detected resolution, not configured resolution
        # IMPORTANT: Don't force framerate - let v4l2src negotiate natively
        src_width = caps.get('width') or int(width)
        src_height = caps.get('height') or int(height)
        logger.info(f"{cam_id}: hdmirx recording using detected resolution {src_width}x{src_height} (native framerate)")
        source_str = (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format=NV16,width={src_width},height={src_height} ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},format=NV12"
        )
    elif device_type == "hdmi_rkcif":
        # HDMI input via rkcif (LT6911 bridge): Use explicit format like hdmirx
        # Query actual device capabilities for reliable pipeline construction
        if not caps['has_signal']:
            # No signal - use test pattern fallback
            logger.warning(f"{cam_id}: No HDMI signal on {device}, using test pattern")
            source_str = (
                f"videotestsrc pattern=black is-live=true ! "
                f"video/x-raw,width={width},height={height},framerate=30/1,format=NV12"
            )
        elif caps['is_bayer']:
            # Bayer format (video21) - needs bayer2rgb conversion
            bayer_fmt = caps['bayer_format'] or 'rggb'
            src_width = caps['width']
            src_height = caps['height']
            logger.info(f"{cam_id}: Using Bayer format {bayer_fmt} at {src_width}x{src_height}")
            source_str = (
                f"v4l2src device={device} io-mode=mmap ! "
                f"video/x-bayer,format={bayer_fmt},width={src_width},height={src_height} ! "
                f"bayer2rgb ! "
                f"videoconvert ! "
                f"videoscale ! "
                f"video/x-raw,width={width},height={height},format=NV12"
            )
        else:
            # NV16/YVYU format - use explicit format specification like hdmirx
            src_format = caps['format'] or 'NV16'
            src_width = caps['width']
            src_height = caps['height']
            src_fps = caps['framerate'] or 60
            logger.info(f"{cam_id}: Using explicit format {src_format} at {src_width}x{src_height}@{src_fps}fps")
            source_str = (
                f"v4l2src device={device} io-mode=mmap ! "
                f"video/x-raw,format={src_format},width={src_width},height={src_height},framerate={src_fps}/1 ! "
                f"videorate ! video/x-raw,framerate=30/1 ! "
                f"videoconvert ! "
                f"videoscale ! "
                f"video/x-raw,width={width},height={height},format=NV12"
            )
    elif device_type == "usb":
        # USB capture devices: typically use different formats, let v4l2src negotiate
        # USB devices may have different framerates, so we use videorate to normalize
        source_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},format=NV12"
        )
    else:
        # For other video devices (MIPI cameras, etc.)
        # Let v4l2src negotiate format, then convert and scale
        source_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},format=NV12"
        )

    # Use H.265 hardware encoder for recording (tested stable 2025-12-19)
    encoder_str, caps_str, parse_str = get_h265_encoder(bitrate)
    mux_str = "matroskamux"

    # Build pipeline with optional tee for MediaMTX streaming
    # CRITICAL: Use tee in single pipeline to avoid dual device access crashes
    if mediamtx_path:
        # H.265 recording with H.264 streaming (RTMP/flvmux doesn't support H.265)
        # Tee after source, encode separately for recording and streaming
        stream_path = mediamtx_path.split("/")[-1] if "/" in mediamtx_path else cam_id
        rtmp_url = f"rtmp://127.0.0.1:1935/{stream_path}"
        
        pipeline_str = (
            f"{source_str} ! "
            f"timeoverlay ! "
            f"tee name=source_tee ! "
            # Recording branch (H.265 hardware)
            f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
            f"{encoder_str} ! "
            f"{caps_str} ! "
            f"{parse_str} ! "
            f"{mux_str} ! "
            f"filesink location={output_path} "
            # Streaming branch (H.264 software for RTMP compatibility)
            f"source_tee. ! "
            f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
        )
        # Use software H.264 for streaming (mpph264enc causes kernel panics)
        stream_encoder_str, stream_caps_str = get_h264_encoder_for_streaming(bitrate)
        pipeline_str += (
            f"{stream_encoder_str} ! "
            f"{stream_caps_str} ! "
            f"h264parse ! "
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
    Gst = get_gst()
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
):
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
        Gst = get_gst()
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
):
    """Build preview-only pipeline for R58 (streaming to MediaMTX, no recording)."""
    width, height = resolution.split("x")

    # Video source - use explicit format specification for reliability
    # Import device detection (lazy import to avoid circular dependencies)
    try:
        from .device_detection import detect_device_type, get_device_capabilities, initialize_rkcif_device, RKCIF_SUBDEV_MAP
        device_type = detect_device_type(device)
        
        # For rkcif devices (LT6911 bridges), initialize format from subdev first
        if device in RKCIF_SUBDEV_MAP:
            caps = initialize_rkcif_device(device)
        else:
            caps = get_device_capabilities(device)
    except ImportError:
        # Fallback to simple detection
        device_type = "hdmirx" if ("video60" in device or "hdmirx" in device.lower()) else "unknown"
        caps = {'format': 'NV16', 'width': int(width), 'height': int(height), 'framerate': 60, 'has_signal': True, 'is_bayer': False, 'bayer_format': None}
    
    logger.info(f"Building preview pipeline for {cam_id}: device_type={device_type}, caps={caps}")
    
    if device_type == "hdmirx":
        # Use actual detected resolution, not configured resolution
        # IMPORTANT: Don't force framerate - let v4l2src negotiate natively
        src_width = caps.get('width') or int(width)
        src_height = caps.get('height') or int(height)
        logger.info(f"{cam_id}: hdmirx preview using detected resolution {src_width}x{src_height} (native framerate)")
        source_str = (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,format=NV16,width={src_width},height={src_height} ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},format=NV12"
        )
    elif device_type == "hdmi_rkcif":
        # HDMI input via rkcif (LT6911 bridge): Use explicit format like hdmirx
        # Query actual device capabilities for reliable pipeline construction
        if not caps['has_signal']:
            # No signal - use test pattern fallback with "No Signal" indicator
            logger.warning(f"{cam_id}: No HDMI signal on {device}, using test pattern")
            source_str = (
                f"videotestsrc pattern=black is-live=true ! "
                f"video/x-raw,width={width},height={height},framerate=30/1,format=NV12"
            )
        elif caps['is_bayer']:
            # Bayer format (video21) - needs bayer2rgb conversion
            bayer_fmt = caps['bayer_format'] or 'rggb'
            src_width = caps['width']
            src_height = caps['height']
            logger.info(f"{cam_id}: Using Bayer format {bayer_fmt} at {src_width}x{src_height}")
            source_str = (
                f"v4l2src device={device} io-mode=mmap ! "
                f"video/x-bayer,format={bayer_fmt},width={src_width},height={src_height} ! "
                f"bayer2rgb ! "
                f"videoconvert ! "
                f"videoscale ! "
                f"video/x-raw,width={width},height={height},format=NV12"
            )
        else:
            # NV16/YVYU format - use explicit format specification like hdmirx
            src_format = caps['format'] or 'NV16'
            src_width = caps['width']
            src_height = caps['height']
            src_fps = caps['framerate'] or 60
            logger.info(f"{cam_id}: Using explicit format {src_format} at {src_width}x{src_height}@{src_fps}fps")
            source_str = (
                f"v4l2src device={device} io-mode=mmap ! "
                f"video/x-raw,format={src_format},width={src_width},height={src_height},framerate={src_fps}/1 ! "
                f"videorate ! video/x-raw,framerate=30/1 ! "
                f"videoconvert ! "
                f"videoscale ! "
                f"video/x-raw,width={width},height={height},format=NV12"
            )
    elif device_type == "usb":
        # USB capture devices: let v4l2src negotiate format, then normalize framerate
        source_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},format=NV12"
        )
    else:
        source_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},framerate=30/1,format=NV12"
        )

    # Encoder - ALWAYS use H.264 for preview (flvmux doesn't support H.265)
    # Use 80% of recording bitrate for preview (better quality)
    preview_bitrate = max(4000, int(bitrate * 0.8))  # 80% of recording bitrate
    # Use hardware encoder for low CPU usage
    encoder_str, caps_str, _ = get_h264_hardware_encoder(preview_bitrate)

    # Preview pipeline: stream to MediaMTX only (no recording)
    if mediamtx_path:
        stream_path = mediamtx_path.split("/")[-1] if "/" in mediamtx_path else f"{cam_id}_preview"
        rtmp_url = f"rtmp://127.0.0.1:1935/{stream_path}"
    else:
        rtmp_url = f"rtmp://127.0.0.1:1935/{cam_id}_preview"

    # Add queue with minimal buffering for lower latency
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
    Gst = get_gst()
    pipeline = Gst.parse_launch(pipeline_str)
    return pipeline


def build_ingest_pipeline(
    platform: str,
    cam_id: str,
    device: str,
    resolution: str = "1920x1080",
    bitrate: int = 8000,
    codec: str = "h264",
    mediamtx_path: Optional[str] = None,
):
    """Build always-on ingest pipeline (streaming only, no recording).
    
    This pipeline captures from device and streams to MediaMTX.
    All consumers (preview, recording, mixer) subscribe to the MediaMTX stream.
    """
    if platform == "macos":
        # Mock ingest pipeline for development
        width, height = resolution.split("x")
        pipeline_str = (
            f"videotestsrc pattern=ball is-live=true ! "
            f"video/x-raw,width={width},height={height},framerate=30/1 ! "
            f"x264enc bitrate={bitrate} speed-preset=ultrafast tune=zerolatency ! "
            f"video/x-h264,profile=baseline ! "
            f"flvmux streamable=true ! "
            f"rtmpsink location={mediamtx_path or f'rtmp://127.0.0.1:1935/{cam_id}'}"
        )
        Gst = get_gst()
        return Gst.parse_launch(pipeline_str)
    else:  # r58
        return build_r58_ingest_pipeline(
            cam_id=cam_id,
            device=device,
            resolution=resolution,
            bitrate=bitrate,
            codec=codec,
            mediamtx_path=mediamtx_path,
        )


def build_r58_ingest_pipeline(
    cam_id: str,
    device: str,
    resolution: str = "1920x1080",
    bitrate: int = 8000,
    codec: str = "h264",
    mediamtx_path: Optional[str] = None,
):
    """Build always-on ingest pipeline for R58 (streaming to MediaMTX only)."""
    width, height = resolution.split("x")

    # Video source - reuse device detection logic
    try:
        from .device_detection import detect_device_type, get_device_capabilities, initialize_rkcif_device, RKCIF_SUBDEV_MAP
        device_type = detect_device_type(device)
        
        # For rkcif devices, initialize format from subdev first
        if device in RKCIF_SUBDEV_MAP:
            caps = initialize_rkcif_device(device)
        else:
            caps = get_device_capabilities(device)
    except ImportError:
        device_type = "hdmirx" if ("video60" in device or "hdmirx" in device.lower()) else "unknown"
        caps = {'format': 'NV16', 'width': int(width), 'height': int(height), 'framerate': 60, 'has_signal': True, 'is_bayer': False, 'bayer_format': None}
    
    logger.info(f"Building ingest pipeline for {cam_id}: device_type={device_type}, caps={caps}")
    
    if device_type == "hdmirx":
        # Use actual detected resolution, not configured resolution
        # This is critical for hdmirx which may receive 4K even if config says 1080p
        # IMPORTANT: Don't force format or framerate - let v4l2src negotiate natively
        # The camera may output at various formats (NV16, BGR, etc.) and framerates
        src_width = caps.get('width') or int(width)
        src_height = caps.get('height') or int(height)
        logger.info(f"{cam_id}: hdmirx using detected resolution {src_width}x{src_height} (native format/framerate)")
        source_str = (
            f"v4l2src device={device} io-mode=mmap ! "
            f"video/x-raw,width={src_width},height={src_height} ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},format=NV12"
        )
    elif device_type == "hdmi_rkcif":
        if not caps['has_signal']:
            logger.warning(f"{cam_id}: No HDMI signal on {device}, using test pattern")
            source_str = (
                f"videotestsrc pattern=black is-live=true ! "
                f"video/x-raw,width={width},height={height},framerate=30/1,format=NV12"
            )
        elif caps['is_bayer']:
            bayer_fmt = caps['bayer_format'] or 'rggb'
            src_width = caps['width']
            src_height = caps['height']
            logger.info(f"{cam_id}: Using Bayer format {bayer_fmt} at {src_width}x{src_height}")
            source_str = (
                f"v4l2src device={device} io-mode=mmap ! "
                f"video/x-bayer,format={bayer_fmt},width={src_width},height={src_height} ! "
                f"bayer2rgb ! "
                f"videoconvert ! "
                f"videoscale ! "
                f"video/x-raw,width={width},height={height},format=NV12"
            )
        else:
            src_format = caps['format'] or 'NV16'
            src_width = caps['width']
            src_height = caps['height']
            src_fps = caps['framerate'] or 60
            logger.info(f"{cam_id}: Using explicit format {src_format} at {src_width}x{src_height}@{src_fps}fps")
            source_str = (
                f"v4l2src device={device} io-mode=mmap ! "
                f"video/x-raw,format={src_format},width={src_width},height={src_height},framerate={src_fps}/1 ! "
                f"videorate ! video/x-raw,framerate=30/1 ! "
                f"videoconvert ! "
                f"videoscale ! "
                f"video/x-raw,width={width},height={height},format=NV12"
            )
    elif device_type == "usb":
        source_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videorate ! video/x-raw,framerate=30/1 ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},format=NV12"
        )
    else:
        source_str = (
            f"v4l2src device={device} ! "
            f"video/x-raw ! "
            f"videoconvert ! "
            f"videoscale ! "
            f"video/x-raw,width={width},height={height},framerate=30/1,format=NV12"
        )

    # Use H.264 hardware encoder (mpph264enc - raspberry.ninja-proven config)
    encoder_str, caps_str, parse_str = get_h264_hardware_encoder(bitrate)
    
    # Stream to MediaMTX via RTSP (H.264 native support)
    # Using rtspclientsink with UDP transport for low latency
    # rtspclientsink handles RTP payloading internally
    # Pipeline: encode → parse → RTSP client sink
    pipeline_str = (
        f"{source_str} ! "
        f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"{encoder_str} ! "
        f"{caps_str} ! "
        f"queue max-size-buffers=5 max-size-time=0 max-size-bytes=0 leaky=downstream ! "
        f"{parse_str} ! "
        f"rtspclientsink location=rtsp://127.0.0.1:8554/{cam_id} protocols=udp latency=0"
    )

    logger.info(f"Building ingest pipeline for {cam_id}: {pipeline_str}")
    Gst = get_gst()
    pipeline = Gst.parse_launch(pipeline_str)
    return pipeline


def build_recording_subscriber_pipeline(
    cam_id: str,
    source_url: str,
    output_path: str,
    codec: str = "h264",
):
    """Build recording pipeline that subscribes to MediaMTX stream.
    
    This pipeline reads from an RTSP source (MediaMTX) instead of directly
    from a V4L2 device, allowing recording to be independent of ingest.
    
    NOTE: The ingest pipeline now streams H.264 to MediaMTX via RTP.
    This pipeline uses H.264 depay/parse for recording.
    
    Args:
        cam_id: Camera identifier
        source_url: RTSP URL to subscribe to (e.g., rtsp://localhost:8554/cam0)
        output_path: Path to output file
        codec: Codec parameter (ignored - always H.264 from ingest)
    """
    # RTSP source with minimal latency
    # Use H.264 depay because ingest now streams H.264 via RTP
    # UDP protocol is faster for local connections
    source_str = f"rtspsrc location={source_url} latency=100 protocols=udp ! rtph264depay"
    
    # Use H.264 parser and MP4 muxer (MP4 has excellent H.264 support)
    parse_str = "h264parse"
    mux_str = "mp4mux"
    
    # Use splitmuxsink for clean file segments (optional, can segment by time)
    # max-size-time in nanoseconds (3600000000000 = 1 hour)
    # For now, use single file (no splitting)
    pipeline_str = (
        f"{source_str} ! "
        f"queue max-size-buffers=0 max-size-time=0 max-size-bytes=0 ! "
        f"{parse_str} ! "
        f"{mux_str} ! "
        f"filesink location={output_path}"
    )
    
    logger.info(f"Building recording subscriber pipeline for {cam_id}: {pipeline_str}")
    Gst = get_gst()
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
):
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

