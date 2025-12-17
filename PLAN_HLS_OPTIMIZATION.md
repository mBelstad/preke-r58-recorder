# Plan: HLS Optimization and Video Synchronization

## User Requirements
- **Latency**: Sub-1-second (keep low-latency mode)
- **Sync**: Approximate sync (±1 second drift allowed, smooth playback)
- **UI Toggle**: Yes, add mode selector
- **cam3 Issue**: 4K source (others are HD) - likely bandwidth/encoding bottleneck

## Current Issues

1. **Choppy playback** - Video stutters over slow/variable internet connections
2. **cam3 freezing** - 4K source pushing too much data (3840x2160 vs 1920x1080)
3. **Streams out of sync** - Multiple cameras not playing at the same time position

## Root Cause Analysis

### Why Choppy/Freezing Happens

1. **Aggressive LL-HLS settings** in MediaMTX:
   - `hlsSegmentDuration: 100ms` - Very short segments
   - `hlsPartDuration: 50ms` - Very small parts
   - Short segments = more HTTP requests = more susceptible to latency

2. **Aggressive HLS.js settings** in frontend:
   - `lowLatencyMode: true` - Prioritizes latency over stability
   - Buffer sizes still relatively small for high-latency connections

3. **No adaptive bitrate** - Single bitrate (8 Mbps) regardless of connection quality

4. **Encoder settings** - `speed-preset=veryfast` may cause quality issues

### Why Streams Go Out of Sync

1. **Independent HLS players** - Each camera has its own HLS.js instance
2. **Different buffer states** - Each player buffers independently
3. **No synchronization mechanism** - Players don't coordinate playback time
4. **Network variability** - Different segments may arrive at different times

---

## Proposed Solutions

### Phase 1: MediaMTX HLS Optimization (Server-Side)

**Goal**: Make HLS more resilient to network variability

**Changes to `mediamtx.yml`**:
```yaml
# Increase segment duration for better network tolerance
hlsSegmentDuration: 1s      # Was 100ms - larger segments = fewer requests
hlsPartDuration: 200ms      # Was 50ms - still low-latency but more stable
hlsSegmentCount: 10         # Was 7 - more buffer available
```

**Trade-off**: Latency increases from ~700ms to ~2-3s, but stability improves significantly.

### Phase 2: Adaptive HLS.js Configuration (Client-Side)

**Goal**: Detect connection quality and adjust settings

**Implementation**:
1. Add connection quality detection (Network Information API)
2. Create "stability mode" vs "low-latency mode" profiles
3. Auto-switch based on detected conditions

**HLS.js Profiles**:

```javascript
// Low-latency mode (good connection)
const lowLatencyConfig = {
    lowLatencyMode: true,
    maxBufferLength: 2,
    liveSyncDurationCount: 2,
    // ... current settings
};

// Stability mode (poor connection)
const stabilityConfig = {
    lowLatencyMode: false,       // Disable LL-HLS
    maxBufferLength: 10,         // 10 seconds buffer
    maxMaxBufferLength: 30,      // Up to 30 seconds
    liveSyncDurationCount: 5,    // Sync to 5 segments behind live
    liveMaxLatencyDurationCount: 10,
    maxStarvationDelay: 4,
    maxLoadingDelay: 4,
};
```

### Phase 3: Stream Synchronization

**Goal**: Keep all camera streams in sync

**Approach A: Shared Timeline (Recommended)**
- Use `video.currentTime` to align all players
- Designate one stream as "master"
- Other streams adjust to match master's position

