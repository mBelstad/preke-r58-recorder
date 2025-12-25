# VDO.ninja with FRP - Test Results

**Date**: December 25, 2025  
**Test**: WebRTC functionality through FRP tunnel (UDP support)

---

## 🧪 Test Results

### ✅ What's Working

1. **WebSocket Signaling** - ✅ Working
   - Publishers appear in director view as "Guest 1" and "Guest 2"
   - Room joining successful
   - Signaling server accessible via `https://r58-vdo.itagenten.no`

2. **Publisher Services** - ✅ Running (last verified)
   - All 3 publishers were running with correct stream IDs
   - Hardware encoder (`mpph264enc`) active
   - Connected to signaling server

3. **FRP Web Access** - ✅ Working
   - VDO.ninja web interface accessible
   - Director view loads correctly
   - No HTTPS/WSS errors

### ❌ What's NOT Working

1. **WebRTC Media Transmission** - ❌ Still Failing
   - Publishers appear as user icons (no video)
   - No video stream visible in director view
   - Viewer page shows "Please select an option to join" instead of stream

2. **SSH Access via FRP** - ❌ Currently Down
   - Getting "websocket: bad handshare" errors
   - Cannot verify current publisher status
   - Cannot check logs

---

## 🔍 Root Cause Analysis

### Why WebRTC Media Still Fails with FRP

Even though FRP supports UDP, WebRTC requires specific configuration:

#### 1. **UDP Port Range Not Forwarded**

WebRTC uses a range of UDP ports for media:
- **STUN**: UDP port 3478 (or 19302)
- **Media**: Random UDP ports (typically 10000-60000)

FRP needs explicit configuration to forward these UDP ports:

```ini
# FRP Client Configuration (on R58)
[webrtc-udp]
type = udp
local_ip = 127.0.0.1
local_port = 10000-60000
remote_port = 10000-60000
```

#### 2. **ICE Candidate Issues**

The publishers are generating ICE candidates with local IP addresses, but:
- Browser receives candidates with FRP server's public IP
- NAT traversal fails because UDP ports aren't properly mapped
- No direct path established between browser and publishers

#### 3. **STUN/TURN Server Accessibility**

Current configuration:
- **STUN**: `stun://stun.cloudflare.com:3478` (public, should work)
- **TURN**: `turns://...@turn.cloudflare.com:5349` (public, should work)

But if the FRP tunnel doesn't properly forward UDP, STUN/TURN can't help.

---

## 🎯 Why This is Different from Cloudflare Tunnel

| Feature | Cloudflare Tunnel | FRP |
|---------|-------------------|-----|
| HTTP/HTTPS | ✅ Yes | ✅ Yes |
| WebSocket (TCP) | ✅ Yes | ✅ Yes |
| UDP Support | ❌ No | ✅ Yes (with config) |
| Port Forwarding | ❌ No | ✅ Yes (manual) |
| WebRTC Ready | ❌ No | ⚠️ Requires configuration |

**Key Difference**: FRP *can* support WebRTC, but it requires **explicit UDP port forwarding configuration**.

---

## 🔧 Solutions to Fix WebRTC with FRP

### Solution 1: Configure FRP UDP Port Forwarding (Recommended)

#### On FRP Server (VPS)
```ini
# frps.ini
[common]
bind_port = 7000
bind_udp_port = 7001

# Allow UDP port range for WebRTC
allow_ports = 10000-60000
```

#### On FRP Client (R58)
```ini
# frpc.ini
[common]
server_addr = your-vps.com
server_port = 7000

# Forward WebRTC UDP port range
[webrtc-media]
type = udp
local_ip = 127.0.0.1
local_port = 10000-60000
remote_port = 10000-60000

# Forward STUN port
[stun]
type = udp
local_ip = 127.0.0.1
local_port = 3478
remote_port = 3478
```

### Solution 2: Use TURN Server with TCP Fallback

Configure publishers to use TURN with TCP:

```bash
--turn-server "turn:your-vps.com:3478?transport=tcp"
```

This forces WebRTC to use TCP instead of UDP, which FRP already forwards.

### Solution 3: Direct IP Access (Testing Only)

For testing, access the R58 directly by IP (if on same network or VPN):

```
https://192.168.1.24:8443/?view=r58-cam1&room=r58studio
```

This bypasses FRP entirely and should work if on the same network.

### Solution 4: ZeroTier/Tailscale VPN (Best for Production)

Create a virtual LAN so remote viewers appear on the same network:

```bash
# Install ZeroTier on R58 and viewer devices
curl -s https://install.zerotier.com | sudo bash
sudo zerotier-cli join <network-id>

# Access R58 via ZeroTier IP
https://<zerotier-ip>:8443/?view=r58-cam1&room=r58studio
```

**Advantages:**
- Full WebRTC functionality
- No port forwarding needed
- Encrypted tunnel
- Works from anywhere

---

## 📊 Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
│  https://r58-vdo.itagenten.no/?director=r58studio          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ HTTPS/WSS (TCP) ✅
                 │ WebRTC Media (UDP) ❌
                 │
          ┌──────▼──────┐
          │  FRP Server │
          │    (VPS)    │
          │             │
          │ ⚠️ UDP ports│
          │   not fwd'd │
          └──────┬──────┘
                 │
                 │ TCP Tunnel ✅
                 │ UDP Tunnel ❌
                 │
          ┌──────▼──────┐
          │  FRP Client │
          │    (R58)    │
          └──────┬──────┘
                 │
     ┌───────────┴───────────┐
     │                       │
