# HLS Optimization Plan - Focus on What Works

## Current Situation

### What Happened
1. Implemented MSE streaming as alternative to HLS
2. MSE had fMP4 format issues (90% working but broken playback)
3. MSE code deployed to production
4. **Result**: All cameras stuck on "Loading preview..." because `startMSEPreview()` function doesn't exist on server

### Root Cause
- MSE implementation added complexity without clear benefit
- FFmpeg + fMP4 approach was overkill
- Current HLS + WebRTC setup already works well
- MSE broke production streaming

## Decision: Focus on HLS

**Why HLS:**
- ✅ Already working (with recent fixes)
- ✅ Universal browser support
- ✅ Works through Cloudflare Tunnel
- ✅ Simpler architecture (no FFmpeg processes)
- ✅ MediaMTX handles everything

**Current Performance:**
- Local: WebRTC (200-500ms latency)
- Remote: HLS (2-4s latency with optimizations)

## Cleanup Status

### Completed ✅
- MSE commit reverted locally
- MSE files removed (mse_stream.py, mse_test.html, docs)
- Force pushed clean code to GitHub

### Needs Deployment 🔄
- R58 server still has broken MSE code
- Need to pull clean code and restart

## HLS Issues to Fix

### Issue 1: Cameras Stuck on "Loading preview..."
**Status**: Caused by broken MSE code on server
**Fix**: Deploy clean code (see DEPLOY_HLS_FIX.md)

### Issue 2: HLS Connection Errors (from previous testing)
**Symptoms**:
- NS_BINDING_ABORTED
- Media resource could not be decoded  
- HTTP 500 on segments

**Already Fixed** (in HLS_ERROR_FIX.md):
- ✅ Progressive media error recovery
- ✅ Proper fragment vs manifest error handling
- ✅ Buffer stall recovery
- ✅ Non-fatal error filtering

### Issue 3: H.265 vs H.264
**Current**: MediaMTX receives H.265 from cameras
**HLS Output**: MediaMTX transcodes to H.264 for HLS
**Impact**: CPU load for transcoding

**Options**:
1. Keep current (works, proven)
2. Optimize transcoding settings
3. Accept H.265 limitation (browsers don't support it in HLS anyway)

## Next Steps

### 1. Deploy Clean Code (IMMEDIATE)
```bash
# See DEPLOY_HLS_FIX.md for commands
ssh linaro@r58.itagenten.no
cd /opt/preke-r58-recorder
sudo git reset --hard origin/feature/webrtc-switcher-preview
sudo systemctl restart preke-recorder
```

### 2. Test HLS Streaming
- Open https://recorder.itagenten.no/
- Verify all 4 cameras load and play
- Check console for errors
- Monitor network requests for HLS segments

### 3. Analyze HLS Performance
**Metrics to check**:
- Latency (time from camera to browser)
- Buffer health (stalls, rebuffering)
- Error rate (404s, 500s on segments)
- CPU usage (transcoding load)

### 4. Optimize HLS Configuration

**Current mediamtx.yml settings**:
```yaml
hlsSegmentCount: 10         # 20s buffer (10 x 2s)
hlsSegmentDuration: 2s      # Segment length
hlsPartDuration: 400ms      # LL-HLS part duration
```

**Potential optimizations**:
- Reduce segment duration for lower latency
- Adjust buffer size based on network stability
- Tune transcoding parameters

### 5. Monitor and Iterate
- Watch for errors in production
- Collect latency metrics
- Adjust based on real usage

## What We Learned

### MSE Lessons
- ❌ FFmpeg + fMP4 was unnecessary complexity
- ❌ Solving problems that don't exist
- ❌ Added fragility to working system
- ✅ MediaMTX already does what we need

### HLS Strengths
- ✅ Battle-tested, reliable
- ✅ Universal compatibility
- ✅ Works through Cloudflare Tunnel
- ✅ MediaMTX handles transcoding
- ✅ Simple architecture

### WebRTC Reality
- ✅ Excellent for local access
- ❌ Doesn't work through Cloudflare Tunnel (UDP blocked)
- ⚠️ Could work with TURN server (future enhancement)

## Architecture (Simplified)

```
┌─────────────────────────────────────────┐
│           R58 Device                     │
│                                          │
│  Cameras → MediaMTX                      │
│            ├─ RTSP (H.265 input)        │
│            ├─ WebRTC (local, H.265)     │
│            └─ HLS (remote, H.264)       │
│                                          │
└──────────────┬───────────────────────────┘
               │
        Cloudflare Tunnel
               │
┌──────────────▼───────────────────────────┐
│          Browser                          │
│                                          │
│  Local:  WebRTC (200-500ms)             │
│  Remote: HLS (2-4s)                     │
│                                          │
└──────────────────────────────────────────┘
```

**Simple. Works. Reliable.**

## Success Criteria

After deployment and optimization:

- ✅ All 4 cameras load within 5 seconds
- ✅ No stuck "Loading preview..." states
- ✅ < 5% error rate on HLS segments
- ✅ Smooth playback, no frequent buffering
- ✅ Latency < 5s for remote access
- ✅ CPU usage < 50% during streaming

## Files Reference

- **Current Plan**: This file
- **Deployment**: DEPLOY_HLS_FIX.md
- **HLS Fixes**: HLS_ERROR_FIX.md (already implemented)
- **MediaMTX Config**: mediamtx.yml
- **Frontend**: src/static/index.html

## Status

- **MSE Cleanup**: ✅ Complete locally
- **GitHub**: ✅ Clean code pushed
- **R58 Server**: 🔄 Needs deployment
- **HLS Testing**: ⏳ Pending deployment
- **Optimization**: ⏳ After testing

**Next Action**: Deploy clean code to R58 (see DEPLOY_HLS_FIX.md)

**Date**: December 20, 2025
