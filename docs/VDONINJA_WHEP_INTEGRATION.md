# VDO.ninja WHEP Integration Guide

**Last Updated**: December 27, 2025 (17:30 UTC)  
**Status**: WORKING - Direct WHEP playback confirmed working through FRP tunnels

---

## Overview

This document describes how to integrate HDMI camera streams from MediaMTX into VDO.ninja for remote live production. It covers the lessons learned, what works, what doesn't work, and the recommended architecture.

---

## The Problem

We have HDMI cameras connected to an R58 device. These cameras are captured via GStreamer and published to MediaMTX (local) via RTSP. MediaMTX exposes these streams via WHEP (WebRTC-HTTP Egress Protocol).

**Goal**: Make these camera streams visible in VDO.ninja mixer/director, accessible both locally and remotely through FRP tunnels.

---

## What Doesn't Work (DO NOT USE)

### 1. raspberry.ninja P2P Publishers

**Services**: `ninja-publish-cam1/2/3.service`  
**Status**: DISABLED and DEPRECATED (December 27, 2025)

**Why it doesn't work**:
- P2P WebRTC requires direct UDP connections between peers
- FRP tunnels only support TCP/HTTP traffic
- NAT traversal (ICE/STUN/TURN) fails through HTTP proxies
- Device conflicts: Both GStreamer (for MediaMTX) and raspberry.ninja try to access V4L2 devices

### 2. VDO.ninja Room-Based P2P Mode

**URL Pattern**: `?room=r58studio&wss=...`  
**Status**: Does NOT work through FRP tunnels

**Why it doesn't work**:
- Room mode uses P2P WebRTC signaling
- Peers attempt direct connections which fail through tunnels
- The `&wss=` parameter only affects signaling, not media transport

### 3. Direct Stream Auto-Import

**Attempted**: Using `&mediamtx=` to auto-import existing MediaMTX streams  
**Status**: Does NOT work as expected

**Why it doesn't work**:
- The `&mediamtx=` parameter is for guests who JOIN and PUBLISH to MediaMTX
- It does NOT auto-import streams that are already in MediaMTX
- Cameras are already in MediaMTX (via GStreamer RTSP), not through VDO.ninja guest flow

---

## What Works (USE THIS)

### 1. MediaMTX WHEP/WHIP Through FRP Tunnels

**Status**: Works perfectly

**Why it works**:
- WHIP (publish) and WHEP (view) are HTTP-based protocols
- HTTP works through FRP TCP tunnels
- No P2P negotiation required

**URLs**:
- View camera: `https://app.itagenten.no/cam2/whep`
- Publish speaker: `https://app.itagenten.no/speaker0/whip`

### 2. VDO.ninja `&whepplay=` Parameter ⭐ RECOMMENDED

**Status**: ✅ WORKING - This is the best method for viewing HDMI cameras remotely

**URL Pattern**:
```
https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam3/whep
```

**What it does**:
- Pulls a WHEP stream from any MediaMTX endpoint
- Displays it in the VDO.ninja player
- Works remotely through FRP tunnels
- Video confirmed working December 27, 2025

**Best Practices**:
- Use this URL directly in OBS as a Browser Source for each camera
- Use in the VDO.ninja WHIP/WHEP tool page (`/whip.html`) for testing
- Each camera gets its own `&whepplay=` URL

**Example URLs**:
| Camera | URL |
|--------|-----|
| cam0 | `https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam0/whep` |
| cam2 | `https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam2/whep` |
| cam3 | `https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam3/whep` |

**Limitations**:
- Views the stream but doesn't automatically inject it into a VDO.ninja room
- Combining with `&push=` and `&room=` opens a Director view, not a guest view
- VDO.ninja room P2P still doesn't work through FRP for video transport

### 3. VDO.ninja `&mediamtx=` Parameter for Rooms

**Status**: Works for guest publishing

**URL Pattern**:
```
https://r58-vdo.itagenten.no/mixer.html?mediamtx=r58-mediamtx.itagenten.no&room=r58studio
```

**What it does**:
- Guests who join with this URL publish their video through MediaMTX (not P2P)
- Works for remote speakers joining the room
- Mixer and Director can see guests through MediaMTX

**Limitations**:
- Only works for NEW guests joining through VDO.ninja
- Does NOT auto-import existing MediaMTX streams (our cameras)

---

## The Bridge Solution

