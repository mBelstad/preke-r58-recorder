# VDO.ninja Mixer Architecture Guide

**Last Updated**: January 2, 2026  
**Status**: ✅ WORKING - HDMI cameras visible as guests in VDO.ninja mixer

---

## Quick Overview

The R58 Mixer provides live video mixing of HDMI camera inputs using a self-hosted VDO.ninja instance. This document explains how all the components work together.

### TL;DR - How It Works

1. **HDMI cameras** → captured by GStreamer → streamed to **MediaMTX** (on R58)
2. **VDO.ninja Bridge** (Chromium on R58) → joins VDO.ninja room with `&whepshare` → tells viewers to fetch video from MediaMTX
3. **Web Mixer** (your browser) → loads VDO.ninja mixer.html → sees cameras as "guests" → mix/switch between them

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              R58 DEVICE (192.168.1.24)                       │
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                        │
│  │ HDMI IN 0   │   │ HDMI IN 11  │   │ HDMI IN 21  │    Physical Ports      │
│  │ (cam0)      │   │ (cam2)      │   │ (cam3)      │                        │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘                        │
│         │                 │                 │                                │
│         ▼                 ▼                 ▼                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     GStreamer Pipelines                              │   │
│  │  (Capture → Scale to 720p → Encode H.264 → RTSP to MediaMTX)        │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      MediaMTX (Port 8889)                            │   │
│  │                                                                       │   │
│  │  Endpoints:                                                           │   │
│  │  - /cam0/whep  → WebRTC WHEP playback                                │   │
│  │  - /cam2/whep  → WebRTC WHEP playback                                │   │
│  │  - /cam3/whep  → WebRTC WHEP playback                                │   │
│  │  - /cam0/whip  → WebRTC WHIP publish (for remote speakers)           │   │
│  │                                                                       │   │
│  │  Protocols: WHEP, WHIP, HLS, RTSP                                    │   │
│  └──────────────────────────────┬───────────────────────────────────────┘   │
│                                 │                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    VDO.ninja (Port 8443)                             │   │
│  │                                                                       │   │
│  │  Self-hosted VDO.ninja instance providing:                           │   │
│  │  - /mixer.html  → Director/mixer interface                           │   │
│  │  - /           → Guest join, director, scene views                   │   │
│  │  - WebSocket signaling server                                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                   VDO.ninja Bridge Service                           │   │
│  │                   (vdoninja-bridge.service)                          │   │
│  │                                                                       │   │
│  │  Runs Chromium with multiple tabs:                                   │   │
│  │  - Director tab: ?director=studio&password=xxx                       │   │
│  │  - Camera tabs: ?push=hdmi0&room=studio&whepshare=WHEP_URL           │   │
│  │                                                                       │   │
│  │  Each camera tab joins the room as a "guest" but uses &whepshare     │   │
│  │  to redirect video playback to MediaMTX WHEP endpoints               │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Backend (Port 8000)                       │   │
│  │                                                                       │   │
│  │  - Recorder API & Mode switching                                     │   │
│  │  - Web frontend (Vue.js app)                                         │   │
│  │  - Static files (HTML, CSS, JS)                                      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      FRP Client                                       │   │
│  │                                                                       │   │
│  │  Tunnels local services to VPS:                                       │   │
│  │  - Port 8889 (MediaMTX) → VPS:18889                                  │   │
│  │  - Port 8443 (VDO.ninja) → VPS:18443                                 │   │
│  │  - Port 8000 (API) → VPS:18000                                       │   │
│  │  - Port 22 (SSH) → VPS:10022                                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   │ FRP Tunnel (TCP)
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         VPS (65.109.32.111)                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        FRP Server (Port 7000)                         │   │
│  │                                                                       │   │
│  │  Receives FRP tunnel connections from R58                             │   │
│  │  Exposes R58 services on VPS ports                                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     Nginx Reverse Proxy                               │   │
│  │                                                                       │   │
│  │  Domain Routing:                                                       │   │
│  │  app.itagenten.no → localhost:18889 → R58 MediaMTX          │   │
│  │  r58-vdo.itagenten.no      → localhost:18443 → R58 VDO.ninja         │   │
│  │  app.itagenten.no      → localhost:18000 → R58 FastAPI           │   │
│  │                                                                       │   │
│  │  CORS Headers: Access-Control-Allow-Origin: *                         │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                   Traefik (Coolify Ingress)                           │   │
│  │                                                                       │   │
│  │  - SSL termination (Let's Encrypt certificates)                       │   │
│  │  - HTTPS on port 443                                                  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTPS
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           Remote Users (Browser)                             │
│                                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │    Mixer Operator   │  │   Remote Speakers   │  │      Viewers        │  │
│  │                     │  │                     │  │                     │  │
│  │ app.itagenten.no│  │ WHIP publish to     │  │ View via WHEP or    │  │
│  │ /mixer              │  │ MediaMTX            │  │ HLS                 │  │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components Explained

### 1. MediaMTX (on R58)

**What it does**: Receives camera streams from GStreamer and serves them via multiple protocols.

**Local Port**: 8889  
**Public URL**: https://app.itagenten.no

**Protocols**:
- **WHEP** (WebRTC-HTTP Egress Protocol): For viewing streams - this is what VDO.ninja uses
- **WHIP** (WebRTC-HTTP Ingress Protocol): For remote speakers to publish
- **HLS**: HTTP Live Streaming fallback for browsers without WebRTC
- **RTSP**: For local network access

**Key Endpoints**:
| Endpoint | Purpose |
|----------|---------|
| `/{stream}/whep` | WebRTC playback (GET) |
| `/{stream}/whip` | WebRTC publish (POST) |
| `/v3/paths/list` | API: List active streams |

### 2. VDO.ninja (on R58)

**What it does**: Provides the mixer interface and WebRTC signaling for room-based collaboration.

**Local Port**: 8443  
**Public URL**: https://r58-vdo.itagenten.no

**Important**: This is a **self-hosted** VDO.ninja instance running ON the R58 device. It is NOT on the VPS.

**Key Pages**:
| Page | Purpose |
|------|---------|
| `/mixer.html` | Director interface with scene controls |
| `/?director=ROOM` | Director view for a room |
| `/?scene&room=ROOM` | Scene output (for OBS) |
| `/?push=ID&room=ROOM` | Guest join with push ID |

### 3. VDO.ninja Bridge (on R58)

**What it does**: Runs Chromium instances that "bridge" the HDMI cameras into the VDO.ninja room.

**Service**: `vdoninja-bridge.service`  
**Script**: `/opt/preke-r58-recorder/scripts/start-vdoninja-bridge.sh`

**How it works**:

1. Opens a **director tab** to claim the director role for the room
2. Opens **camera tabs** (one per HDMI input) that join the room as "guests"
3. Each camera tab uses `&whepshare=WHEP_URL` which tells VDO.ninja:
   > "I'm joining as a guest, but instead of streaming my camera, tell viewers to fetch video from this WHEP URL"

4. Puppeteer automation clicks the "Join Room with Camera" and "START" buttons

**The `&whepshare` Parameter**:

This is the key to making it work! Without it, the browser would try to stream video via P2P WebRTC, which fails through FRP tunnels.

```
?push=hdmi0&room=studio&whepshare=https%3A%2F%2Fapp.itagenten.no%2Fcam0%2Fwhep
```

**Result**: The camera appears as a "guest" in the VDO.ninja room, but video is fetched directly from MediaMTX.

### 4. FRP Tunnel (R58 → VPS)

**What it does**: Creates TCP tunnels from the R58 to the VPS, making R58 services accessible via public URLs.

**Configuration**: `/opt/frp/frpc.toml`

**Port Mappings**:
| R58 Port | VPS Port | Service |
|----------|----------|---------|
| 8889 | 18889 | MediaMTX (WebRTC) |
| 8443 | 18443 | VDO.ninja |
| 8000 | 18000 | FastAPI |
| 22 | 10022 | SSH |

**Why FRP works for WebRTC**: MediaMTX supports `webrtcLocalTCPAddress` which allows WebRTC over TCP instead of UDP. FRP tunnels TCP connections perfectly.

### 5. Nginx Proxy (on VPS)

**What it does**: Routes domain names to FRP tunnel ports and adds CORS headers.

**Critical**: The CORS headers (`Access-Control-Allow-Origin: *`) are added here, enabling VDO.ninja to fetch WHEP streams cross-origin.

---

## Data Flow: Camera to Mixer

```
1. HDMI Camera Signal
        ↓
2. V4L2 Device (/dev/video0, etc.)
        ↓
3. GStreamer Pipeline (capture → scale 720p → H.264 encode)
        ↓
4. MediaMTX (RTSP ingest → serves via WHEP/HLS)
        ↓
5. VDO.ninja Bridge Tab (joins room with &whepshare)
        ↓
6. VDO.ninja Signaling (WebSocket: "new guest: hdmi0")
        ↓
7. Mixer Browser loads VDO.ninja mixer.html
        ↓
8. Mixer receives "new guest" signal
        ↓
9. Mixer fetches video from MediaMTX WHEP endpoint
        ↓
10. Video displays in mixer interface
```

---

## URL Reference

### For Operators

| Purpose | URL |
|---------|-----|
| **Mixer Interface** | `https://app.itagenten.no/mixer` |
| **Director View** | `https://r58-vdo.itagenten.no/?director=studio&password=preke-r58-2024` |
| **Scene Output (OBS)** | `https://r58-vdo.itagenten.no/?scene&room=studio` |

### For Debugging

| Purpose | URL |
|---------|-----|
| **Direct WHEP Playback (cam0)** | `https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam0/whep` |
| **MediaMTX API** | `https://app.itagenten.no/v3/paths/list` |
| **VDO.ninja WHIP/WHEP Tool** | `https://r58-vdo.itagenten.no/whip.html` |

### For Remote Guests

| Purpose | URL |
|---------|-----|
| **Join as Guest** | `https://r58-vdo.itagenten.no/?room=studio` |

---

## Configuration Files

### On R58

| File | Purpose |
|------|---------|
| `/opt/preke-r58-recorder/config.yml` | Main application config |
| `/opt/mediamtx/mediamtx.yml` | MediaMTX streams and protocols |
| `/opt/frp/frpc.toml` | FRP tunnel configuration |
| `/etc/systemd/system/vdoninja-bridge.service` | Bridge service config |
| `/opt/preke-r58-recorder/scripts/start-vdoninja-bridge.sh` | Bridge startup script |

### Frontend (Vue.js)

| File | Purpose |
|------|---------|
| `packages/frontend/src/lib/vdoninja.ts` | VDO.ninja URL builders |
| `packages/frontend/src/views/MixerView.vue` | Mixer page component |

---

## Service Management

```bash
# Check all services
sudo systemctl status mediamtx vdoninja-bridge preke-recorder frpc

# Restart the bridge (if cameras not appearing)
sudo systemctl restart vdoninja-bridge

# View bridge logs
sudo journalctl -u vdoninja-bridge -f
tail -f /var/log/vdoninja-bridge.log

# Restart MediaMTX (if streams not working)
sudo systemctl restart mediamtx

# Check camera streams
curl -s http://localhost:9997/v3/paths/list | jq
```

---

## Troubleshooting

### Cameras Not Appearing in Mixer

1. **Check bridge service**:
   ```bash
   sudo systemctl status vdoninja-bridge
   ```

2. **Check if Chromium tabs are running**:
   ```bash
   curl -s http://127.0.0.1:9222/json | jq '.[].title'
   ```

3. **Check MediaMTX streams**:
   ```bash
   curl -s https://app.itagenten.no/v3/paths/list | jq
   ```

4. **Restart the bridge**:
   ```bash
   sudo systemctl restart vdoninja-bridge
   ```

### CORS Errors in Browser

- Verify nginx CORS headers are configured on VPS
- Use FRP-proxied URLs (`app.itagenten.no`), not Tailscale Funnel

### Director Conflict ("You are not the director")

- The room password must match: `preke-r58-2024`
- Only one session can be director at a time
- Restart the bridge to reclaim director role

### FRP Tunnel Down

```bash
# On R58
sudo systemctl status frpc
sudo systemctl restart frpc
sudo journalctl -u frpc -n 50
```

---

## Room Configuration

| Setting | Value |
|---------|-------|
| Room Name | `studio` |
| Director Password | `preke-r58-2024` |
| VDO.ninja Host | `r58-vdo.itagenten.no` |
| MediaMTX Host | `app.itagenten.no` |

These are configured in:
- `packages/frontend/src/lib/vdoninja.ts` (frontend)
- `/etc/systemd/system/vdoninja-bridge.service` (bridge service)
- `/opt/preke-r58-recorder/scripts/start-vdoninja-bridge.sh` (bridge script)

---

## Camera Port Mapping

| Camera ID | V4L2 Device | HDMI Port | Subdev | Format |
|-----------|-------------|-----------|--------|--------|
| cam0 | /dev/video0 | HDMI IN0 | /dev/v4l-subdev2 | UYVY |
| cam2 | /dev/video11 | HDMI IN11 | /dev/v4l-subdev7 | UYVY |
| cam3 | /dev/video22 | HDMI IN21 | /dev/v4l-subdev12 | UYVY |

Note: `cam1` (/dev/video60, hdmirx) is a different hardware path and may not always be active.

---

## Why This Architecture?

### Why `&whepshare` Instead of Direct Streaming?

P2P WebRTC doesn't work through HTTP tunnels (FRP). The browser on R58 can't establish direct UDP connections to remote viewers. 

`&whepshare` solves this by:
1. Using VDO.ninja's signaling for guest presence (works over WebSocket through FRP)
2. Redirecting video to MediaMTX WHEP (works over HTTP/TCP through FRP)

### Why Self-Hosted VDO.ninja?

1. **Lower latency**: VDO.ninja runs locally on R58, no round-trip to public VDO.ninja servers
2. **Custom CSS**: Can apply R58-specific styling
3. **Privacy**: All signaling stays on-premises
4. **Control**: Can customize behavior and debug locally

### Why MediaMTX Instead of Direct VDO.ninja Publishing?

1. **Multi-protocol**: Serves WHEP, HLS, RTSP from same source
2. **Recording**: Can record streams while serving them
3. **Reliable**: Well-tested, production-grade media server
4. **TCP WebRTC**: Supports WebRTC over TCP (required for FRP)

---

## Related Documentation

- [VDO.ninja WHEP Integration](./VDONINJA_WHEP_INTEGRATION.md) - Detailed WHEP guide
- [Current Architecture](./CURRENT_ARCHITECTURE.md) - Full system architecture
- [VDO.ninja Room Setup](./VDONINJA_ROOM_SETUP.md) - Room configuration details
- [R58 Services](./R58_SERVICES.md) - All system services

---

## Summary for AI/Developers

**Key Points to Remember**:

1. **All services run on the R58 device** - MediaMTX, VDO.ninja, FastAPI, FRP client
2. **VPS only provides public access** - FRP server + nginx proxy + SSL termination
3. **Domains are proxied via FRP** - `r58-*.itagenten.no` → VPS nginx → FRP tunnel → R58
4. **`&whepshare` is critical** - Makes cameras appear as guests while fetching video from MediaMTX
5. **CORS headers on VPS nginx** - Required for cross-origin WHEP fetching
6. **Room password required** - `preke-r58-2024` for authenticated access
7. **Bridge runs on R58** - Chromium with Puppeteer automation

**When Debugging**:
- Check `vdoninja-bridge.service` first
- Verify MediaMTX streams are active
- Confirm FRP tunnel is up
- Look for CORS errors in browser console

---

**Status**: ✅ Production Ready  
**Last Verified**: January 2, 2026  
**Maintainer**: R58 Team

