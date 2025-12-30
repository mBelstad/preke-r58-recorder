# R58 Multi-Camera Pipeline Investigation Summary

**Date:** December 30, 2025  
**Status:** Blocked - System unstable with current architecture

---

## Goal

Enable stable operation of 3-4 HDMI cameras simultaneously with:
- Live preview streaming (WHEP/WebRTC)
- Recording to MKV files (DaVinci Resolve compatible)
- VDO.ninja mixer integration
- Hot-plug support

---

## Hardware

| Port | Device | Type | Notes |
|------|--------|------|-------|
| IN0 | /dev/video0 | rkcif (LT6911 bridge) | Requires subdev initialization |
| IN60 | /dev/video60 | hdmirx (direct) | Native RK3588 HDMI receiver |
| IN11 | /dev/video11 | rkcif (LT6911 bridge) | Requires subdev initialization |
| IN21 | /dev/video22 | rkcif (LT6911 bridge) | Requires subdev initialization |

---

## What Worked Before (Weeks Ago)

The original architecture in `src/ingest.py` + `src/recorder.py` was stable with 4 cameras:

```
INGEST (1 encoder per camera):
Camera → v4l2src → mpph264enc → RTSP → MediaMTX

RECORDING (subscriber, NO encoding):
MediaMTX → rtspsrc → rtph264depay → matroskamux → file

PREVIEW (passthrough, NO encoding):
MediaMTX → WHEP → Browser
```

**Key characteristics:**
- Only 1 hardware encoder per camera
- Recording re-muxes already-encoded stream (zero VPU load)
- 4 cameras = 4 encoders = within VPU limits
- Tested stable for 1 week without kernel panics

---

## What We Built (Last 48 Hours)

TEE pipeline architecture per `docs/TEE_RECORDING_PIPELINE_SPEC.md`:

```
INGEST (2 encoders per camera):
Camera → v4l2src → videoscale → tee
                                 ├→ mpph264enc (18Mbps) → matroskamux → file
                                 └→ mpph264enc (6Mbps) → RTSP → MediaMTX
```

**Key characteristics:**
- 2 hardware encoders per camera
- 2 cameras = 4 encoders
- 4 cameras = 8 encoders = exceeds VPU limits

---

## Test Results

### Test 1: Cold Boot with 2 Cameras (Hardware Encoding)
- **Result:** Stable for 5 minutes, then crashed at ~9 minutes
- **CPU:** ~45% (reasonable)
- **Crash trigger:** Possibly device monitor polling or v4l2-ctl query

### Test 2: Hot-Plug Testing
- **Result:** Could not complete - device crashes too frequently
- **Observation:** Crashes occur when connecting new cameras

### Test 3: Single Camera
- **Result:** Stable for extended periods with 1 camera
- **Observation:** Problem appears with 2+ cameras

---

## All Changes Made (Last 48 Hours)

1. **TEE Pipeline Architecture** - Dual encoder per camera
2. **Device Format Changes** - UYVY → NV12 → UYVY → NV16 experiments
3. **RGA Enablement** - `GST_VIDEO_CONVERT_USE_RGA=1` before GStreamer import
4. **Device Monitor Changes** - Active pipeline tracking, read-only queries
5. **Preview Encoding Toggle** - mpph264enc ↔ x264enc experiments
6. **Pipeline Elements** - Added videorate, videoscale, queue changes
7. **Config Changes** - Bitrate settings, resolution changes
8. **Valve Element** - For recording start/stop control

---

## Confirmed Issues

1. **VPU Overload** - 4+ concurrent hardware encoders causes crashes
2. **Device Monitor Polling** - Querying devices while pipelines run causes instability
3. **Hot-Plug Race Conditions** - Connecting cameras while others run triggers crashes
4. **RGA Instability** - RGA_BLIT errors when under load

---

## Key Technical Findings

### VPU Limits (RK3588)
- 3 simultaneous encoders: ✅ Stable
- 4 simultaneous encoders: ⚠️ Risky
- 4+ encoders: ❌ Crashes with RGA_BLIT errors

### Working Encoder Settings
```
mpph264enc qp-init=26 qp-min=10 qp-max=51 gop=30 profile=baseline rc-mode=cbr bps=4000000
```

### Device Initialization
- rkcif devices require format initialization via V4L2 subdevs
- hdmirx (IN60) works directly without subdev
- Format: NV12 supported by all devices

---

## Files Reference

### Original Working Implementation
- `src/ingest.py` - IngestManager (single encoder → MediaMTX)
- `src/recorder.py` - Recorder (subscriber, re-mux from MediaMTX)
- `src/pipelines.py` - Original pipeline builders

### Current (Broken) Implementation
- `packages/backend/pipeline_manager/ingest.py` - TEE pipeline manager
- `packages/backend/pipeline_manager/gstreamer/pipelines.py` - TEE pipeline builders
- `packages/backend/pipeline_manager/device_monitor.py` - Device polling

### Documentation
- `docs/TEE_RECORDING_PIPELINE_SPEC.md` - TEE architecture specification
- `docs/vpu-resource-limits.md` - VPU analysis (from other chat)

---

## Recommended Path Forward

### Option A: Revert to Original Architecture
Use single-encoder ingest + subscriber recording:
- 4 cameras = 4 encoders (within limits)
- Recording = re-mux only (zero VPU load)
- Proven stable

### Option B: Optimize TEE Architecture
- Use software encoding (x264enc) for preview branch
- Keep hardware encoding for recording only
- 4 cameras = 4 encoders (within limits)
- Trade-off: Higher CPU usage for preview

### Option C: Hybrid Approach
- Single encoder to MediaMTX (like original)
- High-bitrate setting (18Mbps) for quality recording
- Recording subscribes and re-muxes
- Preview via WHEP (passthrough)

---

## Success Criteria

- [ ] 4 cameras preview simultaneously
- [ ] 4 cameras record simultaneously
- [ ] Preview continues during recording
- [ ] Hot-plug support (connect/disconnect without crash)
- [ ] No VPU crashes for 1+ hour
- [ ] MKV files playable in DaVinci Resolve

