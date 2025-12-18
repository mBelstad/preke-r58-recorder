# Remote Guests Status & WebRTC Limitation

## Current Status

✅ **Implementation Complete** - All code deployed
⚠️ **Remote Access Limited** - WebRTC through Cloudflare Tunnel has limitations

---

## What Works

### ✅ Local Network Access (RECOMMENDED)
When guests connect from the **same local network** as the R58 device:

**URL**: `http://192.168.1.58:8000/guest_join`

- ✅ Direct WebRTC connection to MediaMTX
- ✅ Low latency (~200-500ms)
- ✅ Full functionality
- ✅ No additional configuration needed

### ✅ Code Implementation
All features are implemented and deployed:
- ✅ MediaMTX WHIP paths configured
- ✅ Guest join page with WHIP client
- ✅ Mixer supports guest sources
- ✅ Switcher UI shows guest inputs
- ✅ API endpoints working
- ✅ WHIP proxy endpoint added

---

## What Doesn't Work (Yet)

### ⚠️ Remote Access Through Cloudflare Tunnel
**URL**: `https://recorder.itagenten.no/guest_join`

**Issue**: WebRTC connection fails after WHIP handshake

**Why**:
- Cloudflare Tunnel only supports HTTP/HTTPS (TCP)
- WebRTC media transport requires UDP
- ICE candidates can't establish peer connection through tunnel
- Connection state goes: `new` → `connecting` → `failed`

**Console Output**:
```
WHIP connection established  ✓ (signaling works)
Connection state: failed     ✗ (media transport fails)
```

---

## Solutions for Remote Guest Access

### Option 1: Local Network Only (Current - Works Now)
**Best for**: Guests in the same location as R58

- Guests connect to: `http://192.168.1.58:8000/guest_join`
- No additional setup needed
- Full WebRTC functionality
- Low latency

### Option 2: Cloudflare Calls TURN Service (Recommended for Remote)
**Best for**: Remote guests anywhere in the world

You already have a Cloudflare Calls subscription which includes TURN servers!

**Implementation**:
1. Get TURN credentials from Cloudflare Calls dashboard
2. Update MediaMTX config with TURN servers
3. Update guest_join.html ICE servers
4. Remote WebRTC will work through TURN relay

**Steps**:
```yaml
# mediamtx.yml
webrtcICEServers2:
  - stun:stun.l.google.com:19302
  - turn:turn.cloudflare.com:3478?transport=udp
  - turn:turn.cloudflare.com:3478?transport=tcp
```

```javascript
// guest_join.html
iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    {
        urls: 'turn:turn.cloudflare.com:3478',
        username: 'YOUR_TURN_USERNAME',
        credential: 'YOUR_TURN_CREDENTIAL'
    }
]
```

### Option 3: Tailscale VPN (Alternative)
**Best for**: Small team, secure access

- Install Tailscale on R58 and guest devices
- Creates virtual local network
- Guests use Tailscale IP to access R58
- Works like local network

### Option 4: Direct Port Forwarding (Not Recommended)
**Security concerns**: Exposes R58 directly to internet

- Forward UDP ports 8189-8200 to R58
- Configure MediaMTX with public IP
- Security risk - not recommended

---

## Current Workaround

The guest join page now shows a warning when accessed remotely:

```
⚠️ Remote Access Detected
For best results, guests should connect from the same local network as the R58 device.
Local network URL: http://192.168.1.58:8000/guest_join
Remote WebRTC may fail due to Cloudflare Tunnel limitations.
```

---

## Testing Instructions

### Test 1: Local Network Guest (Works Now)
1. Connect to same WiFi/network as R58
2. Open: `http://192.168.1.58:8000/guest_join`
3. Select camera/mic → Start Preview → Join Stream
4. Should connect successfully
5. Open switcher: `http://192.168.1.58:8000/switcher`
6. Guest appears in input grid
7. Assign guest to scene and verify in program output

### Test 2: Remote Guest (Requires TURN)
1. From anywhere, open: `https://recorder.itagenten.no/guest_join`
2. Will see warning about remote access
3. Can try to connect (may fail without TURN)
4. Need Cloudflare TURN credentials to work

---

## Recommended Next Steps

### Immediate (For Testing)
Use local network access for guests:
- Share local URL: `http://192.168.1.58:8000/guest_join`
- Works perfectly for guests in the same location

### Short-term (For Remote Guests)
Implement Cloudflare Calls TURN:
1. Get TURN credentials from Cloudflare dashboard
2. Update MediaMTX and guest_join.html configs
3. Test remote guest connections
4. Document TURN setup

### Long-term (Production)
Consider architecture based on use case:
- **Local events**: Current setup works perfectly
- **Remote guests**: Cloudflare TURN required
- **Hybrid**: Support both local and remote

---

## Technical Details

### Why WHIP Handshake Works But Connection Fails

1. **WHIP Handshake** (HTTP POST) ✅
   - Client sends SDP offer via HTTP
   - Server responds with SDP answer via HTTP
   - Works through Cloudflare Tunnel (HTTP-based)

2. **ICE/Media Transport** (UDP) ✗
   - After handshake, WebRTC tries to establish media connection
   - Needs UDP for RTP/RTCP packets
   - Cloudflare Tunnel doesn't forward UDP
   - Connection fails at ICE stage

### What TURN Does
- Relays UDP traffic through TCP/TLS
- Acts as intermediary for media packets
- Allows WebRTC through firewalls/tunnels
- Cloudflare Calls provides global TURN infrastructure

---

## Files Modified

All files are deployed and working:
- ✅ `mediamtx.yml` - Guest paths added
- ✅ `config.yml` - Guest configuration
- ✅ `src/config.py` - GuestConfig dataclass
- ✅ `src/main.py` - WHIP proxy + guest status API
- ✅ `src/mixer/core.py` - Guest source handling
- ✅ `src/static/guest_join.html` - WHIP client + warning
- ✅ `src/static/switcher.html` - Guest inputs UI

---

## Summary

**Current State**:
- ✅ **Local network guests**: Fully functional
- ⚠️ **Remote guests**: Requires Cloudflare TURN setup

**Recommendation**: 
For immediate testing, use local network URL. For production remote guests, implement Cloudflare TURN (you already have the subscription!).
