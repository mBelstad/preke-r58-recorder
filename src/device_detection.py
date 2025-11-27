"""Device detection utilities for identifying video input types."""
import logging
import subprocess
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


def detect_device_type(device_path: str) -> str:
    """Detect the type of video device.
    
    Returns:
        'hdmirx' - RK3588 HDMI receiver
        'usb' - USB capture device
        'mipi' - MIPI/CSI camera interface
        'isp' - ISP virtual path
        'unknown' - Unknown device type
    """
    device_path = Path(device_path)
    if not device_path.exists():
        return "unknown"
    
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
            if "mipi" in device_str.lower() or "csi" in device_str.lower():
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
        List of device paths that are HDMI inputs
    """
    devices = list_available_devices()
    hdmi_devices = [
        path for path, info in devices.items()
        if info["type"] == "hdmirx"
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


def suggest_camera_mapping() -> Dict[str, Optional[str]]:
    """Suggest camera device mappings based on available hardware.
    
    Returns:
        Dictionary mapping cam0-3 to device paths (or None if not available)
    """
    hdmi_devices = find_hdmi_devices()
    usb_devices = find_usb_capture_devices()
    
    mapping = {
        "cam0": None,
        "cam1": None,
        "cam2": None,
        "cam3": None
    }
    
    # Map HDMI devices first (preferred)
    for i, device in enumerate(hdmi_devices[:4]):
        mapping[f"cam{i}"] = device
    
    # Fill remaining slots with USB devices
    remaining_slots = [f"cam{i}" for i in range(len(hdmi_devices), 4) if mapping[f"cam{i}"] is None]
    for i, device in enumerate(usb_devices[:len(remaining_slots)]):
        if i < len(remaining_slots):
            mapping[remaining_slots[i]] = device
    
    return mapping