┌────▼────┐          ┌───────▼────────┐
│ VDO.ninja│          │ Publishers     │
│ Signaling│          │ (raspberry.ninja)│
│  Server  │          │                │
│  :8443   │          │ r58-cam1/2/3   │
└──────────┘          └────────────────┘
```

---

## 🎯 Recommended Next Steps

### Immediate (Today)

1. **Fix FRP SSH Access**
   - Restart FRP client on R58
   - Verify SSH tunnel is working
   - Check publisher service status

2. **Check FRP Configuration**
   - Review FRP client config (`/etc/frp/frpc.ini`)
   - Verify UDP forwarding is configured
   - Check FRP server logs on VPS

3. **Test Direct IP Access** (if possible)
   - Connect to R58's network
   - Access `https://192.168.1.24:8443/?view=r58-cam1`
   - Verify WebRTC works without FRP

### Short Term (This Week)

1. **Configure FRP UDP Forwarding**
   - Add UDP port range forwarding to FRP config
   - Restart FRP client and server
   - Test WebRTC again

2. **Alternative: Setup ZeroTier**
   - Install ZeroTier on R58
   - Create network for team
   - Test WebRTC over ZeroTier

### Long Term (Next Month)

1. **Evaluate Best Solution**
   - FRP with UDP forwarding
   - ZeroTier/Tailscale VPN
   - Dedicated TURN server
   - Accept limitation and use Recorder Mode

2. **Document Final Architecture**
   - Update team documentation
   - Create troubleshooting guide
   - Document network requirements

---

## 📝 Conclusion

### Current Status

- ✅ **Publishers**: Correctly configured with clean stream IDs
- ✅ **Signaling**: Working through FRP (TCP/WSS)
- ❌ **Media**: Not working (VDO.ninja doesn't support UDP muxing)
- ✅ **SSH**: Working via `./connect-r58-frp.sh`
- ✅ **FRP UDP**: Configured for MediaMTX (port 8189)
- ❌ **TURN Relay Attempt**: Failed (see `VDO_NINJA_FRP_RELAY_ATTEMPT.md`)

### Key Finding

**FRP is correctly configured with UDP muxing (port 8189) for MediaMTX WebRTC.** However, **VDO.ninja/raspberry.ninja publishers don't support UDP muxing** - they use random UDP ports for each peer connection, which cannot be forwarded through FRP.

**MediaMTX WebRTC (Recorder Mode) works through FRP** because it uses UDP muxing on a single port (8189).

**VDO.ninja WebRTC cannot work through FRP** because:
1. raspberry.ninja doesn't support UDP muxing
2. Even with TURN relay mode (`--ice-transport-policy relay`), WebRTC negotiation fails
3. Peer-to-peer architecture requires both sides to be properly configured

### Final Recommendation

**Accept the Hybrid Mode architecture as designed:**

1. ✅ **Recorder Mode (Remote)** - Use MediaMTX WebRTC through FRP
   - Access: `https://r58-api.itagenten.no/static/switcher.html`
   - Works perfectly for remote viewing and recording
   - Low latency WebRTC with UDP muxing

2. ✅ **VDO.ninja Mode (Local)** - Use on same network or VPN
   - Access: `https://192.168.1.24:8443/?director=r58studio` (local)
   - Full mixer, director, and scene features
   - Best for live production work

3. 🔄 **Alternative for Remote VDO.ninja** - ZeroTier/Tailscale
   - Create virtual local network
   - VDO.ninja works as if on same LAN
   - Simpler than trying to force through FRP

### Technical Explanation

The fundamental issue is architectural:

**MediaMTX (Recorder Mode):**
- ✅ Supports UDP muxing (`webrtcICEUDPMuxAddress`)
- ✅ All WebRTC traffic goes through single UDP port (8189)
- ✅ Server-based SFU architecture
- ✅ **Works remotely through FRP**

**VDO.ninja/raspberry.ninja:**
- ❌ No UDP muxing support
- ❌ Each peer connection uses random UDP ports
- ❌ Peer-to-peer architecture requires both sides configured
- ❌ TURN relay mode doesn't solve the signaling/negotiation issues
- ❌ **Cannot work remotely through FRP**

### Attempts Made

1. ✅ Fixed stream ID hashing (`--password false`)
2. ✅ Removed audio device issues (`--noaudio`)
3. ✅ Configured FRP UDP forwarding (port 8189)
4. ❌ Attempted TURN relay mode (`--ice-transport-policy relay`)
   - Result: Publishers start but no WebRTC negotiation occurs
   - See: `VDO_NINJA_FRP_RELAY_ATTEMPT.md` for details

---

## 📁 Related Documentation

- `VDO_NINJA_TROUBLESHOOTING_RESULTS.md` - Initial troubleshooting
- `HYBRID_MODE_COMPLETE_TESTED.md` - Hybrid mode documentation
- `FRP_TUNNEL_ISSUE_PROMPT.md` - FRP tunnel troubleshooting

---

**Test Date**: December 25, 2025  
**Result**: WebRTC media still not working - FRP UDP forwarding needed  
**Next Action**: Configure FRP UDP port forwarding or use ZeroTier

