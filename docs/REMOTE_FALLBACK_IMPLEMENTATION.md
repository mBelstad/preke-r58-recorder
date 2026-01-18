# Remote Fallback Implementation Summary

**Date**: January 18, 2026  
**Status**: ✅ Implemented

## Overview

This document summarizes the implementation of intelligent remote fallback mechanisms to prevent network crashes on poor internet connections and restore functionality after device wipe.

---

## Problems Solved

### 1. Network Crashes on Poor Connections
**Root Cause**: 
- MediaMTX advertised 3 IPs simultaneously, causing browsers to attempt ICE connections to all of them
- High bandwidth consumption (12-32 Mbps) with no adaptation
- Aggressive reconnection without rate limiting

**Solution**:
- Removed multiple host candidates from MediaMTX ICE configuration
- Added connection quality monitoring with automatic HLS fallback
- Implemented progressive camera loading for poor connections

### 2. Fallback Not Working After Device Wipe
**Root Cause**: Services may not be properly configured or running

**Solution**:
- Created verification scripts to check all services
- Documented expected configurations

---

## Implementation Details

### Phase 1: Service Verification

**Files Created**:
- `scripts/verify-r58-services.sh` - Checks all R58 services
- `scripts/verify-vps-services.sh` - Checks VPS services

**Usage**:
```bash
# Verify R58 services
./connect-r58-frp.sh "bash -s" < scripts/verify-r58-services.sh

# Verify VPS services
ssh root@65.109.32.111 "bash -s" < scripts/verify-vps-services.sh
```

### Phase 2: MediaMTX ICE Configuration Fix

**File Modified**: `mediamtx.yml`

**Changes**:
- Removed `webrtcAdditionalHosts` (was causing ICE candidate flooding)
- Set `webrtcICEHostNAT1To1IPs` to only VPS IP (for FRP relay case)
- Direct connections (LAN/Tailscale) use normal ICE discovery via STUN

**Impact**: Reduces connection attempts from 3 simultaneous to 1, preventing network flooding.

### Phase 3: HLS Fallback Implementation

**Files Modified**:
- `packages/frontend/src/lib/whepConnectionManager.ts`
- `packages/frontend/src/components/shared/InputPreview.vue`

**Features Added**:
1. **Connection Quality Monitoring**:
   - Tracks RTT, packet loss, and jitter via WebRTC stats
   - Updates every 5 seconds
   - Quality levels: excellent, good, fair, poor, very-poor

2. **Automatic HLS Fallback**:
   - Switches to HLS when RTT > 500ms OR packet loss > 5% for 10+ seconds
   - HLS provides stable playback at higher latency
   - Manual fallback button available in UI

3. **HLS.js Integration**:
   - Added `hls.js` dependency
   - Supports both HLS.js (Chrome/Firefox) and native HLS (Safari)

### Phase 4: Connection Quality Display

**UI Enhancements**:
- Connection type indicator (P2P/RELAY/HLS) with color coding
- Real-time RTT display
- Quality-based color coding (green/yellow/red)
- Tooltip showing full metrics (RTT, loss, jitter)

### Phase 5: Bandwidth Management

**Files Modified**:
- `config.yml` - Added adaptive bitrate settings
- `packages/frontend/src/lib/progressiveLoader.ts` - New progressive loading system

**Features**:
1. **Adaptive Bitrate Settings** (per camera):
   - `preview_bitrate: 4000` - Normal (P2P connections)
   - `preview_bitrate_low: 2000` - Poor connections (FRP/DERP)
   - `preview_bitrate_min: 1000` - Minimum viable (HLS fallback)

2. **Progressive Camera Loading**:
   - Loads cameras one at a time on poor connections
   - Waits 2 seconds for each camera to stabilize
   - Prevents network overload

---

## Fallback Chain

The system now implements a complete fallback chain:

```
1. Tailscale P2P (2-20ms) → Direct connection, 4 Mbps
   ↓ (if fails)
2. Tailscale DERP (50-200ms) → Relay, 2 Mbps
   ↓ (if fails)
3. FRP Tunnel (100-300ms) → VPS relay, 1.5 Mbps
   ↓ (if quality poor)
4. HLS Fallback → Stable but higher latency, 1 Mbps
```

---

## Usage

### Automatic Fallback

