# Cloudflare Services - Historical Reference

**Status**: DEPRECATED (December 2025)  
**Replaced By**: FRP (Fast Reverse Proxy) with TCP WebRTC support

---

## Overview

This project previously used multiple Cloudflare services for remote access and WebRTC connectivity. All Cloudflare services have been removed and replaced with FRP tunneling. This document exists for historical context and to explain why the migration was necessary.

---

## Services Previously Used

### 1. Cloudflared Tunnel

**Purpose**: Secure HTTP/HTTPS tunnel from R58 device to the internet  
**Port**: 443 (HTTPS)  
**Configuration**: `/etc/cloudflared/config.yml`

**Why it was used**:
- Easy setup for HTTPS remote access
- Automatic SSL certificates
- No port forwarding required

**Why it was replaced**:
- **WebRTC/UDP traffic doesn't work through Cloudflare Tunnel**
- Cloudflare Tunnel only proxies HTTP/HTTPS (TCP)
- WebRTC media streams require UDP or TCP with specific ICE negotiation
- Even with TURN relay, the tunnel architecture blocked proper WebRTC connections

**Replaced by**: FRP (Fast Reverse Proxy)
- FRP supports TCP tunneling with proper WebRTC support
- MediaMTX v1.15.5's `webrtcLocalTCPAddress` enables WebRTC over TCP
- Works through FRP tunnel without UDP requirements

---

### 2. Cloudflare TURN Server

**Purpose**: WebRTC relay for NAT traversal  
**Endpoint**: `turns://...@turn.cloudflare.com:5349`  
**Protocol**: TURNS (TLS over TCP)

**Configuration**:
```bash
# Environment variables (removed)
CLOUDFLARE_TURN_TOKEN_ID=...
CLOUDFLARE_TURN_API_TOKEN=...
```

**Why it was used**:
- Attempted to enable VDO.ninja peer-to-peer WebRTC through tunnels
- TURN relay can work over TCP/TLS (port 5349)
- Cloudflare provides free TURN service

**Why it was replaced**:
- **VDO.ninja's p2p architecture doesn't work through tunnels regardless of TURN**
- Even with TURN relay forcing TCP, the signaling and media paths were incompatible with tunnel architecture
- Added complexity without solving the core problem
- TURN relay adds latency and bandwidth costs

**Replaced by**: Direct WHIP to MediaMTX
- WHIP (WebRTC-HTTP Ingestion Protocol) works over HTTP/TCP
- Guests publish directly to MediaMTX via WHIP endpoints
- No peer-to-peer negotiation required
- Works perfectly through FRP tunnel

---

### 3. Cloudflare Calls (SFU)

**Purpose**: Selective Forwarding Unit for WebRTC  
**API**: `https://rtc.live.cloudflare.com/v1/apps/{app_id}/sessions`  
**Files**: `src/cloudflare_calls.py`, `src/calls_relay.py`

**Why it was used**:
- Attempted to use Cloudflare's SFU to handle WebRTC complexity
- SFU would handle guest connections and forward streams
- Relay would pull from Cloudflare and push to MediaMTX

**Architecture attempted**:
```
Guest Browser → Cloudflare Calls SFU → Relay → MediaMTX → Mixer
```

**Why it was replaced**:
- Added unnecessary complexity (3-hop architecture)
- Required maintaining relay processes
- Cloudflare Calls API had limitations
- Direct WHIP is simpler and more reliable
- Latency from multiple hops

**Replaced by**: Direct WHIP to MediaMTX
- Single hop: Guest → MediaMTX
- No relay processes needed
- Lower latency
- Simpler architecture

---

### 4. Cloudflare STUN

**Purpose**: NAT discovery for WebRTC  
**Endpoint**: `stun:stun.cloudflare.com:3478`

**Why it was used**:
- Part of ICE server configuration
- Helps WebRTC clients discover their public IP

**Why it was replaced**:
- Using Google STUN instead: `stun:stun.l.google.com:19302`
- More widely used and tested
- No dependency on Cloudflare

**Current**: Google STUN for local network WebRTC only

---

## Migration Timeline

### Before (Cloudflare Era)
- **Remote Access**: Cloudflared Tunnel
- **Guest Publishing**: Cloudflare Calls SFU + Relay
- **WebRTC**: Cloudflare TURN + STUN
- **Status**: Unreliable, complex, didn't work properly

### After (FRP Era)
- **Remote Access**: FRP Tunnel through Coolify VPS
- **Guest Publishing**: Direct WHIP to MediaMTX
- **WebRTC**: MediaMTX TCP WebRTC through FRP
- **Status**: ✅ Working, simple, reliable

---

## Files Removed (December 2025)

### Python Files
- `src/cloudflare_calls.py` - Cloudflare Calls SFU manager
- `src/calls_relay.py` - Cloudflare Calls relay process

### JavaScript Files
- `src/static/js/turn-client.js` - Cloudflare TURN client

