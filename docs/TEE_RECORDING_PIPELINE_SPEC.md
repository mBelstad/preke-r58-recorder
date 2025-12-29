# TEE Recording Pipeline Specification

**Created**: December 29, 2025  
**Status**: Planning Complete - Ready for Implementation

---

## Overview

This document specifies the optimized TEE-based pipeline architecture for the R58 multi-camera recorder. The design enables high-quality recording while maintaining always-on preview streams.

### Goals

1. **Recording**: 1080p H.264 18Mbps → .mkv (editable in DaVinci Resolve while recording)
2. **Preview**: 1080p H.264 6Mbps → MediaMTX → WHEP for operators and mixer
3. **Independence**: Recording can start/stop without interrupting preview
4. **Mixer**: Subscribes to MediaMTX preview streams, outputs WHIP at 1080p 5Mbps

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PER-CAMERA PIPELINE                               │
│                                                                             │
│   v4l2src (UYVY 4:2:2, native resolution)                                  │
│       │                                                                     │
│       ▼                                                                     │
│   ┌───────────────────────────────────┐                                     │
│   │ RGA: videoscale → 1920x1080       │  ← Hardware accelerated            │
│   │ videoconvert → NV12               │  ← ONCE (shared by both branches)  │
│   └─────────────────┬─────────────────┘                                     │
│                     │                                                       │
│                     ▼                                                       │
│   ┌─────────────────────────────────────┐                                   │
│   │              TEE                     │  ← Zero-copy buffer sharing      │
│   └────────┬─────────────────┬──────────┘                                   │
│            │                 │                                              │
│            ▼                 ▼                                              │
│   ┌────────────────┐  ┌────────────────┐                                    │
│   │   RECORDING    │  │    PREVIEW     │                                    │
│   │                │  │  (Always On)   │                                    │
│   │ mpph264enc     │  │ mpph264enc     │                                    │
│   │ 18 Mbps        │  │ 6 Mbps         │                                    │
│   │ High profile   │  │ Baseline       │                                    │
│   │      │         │  │      │         │                                    │
│   │      ▼         │  │      ▼         │                                    │
│   │ matroskamux    │  │ rtspclientsink │                                    │
│   │      │         │  │      │         │                                    │
│   │      ▼         │  │      ▼         │                                    │
│   │  .mkv file     │  │   MediaMTX     │                                    │
│   │ (DaVinci edit) │  │      │         │                                    │
│   └────────────────┘  │      ├──→ Op 1 │                                    │
│                       │      ├──→ Op 2 │                                    │
│                       │      ├──→ Op 3 │                                    │
│                       │      └──→ Mixer│                                    │
│                       └────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                MIXER                                        │
│                                                                             │
│   MediaMTX streams (WHEP subscribe)                                        │
│       │                                                                     │
│       ▼                                                                     │
│   ┌─────────────┐                                                           │
│   │ Compositor  │  ← Scene-based layouts                                   │
│   │ 1920x1080   │                                                           │
│   └──────┬──────┘                                                           │
│          ▼                                                                  │
│   ┌─────────────┐                                                           │
│   │ mpph264enc  │                                                           │
│   │ 5 Mbps      │                                                           │
│   └──────┬──────┘                                                           │
│          ▼                                                                  │
│   ┌─────────────┐                                                           │
│   │ WHIP Sink   │ ──────────────────────────────→ VDO.ninja                │
│   └─────────────┘                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Critical Technical Requirements

### 1. RGA Hardware Scaling

**MUST be enabled before GStreamer is imported!**

```python
# In main.py, BEFORE any GStreamer imports:
import os
os.environ['GST_VIDEO_CONVERT_USE_RGA'] = '1'
```

Without this, `videoscale` uses software scaling at ~30% CPU instead of ~0%.

### 2. Device Initialization (rkcif devices)

The LT6911 bridge devices require explicit format initialization:

| Device | Subdev | HDMI Port |
|--------|--------|-----------|
| `/dev/video0` | `/dev/v4l-subdev2` | HDMI N0 |
| `/dev/video11` | `/dev/v4l-subdev7` | HDMI N11 |
| `/dev/video22` | `/dev/v4l-subdev12` | HDMI N21 |
| `/dev/video60` | (direct hdmirx) | HDMI N60 |

