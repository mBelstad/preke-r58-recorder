# R58 Remote Access - Complete Guide

**Last Updated**: January 8, 2026  
**Status**: ✅ STABLE & WORKING (Same-Domain Proxy + Tailscale P2P)

---

## 🚀 Quick Start

### Connect to R58
```bash
./connect-r58-frp.sh                    # Interactive shell (via FRP)
./connect-r58-frp.sh "ls -la"          # Run command
```

### Deploy Code to R58
```bash
./deploy-simple.sh
```

### Access Web Interface

**Preke Studio Web App (Vue Frontend):**
- **Main App**: https://app.itagenten.no/
- **Recorder**: https://app.itagenten.no/#/recorder
- **Mixer**: https://app.itagenten.no/#/mixer
- **Library**: https://app.itagenten.no/#/library
- **Admin**: https://app.itagenten.no/#/admin

**VDO.ninja (Self-Hosted):**
- **Mixer**: https://r58-vdo.itagenten.no/mixer.html?room=studio&password=preke-r58-2024
- **Director**: https://r58-vdo.itagenten.no/?director=studio&password=preke-r58-2024

**Via Tailscale (P2P - Preferred for WHEP):**
- **WHEP cam0**: https://linaro-alip.tailab6fd7.ts.net/cam0/whep
- **WHEP cam2**: https://linaro-alip.tailab6fd7.ts.net/cam2/whep
- **WHEP cam3**: https://linaro-alip.tailab6fd7.ts.net/cam3/whep

**Direct API Access (for testing):**
- **API Health**: https://app.itagenten.no/health
- **API Status**: https://app.itagenten.no/status
- **Legacy App**: https://app.itagenten.no/static/app.html

---

## 🌐 Tailscale P2P (PREFERRED)

Tailscale provides direct P2P connectivity without routing through VPS.

### Why Tailscale?
| Method | Bandwidth Cost | Latency | Reliability |
|--------|---------------|---------|-------------|
| **Tailscale P2P** | **$0** | ~2ms | ✅ Excellent |
| **Tailscale Relay** | **$0** | ~50ms | ✅ Good |
| FRP/VPS | You pay | ~100ms | ⚠️ Depends on VPS |

### Tailscale URLs (Public - No Install Needed)
```
https://linaro-alip.tailab6fd7.ts.net/cam0/whep
https://linaro-alip.tailab6fd7.ts.net/cam2/whep
https://linaro-alip.tailab6fd7.ts.net/cam3/whep
```

### VDO.ninja Links
```
https://vdo.ninja/?whepplay=https://linaro-alip.tailab6fd7.ts.net/cam0/whep
https://vdo.ninja/?whepplay=https://linaro-alip.tailab6fd7.ts.net/cam2/whep
https://vdo.ninja/?whepplay=https://linaro-alip.tailab6fd7.ts.net/cam3/whep
```

### P2P Direct Access (Tailscale Users Only)
```bash
# Tailscale IP
curl http://100.98.37.53:8000/health

# Check P2P status
tailscale ping linaro-alip
# Expected: "pong via 192.168.x.x:xxxxx in 2ms" (P2P)
# If shows "via DERP(xxx)" = relay mode
```

### Tailscale on R58
```bash
# Check status
tailscale status

# Services (auto-start on boot)
sudo systemctl status tailscale-userspace   # Main daemon
sudo systemctl status tailscale-funnel       # Funnel for public access
```

**See full documentation**: [docs/TAILSCALE_P2P_INTEGRATION.md](docs/TAILSCALE_P2P_INTEGRATION.md)

---

## 📡 FRP Tunnel (BACKUP)

FRP is used as backup when Tailscale is unavailable.

### FRP Tunnel Architecture

```
Your Mac
    ↓ SSH (via SSH key - ~/.ssh/r58_key)
    ↓
Coolify VPS (65.109.32.111:10022)
    ↓ FRP Tunnel
    ↓
R58 Device (local port 22)
```

