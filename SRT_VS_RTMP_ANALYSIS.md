# SRT vs RTMP Analysis for External Streaming

**Date**: 2025-12-19  
**Status**: ✅ SRT Available, Recommendation Provided

---

## Current State

### RTMP Usage (Internal Only)
Currently, RTMP is used **exclusively for internal communication** between components:
- Ingest → MediaMTX (localhost:1935)
- Mixer → MediaMTX (localhost:1935)
- Calls Relay → MediaMTX (localhost:1935)

**Key Point**: RTMP is NOT used for external streaming. It's only for localhost communication.

### External Streaming
MediaMTX handles external streaming via:
- **WebRTC** (port 8889) - Primary for browsers
- **HLS** (port 8888) - Fallback for browsers
- **RTSP** (port 8554) - For VLC/players
- **SRT** (port 8890) - Available but not actively used

---

## SRT vs RTMP Comparison

| Feature | RTMP | SRT |
|---------|------|-----|
| **Latency** | 2-3 seconds | 0.5-2 seconds |
| **Error Recovery** | TCP retransmission | ARQ + FEC |
| **Network Resilience** | Poor (TCP) | Excellent (UDP) |
| **Firewall Friendly** | Yes (TCP 1935) | Moderate (UDP) |
| **Bandwidth Efficiency** | Good | Better |
| **Encryption** | Optional (RTMPS) | Built-in AES |
| **Jitter Handling** | Poor | Excellent |
| **Packet Loss Tolerance** | 0% (TCP) | Up to 20% |
| **Long Distance** | Poor | Excellent |
| **Browser Support** | No (requires server) | No (requires server) |
| **GStreamer Support** | ✅ rtmpsink | ✅ srtsink |
| **MediaMTX Support** | ✅ Port 1935 | ✅ Port 8890 |

---

## Use Case Analysis

### Internal Communication (Current RTMP Usage)
**Verdict**: ✅ **Keep RTMP**

**Reasons**:
1. **Localhost only** - No network issues (packet loss, jitter, etc.)
2. **Simpler** - RTMP is well-established and debugged
3. **FLV compatibility** - RTMP uses FLV which MediaMTX handles well
4. **No latency concerns** - Internal communication is fast enough
5. **Firewall irrelevant** - Localhost traffic

**Recommendation**: No change needed for internal RTMP usage.

### External Streaming (Future/Optional)
**Verdict**: ✅ **Use SRT**

**Reasons**:
1. **Better for unreliable networks** - Internet, WiFi, cellular
2. **Lower latency** - 0.5-2s vs 2-3s
3. **Built-in encryption** - Secure by default
4. **Packet loss recovery** - Works over lossy connections
5. **Industry standard** - OBS, vMix, Wirecast all support SRT

---

## Recommendation

### For Internal Communication (Ingest/Mixer → MediaMTX)
**Keep RTMP** - No changes needed
- Simple, reliable, well-tested
- Localhost has no network issues
- FLV format works well with MediaMTX

### For External Streaming (Future Feature)
**Add SRT Output** - Implement when needed for external streaming

**Implementation**:
```python
# Option 1: Direct SRT from ingest (bypasses MediaMTX)
def build_srt_streaming_pipeline(cam_id, srt_url, bitrate):
    """Stream directly to external SRT server."""
    pipeline_str = (
        f"v4l2src device=/dev/video{cam_id} ! "
        f"videoconvert ! videoscale ! "
        f"video/x-raw,width=1920,height=1080 ! "
        f"x264enc tune=zerolatency bitrate={bitrate} ! "
        f"mpegtsmux ! "
        f"srtsink uri={srt_url} latency=1000"
    )
    return pipeline_str

# Option 2: SRT output from MediaMTX (recommended)
# MediaMTX automatically provides SRT output at:
# srt://<server>:8890/<path>
# No code changes needed!
```

---

## When to Use SRT

### ✅ Use SRT For:
1. **External streaming** to remote servers
2. **Long-distance** streaming (across cities/countries)
3. **Unreliable networks** (WiFi, cellular, internet)
4. **Low-latency requirements** over distance
5. **Secure streaming** (built-in encryption)
6. **Professional broadcast** workflows

