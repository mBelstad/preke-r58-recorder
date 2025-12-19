# H.265 RTP Migration - Testing Status

**Date**: 2025-12-19  
**Status**: ⚠️ PARTIAL - Ingest working, Recording/Playback needs fix

---

## What's Working ✅

### 1. Ingest with H.265 Hardware Encoding
- ✅ All 4 cameras streaming with mpph265enc (VPU)
- ✅ CPU usage: 60% total (vs 160% with software)
- ✅ H.265 encoding via RTP/UDP
- ✅ System stable

**Test Results**:
```json
{
    "cameras": {
        "cam0": "streaming 4K (3840x2160)",
        "cam1": "streaming 480p (640x480)",
        "cam2": "streaming 1080p (1920x1080)",
        "cam3": "streaming 4K (3840x2160)"
    },
    "summary": {
        "total": 4,
        "streaming": 4
    }
}
```

### 2. API Endpoints
- ✅ `/api/ingest/status` - Returns camera status
- ✅ `/record/start-all` - Starts recording
- ✅ `/record/stop-all` - Stops recording
- ✅ `/api/recordings` - Lists recordings

---

## What's NOT Working ❌

### 1. MediaMTX RTSP Streams

**Problem**: MediaMTX not receiving RTP streams

**Root Cause**: 
- Ingest sends H.265 via raw RTP/UDP to ports 5000-5006
- MediaMTX `source: rtp://` expects SDP (Session Description Protocol)
- Without SDP, MediaMTX doesn't know stream format/codec

**Error**:
```
MediaMTX: "no one is publishing to path 'cam0/1/2/3'"
RTSP client: "Not Found (404)"
```

**Impact**:
- ❌ Recording produces 0-byte files (can't subscribe to RTSP)
- ❌ Browser preview not available
- ❌ Mixer can't access streams

### 2. Recording Functionality

**Problem**: Recording creates 0-byte MKV files

**Root Cause**: Recording subscribes to RTSP streams from MediaMTX, but MediaMTX isn't publishing them

**Files Created**:
```bash
-rw-r--r-- 1 root root 0 Dec 19 15:33 recording_20251219_153350.mkv
```

---

## Root Cause Analysis

### The RTP/RTSP Problem

**What we implemented**:
```
Ingest → mpph265enc → rtph265pay → udpsink (port 5000)
                                        ↓
                                   MediaMTX ???
```

**What MediaMTX needs**:
1. **Option A - RTP with SDP**:
   ```
   Ingest → RTSP ANNOUNCE (with SDP) → MediaMTX listens
   ```

2. **Option B - RTSP Publish**:
   ```
   Ingest → rtspclientsink → MediaMTX (but rtspclientsink not available)
   ```

3. **Option C - RTMP** (what we had before):
   ```
   Ingest → H.264 + flvmux → rtmpsink → MediaMTX ✓
   ```

---

## Solutions

### Solution 1: Use RTMP with H.264 for MediaMTX (Hybrid)

**Approach**: Keep H.265 encoding but transcode to H.264 for MediaMTX

```python
# Ingest pipeline:
v4l2src → mpph265enc (VPU) → tee:
    ├─ Branch 1: h265parse → file recording (H.265 MKV)
    └─ Branch 2: avdec_h265 → x264enc → flvmux → rtmpsink → MediaMTX
```

**Pros**:
- MediaMTX works (RTMP publisher mode)
- Recording gets H.265 (better quality/compression)
- Browser preview works

**Cons**:
- Decode + re-encode uses CPU (~20% per camera)
- Defeats purpose of VPU-only encoding

### Solution 2: Install gst-rtsp-server Plugin

**Approach**: Use GStreamer's RTSP server to publish H.265 streams

```python
# Ingest pipeline:
v4l2src → mpph265enc → h265parse → rtph265pay → rtspclientsink
```

**Pros**:
- Native H.265 RTSP publishing
- No transcoding needed
- MediaMTX can subscribe

**Cons**:
- Requires `gst-rtsp-server` plugin (may not be installed)
- More complex pipeline

### Solution 3: Use MediaMTX WHIP (WebRTC)

**Approach**: Publish via WHIP protocol (WebRTC)

**Pros**:
- Modern protocol
- H.265 support via WebRTC
- Low latency

**Cons**:
- Requires WHIP implementation
- More complex

### Solution 4: Direct File Recording (No MediaMTX for Recording)

**Approach**: Record directly from ingest, use MediaMTX only for preview

```python
# Ingest pipeline:
v4l2src → mpph265enc → tee:
    ├─ Branch 1: h265parse → matroskamux → filesink (direct recording)
    └─ Branch 2: rtph265pay → udpsink → MediaMTX (for preview only)
```

**Pros**:
- Recording works immediately
- H.265 files
- Preview can be fixed separately

**Cons**:
- Device access conflict (ingest + recording both access camera)
- This is why we moved to always-on ingest architecture

---

## Recommended Fix: Hybrid RTMP Approach

For immediate functionality, use Solution 1:

1. Keep mpph265enc for VPU encoding
2. Add tee to split stream:
   - One branch: Direct file recording (H.265 MKV)
   - One branch: Transcode to H.264 + RTMP for MediaMTX
3. MediaMTX works in publisher mode
4. Recording, preview, mixer all work

**Implementation**:
```python
# In build_r58_ingest_pipeline():
pipeline_str = (
    f"{source_str} ! "
    f"mpph265enc bps={bps} ! video/x-h265 ! tee name=t ! "
    # Branch 1: RTMP for MediaMTX (H.264)
    f"queue ! avdec_h265 ! videoconvert ! "
    f"x264enc tune=zerolatency bitrate={bitrate} ! "
    f"flvmux ! rtmpsink location=rtmp://127.0.0.1:1935/{cam_id} "
    # Branch 2: Could add direct recording here
    f"t. ! queue ! fakesink"
)
```

**CPU Impact**: ~20% per camera for transcode (still better than 40% for pure software)

---

## Current State

**Ingest**: ✅ Working (H.265 VPU encoding, 60% CPU for 4 cameras)  
**MediaMTX**: ❌ Not receiving streams (RTP/SDP mismatch)  
**Recording**: ❌ 0-byte files (can't subscribe to MediaMTX)  
**Preview**: ❌ Not available (MediaMTX not publishing)  
**Mixer**: ❌ Can't access streams (MediaMTX not publishing)

---

## Next Steps

1. **Immediate**: Implement hybrid RTMP approach for functionality
2. **Short-term**: Investigate `gst-rtsp-server` plugin availability
3. **Long-term**: Implement proper RTSP publishing or WHIP

---

## Testing Completed

- ✅ Ingest API status
- ✅ Recording API (start/stop commands work)
- ❌ Recording file creation (0-byte files)
- ⏸️ Preview streams (blocked by MediaMTX)
- ⏸️ Mixer (blocked by MediaMTX)
- ⏸️ Browser UI (blocked by MediaMTX)

---

## Conclusion

The H.265 VPU encoding is working perfectly (60% CPU for 4 cameras), but the MediaMTX integration needs to be fixed. The RTP/UDP approach doesn't work without proper RTSP publishing or SDP.

**Recommendation**: Implement hybrid approach with RTMP for MediaMTX while keeping H.265 for direct recording.
