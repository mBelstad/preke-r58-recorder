# VDO.ninja Research Findings

**Date:** December 25, 2025

---

## 🔍 Version Analysis

### Current R58 Versions vs Latest Available:

| Software | R58 Version | Latest | Status |
|----------|-------------|--------|--------|
| **MediaMTX** | v1.5.1 | **v1.15.5** | ❌ **VERY OUTDATED** |
| **VDO.ninja** | ver=4025 (~v25) | **v28.0** | ⚠️ Outdated |
| **raspberry.ninja** | main branch | **v10.0.0** (Dec 18, 2025) | ⚠️ Check |
| **Signaling Server** | Custom | Simple broadcast | ❌ **WRONG** |

---

## 🚨 Critical Finding: Signaling Server Protocol Mismatch

### Official VDO.ninja Websocket Server

**Source:** https://github.com/steveseguin/websocket_server

**The official server is EXTREMELY SIMPLE:**

```javascript
websocketServer.on('connection', (webSocketClient) => {
    webSocketClient.on('message', (message) => {
        // Broadcast to ALL other clients
        websocketServer.clients.forEach(client => {
            if (webSocketClient != client) {
                client.send(message.toString());
            }
        });
    });
});
```

**Key characteristics:**
- ✅ No room filtering
- ✅ No special message handling
- ✅ Just broadcasts EVERYTHING to EVERYONE
- ✅ VDO.ninja clients handle room logic themselves

### Our Custom Signaling Server

**Our server adds:**
- Room filtering
- Publisher/Viewer detection
- Special handling for `joinroom`, `seed`, `play` messages
- UUID tracking

**Problem:** This might be breaking the signaling protocol that raspberry.ninja expects!

---

## 📦 Available Tools & Apps

### 1. VDO.ninja Native WHEP Support

**VDO.ninja can now consume WHEP streams directly:**

```
https://vdo.ninja/?whep=https://yourdomain.com/whep/YourStreamID
```

This means we could potentially:
1. Keep MediaMTX serving WHEP streams
2. Pull them into VDO.ninja mixer using `&whep=` parameter

**BUT:** This requires VDO.ninja v28+ which we don't have.

---

### 2. `&mediamtx=` Parameter

VDO.ninja v28+ has native MediaMTX integration:

```
https://vdo.ninja/?push=streamID&mediamtx=yourdomain.com:8889
```

This makes VDO.ninja push/pull directly to/from MediaMTX without needing raspberry.ninja at all!

---

### 3. Companion Ninja

**Repo:** https://github.com/steveseguin/Companion-Ninja

Remote control of VDO.ninja via HTTP/WebSocket API - useful for automation but doesn't solve our immediate problem.

---

### 4. VDO.ninja Chrome Extension (v1.1.5)

Captures video from web pages and streams via VDO.ninja - not applicable for HDMI input.

---

### 5. Official Signaling Server

**Repo:** https://github.com/steveseguin/websocket_server

The official simple broadcast server that VDO.ninja expects. Our custom one is NOT compatible.

---

## 🎯 Root Cause Analysis

### Why raspberry.ninja + VDO.ninja Doesn't Work:

1. **Signaling Server Mismatch**
   - VDO.ninja expects simple broadcast-all server
   - Our custom server adds room filtering
   - This breaks the peer-to-peer signaling protocol

2. **Version Mismatch**
   - Our VDO.ninja (v25) is old
   - Latest v28 has native MediaMTX integration
   - raspberry.ninja v10 may require newer VDO.ninja

3. **MediaMTX Version**
   - v1.5.1 is ancient (v1.15.5 is current)
   - Missing many bugfixes and features
   - Could affect WHEP/WHIP compatibility

---

## 📋 Recommended Actions

### Option A: Fix Current Setup (Moderate Effort)

1. **Replace signaling server** with official simple broadcast version
2. **Update all software** to latest versions
3. **Test raspberry.ninja** with simple signaling server

### Option B: Use VDO.ninja Native MediaMTX (Recommended)

1. **Update VDO.ninja** to v28+
2. **Update MediaMTX** to v1.15.5
3. **Use `&mediamtx=` parameter** instead of raspberry.ninja
4. **VDO.ninja handles everything** - no need for raspberry.ninja at all!

### Option C: MediaMTX Only (Current Working Solution)

1. Keep using MediaMTX for all streaming
2. Build custom mixer UI (already created: `mediamtx_mixer.html`)
3. Skip VDO.ninja entirely for remote access

---

## 🔧 Update Script Created

A comprehensive update script has been created: `update_r58_software.sh`

This script will:
1. Update MediaMTX from v1.5.1 to v1.15.5
2. Update raspberry.ninja to v10.0.0
3. Update VDO.ninja to latest
4. Replace signaling server with official simple broadcast version

---

## 📚 VDO.ninja v28 Features We Need

**New in v28:**
- Native `&mediamtx=` parameter for direct WHIP/WHEP to MediaMTX
- `&whep=URL` to pull any WHEP stream into VDO.ninja
- Improved WHIP/WHEP primary/screen routing
- Better MediaMTX URL construction
- Token user-set guards

**This is exactly what we need!** With VDO.ninja v28, we can:
1. Stream from R58 cameras to MediaMTX (already working)
2. Pull MediaMTX streams into VDO.ninja using `&whep=`
3. Use VDO.ninja mixer with MediaMTX backend

---

## 🚀 Fastest Path Forward

### Immediate Fix: Update Everything + Simple Signaling

1. Run `update_r58_software.sh` to update all software
2. Restart all services
3. Test raspberry.ninja with simple signaling

### If That Fails: Use VDO.ninja v28 + MediaMTX Native

1. Access VDO.ninja director with:
   ```
   https://localhost:8443/?director=r58studio&mediamtx=localhost:8889
   ```
2. This tells VDO.ninja to use MediaMTX for media routing
3. No raspberry.ninja needed

### Best Long-Term: Custom MediaMTX Mixer

1. Use `mediamtx_mixer.html` for remote access
2. Use VDO.ninja locally when on same network
3. Best of both worlds

---

## 📝 Summary

**The main issues are:**

1. ❌ **Signaling server is incompatible** - needs to be simple broadcast, not room-filtered
2. ❌ **MediaMTX is ancient** - v1.5.1 vs v1.15.5
3. ⚠️ **VDO.ninja is outdated** - missing v28's MediaMTX integration

**Solutions:**

1. ✅ Update all software to latest versions
2. ✅ Replace signaling server with official simple version
3. ✅ Use VDO.ninja v28's native `&mediamtx=` support
4. ✅ Alternatively, use custom MediaMTX mixer (already working!)

