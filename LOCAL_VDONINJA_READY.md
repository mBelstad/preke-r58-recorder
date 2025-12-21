# Local VDO.ninja Setup Complete!

**Date**: December 21, 2025  
**Status**: ✅ **CONFIGURED AND RUNNING**

---

## ✅ What's Working

### Local VDO.ninja Server
- **Service**: vdo-ninja.service ✅ Active
- **Port**: 8443 (HTTPS/WSS)
- **Location**: Running on R58

### Camera Publishers
All 3 cameras are publishing to the local server:
- ✅ ninja-publish-cam1: r58-cam1
- ✅ ninja-publish-cam2: r58-cam2
- ✅ ninja-publish-cam3: r58-cam3

**Configuration**:
- Server: `wss://localhost:8443` (local)
- Room: `r58studio`
- TURN: Cloudflare (for remote access)

---

## 🌐 How to Access

### Option 1: Local WiFi (When On-Site)

1. **Connect to WiFi**: `R58-Studio` (password: `r58studio2025`)
2. **Open Director**:
   ```
   https://10.58.0.1:8443/?director=r58studio
   ```
3. **Accept SSL warning** (self-signed certificate)

### Option 2: Via Cloudflare Tunnel (Remote Access)

**Setup Required**: Add DNS record in Cloudflare

1. Go to Cloudflare dashboard
2. Select domain: `itagenten.no`
3. Go to **DNS** → **Records**
4. Add **CNAME** record:
   - Name: `vdoninja`
   - Target: `r58.itagenten.no` (or your tunnel ID)
   - Proxy status: **Proxied** (orange cloud)

Then access via:
```
https://vdoninja.itagenten.no/?director=r58studio
```

---

## 🎬 Access URLs

### Director/Mixer View
**Local (WiFi)**:
```
https://10.58.0.1:8443/?director=r58studio
```

**Remote (after DNS setup)**:
```
https://vdoninja.itagenten.no/?director=r58studio
```

### Individual Camera Views
**Camera 1**:
```
https://10.58.0.1:8443/?view=r58-cam1&room=r58studio
```

**Camera 2**:
```
https://10.58.0.1:8443/?view=r58-cam2&room=r58studio
```

**Camera 3**:
```
https://10.58.0.1:8443/?view=r58-cam3&room=r58studio
```

---

## 🔧 Current Configuration

### Cloudflare Tunnel Routes
```yaml
ingress:
  - hostname: r58.itagenten.no → SSH
  - hostname: recorder.itagenten.no → Web UI
  - hostname: hls.itagenten.no → HLS streams
  - hostname: webrtc.itagenten.no → WebRTC (MediaMTX)
  - hostname: vdoninja.itagenten.no → VDO.ninja ✅ NEW
```

### Publishers
- Server: `wss://localhost:8443` (local VDO.ninja)
- Room: `r58studio`
- TURN: Configured for remote users
- Bitrate: 8000 kbps
- Resolution: 1920x1080 @ 30fps

---

## ⚠️ Important Note About WebRTC Through Tunnel

While the VDO.ninja **web interface** works through Cloudflare Tunnel, the **WebRTC media streams** may have issues because:

1. **Cloudflare blocks UDP** (WebRTC media)
2. **TURN relay required** for all connections (adds latency)
3. **Signaling works** (WebSocket over HTTPS)
4. **Media may be slow** or fail without proper TURN

### Best Access Methods

| Method | Latency | Reliability | Use Case |
|--------|---------|-------------|----------|
| **Local WiFi** | Lowest (~50ms) | Best | On-site mixing |
| **DynDNS + Port Forward** | Low (~100ms) | Good | Remote direct |
| **Cloudflare Tunnel** | High (~200-500ms) | OK | Remote via TURN |

---

## 🚀 Quick Start

### If You're On-Site:
1. Connect to `R58-Studio` WiFi
2. Open: `https://10.58.0.1:8443/?director=r58studio`
3. Accept SSL warning
4. Start mixing!

### If You're Remote:
1. Add DNS record: `vdoninja.itagenten.no`
2. Wait 1-2 minutes for DNS propagation
3. Open: `https://vdoninja.itagenten.no/?director=r58studio`
4. WebRTC will use TURN relay (may be slower)

---

## 🎥 Recording

The mix output can be recorded:
1. **In browser**: VDO.ninja has built-in recording
2. **Via OBS**: Capture the director view
3. **Back to R58**: Publish mix via WHIP (future enhancement)

---

## 🔍 Troubleshooting

### Can't access via WiFi
- Verify WiFi AP is broadcasting: Check WiFi settings for "R58-Studio"
- Check you're connected and have IP: `ipconfig` (Windows) or `ifconfig` (Mac)

### Can't access via tunnel
- Add DNS record in Cloudflare
- Wait for DNS propagation
- Check: `dig vdoninja.itagenten.no`

### Cameras not visible
- Check publishers: `./connect-r58.sh "sudo systemctl status ninja-publish-cam*"`
- Check logs: `./connect-r58.sh "sudo journalctl -u ninja-publish-cam1 -f"`

---

**Status**: Local VDO.ninja is ready! Access via WiFi when on-site, or add DNS record for remote access.

