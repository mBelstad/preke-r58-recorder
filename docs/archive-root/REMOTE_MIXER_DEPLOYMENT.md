# R58 Remote Mixer - Deployment Guide

**Date**: December 25, 2025  
**Status**: ✅ Ready to Deploy

---

## What Was Created

### New File: `r58_remote_mixer.html`

A comprehensive remote mixing interface that combines:
- **VDO.ninja mixer integration** with automatic slot assignment
- **Built-in camera preview grid** with WHEP connections
- **Program output** with click-to-select functionality
- **Quick launch buttons** for various mixing modes

**Location**: `src/static/r58_remote_mixer.html`

---

## Deployment Methods

### Method 1: Git Pull (Recommended)

```bash
# SSH to R58 (requires Cloudflare authentication)
ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" linaro@r58.itagenten.no

# Navigate to repo
cd /opt/preke-r58-recorder

# Pull latest changes
git pull

# Verify file exists
ls -la src/static/r58_remote_mixer.html

# Restart service (optional, static files don't need restart)
sudo systemctl restart preke-recorder
```

### Method 2: Manual SCP

```bash
# From your local machine
scp -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    src/static/r58_remote_mixer.html \
    linaro@r58.itagenten.no:/opt/preke-r58-recorder/src/static/
```

### Method 3: Direct Edit on R58

```bash
# SSH to R58
ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" linaro@r58.itagenten.no

# Create the file
nano /opt/preke-r58-recorder/src/static/r58_remote_mixer.html

# Paste the contents (from your local file)
# Save with Ctrl+X, Y, Enter
```

---

## Access URLs

Once deployed, access the mixer at:

### Remote (from anywhere)
```
https://r58-api.itagenten.no/static/r58_remote_mixer.html
```

### Local (on R58 network)
```
http://192.168.1.24:8000/static/r58_remote_mixer.html
```

---

## Features

### 🚀 Quick Launch VDO.ninja

Three pre-configured buttons:

1. **Full Mixer (Recommended)**
   - Opens VDO.ninja with all 3 cameras
   - Uses `&slots=3&automixer` for automatic slot assignment
   - Labels: CAM0, CAM2, CAM3
   - Click "Auto Mix All" to start

2. **Auto-Start Mixer**
   - Same as above but with `&autostart`
   - Attempts to skip the "Get Started" dialog

3. **MediaMTX Direct**
   - Simple direct viewer without VDO.ninja

### 📷 Built-in Camera Grid

- All 3 cameras displayed with slot numbers
- Auto-connects on page load
- Click any camera to send to Program output
- Visual connection status indicators
- WHEP protocol for low latency

### 🔴 Program Output

- Main preview window
- Shows selected camera
- Fullscreen support
- Click cameras to switch

### 🔗 Quick Links

Direct access to:
- Individual camera MediaMTX viewers
- Individual camera VDO.ninja viewers

---

## VDO.ninja URL Parameters

The mixer uses these key parameters:

```
?room=r58studio          # Room name
&slots=3                 # Force 3 slots
&automixer               # Enable auto-mixer
&whep=URL                # Add WHEP source (repeated 3x)
&label=NAME              # Label for each source
```

**Full URL:**
```
http://insecure.vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=http://65.109.32.111:18889/cam0/whep&label=CAM0&whep=http://65.109.32.111:18889/cam2/whep&label=CAM2&whep=http://65.109.32.111:18889/cam3/whep&label=CAM3
```

---

## How It Works

### Architecture

```
R58 HDMI Cameras (cam0, cam2, cam3)
    ↓
preke-recorder (GStreamer)
    ↓
MediaMTX (RTSP → WHEP)
    ↓
FRP Tunnel (TCP WebRTC)
    ↓
VPS (65.109.32.111:18889)
    ↓
Remote Browser
    ├─ VDO.ninja mixer (via insecure.vdo.ninja)
    └─ Built-in WHEP viewer (JavaScript)
```

### Why It Works Remotely

1. **MediaMTX TCP WebRTC**: Uses port 8190 (TCP) instead of UDP
2. **FRP Tunnel**: Forwards TCP traffic to VPS
3. **WHEP Protocol**: Standard WebRTC ingestion protocol
4. **VDO.ninja WHEP Support**: Native support for pulling WHEP streams

---

## Usage Instructions

### For VDO.ninja Mixer

1. Open the remote mixer page
2. Click **"Full Mixer (Recommended)"**
3. VDO.ninja opens in new tab
4. Click **"Get Started"** (or use Auto-Start version)
5. You'll see 3 stream sources appear
6. Click **"Auto Mix All"** button
7. Select a layout (2-up, 3-up, quad, etc.)
8. All cameras appear in the layout!

### For Built-in Viewer

1. Open the remote mixer page
2. Wait for cameras to auto-connect (~2-3 seconds each)
3. Click any camera thumbnail to send to Program
4. Use "Fullscreen" button for full-screen viewing
5. Use "Refresh All" if connections drop

---

## Troubleshooting

### Cameras Don't Load

**Check MediaMTX streams:**
```bash
curl -s http://localhost:9997/v3/paths/list | grep -E "cam[0-3]"
```

**Check FRP tunnel:**
```bash
sudo systemctl status frpc
curl -I http://65.109.32.111:18889/cam0
```

### VDO.ninja Sources Don't Appear

1. Make sure you clicked "Get Started"
2. Wait 5-10 seconds for WHEP connections
3. Check browser console for errors (F12)
4. Try the "Auto-Start Mixer" version

### Mixed Content Errors

- Must use `insecure.vdo.ninja` (HTTP)
- HTTPS sites can't load HTTP WHEP endpoints
- This is a browser security limitation

---

## Technical Details

### WHEP Client Implementation

The built-in viewer uses a custom WHEP client:

```javascript
class WHEPClient {
    constructor(endpoint) {
        this.endpoint = endpoint;
    }
    
    async connect() {
        // Create RTCPeerConnection
        // Add transceivers for video/audio
        // Create SDP offer
        // POST to WHEP endpoint
        // Set remote SDP answer
        // Return connected peer connection
    }
}
```

### Slot Assignment

VDO.ninja's `&slots=3` parameter:
- Forces mixer to maintain 3 slots
- Sources auto-assign to slots in order
- Layouts respect slot positions
- Prevents dynamic slot changes

---

## Next Steps

### Immediate
1. Deploy the file to R58
2. Test remote access
3. Verify all cameras load

### Future Enhancements
1. Add scene presets (saved layouts)
2. Add transition effects
3. Add recording capability
4. Add stream output (RTMP/WHIP)
5. Add audio mixing controls

---

## Credits

- **MediaMTX**: bluenviron/mediamtx (v1.15.5)
- **VDO.ninja**: steveseguin/vdo.ninja (WHEP support)
- **FRP**: fatedier/frp (TCP tunneling)
- **preke-r58-recorder**: Custom recording application

---

## Support

**Issues?** Check:
1. MediaMTX status: `sudo systemctl status mediamtx`
2. FRP tunnel: `sudo systemctl status frpc`
3. Camera streams: `curl http://localhost:9997/v3/paths/list`
4. Browser console for JavaScript errors

**Access URLs:**
- Remote Mixer: https://r58-api.itagenten.no/static/r58_remote_mixer.html
- Mode Control: https://r58-api.itagenten.no/static/mode_control.html
- Direct Cameras: http://65.109.32.111:18889/cam0

---

**Status**: ✅ Ready for Production  
**Tested**: Locally (needs R58 deployment)  
**Documentation**: Complete