To get existing MediaMTX streams (cameras) into VDO.ninja rooms, we need a **bridge**.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      R58 Device (Local)                       │
│                                                              │
│  ┌─────────┐     ┌───────────┐     ┌──────────────────────┐ │
│  │  HDMI   │────▶│ GStreamer │────▶│      MediaMTX        │ │
│  │ Cameras │     │ Pipelines │RTSP │   (WHEP endpoints)   │ │
│  └─────────┘     └───────────┘     └──────────┬───────────┘ │
│                                                │             │
│                                         FRP Tunnel          │
│                                                │             │
│  ┌─────────────────────────────────────────────┼───────────┐ │
│  │              Camera Bridge                   │           │ │
│  │  (Headless Chromium running bridge page)    │           │ │
│  │                                             │           │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │           │ │
│  │  │ cam0    │ │ cam2    │ │ cam3    │◀──────┘           │ │
│  │  │ bridge  │ │ bridge  │ │ bridge  │                   │ │
│  │  └────┬────┘ └────┬────┘ └────┬────┘                   │ │
│  │       │           │           │                         │ │
│  │       └───────────┴───────────┴──────────────┐         │ │
│  │                                              │         │ │
│  │                                     ┌────────▼───────┐ │ │
│  │                                     │  VDO.ninja     │ │ │
│  │                                     │  Signaling     │ │ │
│  │                                     │  (room join)   │ │ │
│  │                                     └────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                              │
                        FRP Tunnel
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                      Remote Browser                          │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    VDO.ninja Mixer                      │ │
│  │                                                        │ │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │ │
│  │   │  CAM 1  │  │  CAM 2  │  │  CAM 3  │  │  Guest  │  │ │
│  │   │ (bridge)│  │ (bridge)│  │ (bridge)│  │ (direct)│  │ │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘  │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Bridge Implementation

The camera bridge is a web page (`camera-bridge.html`) that:

1. Fetches active cameras from the API
2. For each camera, creates a hidden iframe with VDO.ninja
3. Each iframe uses `&whepplay=` to pull the camera stream
4. The page shows preview video via direct WHEP connection
5. Runs headlessly on R58 via systemd service

**Bridge URL Pattern** (per camera):
```
https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam2/whep&push=cam2&room=r58studio&label=Camera2&autostart
```

### Files

- **Bridge Page**: `src/static/camera-bridge.html`
- **Systemd Service**: `systemd/r58-camera-bridge.service`
- **Setup Script**: `systemd/setup-camera-bridge.sh`

---

## URL Reference

### For Remote Access (via FRP tunnels)

| Purpose | URL |
|---------|-----|
| Mixer | `https://r58-vdo.itagenten.no/mixer.html?room=r58studio&mediamtx=r58-mediamtx.itagenten.no` |
| Director | `https://r58-vdo.itagenten.no/?director=r58studio&mediamtx=r58-mediamtx.itagenten.no` |
| Scene View | `https://r58-vdo.itagenten.no/?scene&room=r58studio&mediamtx=r58-mediamtx.itagenten.no` |
| Single Camera | `https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam2/whep` |
| Guest Join | `https://r58-vdo.itagenten.no/?room=r58studio&push=guest1&mediamtx=r58-mediamtx.itagenten.no` |

### For Local Access

| Purpose | URL |
|---------|-----|
| Camera Bridge | `http://localhost:8000/static/camera-bridge.html` |
| Custom Mixer | `http://localhost:8000/static/mediamtx_mixer.html` |
| MediaMTX WHEP | `http://localhost:8889/cam2/whep` |

---

## Key VDO.ninja URL Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `&mediamtx=HOST` | Use MediaMTX as SFU instead of P2P | `&mediamtx=r58-mediamtx.itagenten.no` |
| `&whepplay=URL` | Pull and play a WHEP stream | `&whepplay=https://host/cam2/whep` |
| `&push=ID` | Stream ID for publishing | `&push=cam2` |
| `&room=NAME` | Join a room | `&room=r58studio` |
| `&label=TEXT` | Display label for stream | `&label=Camera2` |
| `&autostart` | Auto-start streaming | `&autostart` |
| `&director=ROOM` | Open as Director | `&director=r58studio` |
| `&scene` | Open as scene view | `&scene` |

---

## External Documentation References

### VDO.ninja Official Docs

