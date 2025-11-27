#!/usr/bin/env python3
"""Test device detection utilities."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from device_detection import (
    detect_device_type,
    list_available_devices,
    find_hdmi_devices,
    find_usb_capture_devices,
    suggest_camera_mapping
)

def main():
    print("=== Device Detection Test ===\n")
    
    # Test HDMI device
    hdmi_type = detect_device_type("/dev/video60")
    print(f"HDMI device (/dev/video60) type: {hdmi_type}")
    
    # List all devices
    print("\n=== All Available Devices ===")
    devices = list_available_devices()
    print(f"Found {len(devices)} devices:")
    for path, info in sorted(devices.items()):
        print(f"  {path}: {info}")
    
    # Find HDMI devices
    print("\n=== HDMI Devices ===")
    hdmi_devices = find_hdmi_devices()
    print(f"Found {len(hdmi_devices)} HDMI devices:")
    for dev in hdmi_devices:
        print(f"  {dev}")
    
    # Find USB devices
    print("\n=== USB Capture Devices ===")
    usb_devices = find_usb_capture_devices()
    print(f"Found {len(usb_devices)} USB capture devices:")
    for dev in usb_devices:
        print(f"  {dev}")
    
    # Suggest camera mapping
    print("\n=== Suggested Camera Mapping ===")
    mapping = suggest_camera_mapping()
    for cam_id, device in mapping.items():
        status = device if device else "NOT AVAILABLE"
        print(f"  {cam_id}: {status}")

if __name__ == "__main__":
    main()

