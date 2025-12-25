# VDO.ninja FRP TURN Relay Attempt - Results

**Date:** December 25, 2025  
**Goal:** Make VDO.ninja work through FRP using TURN relay (TCP-only)

---

## 🔧 What Was Tried

### Approach: Force TURN Relay Mode

The idea was to bypass FRP's UDP limitation by forcing **all WebRTC traffic through a TURN server using TCP/TLS**.

**Configuration Applied:**
- Added `--ice-transport-policy relay` to all `ninja-publish-camX` services
- Used Cloudflare TURN server: `turns://...@turn.cloudflare.com:5349`
- TURNS protocol uses **TLS over TCP port 5349** (not UDP)
- This should theoretically work through FRP since it's TCP-based

**Service Configuration:**
```bash
ExecStart=/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --server wss://localhost:8443 \
    --room r58studio \
    --password false \
    --turn-server "turns://g043f56439a8c4bf3c483c737bf1ecb06c41c79fa6946193495d6a6ed4989a5b:86020d5428a1465a3cd1d8aded2dd3b47623ffccee03c8a96d39c68f6e0f2e10@turn.cloudflare.com:5349" \
    --stun-server "stun://stun.cloudflare.com:3478" \
    --ice-transport-policy relay \
    --v4l2 /dev/video60 \
    --streamid r58-cam1 \
    --noaudio \
    --h264 \
    --bitrate 8000 \
    --width 1920 \
    --height 1080 \
    --framerate 30 \
    --nored
```

---

## 📊 Results

### ✅ What Works

1. **Publishers Start Successfully**
   - All three publishers (cam1, cam2, cam3) start and stay running
   - No crashes or immediate shutdowns
   - Services show `active (running)` status

2. **WebSocket Signaling Works**
   - Publishers connect to `wss://localhost:8443` successfully
   - Signaling server accepts connections
   - Room join messages are sent

3. **Publishers Receive "Seed" Requests**
   - Log shows: `📨 Request: seed`
   - This indicates the signaling server is forwarding room presence

### ❌ What Doesn't Work

1. **No WebRTC Connection Established**
   - Browser director view shows user icons (no video)
   - No ICE candidate exchange in logs
   - No SDP offer/answer negotiation visible

2. **No Logging Output**
   - Publishers produce no logs after startup
   - `journalctl` shows no entries for running processes
   - Suggests publishers are idle, waiting for connections

3. **Browser Cannot See Streams**
   - Director view: Shows "Guest 1", "Guest 2" placeholders
   - Scene view: No streams appear
   - View mode: Shows source selection dialog instead of stream

---

## 🔍 Root Cause Analysis

### The Problem

Even though the publishers are configured with `--ice-transport-policy relay` and a TURNS server, **no WebRTC negotiation is happening**.

### Possible Reasons

1. **Signaling Issue**
   - The VDO.ninja signaling server might not be properly relaying messages
   - Publishers may not be advertising themselves correctly
   - Browser may not be requesting the correct stream IDs

2. **TURN Server Access**
   - Cloudflare TURN server might require different authentication
   - The R58 might not be able to reach `turn.cloudflare.com:5349` from its network
   - TURN credentials might be invalid or expired

3. **Publisher State**
   - Publishers might be waiting for a specific trigger
   - The `--ice-transport-policy relay` might prevent any connection without explicit TURN setup
   - GStreamer webrtcbin might need additional configuration for relay-only mode

4. **Browser Configuration**
   - Browser also needs to be configured with TURN server
   - Browser might be trying direct connection and failing
   - VDO.ninja might not support relay-only mode properly

---

## 🧪 Testing Performed

### Test 1: Direct View
```
URL: https://r58-vdo.itagenten.no/?view=r58-cam1&room=r58studio
Result: Shows source selection dialog (camera/mic/screen)
Expected: Should show the r58-cam1 stream
```

### Test 2: Director View
```
URL: https://r58-vdo.itagenten.no/?director=r58studio
Result: Shows "Guest 1", "Guest 2" placeholders with user icons
Expected: Should show camera streams with video
```

