# Low-Latency Streaming Architecture

## Overview

This document describes the low-latency streaming architecture for the R58 Recorder, optimized for live view with minimal delay.

## Current Implementation

### WebRTC (Primary - Ultra Low Latency)
- **Latency**: <1 second
- **Protocol**: WebRTC via MediaMTX
- **Port**: 8889 (HTTP), 8189 (ICE/UDP)
- **Use Case**: Live view in web browser
- **Status**: ✅ Implemented

### RTMP Push (Recording + Streaming)
- **Latency**: ~2-3 seconds
- **Protocol**: RTMP to MediaMTX
- **Port**: 1935
- **Use Case**: Recording + streaming simultaneously via tee
- **Status**: ✅ Implemented

### HLS (Fallback)
- **Latency**: 7+ seconds
- **Protocol**: HLS via MediaMTX
- **Port**: 8888
- **Use Case**: Fallback for browsers without WebRTC support
- **Status**: ✅ Implemented

## Architecture

```
HDMI Input (/dev/video60)
    ↓
GStreamer Pipeline (single, with tee)
    ├─→ Recording: h264parse → mp4mux → filesink
    └─→ Streaming: flvmux → rtmpsink → MediaMTX (port 1935)
                    ↓
            MediaMTX Server
                ├─→ WebRTC (port 8889) → Browser (low latency)
                ├─→ HLS (port 8888) → Browser (fallback)
                ├─→ RTSP (port 8554) → VLC/Players
                └─→ SRT (port 8890) → Future use
```

## Vdo.Ninja Integration

### Option 1: Direct WebRTC to Vdo.Ninja
Vdo.Ninja can ingest WebRTC streams directly. Use the MediaMTX WebRTC endpoint:

```
http://<r58_ip>:8889/cam0/whep
```

### Option 2: Vdo.Ninja → MediaMTX → SRT (Future)
1. Vdo.Ninja publishes to MediaMTX via WHIP
2. MediaMTX converts to SRT
3. SRT output for external distribution

**Configuration needed:**
- Enable WHIP in MediaMTX
- Configure SRT output path
- Set up Vdo.Ninja with MediaMTX endpoint

## NDI Support (Future)

NDI (Network Device Interface) provides low-latency video over IP networks.

### Implementation Plan:
1. **NDI Source**: Use GStreamer `ndisrc` or `ndivideosrc` to capture NDI streams
2. **NDI Output**: Use `ndivideosink` to publish streams as NDI sources
3. **Integration**: Add NDI paths to MediaMTX configuration

### GStreamer NDI Pipeline Example:
```bash
# NDI Input → Recording + Streaming
ndivideosrc ndi-name="R58-Camera" ! 
videoconvert ! 
x264enc ! 
tee name=t ! 
queue ! h264parse ! mp4mux ! filesink location=recording.mp4 
t. ! queue ! flvmux ! rtmpsink location=rtmp://localhost:1935/cam0
```

### NDI Output (for other NDI-compatible software):
```bash
# MediaMTX RTSP → NDI Output
gst-launch-1.0 rtspsrc location=rtsp://localhost:8554/cam0 ! 
rtph264depay ! 
h264parse ! 
ndivideosink ndi-name="R58-Stream"
```

## SRT Output (Future)

SRT (Secure Reliable Transport) is ideal for long-distance, unreliable networks.

### MediaMTX SRT Configuration:
```yaml
paths:
  cam0:
    source: publisher
    sourceProtocol: rtmp
    # SRT output will be available at srt://<server>:8890/cam0
```

### GStreamer SRT Publishing:
```bash
# Direct SRT publish (alternative to RTMP)
gst-launch-1.0 v4l2src device=/dev/video60 ! 
videoconvert ! 
x264enc ! 
srtsink uri=srt://localhost:8890/cam0
```

## Performance Optimization

### Low Latency Settings:
- **Encoder**: `x264enc tune=zerolatency speed-preset=superfast`
- **Queue**: `max-size-buffers=0 max-size-time=0` (no buffering)
- **WebRTC**: Direct connection, no transcoding delay
- **HLS**: `hlsSegmentDuration=1s` (minimum segment size)

### Bandwidth Considerations:
- **Recording**: 5 Mbps (configurable)
- **Streaming**: Same bitrate (tee splits, doesn't duplicate encoding)
- **WebRTC**: Adaptive bitrate based on network conditions

## Testing

### WebRTC Test:
```bash
# Check WebRTC endpoint
curl http://localhost:8889/cam0/whep

# Test in browser console:
const player = new MediaMTXWebRTC({
    url: 'http://localhost:8889/cam0/whep',
    video: document.getElementById('video')
});
player.start();
```

### Latency Measurement:
1. Point camera at clock with seconds display
2. Compare browser display time vs actual time
3. WebRTC should show <1s difference
4. HLS will show 7-10s difference

## Troubleshooting

### WebRTC Not Working:
- Check MediaMTX logs: `journalctl -u mediamtx.service`
- Verify WebRTC port 8889 is open
- Check browser console for WebRTC errors
- Fallback to HLS automatically

### High Latency:
- Ensure WebRTC is being used (not HLS fallback)
- Check encoder settings (zerolatency, superfast)
- Verify queue settings (no buffering)
- Check network conditions

### Stream Not Showing:
- Verify recording is active: `curl http://localhost:8000/status/cam0`
- Check MediaMTX is receiving RTMP: `journalctl -u mediamtx.service | grep RTMP`
- Test RTSP directly: `vlc rtsp://localhost:8554/cam0`

