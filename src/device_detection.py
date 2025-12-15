"""Device detection utilities for identifying video input types."""
import logging
import re
import subprocess
from typing import Dict, Optional, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Mapping of rkcif video devices to their V4L2 subdevs
# These subdevs report the actual HDMI signal resolution from LT6911 bridges
RKCIF_SUBDEV_MAP = {
    "/dev/video0": "/dev/v4l-subdev2",   # HDMI N0 via LT6911 7-002b
    "/dev/video11": "/dev/v4l-subdev7",  # HDMI N11 via LT6911 4-002b
    "/dev/video22": "/dev/v4l-subdev12", # HDMI N21 via LT6911 2-002b
}


def detect_device_type(device_path: str) -> str:
    """Detect the type of video device.
    
    Returns:
        'hdmirx' - RK3588 HDMI receiver (direct)
        'hdmi_rkcif' - HDMI input via rkcif (LT6911 bridge)
        'usb' - USB capture device
        'mipi' - MIPI/CSI camera interface
        'isp' - ISP virtual path
        'unknown' - Unknown device type
    """
    device_path = Path(device_path)
    if not device_path.exists():
        return "unknown"
    
    # R58 4x4 3S specific: Known HDMI port mappings via LT6911 bridges
    # HDMI N0 → /dev/video0 (rkcif-mipi-lvds via LT6911 7-002b)
    # HDMI N60 → /dev/video60 (hdmirx direct)
    # HDMI N11 → /dev/video11 (rkcif-mipi-lvds1 via LT6911 4-002b)
    # HDMI N21 → /dev/video22 (rkcif-mipi-lvds2 via LT6911 2-002b)
    hdmi_rkcif_devices = ["/dev/video0", "/dev/video11", "/dev/video22"]
    if str(device_path) in hdmi_rkcif_devices:
        return "hdmi_rkcif"
    
    # Check sysfs for device information
    try:
        # Find the device in sysfs
        sysfs_path = None
        for v4l_dev in Path("/sys/class/video4linux").iterdir():
            if v4l_dev.name == device_path.name:
                sysfs_path = v4l_dev
                break
        
        if not sysfs_path:
            return "unknown"
        
        # Check device name
        name_path = sysfs_path / "name"
        if name_path.exists():
            name = name_path.read_text().strip()
            if "hdmirx" in name.lower() or "stream_hdmirx" in name.lower():
                return "hdmirx"
            if "uvc" in name.lower() or "usb" in name.lower():
                return "usb"
        
        # Check device path in sysfs
        device_link = sysfs_path / "device"
        if device_link.exists():
            device_real = device_link.resolve()
            device_str = str(device_real)
            
            if "hdmirx" in device_str.lower():
                return "hdmirx"
            if "usb" in device_str.lower():
                return "usb"
            # Check for LT6911 bridge (HDMI-to-MIPI converter)
            if "lt6911" in device_str.lower():
                return "hdmi_rkcif"
            if "mipi" in device_str.lower() or "csi" in device_str.lower():
                # Check if this rkcif device is connected to an LT6911 bridge
                # by looking for I2C devices in the same subsystem
                try:
                    parent = device_real.parent
                    for sibling in parent.iterdir():
                        if "lt6911" in sibling.name.lower():
                            return "hdmi_rkcif"
                except:
                    pass
                return "mipi"
            if "isp" in device_str.lower():
                return "isp"
        
        # Check by-path symlink
        by_path = Path("/dev/v4l/by-path")
        if by_path.exists():
            for link in by_path.iterdir():
                if link.resolve() == device_path:
                    link_name = link.name
                    if "hdmirx" in link_name.lower():
                        return "hdmirx"
                    if "usb" in link_name.lower():
                        return "usb"
                    if "mipi" in link_name.lower() or "csi" in link_name.lower():
                        return "mipi"
        
    except Exception as e:
        logger.warning(f"Error detecting device type for {device_path}: {e}")
    
    return "unknown"


def list_available_devices() -> Dict[str, Dict]:
    """List all available video devices with their types.
    
    Returns:
        Dictionary mapping device paths to device info:
        {
            '/dev/video60': {
                'type': 'hdmirx',
                'name': 'stream_hdmirx',
                'path': '/dev/video60'
            },
            ...
        }
    """
    devices = {}
    
    try:
        # Use v4l2-ctl to list devices
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            logger.warning("v4l2-ctl --list-devices failed")
            return devices
        
        current_device = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("/dev/video"):
                device_path = line
                device_type = detect_device_type(device_path)
                devices[device_path] = {
                    "type": device_type,
                    "path": device_path,
                    "name": None
                }
                current_device = device_path
            elif current_device and line and not line.startswith("\t"):
                # Device name/description
                devices[current_device]["name"] = line
        
    except subprocess.TimeoutExpired:
        logger.error("v4l2-ctl command timed out")
    except FileNotFoundError:
        logger.warning("v4l2-ctl not found")
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
    
    return devices


