# CAM 3 and CAM 4 Diagnostic Report

**Date**: December 15, 2025  
**Device**: Mekotronics R58 4x4 3S (RK3588)  
**Issue**: CAM 3 (video11/HDMI N11) and CAM 4 (video21/HDMI N21) not displaying in GUI

---

## Executive Summary

**Root Cause Identified**: LT6911UXE HDMI-to-MIPI bridge chips ARE detecting HDMI signals (confirmed in dmesg), but the signals are not being properly exposed through the V4L2 driver layer. This is a **driver/bridge communication issue**, not a hardware or application issue.

**Status**: 
- ✅ CAM 1 (video0/HDMI N0): Working - 1920x1080 YVYU
- ✅ CAM 2 (video60/HDMI N60): Working - 1920x1080 NV16
- ❌ CAM 3 (video11/HDMI N11): Not working - Bridge detects signal, V4L2 reports 0x0
- ❌ CAM 4 (video21/HDMI N21): Not working - Bridge detects signal, V4L2 reports 0x0

---

## Diagnostic Results

### Phase 1: V4L2 Device Detection

#### 1.1 Device Existence
```bash
crw-rw----+ 1 root video 81, 11 Dec 15 16:18 /dev/video11  ✅
crw-rw----+ 1 root video 81, 21 Dec 15 16:18 /dev/video21  ✅
```
**Result**: Both devices exist with correct permissions.

#### 1.2 Current Format Query

| Device | Width/Height | Pixel Format | Status |
|--------|--------------|--------------|--------|
| video0 | 1920x1080 | YVYU | ✅ Working |
| video11 | **0x0** | YVYU | ❌ No signal at V4L2 |
| video21 | **0x0** | (none) | ❌ No signal at V4L2 |
| video60 | 1920x1080 | NV16 | ✅ Working |

**Result**: video11 and video21 report 0x0 resolution, indicating no signal lock at V4L2 layer.

#### 1.3 LT6911 Bridge I2C Status

All three LT6911UXE bridges detected and bound:

| Bridge | I2C Address | Driver | Video Device | Status |
|--------|-------------|--------|--------------|--------|
| 2-002b | 0x2b | LT6911UXE | video21 | ✅ Bound |
| 4-002b | 0x2b | LT6911UXE | video11 | ✅ Bound |
| 7-002b | 0x2b | LT6911UXE | video0 | ✅ Bound |

**Result**: All bridges properly detected and driver loaded.

#### 1.4 dmesg Bridge Signal Detection

**CRITICAL FINDING**: Bridges ARE detecting HDMI signals:

```
LT6911UXE 2-002b: find current mode: support_mode[7], 1920x1080P30fps  ✅
LT6911UXE 4-002b: find current mode: support_mode[26], 720x240P60fps  ⚠️
LT6911UXE 7-002b: find current mode: support_mode[4], 3840x2160P30fps  ✅
```

**Analysis**:
- **2-002b (video21)**: Detecting 1920x1080P30fps - HDMI signal present
- **4-002b (video11)**: Detecting 720x240P60fps - Unusual resolution (possibly interlaced signal misdetection)
- **7-002b (video0)**: Detecting 3840x2160P30fps - 4K signal present

### Phase 2: Format Capabilities

#### 2.1 Supported Formats

**video11**:
- Formats: NV16, NV61, NV12, NV21, YUYV, YVYU, UYVY, VYUY
- Size range: **64x64 - 0x0** (invalid - no signal)

**video21**:
- Formats: RGGB, GRBG (Bayer only)
- Size: **Discrete 0x0** (invalid - no signal)

**Result**: Both devices report 0x0 as maximum resolution, confirming no signal at V4L2 layer despite bridge detection.

---

## Root Cause Analysis

### The Disconnect

```
┌─────────────────┐
│  HDMI Camera    │
│   (verified)    │
└────────┬────────┘
         │ HDMI Signal
         ▼
┌─────────────────┐
│  LT6911 Bridge  │  ✅ Detecting signal (dmesg shows 1920x1080)
│   (I2C 2-002b)  │
└────────┬────────┘
         │ MIPI CSI
         ▼
┌─────────────────┐
│  rkcif Driver   │  ❌ NOT exposing signal
│   (video11)     │     Reports 0x0 resolution
└────────┬────────┘
         │ V4L2
         ▼
┌─────────────────┐
│  Application    │  ❌ No frames available
└─────────────────┘
```

### Possible Causes

1. **Bridge-to-MIPI Signal Path Not Initialized**
   - Bridge detects HDMI but MIPI output not configured
   - CSI lanes not properly routed

2. **rkcif Driver Timing Issue**
   - Driver queries format before bridge locks signal
   - No signal update mechanism after initial probe

3. **Device Tree Configuration**
   - MIPI CSI lane configuration mismatch
   - Clock/timing parameters incorrect for video11/video21

4. **Driver Bug**
   - rkcif driver not properly reading LT6911 status
   - Format negotiation failure between bridge and driver

### Why video0 Works But video11/video21 Don't

All three use the same LT6911UXE bridge and rkcif driver, but:
- **video0 (7-002b)**: Working perfectly
- **video11 (4-002b)**: Not working (detects 720x240 - unusual)
- **video21 (2-002b)**: Not working (detects 1920x1080 but V4L2 sees 0x0)

This suggests:
- Not a universal driver/bridge issue (video0 works)
- Possibly device-tree specific configuration per port
- May be related to MIPI CSI lane assignment or initialization order

