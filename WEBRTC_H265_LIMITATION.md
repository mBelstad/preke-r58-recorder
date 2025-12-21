# WebRTC H.265 Limitation - Analysis and Solutions

**Date**: December 22, 2025  
**Status**: Root cause identified

---

## Problem

MediaMTX WHEP endpoint returns 400 Bad Request with error:
```json
{"error":"the stream doesn't contain any supported codec, which are currently AV1, VP9, VP8, H264, Opus, G722, G711"}
```

**Root Cause**: R58 ingest pipelines publish H.265 streams to MediaMTX, but MediaMTX WebRTC (WHEP) only supports H.264 for video.

---

## Current Architecture

```
HDMI Cameras
    |
    | V4L2 capture
    |
    v
R58 Ingest Pipelines
    |
    | mpph265enc (hardware H.265)
    |
    v
MediaMTX (RTSP)
    |
    ├─> HLS (H.265) ✅ Works
    └─> WHEP (WebRTC) ❌ Requires H.264
```

---

## Why H.265 Was Chosen

From the codebase, H.265 was chosen for:
1. **Better compression** - 50% smaller files than H.264
2. **Hardware acceleration** - mpph265enc uses RK3588 hardware encoder
3. **Recording quality** - Higher quality at same bitrate

---

## Solution Options

### Option A: Dual Encode (H.265 + H.264)

Modify ingest pipelines to encode both codecs:
- H.265 for recording/HLS (high quality, small files)
- H.264 for WebRTC (browser compatibility)

**Pros**:
- Best of both worlds
- WebRTC works with low latency
- Recording still uses efficient H.265

**Cons**:
- 2x encoding CPU load
- More complex pipeline

**Implementation**:
```gstreamer
v4l2src ! tee name=t
t. ! queue ! mpph265enc ! h265parse ! rtspclientsink location=rtsp://localhost:8554/cam0
t. ! queue ! x264enc ! h264parse ! rtspclientsink location=rtsp://localhost:8554/cam0_h264
```

---

### Option B: Switch to H.264 Only

Change all ingest pipelines to use H.264:
- Use mpph264enc (hardware H.264 encoder)
- Both recording and WebRTC use H.264

**Pros**:
- Simple, single encode
- WebRTC works immediately
- Lower CPU usage than dual encode

**Cons**:
- Larger recording files (2x size vs H.265)
- Slightly lower quality at same bitrate

**Implementation**: Change encoder in `src/pipelines.py`

---

### Option C: MediaMTX Transcoding (Not Recommended)

Configure MediaMTX to transcode H.265 → H.264 on-demand for WebRTC.

**Pros**:
- No changes to ingest pipelines

**Cons**:
- Very CPU intensive (software transcoding)
- Adds latency
- May not work reliably on RK3588

---

### Option D: Keep HLS for Local (Current State)

Accept that WebRTC doesn't work and use HLS locally.

**Pros**:
- No changes needed
- HLS works fine with H.265
- 1-3 second latency acceptable for many use cases

**Cons**:
- Higher latency than WebRTC
- Not the original goal

---

## Recommendation

**Option B: Switch to H.264** is the best balance:

1. **Simple implementation** - just change encoder in pipelines
2. **WebRTC works** - full browser compatibility
3. **Still hardware accelerated** - mpph264enc uses RK3588
4. **Recording still works** - H.264 is fine for most use cases

The file size increase (H.264 vs H.265) is offset by the benefit of having WebRTC work properly.

---

## Implementation Plan for Option B

### Step 1: Update Ingest Pipelines

In `src/pipelines.py`, change the encoder from mpph265enc to mpph264enc:

```python
# Before
encoder_str = "mpph265enc bps=8000000 bps-max=16000000"
caps_str = "video/x-h265"
parse_str = "h265parse"

# After  
encoder_str = "mpph264enc bps=8000000 bps-max=16000000"
caps_str = "video/x-h264"
parse_str = "h264parse"
```

### Step 2: Update Recording Pipelines

Recording subscriber pipelines also need to expect H.264:

```python
# In build_recording_subscriber_pipeline()
source_str = f"rtspsrc location={source_url} latency=100 protocols=udp ! rtph264depay"
parse_str = "h264parse"
mux_str = "mp4mux"  # or matroskamux, both support H.264
```

### Step 3: Restart Services

```bash
sudo systemctl restart preke-recorder
```

### Step 4: Test

- WebRTC should work immediately
- Recording continues to work
- File sizes will be ~2x larger

---

## Alternative: Option A (Dual Encode)

If file size is critical, implement dual encoding:

### Ingest Pipeline Changes

```python
# Tee after capture, before encoding
pipeline_str = (
    f"{source_str} ! "
    f"tee name=source_tee ! "
    # H.265 branch for recording
    f"queue ! mpph265enc ! h265parse ! rtspclientsink location=rtsp://localhost:8554/{cam_id} "
    # H.264 branch for WebRTC
    f"source_tee. ! queue ! mpph264enc ! h264parse ! rtspclientsink location=rtsp://localhost:8554/{cam_id}_h264"
)
```

### MediaMTX Path Configuration

```yaml
paths:
  cam0:
    source: publisher  # H.265 for HLS/recording
  cam0_h264:
    source: publisher  # H.264 for WebRTC
```

### Frontend Changes

Use `cam0_h264` for WebRTC, `cam0` for HLS.

---

## Current Status

- ✅ MediaMTX WebRTC encryption enabled
- ✅ CORS issue fixed with proxy
- ✅ VDO.ninja room-based signaling working
- ❌ **H.265 incompatible with WebRTC WHEP**

**Blocker**: Codec mismatch between ingest (H.265) and WebRTC requirements (H.264).

---

## Decision Required

Which option do you prefer?

1. **Option B (Simple)**: Switch everything to H.264, accept larger files
2. **Option A (Complex)**: Dual encode H.265 + H.264, best quality but more CPU
3. **Option D (Current)**: Keep HLS with 1-3 second latency

Let me know and I'll implement it!