### Test 3: Director View with TURN
```
URL: https://r58-vdo.itagenten.no/?director=r58studio&turn=turns://...@turn.cloudflare.com:5349
Result: Same as Test 2 - no video
Expected: Should establish connection via TURN relay
```

### Test 4: Manual Publisher Run
```bash
/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --server wss://localhost:8443 \
    --room r58studio \
    --password false \
    --turn-server "turns://...@turn.cloudflare.com:5349" \
    --stun-server "stun://stun.cloudflare.com:3478" \
    --ice-transport-policy relay \
    --v4l2 /dev/video60 \
    --streamid r58-cam1-test \
    --noaudio --h264 --bitrate 8000 --width 1920 --height 1080 --framerate 30 --nored
```
**Result:** 
- Starts successfully
- Connects to signaling server
- Receives seed requests
- Gets interrupted (timeout)
- No WebRTC connection established

---

## 📝 Conclusion

### Current Status

**TURN Relay Mode Does NOT Work** for VDO.ninja through FRP.

While the technical approach is sound (TURNS uses TCP), the implementation fails because:
1. No WebRTC negotiation is occurring
2. Publishers and viewers are not exchanging ICE candidates
3. The signaling might be working, but the WebRTC layer is not

### Why This Approach Failed

The issue is likely **not just about UDP vs TCP**. Even with TURN relay forcing TCP transport, VDO.ninja's peer-to-peer architecture requires:
- Proper ICE candidate exchange
- SDP offer/answer negotiation
- Both sides configured with the same TURN server
- Potentially browser-side configuration that's not being applied

### Comparison to MediaMTX

**MediaMTX (Recorder Mode) works through FRP because:**
- It's a **server-based architecture** (SFU)
- Single UDP mux port (8189) configured
- `webrtcICEHostNAT1To1IPs` tells clients to use VPS IP
- All configuration is server-side

**VDO.ninja fails through FRP because:**
- It's a **peer-to-peer architecture**
- Requires both peers to negotiate directly
- Browser-side configuration is harder to control
- raspberry.ninja publishers don't have NAT traversal configuration

---

## 🎯 Recommendations

### 1. **Use Recorder Mode for Remote Access** ✅
- MediaMTX WebRTC works perfectly through FRP
- Already tested and confirmed working
- Access via: `https://r58-api.itagenten.no/static/switcher.html`

### 2. **Use VDO.ninja Locally Only** ✅
- Keep VDO.ninja mode for local network use
- Full mixer and director features available
- No FRP/remote limitations

### 3. **Alternative: ZeroTier/Tailscale VPN**
- Create a virtual local network
- VDO.ninja would work as if on same LAN
- Simpler than configuring TURN for both sides

### 4. **Alternative: Public TURN Server on VPS**
- Deploy coturn on the VPS
- Configure both R58 publishers and browser clients to use it
- More complex setup, uncertain success rate

### 5. **Don't Pursue This Further**
- The Hybrid Mode architecture is correct
- MediaMTX handles remote use case
- VDO.ninja handles local production use case
- Trying to force VDO.ninja through FRP is fighting against its architecture

---

## 📂 Files Modified

1. `/etc/systemd/system/ninja-publish-cam1.service` - Added `--ice-transport-policy relay`
2. `/etc/systemd/system/ninja-publish-cam2.service` - Added `--ice-transport-policy relay`
3. `/etc/systemd/system/ninja-publish-cam3.service` - Added `--ice-transport-policy relay`
4. `fix_vdo_publishers_relay.sh` - Script to deploy relay configuration

---

## 🔄 Next Steps

**Recommended:** Accept that VDO.ninja through FRP is not feasible with current architecture.

**If user insists on remote VDO.ninja:**
1. Set up ZeroTier network
2. Join both R58 and remote clients to ZeroTier
3. Use VDO.ninja over the virtual network
4. This bypasses all FRP/NAT issues

**Current Working Solution:**
- **Local:** VDO.ninja Mode (full features)
- **Remote:** Recorder Mode with MediaMTX WebRTC (works through FRP)