def find_hdmi_devices() -> List[str]:
    """Find all HDMI input devices.
    
    Returns:
        List of device paths that are HDMI inputs (both direct hdmirx and via rkcif bridges)
    """
    devices = list_available_devices()
    hdmi_devices = [
        path for path, info in devices.items()
        if info["type"] in ("hdmirx", "hdmi_rkcif")
    ]
    return sorted(hdmi_devices)


def find_usb_capture_devices() -> List[str]:
    """Find all USB capture devices.
    
    Returns:
        List of device paths that are USB capture devices
    """
    devices = list_available_devices()
    usb_devices = [
        path for path, info in devices.items()
        if info["type"] == "usb"
    ]
    return sorted(usb_devices)


def get_hdmi_port_mapping() -> Dict[str, str]:
    """Get HDMI port label to device node mapping for R58 4x4 3S.
    
    Returns:
        Dictionary mapping port labels to device paths:
        {
            'HDMI N0': '/dev/video0',
            'HDMI N60': '/dev/video60',
            'HDMI N11': '/dev/video11',
            'HDMI N21': '/dev/video22'
        }
    """
    return {
        "HDMI N0": "/dev/video0",    # rkcif-mipi-lvds (via LT6911 7-002b bridge)
        "HDMI N60": "/dev/video60",  # hdmirx (direct)
        "HDMI N11": "/dev/video11",  # rkcif-mipi-lvds1 (via LT6911 4-002b bridge)
        "HDMI N21": "/dev/video22"   # rkcif-mipi-lvds2 (via LT6911 2-002b bridge)
    }


def initialize_rkcif_device(device_path: str) -> Dict[str, Any]:
    """Initialize rkcif device by querying subdev resolution and setting format.
    
    The LT6911 HDMI-to-MIPI bridges report resolution via their V4L2 subdevs,
    but the video devices start with 0x0 resolution. This function:
    1. Queries the subdev for the actual detected HDMI resolution
    2. Sets that format on the video device using v4l2-ctl
    3. Returns the device capabilities
    
    Args:
        device_path: Path to video device (e.g., /dev/video11)
        
    Returns:
        Device capabilities dictionary from get_device_capabilities()
    """
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
                
                # Set format on video device - use UYVY which works for all LT6911 bridges
                set_result = subprocess.run(
                    ["v4l2-ctl", "-d", device_path,
                     f"--set-fmt-video=width={width},height={height},pixelformat=UYVY"],
                    capture_output=True, text=True, timeout=5
                )
                
                if set_result.returncode != 0:
                    logger.warning(f"Failed to set format on {device_path}: {set_result.stderr}")
                else:
                    logger.info(f"{device_path}: Format set to {width}x{height} UYVY")
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


