# Stable Mode Improvements

**Date:** December 17, 2025  
**Branch:** `always-on-ingest`  
**Commit:** b923eae

## Changes Made

### 1. Enhanced "Stable" Mode for Bad Connections

Updated HLS buffer configuration to be much more aggressive:

| Setting | Before | After | Impact |
|---------|--------|-------|--------|
| `maxBufferLength` | 10s | 30s | 3x larger buffer |
| `maxMaxBufferLength` | 30s | 90s | 3x larger max buffer |
| `backBufferLength` | 5s | 10s | 2x back buffer |
| `maxStarvationDelay` | 4s | 8s | 2x tolerance |
| `maxLoadingDelay` | 4s | 8s | 2x tolerance |
| `liveSyncDurationCount` | 5 | 10 | 2x sync duration |
| `liveMaxLatencyDurationCount` | 10 | 20 | 2x max latency |

**Result:** Stable mode now tolerates ~10s latency with up to 90s of buffering for very poor connections.

### 2. Improved Freeze Detection

Enhanced the freeze detection system with:

- **Consecutive freeze tracking**: Counts how many times a stream freezes in a row
- **Escalating recovery**:
  - 1st freeze: Gentle recovery (`recoverMediaError()`)
  - 2nd+ freeze: Full HLS restart (destroy and recreate player)
- **Faster detection**: Check interval reduced from 3s to 2s
- **Better logging**: Shows freeze count for debugging

```javascript
// Example freeze detection output
cam2 appears frozen (time stuck at 5.2, count: 1), attempting recovery...
cam2 appears frozen (time stuck at 5.2, count: 2), doing full HLS restart...
cam2 recovered, resetting freeze counter
```

### 3. UI Updates

- Updated dropdown text: "Stable (~10s)" (was "~5s")
- Updated hint text: "Most stable for bad connections (~10s delay, large buffer)"

## Testing Results

### Stream Stability
- ✅ cam1 (HD): Stable with new settings
- ✅ cam2 (4K): Some HLS timing errors but auto-recovers
- ✅ cam3 (HD): Stable with new settings
- ✅ Recording works simultaneously with preview

### Freeze Detection
- Monitoring active, checking every 2 seconds
- Will automatically restart frozen streams after 2 consecutive freezes
- Logs show recovery attempts in console

## When to Use Each Mode

### Low Latency (~1s)
- **Use for**: Local network, fast internet
- **Buffer**: Minimal (1-2s)
- **Trade-off**: May stutter on slow connections

### Balanced (~2s)
- **Use for**: Most remote connections
- **Buffer**: Moderate (2-4s)
- **Trade-off**: Good balance of latency and stability

### Stable (~10s)
- **Use for**: Poor/unreliable connections, high packet loss
- **Buffer**: Large (30-90s)
- **Trade-off**: High latency but very stable

## Technical Details

### Buffer Strategy
The "Stable" mode now uses a progressive buffering strategy:
1. Initial buffer: 30s (`maxBufferLength`)
2. Can grow to: 90s (`maxMaxBufferLength`)
3. Back buffer: 10s (keeps old segments)
4. Allows 2s gaps in stream (`maxBufferHole`)

### Freeze Recovery Strategy
1. **Detection**: Video `currentTime` not advancing for 2+ seconds
2. **First attempt**: `hls.recoverMediaError()` (gentle)
3. **Second attempt**: Full player restart (aggressive)
4. **Reset**: Counter resets when video progresses

## Known Behavior

### cam2 (4K Source)
- Still shows debug-level HLS errors due to:
  - Higher bitrate (4K scaled to 1080p)
  - More demanding on network
  - Low-latency HLS timing sensitivity
- **Mitigation**: Freeze detection will auto-restart if it actually freezes
- **Workaround**: Use "Stable" mode for maximum buffering

### HLS Errors vs Freezes
- **HLS Errors** (debug level): Normal for low-latency HLS, stream continues
- **Freezes**: Video `currentTime` stops advancing, triggers recovery

## Future Improvements

1. **Adaptive Bitrate**: Multiple quality levels per camera
2. **Hardware Encoding**: Use RK3588 VPU to reduce CPU load
3. **Network Monitoring**: Auto-switch modes based on detected bandwidth
4. **Per-Camera Settings**: Different modes for different cameras

