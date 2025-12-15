#!/usr/bin/env python3
"""Test script to verify signal detection is working."""

import sys
sys.path.insert(0, '/opt/preke-r58-recorder/src')

from device_detection import get_subdev_resolution

# Test all cameras
cameras = {
    'cam0': '/dev/video0',
    'cam1': '/dev/video60',
    'cam2': '/dev/video11',
    'cam3': '/dev/video22'
}

print("=== Signal Detection Test ===\n")

for cam_id, device in cameras.items():
    resolution = get_subdev_resolution(device)
    if resolution:
        print(f"{cam_id} ({device}): ✅ SIGNAL - {resolution[0]}x{resolution[1]}")
    else:
        print(f"{cam_id} ({device}): ❌ NO SIGNAL")

print("\nTest complete.")

