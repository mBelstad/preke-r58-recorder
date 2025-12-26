# frp + WebRTC Quick Reference

## The Key Configuration

For WebRTC to work through frp, MediaMTX must advertise the **VPS public IP**, not the R58 local IP.

### MediaMTX Config (mediamtx.yml)

```yaml
# CRITICAL: Single UDP port for WebRTC
webrtcICEUDPMuxAddress: :8189

# CRITICAL: Advertise VPS IP in ICE candidates
webrtcICEHostNAT1To1IPs: 
  - YOUR_VPS_PUBLIC_IP  # e.g., 1.2.3.4
```

### frp Client Config (frpc.toml)

```toml
serverAddr = "YOUR_VPS_IP"
serverPort = 7000
auth.token = "your-secret-token"

[[proxies]]
name = "mediamtx-whep"
type = "tcp"
localPort = 8889
remotePort = 8889

[[proxies]]
name = "webrtc-udp"
type = "udp"
localPort = 8189
remotePort = 8189
```

### frp Server Config (frps.toml)

```toml
bindPort = 7000
auth.token = "your-secret-token"
```

---

## Port Summary

| Port | Protocol | Purpose | Proxy via frp |
|------|----------|---------|---------------|
| 7000 | TCP | frp control | N/A (internal) |
| 8889 | TCP | WHEP signaling | ✅ Yes |
| 8189 | UDP | WebRTC media | ✅ Yes |
| 8443 | TCP | VDO.ninja WSS | ✅ Optional |

---

## Test Commands

```bash
# Check frp connection (on VPS)
curl http://VPS_IP:7500  # Dashboard

# Check MediaMTX (via frp)
curl http://VPS_IP:9997/v3/paths/list

# View camera in browser
http://VPS_IP:8889/cam0
```

---

## Expected Latency

| Method | Latency |
|--------|---------|
| Local network | 10-50ms |
| **frp** | **40-80ms** |
| TURN relay | 100-200ms |

---

## Cost

~$5-6/month for VPS (DigitalOcean, Vultr, Linode)