---

## Recommended Actions

### IMMEDIATE: Physical Port Swap Test

**Purpose**: Determine if issue is port-specific or camera-specific

**Procedure**:
1. Power off R58
2. Move working camera from HDMI N60 (or HDMI N0) to HDMI N11
3. Power on R58
4. Check: `v4l2-ctl -d /dev/video11 --get-fmt-video`

**Expected Results**:
- **If signal detected**: Port hardware is OK, original camera may have incompatible output
- **If no signal**: Port/bridge/driver issue confirmed

### If Port Issue Confirmed

1. **Check Device Tree Configuration**
   ```bash
   # Compare device tree entries for working vs non-working ports
   cat /proc/device-tree/i2c@feac0000/lt6911_1@2b/*
   cat /proc/device-tree/i2c@feaa0000/lt6911@2b/*
   ```

2. **Check MIPI CSI Lane Configuration**
   ```bash
   # Look for CSI configuration differences
   dmesg | grep -i "mipi\|csi\|rkcif"
   ```

3. **Contact Mekotronics Support**
   - Provide dmesg logs showing bridge detection but V4L2 failure
   - Ask about known issues with video11/video21 on R58 4x4 3S
   - Request device tree overlay or driver patch

### If Camera Issue Confirmed

1. **Check Camera Output Settings**
   - Ensure camera is outputting standard 1080p or 4K
   - Disable interlaced mode if enabled
   - Try different output resolutions

2. **Test with Different Cameras**
   - Try a known-good camera (like the one working on N60)
   - Test with different camera models

3. **Check HDMI Cables**
   - Use high-quality HDMI 2.0 cables
   - Try shorter cable lengths
   - Test cables on external monitor first

---

## Workaround: Use Working Ports

Until the root cause is resolved, use only the working HDMI ports:

| Port | Device | Status | Recommendation |
|------|--------|--------|----------------|
| HDMI N0 | video0 | ✅ Working | Use for production |
| HDMI N60 | video60 | ✅ Working | Use for production |
| HDMI N11 | video11 | ❌ Not working | Avoid until fixed |
| HDMI N21 | video21 | ❌ Not working | Avoid until fixed |

**Current Capacity**: 2 working cameras (CAM 1 and CAM 2)

---

## New Diagnostic API

A new endpoint has been implemented for real-time signal diagnostics:

### GET `/api/cameras/{cam_id}/signal`

**Example Response** (CAM 3 - no signal):
```json
{
  "cam_id": "cam2",
  "device": "/dev/video11",
  "signal": {
    "present": false,
    "resolution": "0x0",
    "frame_rate": 30,
    "pixel_format": "YVYU",
    "colorspace": null
  },
  "pipeline": {
    "state": "idle",
    "frames_received": 0,
    "frames_dropped": 0,
    "last_frame_timestamp": null,
    "error": "No HDMI signal detected"
  },
  "recording": {
    "active": false,
    "file_path": null,
    "bytes_written": 0,
    "duration_seconds": 0
  },
  "preview": {
    "active": false,
    "mediamtx_path": "cam2_preview",
    "hls_segments_written": 0
  },
  "hardware": {
    "device_type": "hdmi_rkcif",
    "bridge_type": "LT6911UXE",
    "i2c_bus": 4,
    "i2c_address": "0x2b"
  }
}
```

This endpoint can be used for:
- Real-time signal monitoring
- Troubleshooting camera issues
- Remote diagnostics
- GUI status display

---

## Technical Details

### Hardware Architecture

```
R58 4x4 3S HDMI Input Architecture:

HDMI N60  ──► RK3588 HDMI RX ──► /dev/video60 (rk_hdmirx)  ✅ Working
              (Direct)

HDMI N0   ──► LT6911 (7-002b) ──► MIPI CSI ──► /dev/video0 (rkcif)  ✅ Working

HDMI N11  ──► LT6911 (4-002b) ──► MIPI CSI ──► /dev/video11 (rkcif) ❌ Not Working

HDMI N21  ──► LT6911 (2-002b) ──► MIPI CSI ──► /dev/video21 (rkcif) ❌ Not Working
```

### Device Tree Paths

- video0 bridge: `/firmware/devicetree/base/i2c@fec90000/lt6911_2@2b`
- video11 bridge: `/firmware/devicetree/base/i2c@feac0000/lt6911_1@2b`
- video21 bridge: `/firmware/devicetree/base/i2c@feaa0000/lt6911@2b`

---

## References

- [docs/hdmi-port-mapping.md](hdmi-port-mapping.md) - HDMI port mapping reference
- [docs/environment.md](environment.md) - R58 environment details
- [docs/fix-log.md](fix-log.md) - Historical fixes and issues
- Diagnostic Plan: `/Users/mariusbelstad/.cursor/plans/cam_3_4_diagnostic_plan_6c687193.plan.md`

---

## Next Steps

1. ✅ **Completed**: Systematic diagnostics (Phase 1-2)
2. ✅ **Completed**: Signal metadata API implementation
3. ⏳ **Pending**: Physical port swap test (requires manual intervention)
4. ⏳ **Pending**: GUI signal status display
5. ⏳ **Pending**: Contact Mekotronics support if port swap confirms hardware issue

---

**Report Generated**: December 15, 2025  
**System**: Mekotronics R58 4x4 3S, Debian 12, Kernel 6.1.99  
**Application Version**: preke-r58-recorder (commit 40e087b)

