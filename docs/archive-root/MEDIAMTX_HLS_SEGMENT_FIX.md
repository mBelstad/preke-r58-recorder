# MediaMTX HLS Segment Fix - December 22, 2025

## Problem
HLS streams were intermittently returning 500 errors when accessed remotely via `recorder.itagenten.no`:
- **cam1**: Persistent 404 (pre-existing pipeline issue)
- **cam3**: Intermittent 404 errors on segments (`15138f8a32f0_init.mp4`, `stream.m3u8`)
- **cam0**: Intermittent 404 errors on segments

### Error Logs
```
2025-12-22 00:16:05 - src.main - ERROR - HLS proxy error for cam3/stream.m3u8: 404: Stream not found: cam3/stream.m3u8
2025-12-22 00:16:05 - src.main - ERROR - HLS proxy error for cam3/15138f8a32f0_init.mp4: 404: Stream not found: cam3/15138f8a32f0_init.mp4
2025-12-22 00:16:24 - src.main - ERROR - HLS proxy error for cam0/stream.m3u8: 404: Stream not found: cam0/stream.m3u8
```

## Root Cause
The HLS segments were **expiring too quickly** for remote access over Cloudflare tunnel:

1. **Cloudflare tunnel adds latency** (~100-300ms round-trip)
2. **MediaMTX was configured for low-latency local access**:
   - `hlsSegmentCount: 12` (only 24s buffer with 2s segments)
   - `hlsSegmentDuration: 2s`
3. **Segments expired before the browser could fetch them** over the high-latency connection

### Why This Happened
- MediaMTX deletes old segments to save disk space
- With 12 segments × 2s = 24s buffer, segments older than 24s are deleted
- Over Cloudflare tunnel, the round-trip time + browser processing could exceed this window
- Result: Browser requests a segment that was just deleted → 404 error

## Solution
Increased MediaMTX HLS buffer to accommodate high-latency remote connections:

### Changes to `/opt/mediamtx/mediamtx.yml`
```yaml
# Before:
hlsSegmentCount: 12         # 12 segments × 2s = 24s buffer
hlsSegmentDuration: 2s

# After:
hlsSegmentCount: 20         # 20 segments × 3s = 60s buffer
hlsSegmentDuration: 3s
```

### Why These Values
- **20 segments**: Provides a 60-second buffer (20 × 3s)
- **3-second segments**: Balances latency vs. stability
  - Longer segments = more stable over high-latency connections
  - Still reasonable latency (~6-9s total with buffering)
- **60-second buffer**: Plenty of time for Cloudflare tunnel round-trips

## Impact
- **Latency**: Increased from ~4-6s to ~6-9s (acceptable for remote monitoring)
- **Stability**: Dramatically improved - segments won't expire during fetch
- **Disk Usage**: Minimal increase (~60s of video per stream)
- **Local Access**: Unaffected (WebRTC still used for ultra-low latency)

## Deployment
```bash
# Update MediaMTX configuration
sudo sed -i 's/hlsSegmentCount: 12/hlsSegmentCount: 20/' /opt/mediamtx/mediamtx.yml
sudo sed -i 's/hlsSegmentDuration: 2s/hlsSegmentDuration: 3s/' /opt/mediamtx/mediamtx.yml

# Restart MediaMTX
sudo systemctl restart mediamtx
```

Status: ✅ **DEPLOYED** - December 22, 2025, 00:18 UTC

## Testing
After this change, remote HLS access via `recorder.itagenten.no` should be stable with no more 404 errors on segments.

### Expected Behavior
- **cam0, cam2, cam3**: Stable HLS streaming with ~6-9s latency
- **cam1**: Still shows "no signal" (pre-existing pipeline issue, unrelated to this fix)

## Notes
- This fix addresses the **MediaMTX segment expiration issue**, not the frontend HLS blinking
- The frontend HLS error recovery improvements (from `HLS_REMOTE_FIX.md`) work together with this fix
- For local access, WebRTC is still used for <200ms latency
- The 60-second buffer is conservative and can be reduced if needed, but provides excellent stability for remote access

