# Phase 2: WebRTC Switcher Implementation

## Goal

Add ultra-low latency WebRTC support to switcher.html for camera previews and program monitor, replacing the current HLS-based preview system.

## Current State Analysis

### Existing Implementation (HLS-based)

- **switcher.html**: 3313 lines, uses HLS.js for all video streams
- **Camera previews**: 4 compact inputs using HLS (`cam0`, `cam1`, `cam2`, `cam3`)
- **Program monitor**: Uses HLS (`mixer_program`)
- **Latency**: 2-5 seconds (HLS typical)
- **Video elements**: 
- `#previewVideo` (line 1601) - currently unused
- `#programVideo` (line 1612) - shows mixer output
- `.compact-input video` - 4 camera previews

### Reference Implementation (index.html)

- Has working WebRTC implementation with HLS fallback
- Uses WHIPClient for WebRTC playback
- Graceful fallback to HLS if WebRTC unavailable

## Implementation Plan

### Phase 2.1: Add WebRTC Client Library ✅

**Files to modify:**

- `src/static/switcher.html`

**Changes:**

1. Add WHIPClient library (same as index.html uses)
2. Keep HLS.js as fallback

**Code to add:**

```html
<!-- After HLS.js script tag (line ~1837) -->
<script src="https://cdn.jsdelivr.net/npm/@eyevinn/whip-web-client@2/dist/whip-web-client.min.js"></script>
```



### Phase 2.2: Create WebRTC Stream Manager

**New JavaScript functions to add:**

```javascript
// WebRTC configuration
const webrtcConfig = {
    enabled: true,
    fallbackToHLS: true,
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
};

// WebRTC client instances
let webrtcClients = {};

// Load stream with WebRTC (primary) and HLS (fallback)
async function loadStreamWithWebRTC(videoElement, streamPath, instanceId) {
    if (!videoElement) return;
    
    // Try WebRTC first
    if (webrtcConfig.enabled) {
        try {
            const whepUrl = getWHEPUrl(streamPath);
            const client = new WHIPClient.WHEPClient({
                endpoint: whepUrl,
                iceServers: webrtcConfig.iceServers
            });
            
            await client.connect();
            const stream = await client.getMediaStream();
            videoElement.srcObject = stream;
            
            // Store client for cleanup
            webrtcClients[instanceId] = client;
            
            console.log(`WebRTC connected for ${streamPath}`);
            return true;
        } catch (error) {
            console.warn(`WebRTC failed for ${streamPath}, falling back to HLS:`, error);
        }
    }
    
    // Fallback to HLS
    if (webrtcConfig.fallbackToHLS) {
        const hlsUrl = getHLSUrl(streamPath);
        loadHLS(videoElement, hlsUrl, instanceId);
    }
}

// Get WHEP URL for WebRTC
function getWHEPUrl(streamPath) {
    if (window.location.hostname === 'localhost') {
        return `${API_BASE}/webrtc/${streamPath}/whep`;
    } else {
        return `http://${HOSTNAME}:8889/${streamPath}/whep`;
    }
}

// Cleanup WebRTC client
function cleanupWebRTCClient(instanceId) {
    if (webrtcClients[instanceId]) {
        try {
            webrtcClients[instanceId].disconnect();
        } catch (e) {
            console.warn(`Error disconnecting WebRTC client ${instanceId}:`, e);
        }
        delete webrtcClients[instanceId];
    }
}
```



### Phase 2.3: Update Camera Preview Loading

**Function to modify:** `initCompactInputs()` (around line 2285)**Changes:**

```javascript
// OLD:
loadHLS(video, hlsUrl, `compact-input-${i}`);

// NEW:
loadStreamWithWebRTC(video, `cam${i}`, `compact-input-${i}`);
```



### Phase 2.4: Update Program Monitor Loading

**Function to modify:** `updateMixerStatus()` (around line 2512)**Changes:**

```javascript
// OLD:
loadHLS(video, hlsUrl, 'program');