**Key Components**:
- **FRP Server**: Running on Coolify VPS
- **FRP Client**: Running on R58 device
- **Tunnel Port**: 10022 (SSH), 18000 (API), 18889 (MediaMTX)
- **SSH Key**: `~/.ssh/r58_key` (no passphrase, auto-generated)

---

## 🔧 Available Scripts

### Connection Scripts

#### `connect-r58-frp.sh` (PRIMARY - USE THIS!)
**Purpose**: SSH to R58 via FRP tunnel  
**Auth**: SSH key (`~/.ssh/r58_key`) - faster & more reliable than password  
**Features**:
- ConnectTimeout=15 (fails fast instead of hanging)
- ServerAliveInterval=30 (detects dead connections)
- TCPKeepAlive (connection health monitoring)

**Usage**: 
```bash
./connect-r58-frp.sh                    # Interactive shell
./connect-r58-frp.sh "ls -la"          # Run command
./connect-r58-frp.sh "sudo systemctl status preke-recorder"
./connect-r58-frp.sh --password "cmd"  # Force password auth (fallback)
```

**Stability**: ✅ Reliable with SSH key auth

#### `connect-r58-local.sh` (BACKUP)
**Purpose**: SSH to R58 on local network  
**Usage**:
```bash
./connect-r58-local.sh                  # Auto-detect IP
./connect-r58-local.sh 192.168.0.100   # Specific IP
```

**When to use**: When FRP is down or you're on the same network

---

### Deployment Scripts

#### `deploy-simple.sh` (RECOMMENDED)
**Purpose**: One-command deployment to R58  
**What it does**:
1. Commits and pushes to GitHub
2. SSHs to R58 via FRP
3. Pulls latest code
4. Restarts preke-recorder service

**Usage**:
```bash
./deploy-simple.sh
```

#### `deploy.sh` (ALTERNATIVE)
**Purpose**: More detailed deployment with setup steps  
**Usage**:
```bash
./deploy.sh
```

---

### Setup Scripts

#### `ssh-setup.sh`
**Purpose**: Configure SSH keys for passwordless access  
**Usage**:
```bash
./ssh-setup.sh
```

**Note**: After running this, you won't need to enter password for SSH.

#### `check-frp-status.sh`
**Purpose**: Diagnostic tool for FRP tunnel  
**Usage**:
```bash
./check-frp-status.sh
```

Shows:
- Port status
- Commands to check FRP on VPS
- Commands to check FRP on R58

---

## 🔐 Credentials

### R58 Device
- **User**: linaro
- **Password**: linaro
- **SSH via FRP**: `ssh -p 10022 linaro@65.109.32.111`
- **Local IP**: Usually 192.168.0.100 or 192.168.68.50-58

### Coolify VPS
- **IP**: 65.109.32.111
- **FRP SSH Port**: 10022
- **FRP API Port**: 18000
- **FRP MediaMTX Port**: 18889
- **FRP WebRTC Port**: 18189 (UDP)

---

## 🛠️ Troubleshooting

### SSH Connection Fails

1. **Check if port is open**:
   ```bash
   nc -zv 65.109.32.111 10022
   ```

2. **Check FRP status**:
   ```bash
   ./check-frp-status.sh
   ```

3. **Try local connection**:
   ```bash
   ./connect-r58-local.sh
   ```

### Deployment Fails

1. **Check if R58 is accessible**:
   ```bash
   ./connect-r58-frp.sh "hostname"
   ```

2. **Check service status on R58**:
   ```bash
   ./connect-r58-frp.sh "sudo systemctl status preke-recorder"
   ```

3. **View service logs**:
   ```bash
   ./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 50"
   ```

### FRP Tunnel Not Working

**On Coolify VPS** (need root access):
```bash
ssh root@65.109.32.111
docker ps | grep frp          # Check if FRP server running
docker restart frps           # Restart FRP server
docker logs frps             # View logs
```

