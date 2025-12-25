# frp + MediaMTX WebRTC Setup Guide

**Date**: December 22, 2025  
**Status**: 📋 Configuration Guide  
**Goal**: Remote WebRTC access to R58 via frp without TURN relay

---

## Overview

This guide configures frp to properly proxy WebRTC traffic from R58 to remote users. The key is configuring MediaMTX to advertise the VPS public IP as its ICE candidate.

```
┌─────────────┐         ┌─────────────────────┐         ┌─────────────┐
│    R58      │ ──────> │  VPS (frps server)  │ <────── │  Browser    │
│  MediaMTX   │   TCP   │  Public IP: 1.2.3.4 │  WebRTC │             │
│  + frpc     │   UDP   │                     │         │             │
└─────────────┘         └─────────────────────┘         └─────────────┘

Key: MediaMTX advertises VPS IP (1.2.3.4) in ICE candidates
     so browsers connect to VPS, frp forwards to R58
```

---

## Prerequisites

1. **VPS** with public IP (~$5/month from DigitalOcean, Vultr, Linode, etc.)
2. **Domain** (optional but recommended)
3. **R58** running MediaMTX
4. **Ports** open on VPS firewall:
   - TCP 7000 (frp control)
   - TCP 8889 (MediaMTX WHEP signaling)
   - UDP 8189 (WebRTC media)
   - TCP 8443 (VDO.ninja signaling - optional)

---

## Step 1: VPS Setup (frp Server)

### 1.1 Install frp on VPS

```bash
# SSH to your VPS
ssh root@your-vps-ip

# Download latest frp (check https://github.com/fatedier/frp/releases for latest version)
cd /opt
wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz
tar -xzf frp_0.52.3_linux_amd64.tar.gz
mv frp_0.52.3_linux_amd64 frp
cd frp
```

### 1.2 Configure frp Server (frps.toml)

Create `/opt/frp/frps.toml`:

```toml
# frps.toml - frp Server Configuration
# Run on VPS with public IP

bindPort = 7000

# Authentication (IMPORTANT: change this!)
auth.method = "token"
auth.token = "your-super-secret-token-change-this"

# UDP support for WebRTC
udpHolePunchingEnabled = true

# Dashboard (optional - for monitoring)
webServer.addr = "0.0.0.0"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "your-dashboard-password"

# Logging
log.to = "/var/log/frps.log"
log.level = "info"
log.maxDays = 7
```

### 1.3 Create systemd Service for frps

Create `/etc/systemd/system/frps.service`:

```ini
[Unit]
Description=frp Server
After=network.target

[Service]
Type=simple
ExecStart=/opt/frp/frps -c /opt/frp/frps.toml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 1.4 Start frp Server

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable frps
sudo systemctl start frps

# Check status
sudo systemctl status frps

# View logs
sudo journalctl -u frps -f
```

### 1.5 Open Firewall Ports on VPS

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 7000/tcp    # frp control
sudo ufw allow 7500/tcp    # frp dashboard (optional)
sudo ufw allow 8889/tcp    # MediaMTX WHEP
sudo ufw allow 8189/udp    # WebRTC media
sudo ufw allow 8443/tcp    # VDO.ninja signaling (optional)
sudo ufw reload

# Or iptables
sudo iptables -A INPUT -p tcp --dport 7000 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8889 -j ACCEPT
sudo iptables -A INPUT -p udp --dport 8189 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8443 -j ACCEPT
```

---

## Step 2: R58 Configuration

### 2.1 Install frp Client on R58

```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Download frp for ARM64
cd /opt
sudo wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_arm64.tar.gz
sudo tar -xzf frp_0.52.3_linux_arm64.tar.gz
sudo mv frp_0.52.3_linux_arm64 frp
```

### 2.2 Configure frp Client (frpc.toml)

Create `/opt/frp/frpc.toml`:

```toml
# frpc.toml - frp Client Configuration
# Run on R58

# Server connection
serverAddr = "YOUR_VPS_IP_HERE"  # Replace with your VPS public IP
serverPort = 7000

# Authentication (must match server)
auth.method = "token"
auth.token = "your-super-secret-token-change-this"

# Logging
log.to = "/var/log/frpc.log"
log.level = "info"

# =============================================
# PROXY DEFINITIONS
# =============================================

# MediaMTX WHEP Signaling (TCP)
[[proxies]]
name = "mediamtx-whep"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8889
remotePort = 8889

# WebRTC Media via UDP Mux (UDP) - CRITICAL FOR WEBRTC!
[[proxies]]
name = "webrtc-udp"
type = "udp"
localIP = "127.0.0.1"
localPort = 8189
remotePort = 8189

# VDO.ninja Signaling (TCP) - Optional
[[proxies]]
name = "vdoninja-wss"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8443
remotePort = 8443

# MediaMTX API (TCP) - Optional, for debugging
[[proxies]]
name = "mediamtx-api"
type = "tcp"
localIP = "127.0.0.1"
localPort = 9997
remotePort = 9997
```

### 2.3 Create systemd Service for frpc on R58

Create `/etc/systemd/system/frpc.service`:

```ini
[Unit]
Description=frp Client
After=network.target mediamtx.service