// NEW:
loadStreamWithWebRTC(video, 'mixer_program', 'program');
```



### Phase 2.5: Update Stream Reset Logic

**Function to modify:** `resetAllStreams()`**Changes:**

```javascript
function resetAllStreams() {
    console.log('Resetting all streams...');
    
    // Cleanup WebRTC clients
    Object.keys(webrtcClients).forEach(id => {
        cleanupWebRTCClient(id);
    });
    
    // Cleanup HLS instances
    Object.keys(hlsInstances).forEach(key => {
        if (hlsInstances[key]) {
            hlsInstances[key].destroy();
            delete hlsInstances[key];
        }
    });
    
    // Reload streams
    initCompactInputs();
    updateMixerStatus();
}
```



### Phase 2.6: Add WebRTC Status Indicator

**UI Enhancement:**Add visual indicator showing WebRTC vs HLS:

```html
<!-- In toolbar area -->
<div class="stream-protocol-indicator">
    <span id="protocolBadge" class="protocol-badge">HLS</span>
</div>
```



```css
.protocol-badge {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
}

.protocol-badge.webrtc {
    background: #10b981;
    color: white;
}

.protocol-badge.hls {
    background: #f59e0b;
    color: white;
}
```



```javascript
function updateProtocolBadge(protocol) {
    const badge = document.getElementById('protocolBadge');
    if (badge) {
        badge.textContent = protocol.toUpperCase();
        badge.className = `protocol-badge ${protocol}`;
    }
}
```



### Phase 2.7: Add WebRTC Toggle (Optional)

**UI Control:**

```html
<label class="control-label">
    <input type="checkbox" id="webrtcToggle" checked>
    Enable WebRTC (Ultra-low latency)
</label>
```



```javascript
document.getElementById('webrtcToggle')?.addEventListener('change', (e) => {
    webrtcConfig.enabled = e.target.checked;
    resetAllStreams();
});
```



## Testing Plan

### Test 1: WebRTC Camera Previews

1. Open switcher.html
2. Verify all 4 camera previews load
3. Check browser console for "WebRTC connected for cam0/1/2/3"
4. Measure latency (should be <200ms)

### Test 2: WebRTC Program Monitor

1. Start mixer: `curl -X POST http://r58.itagenten.no/api/mixer/start`
2. Check program monitor loads with WebRTC
3. Verify ultra-low latency

### Test 3: HLS Fallback

1. Disable WebRTC in code temporarily
2. Verify HLS fallback works
3. Re-enable WebRTC

### Test 4: Stream Reconnection

1. Stop/start mixer
2. Click refresh button
3. Verify streams reconnect properly

### Test 5: Multiple Browsers

1. Open switcher in 2-3 browsers simultaneously
2. Verify all get WebRTC streams
3. Check for connection issues

## Expected Results

### Performance Improvements

- **Latency**: 2-5s (HLS) → <200ms (WebRTC)
- **Switching responsiveness**: Immediate feedback
- **CPU usage**: Similar or slightly lower
- **Network**: More efficient (no HLS segments)

### User Experience

- Near-instant preview updates
- Professional switching feel
- Smooth scene transitions
- Real-time feedback

## Rollback Plan

If WebRTC causes issues:

1. Set `webrtcConfig.enabled = false`
2. Falls back to HLS automatically
3. No code changes needed

## Dependencies

### Required

- ✅ MediaMTX WebRTC support (already configured)
- ✅ Camera streams available (cam0-3)
- ✅ Mixer output stream (mixer_program)

### Optional

- Browser WebRTC support (all modern browsers)
- STUN server access (using Google's public STUN)

## Safety Measures

1. **Graceful fallback**: Always fall back to HLS if WebRTC fails
2. **Error handling**: Catch and log all WebRTC errors
3. **Cleanup**: Properly disconnect WebRTC clients on stream reset
4. **Backward compatible**: HLS code remains intact

## Implementation Order

1. ✅ Add WHIPClient library
2. ✅ Create WebRTC helper functions
3. ✅ Update camera preview loading
4. ✅ Update program monitor loading
5. ✅ Update reset logic
6. ✅ Add status indicator
7. ✅ Test thoroughly
8. ✅ Deploy to R58

## Success Criteria

- [ ] All 4 camera previews load via WebRTC
- [ ] Program monitor loads via WebRTC
- [ ] Latency < 200ms measured
- [ ] HLS fallback works if WebRTC unavailable
- [ ] No console errors
- [ ] Smooth switching experience
- [ ] Multiple browsers supported

## Notes

- Keep existing HLS code intact for fallback
- Use same WebRTC library as index.html for consistency
- Test with multiple browsers (Chrome, Firefox, Safari)
