# HLS Remote View Fix - December 22, 2025

## Problem
When accessing the recorder remotely via `recorder.itagenten.no` (Cloudflare tunnel):
1. **WebRTC doesn't work** - Cloudflare tunnels don't support WebRTC/UDP traffic
2. **HLS streams were blinking/disconnecting** - Too aggressive error recovery causing constant reconnections

## Root Cause
1. **WebRTC over tunnel**: The frontend was attempting WebRTC connections even for remote access, which fails because Cloudflare tunnels only support HTTP/HTTPS (TCP), not WebRTC (UDP).
2. **Aggressive HLS recovery**: The HLS error handling was too aggressive:
   - Immediately calling `hls.startLoad()` on fragment errors (causing reconnections)
   - Short cooldown periods (2-3s) for media error recovery
   - Recreating players too frequently (5s timeout)

## Solution Implemented

### 1. Disabled WebRTC for Remote Access
Reverted the WebRTC remote access change to ensure HLS is used when accessing via Cloudflare tunnel:

```javascript
// Try WebRTC first for ultra-low latency (local access only - doesn't work over Cloudflare tunnel)
if (window.RTCPeerConnection && !IS_REMOTE) {
    console.log(`🎥 [${camId}] Attempting WebRTC connection (local access)`);
    const webrtcUrl = getWebRTCUrl(streamPath);
    console.log(`🎥 [${camId}] WebRTC URL: ${webrtcUrl}`);
    startWebRTCPreview(video, webrtcUrl, camId, placeholder);
} else {
    console.log(`📺 [${camId}] Using HLS (IS_REMOTE: ${IS_REMOTE}, RTCPeerConnection: ${!!window.RTCPeerConnection})`);
    // Use HLS for remote access (WebRTC doesn't work over Cloudflare tunnel)
    startHLSPreview(video, camId, placeholder, streamPath);
}
```

### 2. Automatic Stable Mode for Remote Access
The frontend now automatically uses "stable" HLS mode when accessing remotely:

```javascript
// Use stable mode for remote access (Cloudflare tunnel), balanced for local
let streamMode = localStorage.getItem('streamMode') || (IS_REMOTE ? 'stable' : 'balanced');
```

### 3. Enhanced Stable HLS Configuration
Improved the "stable" HLS profile with better timeout and retry settings:

```javascript
stable: {
    lowLatencyMode: false,
    backBufferLength: 90,           // Keep 90s of back buffer (increased from 30s)
    maxBufferLength: 60,            // Buffer up to 60s ahead
    maxMaxBufferLength: 120,        // Allow up to 120s max buffer
    maxBufferHole: 5,               // Tolerate 5s gaps in buffer
    maxStarvationDelay: 10,         // Wait 10s before giving up
    maxLoadingDelay: 10,            // Wait 10s for loading
    liveSyncDurationCount: 8,       // Sync to 8 segments behind live
    liveMaxLatencyDurationCount: 15, // Max 15 segments latency
    manifestLoadingTimeOut: 20000,  // 20s timeout for manifest (new)
    manifestLoadingMaxRetry: 10,    // Retry manifest 10 times (new)
    levelLoadingTimeOut: 20000,     // 20s timeout for segments (new)
    levelLoadingMaxRetry: 10,       // Retry segments 10 times (new)
    fragLoadingTimeOut: 30000,      // 30s timeout for fragments (new)
    fragLoadingMaxRetry: 10         // Retry fragments 10 times (new)
}
```

### 4. Less Aggressive Error Recovery
Improved HLS error handling to prevent blinking:

**Fragment/Level Errors:**
```javascript
// For fragment errors (expired segments), just retry loading
// Don't restart load immediately - let hls.js handle it with its retry logic
if (data.details === 'fragLoadError' || data.details === 'fragLoadTimeOut') {
    console.debug(`Fragment error for ${camId}, hls.js will retry automatically`);
    // Don't call hls.startLoad() - it causes blinking. Let hls.js retry internally.
    return;
}

// For level load errors, also let hls.js handle retries
if (data.details === 'levelLoadError' || data.details === 'levelLoadTimeOut') {
    console.debug(`Level load error for ${camId}, hls.js will retry automatically`);
    return;
}
```