[Service]
Type=simple
ExecStart=/opt/frp/frpc -c /opt/frp/frpc.toml
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

---

## Step 3: MediaMTX Configuration (CRITICAL!)

This is the most important step. MediaMTX must advertise the VPS public IP in ICE candidates.

### 3.1 Update MediaMTX Configuration

Edit `/opt/mediamtx/mediamtx.yml` on R58:

```yaml
# MediaMTX configuration for R58 with frp
logLevel: info
logDestinations: [stdout]

# API
api: yes
apiAddress: 127.0.0.1:9997

# RTSP settings
rtspAddress: :8554

# RTMP settings
rtmpAddress: :1935

# HLS settings (optional - you said no HLS)
# hlsAddress: :8888

# SRT settings
srtAddress: :8890

# =============================================
# WebRTC settings - CONFIGURED FOR FRP
# =============================================
webrtcAddress: :8889
webrtcAllowOrigin: "*"
webrtcEncryption: yes
webrtcServerKey: /opt/mediamtx/server.key
webrtcServerCert: /opt/mediamtx/server.crt

# CRITICAL: Use single UDP port for all WebRTC (easier to proxy via frp)
webrtcICEUDPMuxAddress: :8189

# CRITICAL: Tell browsers to connect to VPS IP, not R58 local IP
# Replace YOUR_VPS_PUBLIC_IP with your actual VPS IP (e.g., 1.2.3.4)
webrtcICEHostNAT1To1IPs: 
  - YOUR_VPS_PUBLIC_IP

# Optional: Add STUN servers for fallback
webrtcICEServers2:
  - url: stun:stun.l.google.com:19302

# Paths configuration
paths:
  cam0:
    source: publisher
  cam1:
    source: publisher
  cam2:
    source: publisher
  cam3:
    source: publisher
  mixer_program:
    source: publisher
  guest1:
    source: publisher
  guest2:
    source: publisher
```

### 3.2 Key Configuration Explained

| Setting | Value | Purpose |
|---------|-------|---------|
| `webrtcICEUDPMuxAddress` | `:8189` | All WebRTC UDP goes through ONE port |
| `webrtcICEHostNAT1To1IPs` | `[VPS_IP]` | Browsers connect to VPS, not R58 local IP |
| `webrtcEncryption` | `yes` | Required for browsers (DTLS) |

### 3.3 Generate SSL Certificates (if not already done)

```bash
# On R58
cd /opt/mediamtx
sudo openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes \
  -subj "/C=NO/ST=Oslo/L=Oslo/O=R58/CN=mediamtx.local"
sudo chmod 600 server.key
```

### 3.4 Restart MediaMTX

```bash
sudo systemctl restart mediamtx
sudo systemctl status mediamtx

# Check logs for any errors
sudo journalctl -u mediamtx -f
```

---

## Step 4: Start frp Client on R58

```bash
# Enable and start frpc
sudo systemctl daemon-reload
sudo systemctl enable frpc
sudo systemctl start frpc

# Check status
sudo systemctl status frpc

# View logs
sudo journalctl -u frpc -f
```

---

## Step 5: Test the Setup

### 5.1 Verify frp Connections

**On VPS** (check dashboard):
```
http://YOUR_VPS_IP:7500
Username: admin
Password: your-dashboard-password
```

Should show connected proxies:
- `mediamtx-whep` (TCP)
- `webrtc-udp` (UDP)
- `vdoninja-wss` (TCP)

### 5.2 Test MediaMTX API

```bash
# From your Mac (or any internet-connected device)
curl http://YOUR_VPS_IP:9997/v3/paths/list
```

Should return JSON with camera paths.

### 5.3 Test WHEP Connection

```bash
# Test WHEP signaling
curl -v http://YOUR_VPS_IP:8889/cam0/whep
```

Should return WebRTC SDP with VPS IP in ICE candidates (not 192.168.1.24).

### 5.4 Test WebRTC in Browser

Open in browser:
```
http://YOUR_VPS_IP:8889/cam0
```

Or use VDO.ninja with MediaMTX:
```
https://vdo.ninja/?view=cam0&mediamtx=YOUR_VPS_IP:8889
```

---

## Step 6: VDO.ninja Integration (Optional)

If you want VDO.ninja's mixer/director features via frp:

### 6.1 Access VDO.ninja Signaling

```
wss://YOUR_VPS_IP:8443
```

### 6.2 Director URL

```
https://YOUR_VPS_IP:8443/?director=r58studio&wss=YOUR_VPS_IP:8443
```

### 6.3 View Cameras via MediaMTX WHEP

```
https://vdo.ninja/?view=cam0&mediamtx=YOUR_VPS_IP:8889
```

---

## Troubleshooting

### Problem: ICE candidates still show local IP

**Check MediaMTX logs**:
```bash
sudo journalctl -u mediamtx | grep -i "ice\|nat"
```