The system automatically:
- Monitors connection quality every 5 seconds
- Switches to HLS if quality is poor for 10+ seconds
- Uses progressive loading on relay connections

### Manual Controls

**Force HLS Fallback**:
- Click "Use HLS" button in error overlay
- Or call `forceHlsFallback(cameraId)` from console

**Retry WHEP**:
- Click "Retry WHEP" button in error overlay
- Or call `forceReconnect(cameraId)` from console

### Progressive Loading

```typescript
import { loadCamerasProgressive, shouldUseProgressiveLoading } from '@/lib/progressiveLoader'

// Check if progressive loading is recommended
const useProgressive = shouldUseProgressiveLoading(connectionType)

// Load cameras
await loadCamerasProgressive(['cam0', 'cam2', 'cam3'], useProgressive)
```

---

## Configuration

### MediaMTX (`mediamtx.yml`)

```yaml
# ICE configuration - only VPS IP for FRP relay
webrtcICEHostNAT1To1IPs: ["65.109.32.111"]
# Direct connections use normal STUN discovery
```

### Camera Bitrates (`config.yml`)

```yaml
cameras:
  cam0:
    preview_bitrate: 4000      # Normal
    preview_bitrate_low: 2000  # Poor connections
    preview_bitrate_min: 1000  # HLS fallback
```

---

## Testing

### Test Fallback Chain

1. **P2P Connection**: Connect via Tailscale, verify "P2P" indicator
2. **Relay Connection**: Connect via FRP, verify "RELAY" indicator
3. **HLS Fallback**: Simulate poor connection (throttle network), verify automatic HLS switch
4. **Progressive Loading**: Connect via FRP with multiple cameras, verify sequential loading

### Verify Services

```bash
# R58
./connect-r58-frp.sh "bash -s" < scripts/verify-r58-services.sh

# VPS
ssh root@65.109.32.111 "bash -s" < scripts/verify-vps-services.sh
```

---

## Troubleshooting

### Network Still Crashing

1. **Check MediaMTX config**: Ensure `webrtcAdditionalHosts` is removed
2. **Check connection quality**: Look for RTT > 500ms in UI
3. **Force HLS**: Use manual HLS fallback button
4. **Reduce cameras**: Load fewer cameras simultaneously

### HLS Not Working

1. **Check HLS.js**: Verify `hls.js` is installed (`npm list hls.js`)
2. **Check HLS URL**: Verify MediaMTX HLS endpoint is accessible
3. **Browser support**: Safari uses native HLS, others use HLS.js

### Services Not Running

1. **Run verification script**: `./connect-r58-frp.sh "bash -s" < scripts/verify-r58-services.sh`
2. **Check logs**: `journalctl -u preke-recorder -f`
3. **Restart services**: `sudo systemctl restart preke-recorder mediamtx frpc`

---

## Future Enhancements

1. **Dynamic Bitrate Adjustment**: Change preview bitrate at runtime based on connection quality
2. **Multi-bitrate HLS**: Serve multiple quality levels for adaptive streaming
3. **Connection Pre-warming**: Pre-establish Tailscale P2P before loading video
4. **Bandwidth Estimation**: Estimate available bandwidth before choosing bitrate

---

## Files Modified

### Backend
- `mediamtx.yml` - ICE configuration fix
- `config.yml` - Adaptive bitrate settings

### Frontend
- `packages/frontend/src/lib/whepConnectionManager.ts` - Quality monitoring, HLS fallback
- `packages/frontend/src/components/shared/InputPreview.vue` - HLS support, quality display
- `packages/frontend/src/lib/progressiveLoader.ts` - Progressive loading system
- `packages/frontend/package.json` - Added hls.js dependency

### Scripts
- `scripts/verify-r58-services.sh` - R58 service verification
- `scripts/verify-vps-services.sh` - VPS service verification

---

## Related Documentation

- [REMOTE_ACCESS.md](../REMOTE_ACCESS.md) - Remote access guide
- [docs/TAILSCALE_P2P_INTEGRATION.md](TAILSCALE_P2P_INTEGRATION.md) - Tailscale setup
- [docs/architecture/WEBRTC_CONNECTIVITY.md](architecture/WEBRTC_CONNECTIVITY.md) - WebRTC architecture

---

**Status**: ✅ All features implemented and ready for testing
