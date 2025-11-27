"""Device detection utilities for identifying video input types."""
import logging
import subprocess
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


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
    # HDMI N0 → /dev/video0 (rkcif-mipi-lvds)
    # HDMI N60 → /dev/video60 (hdmirx direct)
    # HDMI N11 → /dev/video11 (rkcif-mipi-lvds1)
    # HDMI N21 → /dev/video21 (rkcif-mipi-lvds1, different format)
    hdmi_rkcif_devices = ["/dev/video0", "/dev/video11", "/dev/video21"]
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
            'HDMI N21': '/dev/video21'
        }
    """
    return {
        "HDMI N0": "/dev/video0",   # rkcif-mipi-lvds (via LT6911 bridge)
        "HDMI N60": "/dev/video60",  # hdmirx (direct)
        "HDMI N11": "/dev/video11",  # rkcif-mipi-lvds1 (via LT6911 bridge)
        "HDMI N21": "/dev/video21"   # rkcif-mipi-lvds1 (via LT6911 bridge, different format)
    }


def suggest_camera_mapping() -> Dict[str, Optional[str]]:
    """Suggest camera device mappings based on available hardware.
    
    For R58 4x4 3S, maps cameras to HDMI ports in order:
    - cam0 → HDMI N0 (/dev/video0)
    - cam1 → HDMI N60 (/dev/video60)
    - cam2 → HDMI N11 (/dev/video11)
    - cam3 → HDMI N21 (/dev/video21)
    
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

