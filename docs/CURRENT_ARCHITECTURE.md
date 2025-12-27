# R58 Current Architecture

**Last Updated**: December 25, 2025  
**Status**: ✅ Working and Tested

---

## Overview

The R58 system is a professional multi-camera recording and streaming solution built on an RK3588 ARM device. It supports local recording, remote viewing, and live mixing through VDO.ninja.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       R58 Device (192.168.1.24)              │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │  HDMI IN   │  │  HDMI IN   │  │  HDMI IN   │           │
│  │  Camera 0  │  │  Camera 2  │  │  Camera 3  │           │
│  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘           │
│         │                │                │                 │
│         └────────────────┴────────────────┘                 │
│                          │                                  │
│                    ┌─────▼──────┐                          │
│                    │  MediaMTX  │                          │
│                    │  Port 8889 │                          │
│                    │  (WebRTC)  │                          │
│                    └─────┬──────┘                          │
│                          │                                  │
│         ┌────────────────┼────────────────┐               │
│         │                │                │               │
│    ┌────▼────┐     ┌────▼────┐     ┌────▼────┐          │
│    │  WHEP   │     │  WHIP   │     │  HLS    │          │
│    │  Viewer │     │ Publish │     │ Stream  │          │
│    └─────────┘     └─────────┘     └─────────┘          │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  VDO.ninja (Port 8443)                           │      │
│  │  - Mixer                                          │      │
│  │  - Director                                       │      │
│  │  - Signaling Server                              │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  FastAPI (Port 8000)                             │      │
│  │  - Mode Control                                   │      │
│  │  - Guest Join                                     │      │
│  │  - API Endpoints                                  │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│                     FRP Client                              │
│                     (TCP Tunnel)                            │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       │ SSH Tunnel
                       │ localhost:7000 → 65.109.32.111:7000
                       │