**On R58** (via local or physical access):
```bash
sudo systemctl status frpc   # Check FRP client
sudo systemctl restart frpc  # Restart FRP client
sudo journalctl -u frpc -n 50  # View logs
```

---

## 📚 Configuration Files

### FRP Client on R58 (`/etc/frp/frpc.ini`)
```ini
[common]
server_addr = 65.109.32.111
server_port = 7000
token = [shared-token]

[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 10022

[api]
type = tcp
local_ip = 127.0.0.1
local_port = 8000
remote_port = 18000

[mediamtx]
type = tcp
local_ip = 127.0.0.1
local_port = 8889
remote_port = 18889

[mediamtx-webrtc]
type = udp
local_ip = 127.0.0.1
local_port = 8189
remote_port = 18189

[mediamtx-hls]
type = tcp
local_ip = 127.0.0.1
local_port = 8888
remote_port = 18888
```

### FRP Server on VPS (`/etc/frp/frps.ini`)
```ini
[common]
bind_port = 7000
dashboard_port = 7500
token = [shared-token]

[ssh-r58]
type = tcp
bind_port = 10022
```

---

## 📖 Related Documentation

- **FRP_SSH_FIX.md** - Detailed troubleshooting guide
- **DEPLOYMENT_SUCCESS_DEC26.md** - Latest deployment results
- **TESTING_SUMMARY.md** - Browser testing report
- **SESSION_SUMMARY_DEC26.md** - Complete session overview

---

## ✅ Tested & Verified

- ✅ SSH connection 100% stable (5/5 tests passed)
- ✅ Deployment successful
- ✅ All web interfaces accessible
- ✅ Camera streams working
- ✅ Recording functionality operational

**Last Test**: December 26, 2025  
**Result**: All systems operational

---

## 🎯 Summary

### Domain Architecture (Same-Domain Proxy)
| Domain | Purpose |
|--------|---------|
| `app.itagenten.no` | **Single entry point** - Vue frontend + API proxy |
| `r58-vdo.itagenten.no` | Self-hosted VDO.ninja |

**Architecture (simplified Jan 2026)**:
- All traffic goes through `app.itagenten.no`
- nginx proxies `/api/*` and `/cam*/whep` to R58 backend
- **No CORS needed** - everything is same-origin
- `r58-api.itagenten.no` redirects to `app.itagenten.no`

### Video Streaming
| Priority | Method | URL Example |
|----------|--------|-------------|
| 1 | **Tailscale Funnel** | `https://linaro-alip.tailab6fd7.ts.net/cam0/whep` |
| 2 | FRP/VPS | `https://r58-api.itagenten.no/cam0/whep` |

### SSH Access
| Priority | Method | Script |
|----------|--------|--------|
| 1 | **FRP Tunnel** | `./connect-r58-frp.sh` |
| 2 | Local Network | `./connect-r58-local.sh` |

### Electron App Discovery
| Priority | Method | Connection Type |
|----------|--------|-----------------|
| 1 | **Tailscale** | P2P or DERP |
| 2 | USB-C Direct | 192.168.42.1 |
| 3 | mDNS | r58.local |
| 4 | LAN Scan | Subnet scan |

**Tailscale = P2P, $0 bandwidth cost!**

---

## 🖥️ Coolify VPS Access

### Connect to VPS
```bash
./connect-coolify-vps.sh                    # Interactive shell
./connect-coolify-vps.sh "docker ps"       # Run command
```

### VPS Details
- **IP**: 65.109.32.111
- **User**: root
- **Port**: 22 (standard SSH)
- **SSH Key**: `~/.ssh/coolify_vps_key`

### First-Time Setup
The VPS requires SSH key auth. Add your public key via Coolify dashboard:
1. Log into Coolify web interface
2. Go to Settings → SSH Keys  
3. Add content of `~/.ssh/coolify_vps_key.pub`

Or if you have existing VPS access, run:
```bash
ssh-copy-id -i ~/.ssh/coolify_vps_key.pub root@65.109.32.111
```

---

Everything is stable, documented, and working! 🚀