Use `initialize_rkcif_device()` before building pipelines.

### 3. Format Flow

```
HDMI Source → V4L2 (UYVY 4:2:2) → RGA Scale → Convert (NV12 4:2:0) → Encoder
```

- Capture 4:2:2 for best quality from source
- Convert to NV12 for hardware encoder compatibility
- Use high bitrate (18 Mbps) to preserve quality despite 4:2:0

---

## Pipeline Implementation

```python
def build_tee_recording_pipeline(
    cam_id: str,
    device: str,
    recording_path: str,
    recording_bitrate: int = 18000,   # 18 Mbps for quality recording
    preview_bitrate: int = 6000,      # 6 Mbps for streaming
    resolution: str = "1920x1080",
    rtsp_port: int = 8554,
) -> str:
    """
    TEE at source pipeline: Independent recording + always-on preview.
    
    Features:
    - Single RGA scale operation (shared by both branches)
    - Recording can start/stop without affecting preview
    - .mkv container for edit-while-record (DaVinci compatible)
    - Dual VPU H.264 encoding (different bitrates/profiles)
    
    Prerequisites:
    - GST_VIDEO_CONVERT_USE_RGA=1 set before GStreamer import
    - MediaMTX running on localhost:8554
    - Device initialized (rkcif devices need format set)
    """
    width, height = resolution.split("x")
    
    # === SOURCE ===
    # Capture UYVY 4:2:2 at native resolution
    source = f"v4l2src device={device} io-mode=mmap ! video/x-raw,format=UYVY"
    
    # === SCALE + CONVERT (ONCE, shared by both branches) ===
    # RGA handles scaling via env var, then convert UYVY→NV12 for encoders
    scale_convert = (
        f"videoscale ! "
        f"video/x-raw,width={width},height={height} ! "
        f"videoconvert ! "
        f"video/x-raw,format=NV12"
    )
    
    # === RECORDING BRANCH ===
    # High bitrate H.264 High profile for quality
    # matroskamux for edit-while-record capability
    recording_branch = (
        f"queue name=rec_queue max-size-buffers=60 max-size-time=0 "
        f"max-size-bytes=0 leaky=downstream ! "
        f"mpph264enc "
        f"qp-init=20 qp-min=10 qp-max=35 "
        f"gop=30 profile=high rc-mode=cbr "
        f"bps={recording_bitrate * 1000} ! "
        f"video/x-h264,stream-format=byte-stream ! "
        f"h264parse config-interval=1 ! "
        f"matroskamux streamable=true ! "
        f"filesink location={recording_path} sync=false"
    )
    
    # === PREVIEW BRANCH ===
    # Lower bitrate H.264 Baseline for streaming efficiency
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
        f"{source} ! "
        f"{scale_convert} ! "
        f"tee name=t ! "
        f"{recording_branch} "
        f"t. ! {preview_branch}"
    )
    
    return pipeline
```

---

## Encoding Settings

| Parameter | Recording | Preview | Mixer Output |
|-----------|-----------|---------|--------------|
| **Codec** | H.264 | H.264 | H.264 |
| **Resolution** | 1920×1080 | 1920×1080 | 1920×1080 |
| **Framerate** | 30 fps | 30 fps | 30 fps |
| **Bitrate** | 18 Mbps | 6 Mbps | 5 Mbps |
| **Profile** | High | Baseline | Main |
| **QP Range** | 10-35 | 10-51 | 10-45 |
| **GOP** | 30 (1 sec) | 30 (1 sec) | 60 (2 sec) |
| **Container** | .mkv | RTSP/RTP | WHIP/RTP |

---

## Resource Estimates (4 Cameras)

| Component | CPU | VPU | Notes |
|-----------|-----|-----|-------|
| 4× v4l2src + TEE | ~2% | - | DMA transfer |
| 4× RGA scale (shared) | ~0% | - | Hardware accelerated |
| 4× mpph264enc (recording 18Mbps) | ~4% | ~32% | High profile |
| 4× mpph264enc (preview 6Mbps) | ~4% | ~24% | Baseline profile |
| **Subtotal (cameras)** | **~10%** | **~56%** | |
| 1× Mixer (decode+composite+encode) | ~15% | ~10% | |
| **Total** | **~25%** | **~66%** | Plenty of headroom |

---

## File Size Estimates

