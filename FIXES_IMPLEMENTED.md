# VDO.ninja and MediaMTX Fixes - Implementation Complete

**Date**: December 21, 2025  
**Status**: ✅ All fixes deployed and ready for testing

---

## Summary

Fixed two critical issues preventing proper WebRTC operation:

1. **MediaMTX WebRTC Encryption** - Enabled DTLS encryption for browser compatibility
2. **VDO.ninja Signaling Server** - Implemented proper room-based message routing

---

## Changes Implemented

### 1. MediaMTX WebRTC Encryption (✅ Complete)

**Problem**: `webrtcEncryption: no` caused browsers to silently fail WebRTC connections, falling back to HLS with 1-3 second latency.

**Solution**:
- Generated self-signed SSL certificate at `/opt/mediamtx/server.key` and `/opt/mediamtx/server.crt`
- Updated `/opt/mediamtx/mediamtx.yml`:
  ```yaml
  webrtcEncryption: yes
  webrtcServerKey: /opt/mediamtx/server.key
  webrtcServerCert: /opt/mediamtx/server.crt
  ```
- Restarted MediaMTX service

**Expected Result**: Recorder interface should now use WebRTC (WHEP) for local viewing with sub-second latency.

---

### 2. VDO.ninja Signaling Server (✅ Complete)

**Problem**: Simple broadcast relay didn't understand VDO.ninja's room-based protocol. Publishers connected but director never saw them.

**Solution**: Rewrote `/opt/vdo-signaling/vdo-server.js` with:
- Room tracking (Map of roomId → Set of connections)
- Parse `joinroom` requests to extract roomId
- Route messages only within the same room
- Handle VDO.ninja message types: `joinroom`, `request`, `offer`, `answer`, `candidate`

**Verification**: Server logs now show:
```
[2025-12-21T23:13:24.553Z] Added k0rga9 to room 61692853ab4b7505 (room size: 1)
[2025-12-21T23:13:24.554Z] Broadcasted joinroom to 0 peers in room 61692853ab4b7505
```

All 3 camera publishers successfully joined room `61692853ab4b7505` (hashed "r58studio").

---

### 3. Frontend WebRTC Debugging (✅ Complete)

**Problem**: No visibility into why WebRTC was failing or falling back to HLS.

**Solution**: Added comprehensive logging to `src/static/index.html`:
- Protocol selection logging (WebRTC vs HLS)
- WHEP request/response tracking
- ICE candidate exchange logging
- Connection state monitoring

**Example logs**:
```javascript
🎥 [cam0] Attempting WebRTC connection (local access)
🎥 [cam0] WebRTC URL: http://192.168.1.24:8889/cam0/whep
🔌 [cam0] Creating RTCPeerConnection
🔌 [cam0] Creating WebRTC offer...
🔌 [cam0] Sending WHEP request to: http://192.168.1.24:8889/cam0/whep
🔌 [cam0] WHEP response status: 200
✅ [cam0] Received SDP answer, setting remote description...
✅ [cam0] WebRTC preview started (ultra-low latency)
```

---

## Testing Instructions

### Test 1: MediaMTX WebRTC (Local Recorder Interface)

1. **Access recorder interface** (from on-site Windows PC):
   ```
   https://recorder.itagenten.no
   ```

2. **Open browser console** (F12) and look for logs:
   - Should see: `🎥 [cam0] Attempting WebRTC connection (local access)`
   - Should see: `✅ [cam0] WebRTC preview started (ultra-low latency)`
   - Should NOT see: `📺 [cam0] Using HLS fallback`

3. **Verify latency**:
   - Wave hand in front of camera
   - Latency should be < 500ms (WebRTC)
   - If > 1 second, it's using HLS (fallback)

4. **Check console for errors**:
   - If WHEP fails, you'll see: `❌ [cam0] WebRTC setup failed: ...`
   - Logs will show exact error and automatic HLS fallback

---

### Test 2: VDO.ninja Director View

1. **Access VDO.ninja director** (from on-site Windows PC):
   ```
   https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443
   ```

2. **Expected behavior**:
   - Director page loads
   - 3 camera feeds appear (r58-cam1, r58-cam2, r58-cam3)
   - Can click on feeds to preview
   - Can add to scenes

