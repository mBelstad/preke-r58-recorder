# VDO.ninja Mixer HDMI Ingest Diagnosis

**Date**: December 25, 2025  
**Status**: 🔍 DIAGNOSED - Ready to Fix

---

## Problem Summary

The VDO.ninja mixer is not showing HDMI camera streams. Both the director view and mixer show 0 connected guests.

---

## System Status

### ✅ Services Running
- **MediaMTX**: Active on ports 8554 (RTSP), 8889 (WHEP), 8888 (HLS), 1935 (RTMP)
- **VDO.ninja Signaling**: Active on port 8443 (HTTPS/WSS)
- **preke-recorder**: Active (camera ingest service)
- **raspberry.ninja publishers**: Active (3 services)

### 🔍 Findings

#### 1. raspberry.ninja Publishers Issue
- **Status**: Running but not successfully connecting
- **Evidence**: 
  - Processes are alive (PIDs 554894, 554895, 554896)
  - Logs show "Received interrupt signal" immediately after connecting
  - Signaling server shows connections opening/closing but no message traffic
  - Director view shows 0 guests

**Root Cause**: The raspberry.ninja publishers are connecting to the signaling server but something is causing them to disconnect immediately. This could be:
- Conflict with preke-recorder using the same video devices
- Signaling protocol mismatch
- Authentication/room joining issue

#### 2. MediaMTX Approach
- **Status**: MediaMTX is running and has WHEP endpoints available
- **Evidence**:
  - `curl http://localhost:8889/cam0/whep` returns 405 (endpoint exists)
  - preke-recorder is active and should be publishing to MediaMTX
  - WHEP endpoints are accessible

**Issue**: The `&mediamtx=` parameter approach requires:
1. Active camera streams in MediaMTX
2. Proper URL parameter passing (currently being stripped by VDO.ninja)
3. CORS headers (should be working via nginx)

---

## Two Possible Approaches

### Option A: Fix raspberry.ninja Publishers (Original Approach)
**Flow**: HDMI → raspberry.ninja → VDO.ninja signaling → mixer

**Required Fixes**:
1. Stop preke-recorder to free video devices
2. Restart raspberry.ninja publishers
3. Verify they stay connected
4. Test director view

**Pros**: Native VDO.ninja peer-to-peer, low latency
**Cons**: Complex signaling, device conflicts

### Option B: Use MediaMTX + WHEP (Documented Working Approach)
**Flow**: HDMI → preke-recorder → MediaMTX → WHEP → VDO.ninja mixer

**Required Fixes**:
1. Stop raspberry.ninja publishers
2. Ensure preke-recorder is publishing to MediaMTX
3. Use mixer URL with `&mediamtx=r58-mediamtx.itagenten.no`
4. Verify WHEP streams are accessible

**Pros**: Stable, proven architecture, works remotely
**Cons**: Slightly higher latency than P2P

---

## Recommended Fix: Option B (MediaMTX + WHEP)

This approach was documented as working in `MEDIAMTX_INTEGRATION_COMPLETE.md`.

### Step 1: Stop Conflicting Services
```bash
sudo systemctl stop ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3
sudo systemctl disable ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3
```

### Step 2: Verify preke-recorder is Streaming
```bash
sudo systemctl status preke-recorder
curl -I http://localhost:8889/cam0/whep
curl -I http://localhost:8889/cam2/whep
curl -I http://localhost:8889/cam3/whep
```

### Step 3: Test WHEP Access Remotely
```bash
curl -I https://r58-mediamtx.itagenten.no/cam0/whep
```

### Step 4: Use Mixer with MediaMTX Parameter
**Local URL**:
```
https://192.168.1.24:8443/mixer?room=r58studio&mediamtx=192.168.1.24:8889
```

**Remote URL**:
```
https://r58-vdo.itagenten.no/mixer?room=r58studio&mediamtx=r58-mediamtx.itagenten.no
```

### Step 5: Test Director View
```
https://r58-vdo.itagenten.no/?director=r58studio&mediamtx=r58-mediamtx.itagenten.no
```

---

## Expected Results

After implementing Option B:
1. Director view should show 3 camera tiles (cam0, cam2, cam3)
2. Mixer should be able to add cameras as WHEP sources
3. Video should play in browser
4. Works both locally and remotely

---

## Next Actions

1. ✅ Stop raspberry.ninja publishers
2. ✅ Verify MediaMTX streams
3. ✅ Test WHEP endpoints
4. ✅ Test mixer with `&mediamtx=` parameter
5. ✅ Document working configuration

