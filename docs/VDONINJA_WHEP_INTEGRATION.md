# VDO.ninja WHEP Integration Guide

**Last Updated**: December 27, 2025  
**Status**: Documented based on extensive research and testing

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
- View camera: `https://r58-mediamtx.itagenten.no/cam2/whep`
- Publish speaker: `https://r58-mediamtx.itagenten.no/speaker0/whip`

### 2. VDO.ninja `&whepplay=` Parameter

**Status**: Works for viewing single streams

**URL Pattern**:
```
https://r58-vdo.itagenten.no/?whepplay=https://r58-mediamtx.itagenten.no/cam2/whep
```

**What it does**:
- Pulls a WHEP stream from any MediaMTX endpoint
- Displays it in the VDO.ninja player
- Works remotely through FRP tunnels

**Limitations**:
- Views the stream but doesn't automatically inject it into a VDO.ninja room
- Combining with `&push=` and `&room=` opens a Director view, not a guest view

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
https://r58-vdo.itagenten.no/?whepplay=https://r58-mediamtx.itagenten.no/cam2/whep&push=cam2&room=r58studio&label=Camera2&autostart
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
| Single Camera | `https://r58-vdo.itagenten.no/?whepplay=https://r58-mediamtx.itagenten.no/cam2/whep` |
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
2. **Check WHEP endpoint**: `curl -I https://r58-mediamtx.itagenten.no/cam2/whep`
3. **Check bridge service**: `sudo systemctl status r58-camera-bridge`
4. **View logs**: `sudo journalctl -u r58-camera-bridge -f`

### Remote access not working

1. **Check FRP tunnel**: `curl -I https://r58-mediamtx.itagenten.no/`
2. **Check VDO.ninja is accessible**: `curl -I https://r58-vdo.itagenten.no/`
3. **Use `&mediamtx=` parameter**: Ensure URL includes `&mediamtx=r58-mediamtx.itagenten.no`

### P2P connections failing

**This is expected!** P2P doesn't work through FRP tunnels.

**Solution**: Use the `&mediamtx=` parameter to route media through MediaMTX WHEP/WHIP instead of P2P.

---

## Lessons Learned Summary

1. **P2P WebRTC through HTTP tunnels fails** - Always use MediaMTX WHEP/WHIP
2. **`&mediamtx=` is for guests publishing** - Not for importing existing streams
3. **`&whepplay=` views but doesn't republish** - Needs bridge for room integration
4. **raspberry.ninja conflicts with MediaMTX** - Both try to access V4L2 devices
5. **Headless browser bridge is required** - To inject cameras into VDO.ninja rooms

---

## DO NOT Re-enable Without Confirmation

The following have been disabled because they don't work through FRP tunnels:

- `ninja-publish-cam*` systemd services
- VDO.ninja room-based URLs without `&mediamtx=`
- raspberry.ninja for remote access

Contact the maintainer before re-enabling any of these.

---

**Status**: Implementation complete  
**Last Tested**: December 27, 2025  
**Maintainer**: R58 Team