- [WHIP/WHEP Tooling](https://docs.vdo.ninja/steves-helper-apps/whip-and-whep-tooling)
- [Deploy MediaMTX Guide](https://docs.vdo.ninja/guides/deploy-your-own-meshcast-like-service)
- [Advanced URL Parameters](https://docs.vdo.ninja/advanced-settings)
- [IFrame API](https://docs.vdo.ninja/guides/iframe-api-documentation)
- [Mixer/Scene Parameters](https://docs.vdo.ninja/advanced-settings/mixer-scene-parameters)

### VDO.ninja Tools

- [WHIP/WHEP Test Tool](https://vdo.ninja/whip) - Test WHIP publishing and WHEP playback
- [Mixer (Alpha)](https://vdo.ninja/alpha/mixer) - Latest mixer with improved MediaMTX support
- [Link Generator](https://linkgen.vdo.ninja/) - Generate VDO.ninja URLs

### MediaMTX Documentation

- [MediaMTX GitHub](https://github.com/bluenviron/mediamtx)
- [WHIP/WHEP Configuration](https://github.com/bluenviron/mediamtx#webrtc-whipwhep)

---

## Troubleshooting

### Camera not showing in VDO.ninja

1. **Check MediaMTX is running**: `curl http://localhost:9997/v3/paths/list`
2. **Check WHEP endpoint**: `curl -I https://app.itagenten.no/cam2/whep`
3. **Check bridge service**: `sudo systemctl status r58-camera-bridge`
4. **View logs**: `sudo journalctl -u r58-camera-bridge -f`

### Remote access not working

1. **Check FRP tunnel**: `curl -I https://app.itagenten.no/`
2. **Check VDO.ninja is accessible**: `curl -I https://r58-vdo.itagenten.no/`
3. **Use `&mediamtx=` parameter**: Ensure URL includes `&mediamtx=r58-mediamtx.itagenten.no`

### P2P connections failing

**This is expected!** P2P doesn't work through FRP tunnels.

**Solution**: Use the `&mediamtx=` parameter to route media through MediaMTX WHEP/WHIP instead of P2P.

---

## Recommended Production Setup

### For HDMI Cameras (via MediaMTX WHEP)

Use `&whepplay=` URLs directly in your production software:

**In OBS Studio**:
1. Add Browser Source
2. URL: `https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam3/whep`
3. Width: 1920, Height: 1080

**In VDO.ninja WHIP/WHEP Tool**:
1. Navigate to `https://r58-vdo.itagenten.no/whip.html`
2. Scroll to "Play a remote video stream available via WHEP"
3. Enter: `https://app.itagenten.no/cam3/whep`
4. Click GO

### For Remote Human Guests (via VDO.ninja with MediaMTX)

Use VDO.ninja room with `&mediamtx=` parameter:

**Guest Invite Link**:
```
https://r58-vdo.itagenten.no/?room=r58studio&wss=wss://r58-vdo.itagenten.no&mediamtx=r58-mediamtx.itagenten.no
```

**Director View**:
```
https://r58-vdo.itagenten.no/?director=r58studio&wss=wss://r58-vdo.itagenten.no&mediamtx=r58-mediamtx.itagenten.no
```

### Hybrid Workflow

For a production with both HDMI cameras and remote guests:

1. **HDMI Cameras**: Use `&whepplay=` URLs as OBS Browser Sources
2. **Remote Guests**: Use VDO.ninja Director with `&mediamtx=` for guest management
3. **Mixing**: Combine in OBS with scenes for each camera and guest

---

## Lessons Learned Summary

1. **P2P WebRTC through HTTP tunnels fails** - Always use MediaMTX WHEP/WHIP for video transport
2. **`&mediamtx=` is for NEW guests publishing** - Not for importing existing MediaMTX streams
3. **`&whepplay=` is the best method for cameras** - Works reliably through FRP tunnels
4. **VDO.ninja rooms are for guests, not cameras** - Use WHEP URLs for HDMI cameras
5. **raspberry.ninja is deprecated** - Use MediaMTX + GStreamer instead
6. **The WHIP/WHEP test page (`/whip.html`) is very useful** - For debugging and testing

---

## Failed Approaches (Do Not Retry)

The following have been tested and confirmed NOT to work:

| Approach | Why It Fails |
|----------|--------------|
| `ninja-publish-cam*` services | P2P WebRTC doesn't work through FRP |
| VDO.ninja rooms without `&mediamtx=` | P2P video transport fails |
| Headless Chromium on ARM | Browser fails on ARM architecture |
| Python aiortc bridge | P2P WebRTC doesn't work through FRP |
| `&whepplay=` + `&push=` + `&room=` | P2P video transport still fails |

Contact the maintainer before re-attempting any of these.

---

**Status**: WORKING - `&whepplay=` confirmed functional  
**Last Tested**: December 27, 2025 17:30 UTC  
**Maintainer**: R58 Team