def get_device_capabilities(device_path: str) -> Dict:
    """Query device for current format, resolution, and framerate.
    
    Uses v4l2-ctl to get the actual device capabilities, allowing pipelines
    to use explicit format specification instead of auto-negotiation.
    
    Returns:
        Dictionary with device capabilities:
        {
            'format': 'NV16',  # GStreamer format name
            'width': 1920,
            'height': 1080,
            'framerate': 60,
            'has_signal': True,  # False if no signal or invalid resolution
            'is_bayer': False,   # True if Bayer format (needs bayer2rgb)
            'bayer_format': None  # 'rggb', 'grbg', etc. if Bayer
        }
    """
    result = {
        'format': None,
        'width': 0,
        'height': 0,
        'framerate': 30,
        'has_signal': False,
        'is_bayer': False,
        'bayer_format': None
    }
    
    try:
        # Query current format using v4l2-ctl
        proc = subprocess.run(
            ["v4l2-ctl", "-d", str(device_path), "--get-fmt-video"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if proc.returncode != 0:
            logger.warning(f"v4l2-ctl failed for {device_path}: {proc.stderr}")
            return result
        
        # Parse output for Width, Height, Pixel Format
        for line in proc.stdout.splitlines():
            line = line.strip()
            if "Width/Height" in line:
                # Format: "Width/Height      : 1920/1080"
                parts = line.split(":")
                if len(parts) >= 2:
                    wh = parts[1].strip().split("/")
                    if len(wh) >= 2:
                        try:
                            result['width'] = int(wh[0])
                            result['height'] = int(wh[1])
                        except ValueError:
                            pass
            elif "Pixel Format" in line:
                # Format: "Pixel Format      : 'NV16' (Y/CbCr 4:2:2)"
                # or: "Pixel Format      : 'RGGB' (8-bit Bayer RGRG/GBGB)"
                parts = line.split(":")
                if len(parts) >= 2:
                    fmt_part = parts[1].strip()
                    # Extract format from quotes
                    if "'" in fmt_part:
                        fmt = fmt_part.split("'")[1]
                        result['format'] = _v4l2_to_gst_format(fmt)
                        # Check for Bayer formats
                        if fmt.upper() in ('RGGB', 'GRBG', 'BGGR', 'GBRG'):
                            result['is_bayer'] = True
                            result['bayer_format'] = fmt.lower()
        
        # Determine if we have a valid signal
        # No signal typically shows as 0x0, 64x64, or very small resolution
        if result['width'] >= 640 and result['height'] >= 480:
            result['has_signal'] = True
        else:
            logger.info(f"{device_path}: No signal (resolution {result['width']}x{result['height']})")
            result['has_signal'] = False
        
        # Try to get framerate
        try:
            parm_proc = subprocess.run(
                ["v4l2-ctl", "-d", str(device_path), "--get-parm"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if parm_proc.returncode == 0:
                for line in parm_proc.stdout.splitlines():
                    if "Frames per second" in line:
                        # Format: "Frames per second: 60.000 (60/1)"
                        parts = line.split(":")
                        if len(parts) >= 2:
                            fps_str = parts[1].strip().split()[0]
                            try:
                                result['framerate'] = int(float(fps_str))
                            except ValueError:
                                pass
        except Exception:
            pass  # Framerate detection is optional
        
        logger.debug(f"{device_path} capabilities: {result}")
        
    except subprocess.TimeoutExpired:
        logger.error(f"v4l2-ctl timed out for {device_path}")
    except FileNotFoundError:
        logger.warning("v4l2-ctl not found")
    except Exception as e:
        logger.error(f"Error getting capabilities for {device_path}: {e}")
    
    return result


def _v4l2_to_gst_format(v4l2_format: str) -> str:
    """Convert V4L2 pixel format name to GStreamer format name.
    
    Args:
        v4l2_format: V4L2 format string (e.g., 'NV16', 'YUYV', 'RGGB')
    
    Returns:
        GStreamer format string
    """
    # Mapping of V4L2 format codes to GStreamer format names
    format_map = {
        'NV16': 'NV16',
        'NV61': 'NV61',
        'NV12': 'NV12',
        'NV21': 'NV21',
        'YUYV': 'YUY2',
        'YVYU': 'YVYU',
        'UYVY': 'UYVY',
        'VYUY': 'VYUY',
        'BGR3': 'BGR',
        'RGB3': 'RGB',
        'NV24': 'NV24',
        'I420': 'I420',
        # Bayer formats - these need special handling
        'RGGB': 'rggb',
        'GRBG': 'grbg',
        'BGGR': 'bggr',
        'GBRG': 'gbrg',
    }
    
    return format_map.get(v4l2_format.upper(), v4l2_format)


def suggest_camera_mapping() -> Dict[str, Optional[str]]:
    """Suggest camera device mappings based on available hardware.
    
    For R58 4x4 3S, maps cameras to HDMI ports in order:
    - cam0 → HDMI N0 (/dev/video0)
    - cam1 → HDMI N60 (/dev/video60)
    - cam2 → HDMI N11 (/dev/video11)
    - cam3 → HDMI N21 (/dev/video22)
    
    Returns:
        Dictionary mapping cam0-3 to device paths (or None if not available)
    """
    port_mapping = get_hdmi_port_mapping()
    hdmi_devices = find_hdmi_devices()
    usb_devices = find_usb_capture_devices()
    
    mapping = {
        "cam0": None,
        "cam1": None,
        "cam2": None,
        "cam3": None
    }
    
    # Map according to R58 4x4 3S port labels
    r58_port_order = ["HDMI N0", "HDMI N60", "HDMI N11", "HDMI N21"]
    for i, port_label in enumerate(r58_port_order):
        device = port_mapping.get(port_label)
        if device and Path(device).exists():
            # Verify device is actually available
            devices = list_available_devices()
            if device in devices:
                mapping[f"cam{i}"] = device
    
    # If any slots are still empty, try to fill with other HDMI devices
    remaining_slots = [f"cam{i}" for i in range(4) if mapping[f"cam{i}"] is None]
    other_hdmi = [d for d in hdmi_devices if d not in port_mapping.values()]
    for i, device in enumerate(other_hdmi[:len(remaining_slots)]):
        if i < len(remaining_slots):
            mapping[remaining_slots[i]] = device
    
    # Fill remaining slots with USB devices
    remaining_slots = [f"cam{i}" for i in range(4) if mapping[f"cam{i}"] is None]
    for i, device in enumerate(usb_devices[:len(remaining_slots)]):
        if i < len(remaining_slots):
            mapping[remaining_slots[i]] = device
    
    return mapping