**Implementation**:
```javascript
class SyncManager {
    constructor() {
        this.masterCam = null;
        this.players = {};
        this.syncInterval = null;
    }
    
    setMaster(camId) {
        this.masterCam = camId;
    }
    
    startSync() {
        this.syncInterval = setInterval(() => {
            if (!this.masterCam) return;
            const masterTime = this.players[this.masterCam].video.currentTime;
            
            for (const [camId, player] of Object.entries(this.players)) {
                if (camId === this.masterCam) continue;
                
                const drift = player.video.currentTime - masterTime;
                if (Math.abs(drift) > 0.5) { // More than 500ms drift
                    // Adjust playback rate or seek
                    if (drift > 0) {
                        player.video.playbackRate = 0.95; // Slow down
                    } else {
                        player.video.playbackRate = 1.05; // Speed up
                    }
                } else {
                    player.video.playbackRate = 1.0;
                }
            }
        }, 1000);
    }
}
```

**Approach B: Buffer-Based Sync**
- Sync based on buffer position rather than playback time
- Use HLS.js events to coordinate

### Phase 4: Encoder Optimization

**Goal**: Better quality at same bitrate, more stable stream

**Changes to ingest pipeline**:
```python
# Current:
encoder_str = f"x264enc tune=zerolatency bitrate={bitrate} speed-preset=veryfast key-int-max=30"

# Optimized:
encoder_str = (
    f"x264enc tune=zerolatency bitrate={bitrate} "
    f"speed-preset=medium "      # Better quality than veryfast
    f"key-int-max=60 "           # Keyframe every 2s (was 1s)
    f"bframes=0 "                # No B-frames for lower latency
    f"sliced-threads=true "      # Better multi-threading
    f"aud=true "                 # Access unit delimiters for HLS
)
```

### Phase 5: Fallback and Recovery

**Goal**: Automatically recover from freezes

**Implementation**:
1. **Freeze detection** - Monitor video time progression
2. **Auto-restart** - Reload HLS source if frozen >3 seconds
3. **Stall recovery** - Already implemented, enhance with more aggressive recovery

```javascript
// Freeze detection
let lastTime = {};
setInterval(() => {
    for (const [camId, player] of Object.entries(hlsPlayers)) {
        const video = player.media;
        const currentTime = video.currentTime;
        
        if (lastTime[camId] === currentTime && !video.paused) {
            // Video is frozen
            console.warn(`${camId} appears frozen, restarting...`);
            player.destroy();
            startHLSPreview(video, camId, placeholder);
        }
        lastTime[camId] = currentTime;
    }
}, 3000);
```

---

## Implementation Order

### Quick Wins (Do First)
1. **Increase MediaMTX segment duration** - Simple config change, big impact
2. **Add stability mode HLS config** - Fallback for poor connections
3. **Add freeze detection/recovery** - Prevent permanent freezes

### Medium Effort
4. **Connection quality detection** - Auto-switch between modes
5. **Stream synchronization** - Keep cameras aligned

### Future Enhancements
6. **Adaptive bitrate streaming** - Multiple quality levels
7. **WebRTC option for local** - Bypass HLS entirely on LAN

---

## Configuration Options

### User-Selectable Modes

Add UI toggle for users to choose:

| Mode | Latency | Stability | Use Case |
|------|---------|-----------|----------|
| Ultra-Low | ~1s | Low | Local/LAN access |
| Balanced | ~3s | Medium | Good internet |
| Stable | ~6s | High | Poor/mobile internet |

---

## Testing Checklist

After implementation:
1. [ ] Test on slow connection (throttle to 3G)
2. [ ] Verify all 3 cameras stay in sync
3. [ ] Confirm no freezes after 10+ minutes
4. [ ] Test recovery from network dropout
5. [ ] Measure actual latency in each mode

---

## Questions for User

Before implementing, please clarify:

1. **Latency tolerance**: Is 3-5 second delay acceptable for stability, or do you need sub-1-second latency?

2. **Sync priority**: Should streams be perfectly synced (may require occasional seek/jump) or is approximate sync okay?

3. **UI controls**: Do you want a user-visible toggle to switch between "Low Latency" and "Stable" modes?

4. **cam3 specifically**: Is cam3 always the one that freezes, or does it vary? (This might indicate a device-specific issue)

