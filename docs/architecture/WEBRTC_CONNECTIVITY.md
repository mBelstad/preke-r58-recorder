# WebRTC Connectivity Architecture

> **Last Updated:** January 5, 2026  
> **Status:** Production - FRP-based approach

---

## Overview

The R58 system uses WebRTC for low-latency video streaming. This document explains our connectivity approach, why TURN is not needed, and when it might be needed in the future.

---

## Current Architecture

### Connection Flow

```
Remote Guest
    ↓ HTTPS/WSS
FRP Tunnel (65.109.32.111:10022)
    ↓ TCP
R58 Device (100.98.37.53 via Tailscale)
    ↓ Local
MediaMTX (:8889 WHEP/WHIP)
    ↓ WebRTC
Video Streams
```

### Key Components

1. **MediaMTX** - WebRTC media server
   - WHEP (WebRTC-HTTP Egress Protocol) for viewing
   - WHIP (WebRTC-HTTP Ingestion Protocol) for publishing
   - Runs on R58 at port 8889

2. **FRP Tunnel** - Fast Reverse Proxy
   - TCP tunnel from VPS to R58
   - Handles NAT traversal reliably
   - Port 10022 on VPS → R58 SSH
   - Port 18889 on VPS → R58 MediaMTX

3. **ICE Servers** - STUN only
   - `stun:stun.l.google.com:19302`
   - Used for ICE candidate gathering
   - No TURN relay needed

---

## Why TURN Is Not Needed

### 1. FRP Handles NAT Traversal

TURN servers are typically needed to relay WebRTC traffic when direct P2P connections fail due to:
- Symmetric NAT
- Strict firewalls
- Corporate proxies

**Our solution:** FRP provides a reliable TCP tunnel that bypasses these issues entirely. The WebRTC signaling and media both flow through the FRP tunnel.

### 2. Simplified Architecture

Without TURN:
- Fewer moving parts
- Lower latency (no relay hop)
- No TURN server maintenance
- No credential management complexity

### 3. Current Use Case

Our v1 deployment model:
- Single R58 device per installation
- Remote access via FRP tunnel
- Local network access via LAN/Tailscale
- Small number of simultaneous guests (< 10)

---

## Connection Types

### Local Network (LAN)

**Path:** Browser → 192.168.x.x:8889 → MediaMTX  
**Latency:** < 50ms  
**ICE:** Host candidates (direct connection)

```javascript
// Example WHEP URL for local access
const whepUrl = 'http://192.168.1.24:8889/cam0/whep'
```

### Tailscale P2P

**Path:** Browser → 100.x.x.x:8889 → MediaMTX  
**Latency:** 50-150ms (depends on P2P route)  
**ICE:** Tailscale WireGuard tunnel

```javascript
// Example WHEP URL for Tailscale
const whepUrl = 'http://100.98.37.53:8889/cam0/whep'
```

### Remote via FRP

**Path:** Browser → HTTPS VPS → FRP → R58 → MediaMTX  
**Latency:** 100-300ms (depends on VPS location)  
**ICE:** TCP through FRP tunnel

```javascript
// Example WHEP URL for remote access
const whepUrl = 'https://app.itagenten.no/cam0/whep'
```

---

## When TURN Would Be Needed

### Future Scenarios

| Scenario | Why TURN Needed | Priority |
|----------|----------------|----------|
| **Multiple R58 Devices** | Direct P2P between devices | Medium |
| **Strict Corporate Firewalls** | Guest behind firewall that blocks WebRTC | Low |
| **Mobile Guests** | Cellular networks with restricted UDP | Low |
| **High Guest Count** | Reduce VPS bandwidth costs | Low |

### Implementation Options

If TURN becomes necessary:

#### Option 1: Cloudflare TURN

**Pros:**
- Managed service
- Global edge network
- Automatic scaling

**Cons:**
- Requires Cloudflare account
- API token management
- Added complexity

**Setup:**
```javascript
const iceServers = [
  { urls: 'stun:stun.cloudflare.com:3478' },
  {
    urls: 'turns:turn.cloudflare.com:5349?transport=tcp',
    username: tokenId,
    credential: apiToken
  }
]
```