### Shell Scripts
- `deploy_turn_remote.sh` - TURN deployment script
- `fix_vdo_publishers_relay.sh` - VDO.ninja publisher fixes
- `fix_vdo_publishers_v2.sh` - VDO.ninja publisher fixes v2
- `fix_vdo_publishers.sh` - VDO.ninja publisher fixes
- `scripts/update-ninja-turn.sh` - TURN configuration updater
- `scripts/update-publishers-with-turn.sh` - Publisher TURN config

### Test Files
- `test-turn-final.sh` - TURN testing script
- `test-raspberry-ninja-turn.sh` - Raspberry Ninja TURN test
- `test-raspberry-ninja-turn-simple.sh` - Simplified TURN test
- `test-vdo-ninja-turn.html` - VDO.ninja TURN test page
- `test_turn_connection.html` - TURN connection test

### Configuration
- Cloudflare config section in `config.yml` (deprecated but kept for compatibility)
- Environment variables: `CLOUDFLARE_*` (no longer used)

---

## Code Changes

### main.py
- Removed Cloudflare Calls initialization
- Removed Cloudflare Calls cleanup
- Removed `/api/calls/*` endpoints
- Simplified `/api/turn-credentials` to return STUN only
- Updated comments from "Cloudflare Tunnel" to "FRP tunnel"

### config.py
- Marked `CloudflareConfig` as deprecated
- Removed environment variable loading for Cloudflare

### guest_join.html
- Removed Cloudflare TURN references
- Updated UI text from "Cloudflare TURN relay" to "FRP tunnel"
- Simplified WebRTC configuration

---

## Current Architecture (FRP-Based)

```
┌─────────────────┐
│  R58 Device     │
│  - MediaMTX     │
│  - VDO.ninja    │
│  - Cameras      │
└────────┬────────┘
         │ FRP Client
         │ (TCP tunnel)
         ↓
┌─────────────────┐
│  Coolify VPS    │
│  - FRP Server   │
│  - Traefik SSL  │
│  - nginx proxy  │
└────────┬────────┘
         │ HTTPS
         ↓
┌─────────────────┐
│  Remote Users   │
│  - Mixer        │
│  - Speakers     │
│  - Viewers      │
└─────────────────┘
```

### Key URLs
- **MediaMTX**: `https://app.itagenten.no`
- **VDO.ninja**: `https://r58-vdo.itagenten.no`
- **API**: `https://app.itagenten.no`

### How It Works
1. **Cameras**: Stream to local MediaMTX on R58
2. **FRP Tunnel**: Exposes MediaMTX/VDO.ninja through TCP tunnel
3. **Traefik**: Provides SSL termination on Coolify VPS
4. **nginx**: Handles CORS and routing
5. **Remote Access**: Users access via HTTPS domains
6. **Speakers**: Publish via WHIP to MediaMTX
7. **Mixer**: Pulls camera/speaker WHEP streams from MediaMTX

---

## Lessons Learned

### What Didn't Work
1. **Cloudflare Tunnel + WebRTC**: UDP/WebRTC doesn't work through HTTP tunnels
2. **TURN as a workaround**: Even TCP TURN couldn't fix the architectural mismatch
3. **VDO.ninja p2p through tunnels**: Peer-to-peer WebRTC requires direct connections
4. **Complex relay architectures**: More hops = more points of failure

### What Works
1. **FRP with TCP WebRTC**: MediaMTX's TCP WebRTC works perfectly through FRP
2. **WHIP for publishing**: HTTP-based WebRTC publishing is tunnel-friendly
3. **WHEP for viewing**: HTTP-based WebRTC viewing works through tunnels
4. **Simple architecture**: Fewer hops = more reliable

### Key Insight
**The solution wasn't better WebRTC configuration—it was using HTTP-based WebRTC protocols (WHIP/WHEP) that work naturally through TCP tunnels.**

---

## References

### Documentation (Archived)
- `CLOUDFLARE_DISABLED_SUCCESS.md` - When we disabled Cloudflare
- `CLOUDFLARE_TO_FRP_MIGRATION.md` - Migration process
- `VDO_NINJA_FRP_RELAY_ATTEMPT.md` - Failed TURN relay attempt
- `FRP_COMPLETE_SUCCESS.md` - FRP working solution

### Current Documentation
- `REMOTE_WEBRTC_SUCCESS.md` - Working remote WebRTC via FRP
- `CORS_FINALLY_FIXED.md` - CORS configuration for WHEP
- `HYBRID_MODE_COMPLETE_TESTED.md` - Mode switching system

---

## For Future Reference

If you're considering using Cloudflare services for WebRTC:

### ✅ Good Use Cases
- Static website hosting
- CDN for assets
- DDoS protection
- DNS management
- HTTP/HTTPS API proxying

### ❌ Bad Use Cases
- WebRTC media streaming
- UDP-based protocols
- Peer-to-peer applications
- Real-time bidirectional media
- Low-latency video streaming

### Better Alternatives for WebRTC
- **FRP + TCP WebRTC**: What we use (works great)
- **Direct public IP**: If available (best performance)
- **Tailscale/WireGuard**: For private networks
- **Dedicated TURN server**: If p2p is required (expensive)

---

**Last Updated**: December 25, 2025  
**Status**: Cloudflare completely removed, FRP working perfectly

