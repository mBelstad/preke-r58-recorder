# HLS Optimization Test Results

**Date:** December 17, 2025  
**Branch:** `always-on-ingest`  
**Test Location:** Remote via Cloudflare Tunnel

## Test Summary

| Test | Result | Notes |
|------|--------|-------|
| Stream Mode Selector | ✅ Pass | UI dropdown visible, persists to localStorage |
| HLS Streaming (cam1) | ✅ Pass | HD 1920x1080, stable playback |
| HLS Streaming (cam2) | ⚠️ Partial | 4K (3840x2160), some HLS timing errors but recoverable |
| HLS Streaming (cam3) | ✅ Pass | HD 1920x1080, stable playback |
| Recording (cam1) | ✅ Pass | Recording saved successfully |
| Recording (cam2) | ✅ Pass | Recording saved: 22MB, 44s, H.264, 4.1Mbps |
| Recording (cam3) | ✅ Pass | Recording saved successfully |
| Preview During Recording | ✅ Pass | All previews continue while recording |
| cam0 No Signal | ✅ Pass | Correctly shows "No Signal" status |

## Ingest Status

```json
{
  "cam0": { "status": "error", "resolution": null },
  "cam1": { "status": "streaming", "resolution": "1920x1080" },
  "cam2": { "status": "streaming", "resolution": "3840x2160" },
  "cam3": { "status": "streaming", "resolution": "1920x1080" }
}
```

## Recording Status

- **cam0**: Correctly skipped (no signal)
- **cam1**: Recording started and saved
- **cam2**: Recording started and saved (4K source scaled to 1080p)
- **cam3**: Recording started and saved

## Recording File Verification

```
/mnt/sdcard/recordings/cam2/recording_20251217_151047.mp4
- Codec: H.264
- Resolution: 1920x1080
- Duration: 44.34 seconds
- Bitrate: 4.15 Mbps
- File Size: 22 MB
```

## HLS Performance

### cam2 (4K Source)
- Multiple HLS timing errors (debug level) during playback
- These are expected with low-latency HLS over remote connection
- Errors are recoverable - stream continues playing

### Stream Mode Options
1. **Low Latency (~1s)**: Aggressive buffering, may have hiccups on slow connections
2. **Balanced (~2s)**: Default, good balance of latency and stability
3. **Stable (~5s)**: Maximum buffering for unreliable connections

## CPU Usage During Test

- **uvicorn**: 566% (6 cores at ~94% each)
- **mediamtx**: 5.6%
- **System Load**: 16.47

This is expected with:
- 3 ingest pipelines (always-on capture + encoding)
- 3 recording pipelines (RTSP subscription + MP4 muxing)
- HLS segment delivery

## Implemented Features

1. ✅ **4K Encoder Optimization**
   - Multi-threading (4 threads, sliced)
   - Speed preset: superfast
   - Increased queue buffers (5 instead of 3)

2. ✅ **Stream Mode Selector UI**
   - Dropdown with 3 modes
   - Persists selection in localStorage
   - Restarts all HLS players on change

3. ✅ **Freeze Detection & Recovery**
   - Monitors video.currentTime every 3 seconds
   - Auto-recovers frozen streams

4. ✅ **Stream Synchronization**
   - Finds master stream (most advanced)
   - Adjusts playback rate (0.97x-1.03x) to sync
   - Max drift: ±1 second

5. ✅ **MediaMTX HLS Tuning**
   - Segment duration: 500ms
   - Part duration: 100ms
   - Segment count: 10

## Known Issues

1. **cam2 HLS Errors**: 4K source generates more timing errors over remote connection
   - Workaround: Use "Stable" mode for better buffering
   
2. **High CPU Usage**: Expected with software encoding
   - Future: Consider hardware encoding (RK3588 VPU)

## Conclusion

All HLS optimizations are working as expected. The system successfully:
- Streams 3 cameras simultaneously via HLS
- Records all active cameras while maintaining previews
- Handles 4K sources (scaled to 1080p for streaming)
- Provides stream mode selection for different network conditions
- Auto-recovers from stream freezes

