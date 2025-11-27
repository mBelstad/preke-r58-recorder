# R58 4x4 3S Hardware Investigation - Four Camera Support

## Executive Summary

**Finding**: The RK3588 SoC has only **ONE** HDMI RX controller in hardware. The "4x 4K 60p" marketing claim does not mean 4 separate HDMI inputs.

## Hardware Reality

### HDMI Input Controllers

- **Single HDMI RX Controller**: `fdee0000.hdmirx-controller` → `/dev/video60`
  - Device name: `stream_hdmirx`
  - Compatible: `rockchip,rk3588-hdmirx-ctrler`
  - Physical address: `0xfdee0000`
  - **This is the ONLY HDMI input available in hardware**

- **HDMI Output Controller**: `fde80000.hdmi` (HDMI TX, not RX)
  - Used for display output, not capture

### Current Device Mapping

From `v4l2-ctl --list-devices`:
- `/dev/video60`: `rk_hdmirx` - **ONLY HDMI input**
- `/dev/video0-32`: `rkcif-mipi-lvds*` - MIPI/CSI camera interfaces (unused unless sensors connected)
- `/dev/video33-59`: `rkisp*` - ISP virtual paths (image processing, not capture)

### Configuration Status

Current `config.yml`:
- `cam0`: `/dev/video60` ✅ (HDMI input - works)
- `cam1`: `/dev/video1` ❌ (MIPI interface - no signal)
- `cam2`: `/dev/video2` ❌ (MIPI interface - no signal)
- `cam3`: `/dev/video3` ❌ (MIPI interface - no signal)

## Understanding "4x 4K 60p" Marketing

The marketing claim likely means:
1. **4K 60p capability** - The device can record at 4K 60fps (not 4 separate inputs)
2. **4 simultaneous streams** - Can record 4 different sources simultaneously (requires external capture devices)
3. **4K resolution support** - Supports 4K input/output (not 4 inputs)

**NOT**: 4 separate built-in HDMI input ports.

## Solutions for Four Camera Support

### Option 1: USB Capture Devices (Recommended)

Use USB 3.0 HDMI capture devices for additional inputs:

**Requirements:**
- USB 3.0 HDMI capture cards (e.g., Elgato Cam Link, Magewell USB Capture, etc.)
- Linux UVC (USB Video Class) support
- GStreamer `uvch264src` or `v4l2src` with USB devices

**Implementation:**
1. Connect USB capture devices
2. Detect with `lsusb` and `v4l2-ctl --list-devices`
3. Map USB devices to cam1-3 in `config.yml`
4. Update pipelines to handle UVC devices (different from hdmirx)

**Pros:**
- Works with existing hardware
- No kernel/device tree changes
- Hot-pluggable

**Cons:**
- Requires external hardware purchase
- USB bandwidth limits (USB 3.0 can handle 4K 30p, may struggle with 4K 60p)
- Additional latency

### Option 2: External PCIe Capture Cards

If the R58 has PCIe slots available:
- Install PCIe HDMI capture cards
- Requires kernel drivers for specific cards
- Higher bandwidth than USB

**Current PCIe Status:**
- PCIe bridge detected: `0002:20:00.0` and `0003:30:00.0`
- Currently used for: WiFi (BCM43752) and Ethernet (RTL8125)
- May have additional slots available

### Option 3: HDMI Switcher + Single Input

Use an external HDMI switcher to cycle between 4 sources:
- Record one at a time
- Switch sources programmatically
- Not true simultaneous recording

### Option 4: MIPI Camera Modules

If the goal is 4 cameras (not necessarily HDMI):
- Connect MIPI camera modules to the CSI interfaces
- Use `/dev/video0-32` for MIPI cameras
- Requires compatible camera modules

## Recommended Path Forward

**For immediate 4-camera HDMI support:**

1. **Purchase USB 3.0 HDMI capture devices** (3 additional units)
2. **Test USB device detection** on the R58
3. **Update pipeline code** to handle UVC devices
4. **Map USB devices** to cam1-3 in configuration

**For native 4K 60p per camera:**
- Verify USB 3.0 bandwidth can handle 4K 60p
- May need to reduce to 4K 30p or 1080p 60p per USB device
- Consider PCIe capture cards for true 4K 60p

## Technical Details

### RK3588 SoC HDMI Capabilities

- **HDMI RX**: 1 controller (fdee0000.hdmirx-controller)
- **HDMI TX**: 1 controller (fde80000.hdmi)
- **Maximum**: 4K 60p per controller

### Device Tree Investigation

```bash
# Only one hdmirx controller found:
/sys/devices/platform/fdee0000.hdmirx-controller

# No additional hdmirx controllers in device tree
# RK3588 SoC has only one HDMI RX controller in silicon
```

### Kernel Module Status

```bash
# No separate hdmirx kernel module
# Integrated into main kernel (rk_hdmirx driver)
```

## Next Steps

1. **Test USB capture device compatibility**
   - Connect USB HDMI capture device
   - Check if it appears as `/dev/video*`
   - Test GStreamer pipeline with USB device

2. **Update codebase for USB devices**
   - Add USB device detection
   - Create pipeline builder for UVC devices
   - Handle different formats (USB devices may use different pixel formats)

3. **Update documentation**
   - Clarify hardware limitations
   - Document USB capture device requirements
   - Update deployment guide with USB device setup

## References

- RK3588 datasheet (if available) - confirms single HDMI RX controller
- Device tree: `/proc/device-tree/fdee0000.hdmirx-controller`
- Kernel driver: `rk_hdmirx` (integrated, not loadable module)