**Verify config loaded**:
```bash
cat /opt/mediamtx/mediamtx.yml | grep -A 2 webrtcICEHostNAT1To1IPs
```

**Solution**: Ensure the VPS IP is correctly set in `webrtcICEHostNAT1To1IPs`.

---

### Problem: UDP connection fails

**Check frp UDP proxy**:
```bash
# On VPS
ss -ulnp | grep 8189

# On R58
sudo journalctl -u frpc | grep -i udp
```

**Check firewall**:
```bash
# On VPS
sudo ufw status | grep 8189
```

**Solution**: Ensure UDP port 8189 is open on VPS firewall.

---

### Problem: frpc can't connect to frps

**Check frpc logs**:
```bash
sudo journalctl -u frpc -f
```

**Common causes**:
- Wrong server IP in `frpc.toml`
- Token mismatch
- Port 7000 blocked on VPS

---

### Problem: Browser shows "ICE failed"

**Check in browser console (F12)**:
- Look for ICE candidate types
- Should see candidates with VPS IP

**If candidates show local IP**:
- MediaMTX config not applied correctly
- Restart MediaMTX: `sudo systemctl restart mediamtx`

---

## Security Considerations

### 1. Use Strong Token
```bash
# Generate random token
openssl rand -hex 32
```

### 2. Enable TLS for frp (Production)
Add to `frps.toml`:
```toml
tls.certFile = "/path/to/cert.pem"
tls.keyFile = "/path/to/key.pem"
```

### 3. Firewall Best Practices
- Only open required ports
- Consider using fail2ban on VPS
- Use VPN for frp control port (7000)

### 4. Domain + Let's Encrypt (Optional)
```bash
# Install certbot on VPS
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Use in configs
```

---

## Cost Summary

| Item | Monthly Cost |
|------|--------------|
| VPS (1GB RAM) | $5-6 |
| Domain (optional) | ~$1 |
| **Total** | **~$6/month** |

Recommended VPS providers:
- DigitalOcean ($6/month)
- Vultr ($5/month)
- Linode ($5/month)
- Hetzner (~$4/month)

---

## Quick Start Commands

### On VPS

```bash
# Install
cd /opt && wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_amd64.tar.gz
tar -xzf frp_0.52.3_linux_amd64.tar.gz && mv frp_0.52.3_linux_amd64 frp

# Configure (edit frps.toml)
nano /opt/frp/frps.toml

# Start
sudo systemctl daemon-reload && sudo systemctl enable frps && sudo systemctl start frps
```

### On R58

```bash
# Install
cd /opt && sudo wget https://github.com/fatedier/frp/releases/download/v0.52.3/frp_0.52.3_linux_arm64.tar.gz
sudo tar -xzf frp_0.52.3_linux_arm64.tar.gz && sudo mv frp_0.52.3_linux_arm64 frp

# Configure (edit frpc.toml)
sudo nano /opt/frp/frpc.toml

# Update MediaMTX config
sudo nano /opt/mediamtx/mediamtx.yml
# Add: webrtcICEUDPMuxAddress: :8189
# Add: webrtcICEHostNAT1To1IPs: [YOUR_VPS_IP]

# Restart services
sudo systemctl restart mediamtx
sudo systemctl daemon-reload && sudo systemctl enable frpc && sudo systemctl start frpc
```

---

## Expected Results

After setup:

| Feature | Status | Latency |
|---------|--------|---------|
| MediaMTX WHEP viewing | ✅ Works | ~40-80ms |
| WebRTC direct connection | ✅ Works | ~40-80ms |
| No TURN relay needed | ✅ | - |
| VDO.ninja integration | ✅ Works | ~40-80ms |

This is **better than TURN** (100-200ms) but not as good as **direct local** (10-50ms).

---

## Files Changed

| File | Location | Changes |
|------|----------|---------|
| `frps.toml` | VPS `/opt/frp/` | New file |
| `frps.service` | VPS `/etc/systemd/system/` | New file |
| `frpc.toml` | R58 `/opt/frp/` | New file |
| `frpc.service` | R58 `/etc/systemd/system/` | New file |
| `mediamtx.yml` | R58 `/opt/mediamtx/` | Added NAT1To1 config |

---

## Next Steps

1. **Get a VPS** (~$5/month)
2. **Get the VPS public IP**
3. **Switch to agent mode** and I'll help you deploy:
   - Install frp on VPS
   - Install frp on R58
   - Configure MediaMTX
   - Test WebRTC connection

Let me know when you have a VPS and I'll help with the deployment!

---

## Summary

**frp CAN work with WebRTC** if:
1. ✅ MediaMTX uses UDP Mux (single port)
2. ✅ MediaMTX advertises VPS IP in ICE candidates
3. ✅ frp proxies both TCP (signaling) and UDP (media)

This gives you:
- **Remote WebRTC access** without TURN relay
- **Lower latency** than TURN (~40-80ms vs 100-200ms)
- **Cost**: ~$5-6/month for VPS