#### Option 2: Self-hosted coturn

**Pros:**
- Full control
- No external dependencies
- Can run on same VPS

**Cons:**
- Requires maintenance
- Need to manage certificates
- Bandwidth costs

**Setup:**
```bash
# Install coturn on VPS
apt-get install coturn

# Configure /etc/turnserver.conf
listening-port=3478
tls-listening-port=5349
realm=turn.itagenten.no
```

---

## Historical Context

### Cloudflare Experiments (Dec 2025)

We extensively tested Cloudflare solutions:

1. **Cloudflare Tunnel** - HTTP/HTTPS only, can't carry WebRTC UDP
2. **Cloudflare TURN** - Works but adds latency without solving core issue
3. **Cloudflare Calls (SFU)** - Too complex for our use case

**Conclusion:** FRP provides better reliability and lower latency for our architecture.

See [`docs/CLOUDFLARE_HISTORY.md`](../CLOUDFLARE_HISTORY.md) for details.

---

## Testing Connectivity

### Check WebRTC Connection Type

```javascript
// In browser console after establishing WHEP connection
pc.getStats().then(stats => {
  stats.forEach(report => {
    if (report.type === 'candidate-pair' && report.state === 'succeeded') {
      console.log('Local:', report.localCandidateId)
      console.log('Remote:', report.remoteCandidateId)
      console.log('Type:', report.candidateType) // 'host', 'srflx', 'relay'
    }
  })
})
```

### Expected Results

| Access Method | Candidate Type | RTT |
|--------------|----------------|-----|
| LAN | host | < 5ms |
| Tailscale | host (via WireGuard) | 20-100ms |
| FRP | srflx (server reflexive) | 100-300ms |

---

## Troubleshooting

### WebRTC Not Connecting

1. **Check MediaMTX is running:**
   ```bash
   curl http://localhost:9997/v3/paths/list
   ```

2. **Verify FRP tunnel:**
   ```bash
   systemctl status frpc
   nc -zv 65.109.32.111 10022
   ```

3. **Test WHEP endpoint:**
   ```bash
   curl -X POST http://localhost:8889/cam0/whep \
     -H "Content-Type: application/sdp" \
     -d "v=0..."
   ```

### High Latency

- **LAN:** Check network congestion, should be < 50ms
- **Tailscale:** Check P2P status with `tailscale status`
- **FRP:** Check VPS location and bandwidth

---

## Configuration Files

### MediaMTX ICE Configuration

[`mediamtx.yml`](../../mediamtx.yml):
```yaml
# STUN servers for ICE gathering
webrtcICEServers2:
  - url: stun:stun.l.google.com:19302

# NAT 1:1 mapping for FRP
webrtcICEHostNAT1To1IPs: ["65.109.32.111"]

# TCP fallback for FRP tunnel
webrtcLocalTCPAddress: :8190
```

### FRP Configuration

R58 [`/etc/frp/frpc.ini`]:
```ini
[common]
server_addr = 65.109.32.111
server_port = 7000
token = <secure-token>

[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 10022

[mediamtx]
type = tcp
local_ip = 127.0.0.1
local_port = 8889
remote_port = 18889
```

---

## Related Documentation

- [System Map](../ops/system-map.md) - Overall architecture
- [Cloudflare History](../CLOUDFLARE_HISTORY.md) - Why we don't use Cloudflare
- [Current Architecture](../CURRENT_ARCHITECTURE.md) - Complete system overview
- [Debug Runbook](../ops/debug-runbook.md) - Troubleshooting procedures

---

## Summary

**Current approach:** FRP tunnel + STUN-only WebRTC  
**Status:** Production-ready, tested, reliable  
**TURN status:** Not needed for v1, documented options for future

The FRP-based approach provides:
- ✅ Reliable connectivity through any NAT
- ✅ Low latency (no relay hop)
- ✅ Simple architecture
- ✅ Easy troubleshooting
- ✅ Cost-effective (no TURN bandwidth costs)