3. **Check VDO.ninja server logs** (if issues):
   ```bash
   ./connect-r58.sh "sudo journalctl -u vdo-ninja -f"
   ```
   
   Should see:
   ```
   [timestamp] Connection <id> joined room 61692853ab4b7505
   [timestamp] Relayed offer from <id1> to 1 peers in room 61692853ab4b7505
   [timestamp] Relayed answer from <id2> to 1 peers in room 61692853ab4b7505
   ```

---

## Troubleshooting

### MediaMTX WebRTC Not Working

**Symptoms**: Still seeing HLS fallback in console logs

**Check**:
1. MediaMTX encryption enabled:
   ```bash
   ./connect-r58.sh "grep webrtcEncryption /opt/mediamtx/mediamtx.yml"
   ```
   Should show: `webrtcEncryption: yes`

2. Certificate files exist:
   ```bash
   ./connect-r58.sh "ls -la /opt/mediamtx/server.*"
   ```

3. MediaMTX running:
   ```bash
   ./connect-r58.sh "systemctl status mediamtx"
   ```

4. WHEP endpoint responding:
   ```bash
   ./connect-r58.sh "curl -I http://localhost:8889/cam0/whep"
   ```
   Should return: `HTTP/1.1 405 Method Not Allowed` (HEAD not allowed, but endpoint exists)

---

### VDO.ninja Cameras Not Visible

**Symptoms**: Director loads but no camera feeds

**Check**:
1. Publishers running:
   ```bash
   ./connect-r58.sh "systemctl status ninja-publish-cam{1..3}"
   ```

2. Publishers connected to signaling server:
   ```bash
   ./connect-r58.sh "sudo journalctl -u vdo-ninja --since '1 minute ago' | grep 'joined room'"
   ```
   Should show 3 connections joining room

3. VDO.ninja server using new code:
   ```bash
   ./connect-r58.sh "sudo journalctl -u vdo-ninja -n 5 | grep 'room-based signaling'"
   ```
   Should show: `VDO.Ninja server started with room-based signaling`

4. Check for WebRTC connection errors in browser console

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        R58 Device                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                │
│  │   MediaMTX   │         │  VDO.ninja   │                │
│  │   (WebRTC)   │         │   Signaling  │                │
│  │              │         │    Server    │                │
│  │ Port: 8889   │         │  Port: 8443  │                │
│  │ WHEP enabled │         │  Room-based  │                │
│  │ DTLS: yes    │         │   routing    │                │
│  └──────┬───────┘         └──────┬───────┘                │
│         │                        │                         │
│         │                        │                         │
│  ┌──────▼────────────────────────▼───────┐                │
│  │     Raspberry Ninja Publishers        │                │
│  │  cam1, cam2, cam3 → room: r58studio   │                │
│  └───────────────────────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                         │
                         │
                         ▼
         ┌───────────────────────────────┐
         │      Browser Clients          │
         ├───────────────────────────────┤
         │                               │
         │  Recorder (Local):            │
         │  → MediaMTX WHEP (WebRTC)     │
         │  → Sub-second latency         │
         │                               │
         │  Director (Local):            │
         │  → VDO.ninja room signaling   │
         │  → See all 3 camera feeds     │
         │                               │
         └───────────────────────────────┘
```

---

## Next Steps

1. **Test locally** - User should test both interfaces from on-site Windows PC
2. **Verify WebRTC** - Check browser console logs to confirm WebRTC (not HLS)
3. **Test VDO.ninja** - Verify all 3 cameras appear in director view
4. **Report results** - Share any errors or issues found

---

## Files Modified

| File | Change |
|------|--------|
| `/opt/mediamtx/mediamtx.yml` | Enabled `webrtcEncryption: yes`, added cert paths |
| `/opt/mediamtx/server.key` | Generated self-signed SSL key |
| `/opt/mediamtx/server.crt` | Generated self-signed SSL certificate |
| `/opt/vdo-signaling/vdo-server.js` | Rewrote with room-based signaling |
| `src/static/index.html` | Added comprehensive WebRTC debugging logs |

---

## Services Restarted

- ✅ MediaMTX (`mediamtx.service`)
- ✅ VDO.ninja (`vdo-ninja.service`)
- ✅ Camera Publishers (`ninja-publish-cam{1..3}.service`)
- ✅ Recorder (`preke-recorder.service`)

All services are running and ready for testing.