┌──────────────────────▼───────────────────────────────────────┐
│              Coolify VPS (65.109.32.111)                     │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  FRP Server (Port 7000)                          │      │
│  │  Exposes:                                         │      │
│  │  - 18889 → MediaMTX                              │      │
│  │  - 18443 → VDO.ninja                             │      │
│  │  - 19997 → MediaMTX API                          │      │
│  └──────────────────┬───────────────────────────────┘      │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────┐      │
│  │  nginx (r58-proxy container)                     │      │
│  │  - CORS handling                                  │      │
│  │  - Proxies to FRP ports                          │      │
│  └──────────────────┬───────────────────────────────┘      │
│                     │                                        │
│  ┌──────────────────▼───────────────────────────────┐      │
│  │  Traefik (Coolify)                               │      │
│  │  - SSL Termination (Let's Encrypt)               │      │
│  │  - Domain Routing                                 │      │
│  └──────────────────┬───────────────────────────────┘      │
│                     │                                        │
└─────────────────────┼────────────────────────────────────────┘
                      │
                      │ HTTPS
                      │
┌─────────────────────▼────────────────────────────────────────┐
│                    Remote Users                              │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐ │
│  │  Mixer/        │  │  Remote        │  │  Viewers     │ │
│  │  Director      │  │  Speakers      │  │              │ │
│  │                │  │  (WHIP)        │  │  (WHEP)      │ │
│  └────────────────┘  └────────────────┘  └──────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. R58 Device

**Hardware**: RK3588 ARM SoC  
**OS**: Ubuntu 22.04 ARM64  
**IP**: 192.168.1.24 (local network)

**Services**:
- **MediaMTX** (port 8889): WebRTC/HLS/RTSP server
- **VDO.ninja** (port 8443): Mixer and signaling server
- **FastAPI** (port 8000): Control API and web UI
- **FRP Client**: Tunnel to Coolify VPS

### 2. MediaMTX

**Version**: v1.15.5+  
**Key Feature**: TCP WebRTC support (`webrtcLocalTCPAddress`)

**Protocols**:
- **WHEP** (WebRTC-HTTP Egress): For viewing streams
- **WHIP** (WebRTC-HTTP Ingress): For publishing streams
- **HLS**: HTTP Live Streaming fallback
- **RTSP**: Local network streaming

**Configuration**: `mediamtx.yml`

**Paths**:
- `cam0`, `cam2`, `cam3`: Camera streams
- `speaker0`, `speaker1`: Remote speaker streams
- Custom paths for graphics/slides

### 3. VDO.ninja

**Version**: v28+  
**Port**: 8443 (HTTPS with self-signed cert)

**Features**:
- **Mixer**: Mix multiple camera/speaker sources
- **Director**: Control and monitor streams
- **Signaling Server**: WebSocket-based room management

**Key URLs**:
- Mixer: `https://r58-vdo.itagenten.no/mixer`
- Director: `https://r58-vdo.itagenten.no/?director=r58studio`

### 4. FRP (Fast Reverse Proxy)

**Purpose**: TCP tunnel from R58 to Coolify VPS

**Configuration**:
- **Client**: `/opt/frp/frpc.toml` on R58
- **Server**: Running on Coolify VPS (port 7000)
- **Tunnel**: SSH tunnel for FRP control connection

**Exposed Ports**:
- 18889 → MediaMTX WebRTC
- 18443 → VDO.ninja
- 19997 → MediaMTX API

### 5. Coolify VPS

**IP**: 65.109.32.111  
**Purpose**: SSL termination and public access

**Components**:
- **FRP Server**: Receives tunnel from R58
- **nginx (r58-proxy)**: CORS and routing
- **Traefik**: SSL certificates and domain routing

**Domains**:
- `r58-mediamtx.itagenten.no` → MediaMTX
- `r58-vdo.itagenten.no` → VDO.ninja
- `r58-api.itagenten.no` → FastAPI

---

## Data Flows

### Camera Viewing (Remote)

```
Camera → MediaMTX (R58) → FRP Tunnel → nginx → Traefik → Browser
                                                            ↓
                                                    WHEP endpoint
                                                    (WebRTC/TCP)
```

**URL**: `https://r58-mediamtx.itagenten.no/cam0`

### Remote Speaker Publishing

```
Browser → WHIP (HTTPS) → Traefik → nginx → FRP → MediaMTX (R58)
                                                        ↓
                                                  speaker0 path
```

**URL**: `https://r58-api.itagenten.no/guest_join`

### VDO.ninja Mixer

```
Mixer (Browser) → WHEP requests → r58-mediamtx.itagenten.no
                       ↓
              Pulls multiple streams:
              - cam0/whep
              - cam2/whep
              - cam3/whep
              - speaker0/whep
              - speaker1/whep
```

**URL**: `https://r58-vdo.itagenten.no/mixer?room=r58studio&slots=5&automixer&whep=...`

---

## Network Configuration

### Local Network (192.168.1.0/24)
- **R58**: 192.168.1.24
- **Router**: 192.168.1.1
- **Local Access**: Direct to R58 services

### Remote Access (via FRP)
- **Public IP**: 65.109.32.111 (Coolify VPS)
- **Domains**: *.itagenten.no
- **SSL**: Let's Encrypt (automatic via Traefik)

### Firewall Rules
- **R58**: Outbound SSH to VPS (for FRP tunnel)
- **VPS**: Inbound 443 (HTTPS), 7000 (FRP)

---

## Mode Switching

The R58 supports two operational modes:

### Recorder Mode (Default)
- **Purpose**: Recording and local viewing
- **Services**: MediaMTX, FastAPI
- **Cameras**: Stream to MediaMTX for recording/viewing

### VDO.ninja Mode
- **Purpose**: Live mixing and remote guests
- **Services**: MediaMTX, VDO.ninja, FastAPI
- **Cameras**: Available via WHEP for mixer

**Switching**: Via web UI at `https://r58-api.itagenten.no/static/mode_control.html`

---

## Security

### SSL/TLS
- **Let's Encrypt**: Automatic certificates via Traefik
- **Domains**: All *.itagenten.no domains have valid SSL

### CORS
- **MediaMTX**: Adds `Access-Control-Allow-Origin: *`
- **nginx**: Handles OPTIONS preflight for CORS
- **No Duplicate Headers**: Fixed to avoid conflicts

### Authentication
- **Local**: No authentication (trusted network)
- **Remote**: Public access (consider adding auth for production)

---

## Key Technologies

| Technology | Purpose | Why Chosen |
|------------|---------|------------|
| **MediaMTX** | WebRTC server | TCP WebRTC support, WHIP/WHEP |
| **FRP** | Tunnel | TCP tunneling, works with WebRTC |
| **VDO.ninja** | Mixer | Professional mixing, WHEP support |
| **Traefik** | SSL/Routing | Automatic Let's Encrypt |
| **nginx** | Proxy | CORS handling, routing |
| **FastAPI** | API | Python, async, easy to extend |

---

## Why This Architecture Works

### TCP WebRTC Through FRP
- MediaMTX v1.15.5+ supports `webrtcLocalTCPAddress`
- WebRTC can use TCP instead of UDP
- FRP tunnels TCP connections
- Result: WebRTC works through tunnel ✅

### WHIP/WHEP vs Peer-to-Peer
- **WHIP/WHEP**: HTTP-based, works through proxies/tunnels
- **P2P WebRTC**: Requires direct connections, fails through tunnels
- Result: Remote speakers can publish via WHIP ✅

### Single Hop Architecture
- Guest → MediaMTX (one hop)
- No relay processes needed
- Lower latency, simpler debugging

---

## Troubleshooting

### Common Issues

**1. CORS Errors**
- Check nginx OPTIONS handling
- Verify only one `Access-Control-Allow-Origin` header
- See: `CORS_FINALLY_FIXED.md`

**2. FRP Tunnel Down**
- Check SSH tunnel: `ps aux | grep ssh`
- Check FRP client: `ps aux | grep frpc`
- Restart: `sudo systemctl restart frp-client`

**3. MediaMTX Not Accessible**
- Check MediaMTX running: `sudo systemctl status mediamtx`
- Check FRP port mapping: `netstat -tlnp | grep 18889`
- Test locally: `curl http://localhost:8889/cam0`

**4. VDO.ninja Mixer No Video**
- Verify cameras streaming: `curl http://localhost:9997/v3/paths/list`
- Check WHEP endpoints: `curl -I https://r58-mediamtx.itagenten.no/cam0/whep`
- Check browser console for errors

---

## Monitoring

### Health Checks

**MediaMTX**:
```bash
curl http://localhost:9997/v3/paths/list
```

**FRP Tunnel**:
```bash
curl -I https://r58-mediamtx.itagenten.no/cam0
```

**VDO.ninja**:
```bash
curl -I https://r58-vdo.itagenten.no/
```

### Logs

**MediaMTX**:
```bash
sudo journalctl -u mediamtx -f
```

**FRP Client**:
```bash
sudo journalctl -u frp-client -f
```

**FastAPI**:
```bash
sudo journalctl -u preke-recorder -f
```

---

## Performance

### Latency
- **Local WHEP**: <1 second
- **Remote WHEP**: 1-3 seconds
- **VDO.ninja Mixer**: 2-4 seconds

### Bandwidth
- **Per Camera**: ~8 Mbps (1080p30)
- **3 Cameras**: ~24 Mbps upload from R58
- **Remote Speakers**: ~2-4 Mbps per speaker

### CPU Usage (R58)
- **Idle**: ~10%
- **3 Cameras Streaming**: ~40-60%
- **With Mixing**: ~60-80%

---

## Future Improvements

### Potential Enhancements
1. **Authentication**: Add login for remote access
2. **Recording**: Automatic recording of mixed output
3. **Multi-bitrate**: Adaptive streaming for different networks
4. **Monitoring Dashboard**: Real-time stats and alerts
5. **Backup Tunnel**: Redundant FRP connection

### Not Recommended
- ❌ Cloudflare Tunnel (doesn't work with WebRTC)
- ❌ VDO.ninja P2P through tunnel (architectural mismatch)
- ❌ Complex relay architectures (adds latency and complexity)

---

## Lessons Learned: raspberry.ninja vs MediaMTX WHEP

### What Doesn't Work (DO NOT USE)

1. **raspberry.ninja P2P publishers through FRP tunnels**
   - Services: `ninja-publish-cam1/2/3.service`
   - Status: DISABLED (Dec 27, 2025)
   - Problem: P2P WebRTC requires direct UDP connections between peers
   
2. **VDO.ninja room-based mode through tunnels**
   - URL pattern: `?room=r58studio&wss=...`
   - Problem: Room mode uses P2P WebRTC which can't traverse tunnels

3. **Any P2P WebRTC through HTTP tunnels**
   - Architectural mismatch: HTTP tunnels don't support UDP/P2P negotiation

### What Works (USE THIS)

1. **MediaMTX WHEP/WHIP through FRP tunnels**
   - WHIP (publish) and WHEP (view) are HTTP-based
   - Works perfectly through FRP TCP tunnels

2. **VDO.ninja with `&mediamtx=` parameter**
   - URL pattern: `mixer.html?mediamtx=r58-mediamtx.itagenten.no`
   - VDO.ninja pulls streams via WHEP (HTTP-based, not P2P)
   - Works both locally AND remotely

3. **Single-hop architecture**
   - Camera → MediaMTX → WHEP → Browser
   - No relay servers or P2P negotiation needed

### DO NOT re-enable without explicit confirmation:
- `ninja-publish-cam*` services
- VDO.ninja room-based URLs (`?room=`, `&wss=`)
- raspberry.ninja for remote access

### Correct URLs for Remote Access

**Mixer**:
```
https://r58-vdo.itagenten.no/mixer.html?mediamtx=r58-mediamtx.itagenten.no
```

**Director**:
```
https://r58-vdo.itagenten.no/?director=r58studio&mediamtx=r58-mediamtx.itagenten.no
```

---

## Related Documentation

- **Cloudflare History**: `docs/CLOUDFLARE_HISTORY.md`
- **Mixer Guide**: `docs/MIXER_GUIDE.md` (to be created)
- **Remote Speakers**: `docs/REMOTE_SPEAKERS.md` (to be created)
- **Archived Docs**: `docs/archive/` (historical reference)

---

**Status**: ✅ Production Ready  
**Last Tested**: December 27, 2025  
**VDO.ninja Mode**: MediaMTX WHEP (raspberry.ninja P2P disabled)
**Maintainer**: R58 Team