| Duration | Recording (18 Mbps) | 4 Cameras |
|----------|---------------------|-----------|
| 1 minute | ~135 MB | ~540 MB |
| 10 minutes | ~1.35 GB | ~5.4 GB |
| 1 hour | ~8.1 GB | ~32.4 GB |

---

## Recording Control

### Recommended: Valve Element

Insert a `valve` element before the recording branch to control flow:

```python
recording_branch = (
    f"queue ! "
    f"valve name=rec_valve drop=true ! "  # Start with recording OFF
    f"mpph264enc ... ! "
    f"matroskamux ! filesink"
)

# To start recording:
rec_valve.set_property("drop", False)

# To stop recording:
rec_valve.set_property("drop", True)
# Then send EOS to finalize the file
```

### Alternative: Dynamic Pad Linking

More complex but cleaner file handling:
- Unlink recording branch pad from TEE
- Create new filesink with new filename
- Relink to TEE

---

## Differences from Current Architecture

| Aspect | Current (IngestManager) | New (TEE Pipeline) |
|--------|-------------------------|-------------------|
| Encode count | 1× per camera | 2× per camera |
| Recording source | Subscribe to MediaMTX | Direct from V4L2 |
| Recording quality | = preview quality | > preview quality |
| Recording format | MP4 (broken during record) | MKV (editable during record) |
| Stop recording impact | None | None (TEE isolation) |
| Bitrate control | Single | Independent per branch |

---

## Files to Modify

1. **`packages/backend/pipeline_manager/gstreamer/pipelines.py`**
   - Add `build_tee_recording_pipeline()` function

2. **`packages/backend/pipeline_manager/ingest.py`**
   - Modify to use TEE pipeline when recording enabled
   - Add valve control for recording start/stop

3. **`packages/backend/pipeline_manager/ipc.py`**
   - Update `start_recording` to control valve
   - Update `stop_recording` to send EOS and reset valve

4. **`config.yml`**
   - Add `recording_bitrate` setting
   - Add `preview_bitrate` setting

---

## Test Commands

### Single Camera TEE Pipeline Test

```bash
# Ensure RGA is enabled
export GST_VIDEO_CONVERT_USE_RGA=1

# Test TEE pipeline with cam2 (video11)
gst-launch-1.0 -v \
  v4l2src device=/dev/video11 io-mode=mmap ! video/x-raw,format=UYVY ! \
  videoscale ! video/x-raw,width=1920,height=1080 ! \
  videoconvert ! video/x-raw,format=NV12 ! \
  tee name=t ! \
    queue ! mpph264enc qp-init=20 gop=30 profile=high bps=18000000 ! \
    h264parse config-interval=1 ! matroskamux streamable=true ! \
    filesink location=/tmp/test_recording.mkv sync=false \
  t. ! \
    queue ! mpph264enc qp-init=26 gop=30 profile=baseline bps=6000000 ! \
    h264parse config-interval=-1 ! \
    rtspclientsink location=rtsp://127.0.0.1:8554/cam2 protocols=tcp latency=0
```

### Verify Edit-While-Record

```bash
# While pipeline is running, check file is readable
ffprobe /tmp/test_recording.mkv

# Should show duration increasing, no errors
```

### Monitor Resources

```bash
# CPU usage
htop

# VPU frequency (higher = more load)
cat /sys/class/devfreq/fdab0000.rkvenc-core/cur_freq
cat /sys/class/devfreq/fdac0000.rkvenc-core/cur_freq
```

---

## Open Questions

1. **Audio capture**: Should HDMI audio be included in recordings?
2. **Mixer recording**: Should mixer output also be recordable to .mkv?
3. **Session management**: How should recording sessions be named/organized?
4. **Disk space**: Auto-stop recording when disk is nearly full?

---

## Related Documentation

- [CURRENT_ARCHITECTURE.md](./CURRENT_ARCHITECTURE.md) - Current system architecture
- [VDONINJA_WHEP_INTEGRATION.md](./VDONINJA_WHEP_INTEGRATION.md) - Mixer integration
- [lessons-learned.md](./lessons-learned.md) - Device initialization details
- [fix-log.md](./fix-log.md) - Encoder stability notes

---

**Status**: Ready for implementation  
**Next Step**: Test single-camera TEE pipeline on R58 device