### ❌ Don't Use SRT For:
1. **Localhost communication** (RTMP is simpler)
2. **Browser playback** (use WebRTC/HLS)
3. **Simple local networks** (RTMP/RTSP sufficient)

---

## Implementation Priority

### Priority 1: ✅ DONE
Keep current RTMP for internal communication

### Priority 2: ⏭️ OPTIONAL (When Needed)
Add SRT output for external streaming:
1. Document SRT endpoints (already available via MediaMTX)
2. Add UI controls for SRT streaming
3. Test SRT with OBS/vMix

### Priority 3: ⏭️ FUTURE
Direct SRT publishing from ingest (bypass MediaMTX):
- Only if MediaMTX SRT output has issues
- Requires pipeline changes
- More complex to maintain

---

## Current Architecture (Correct)

```
┌─────────────────────────────────────────────────────────────┐
│ Ingest Pipelines                                            │
│ v4l2src → mpph265enc (VPU) → rtspclientsink                │
│                                  ↓                          │
│                          MediaMTX (RTSP)                    │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ MediaMTX Server                                             │
│ - Receives: RTSP (H.265) from ingest                       │
│ - Receives: RTMP (H.264) from mixer                        │
│ - Outputs:                                                  │
│   • RTSP :8554 (for recording, mixer input)                │
│   • WebRTC :8889 (for browser preview)                     │
│   • HLS :8888 (for browser fallback)                       │
│   • SRT :8890 (for external streaming - available)         │
└─────────────────────────────────────────────────────────────┘
```

**Note**: Mixer uses RTMP internally because:
1. It's localhost communication (no network issues)
2. FLV format limitation (no H.265 support)
3. MediaMTX handles RTMP → all other formats

---

## SRT Already Available!

MediaMTX automatically provides SRT output for all published streams:

```bash
# Camera streams available via SRT
srt://r58.itagenten.no:8890?streamid=read:cam0
srt://r58.itagenten.no:8890?streamid=read:cam1
srt://r58.itagenten.no:8890?streamid=read:cam2
srt://r58.itagenten.no:8890?streamid=read:cam3

# Mixer program output via SRT
srt://r58.itagenten.no:8890?streamid=read:mixer_program
```

**Test with OBS**:
1. Open OBS Studio
2. Settings → Stream
3. Service: Custom
4. Server: `srt://r58.itagenten.no:8890?streamid=read:mixer_program`
5. Start streaming

**Test with VLC**:
```bash
vlc srt://r58.itagenten.no:8890?streamid=read:cam0
```

**Test with FFmpeg**:
```bash
ffplay srt://r58.itagenten.no:8890?streamid=read:mixer_program?latency=1000
```

---

## Conclusion

### Summary
- ✅ **Keep RTMP for internal communication** (ingest/mixer → MediaMTX)
- ✅ **SRT already available** via MediaMTX for external streaming
- ✅ **No code changes needed** - MediaMTX handles conversion
- ⏭️ **Add SRT UI controls** when external streaming is needed

### Action Items
1. ✅ **No changes needed** to current RTMP internal usage
2. ⏭️ **Document SRT endpoints** for external streaming
3. ⏭️ **Add UI controls** for SRT streaming (when needed)
4. ⏭️ **Test SRT output** with OBS/vMix/FFmpeg

### Performance Impact
- **Internal RTMP**: No change (already optimal for localhost)
- **External SRT**: Available via MediaMTX (no additional CPU)
- **Best of both worlds**: Simple internal, powerful external

---

## Final Recommendation

**Do NOT replace RTMP with SRT for internal communication.**

**Reasons**:
1. RTMP works perfectly for localhost
2. Simpler and more reliable for internal use
3. No network issues on localhost
4. SRT's advantages (error recovery, encryption) are irrelevant for localhost
5. Changing would add complexity without benefit

**Instead**:
- Keep RTMP for internal communication
- Use SRT for external streaming (already available via MediaMTX)
- Document SRT endpoints for users who need external streaming
- Add UI controls for SRT when external streaming feature is requested

**Status**: ✅ Current architecture is optimal - no changes needed.