**Media Errors:**
```javascript
// For bufferAppendError, be less aggressive to avoid blinking
if (data.details === 'bufferAppendError') {
    if (hls.bufferErrorCount === undefined) hls.bufferErrorCount = 0;
    hls.bufferErrorCount++;
    
    // Only try recovery if enough time has passed (5s cooldown, increased from 3s)
    if (timeSinceLastRecovery > 5000 && hls.bufferErrorCount < 3) {
        console.log(`HLS buffer error for ${camId}, recovering... (${hls.bufferErrorCount}/3)`);
        hls.lastMediaRecovery = now;
        hls.recoverMediaError();
    } else if (hls.bufferErrorCount >= 3) {
        // After 3 buffer errors, completely recreate the player (only once every 30s)
        if (timeSinceLastRecovery > 30000) {
            console.warn(`HLS buffer errors for ${camId} - recreating player after 10s...`);
            hls.destroy();
            delete hlsPlayers[camId];
            setTimeout(() => {
                startHLSPreview(video, camId, placeholder);
            }, 10000); // Increased from 5s to 10s
        }
    }
    return;
}

// For other media errors, use conservative recovery (5s cooldown, increased from 2s)
if (hls.mediaRecoveryCount < 3 && timeSinceLastRecovery > 5000) {
    console.log(`HLS media error for ${camId}, recovering... (attempt ${hls.mediaRecoveryCount + 1}/3)`);
    hls.lastMediaRecovery = now;
    hls.mediaRecoveryCount++;
    hls.recoverMediaError();
}
```

## Testing

### Remote Access (via recorder.itagenten.no)
1. Open `https://recorder.itagenten.no` in your browser
2. You should see:
   - Console log: `Access mode: REMOTE (using HLS - WebRTC blocked by Cloudflare tunnel)`
   - Console log: `Using HLS (IS_REMOTE: true, ...)`
   - Stable, continuous video playback without blinking
   - Stream mode automatically set to "Stable (~4s latency)"

### Local Access (via 192.168.1.24:8000)
1. Open `http://192.168.1.24:8000` in your browser (when on the same network as R58)
2. You should see:
   - Console log: `Access mode: LOCAL (using WebRTC with HLS fallback)`
   - Console log: `Attempting WebRTC connection (local access)`
   - Ultra-low latency WebRTC streams (<200ms)
   - Stream mode defaults to "Balanced (~2s latency)"

## Expected Behavior

### Remote Access (Cloudflare Tunnel)
- **Protocol**: HLS only (WebRTC disabled)
- **Latency**: ~4-6 seconds (stable mode)
- **Stability**: Very stable, no blinking
- **Buffering**: Large buffers to handle network variability

### Local Access (Direct)
- **Protocol**: WebRTC (with HLS fallback)
- **Latency**: <200ms (WebRTC) or ~2s (HLS fallback)
- **Stability**: Excellent
- **Quality**: Full resolution, hardware-accelerated H.264

## Key Changes Summary
1. ✅ WebRTC disabled for remote access (only works locally)
2. ✅ Automatic "stable" mode for remote access
3. ✅ Increased back buffer from 30s to 90s
4. ✅ Added explicit timeout and retry settings
5. ✅ Increased error recovery cooldowns (2-3s → 5s)
6. ✅ Increased player recreation timeout (5s → 10s)
7. ✅ Let hls.js handle fragment/level retries internally (don't force `startLoad()`)

## Deployment
```bash
cd /opt/preke-r58-recorder
git pull origin feature/remote-access-v2
sudo systemctl restart preke-recorder
```

Status: ✅ **DEPLOYED** - December 22, 2025, 01:13 UTC

## Notes
- **WebRTC over Cloudflare tunnel is not possible** - This is a fundamental limitation of Cloudflare tunnels, which only support HTTP/HTTPS (TCP) traffic, not WebRTC (UDP).
- **HLS is the correct solution for remote access** - With the improved stable configuration, HLS provides reliable streaming over the internet with acceptable latency (~4-6s).
- **Local access still uses WebRTC** - When accessing the R58 directly on the local network (e.g., `http://192.168.1.24:8000`), WebRTC is used for ultra-low latency.
- **Stream mode can be manually changed** - Users can still manually select "Low Latency" or "Balanced" modes via the UI dropdown, but "Stable" is recommended for remote access.

