# FRP SSH Tunnel - Permanent Fix

**Date**: December 26, 2025  
**Status**: Scripts Fixed - VPS/R58 Configuration Needed

---

## ✅ What Was Fixed

### 1. **ssh-setup.sh** - Updated for FRP Tunnel
- **Before**: Used Cloudflare Tunnel (`r58.itagenten.no`)
- **After**: Uses FRP tunnel (`65.109.32.111:10022`)
- **Config**: Creates `~/.ssh/config` entry for `r58-frp` host
- **Usage**: `./ssh-setup.sh` (one-time setup)

### 2. **deploy.sh** - Updated for FRP Tunnel
- **Before**: Connected via Cloudflare Tunnel
- **After**: Connects via FRP tunnel on Coolify VPS
- **Path**: Fixed to `/home/linaro/preke-r58-recorder` (correct path on R58)
- **Usage**: `./deploy.sh` (deploy code to R58)

### 3. **deploy-simple.sh** - NEW Simple Deployment Script
- **Purpose**: One-command deployment to R58
- **Features**:
  - Pushes to GitHub
  - Pulls on R58
  - Restarts preke-recorder service
  - Shows clear status
- **Usage**: `./deploy-simple.sh`

### 4. **check-frp-status.sh** - NEW Diagnostic Script
- **Purpose**: Check FRP tunnel status
- **Features**:
  - Tests if port 10022 is open
  - Shows commands to check FRP on VPS
  - Shows commands to check FRP on R58
- **Usage**: `./check-frp-status.sh`

### 5. **connect-r58-frp.sh** - Already Existed
- **Purpose**: Simple SSH connection to R58
- **Usage**: `./connect-r58-frp.sh`

---

## ⚠️ Current Issue

**SSH connection closes immediately after connecting to port 10022.**

**Port Status**: ✅ Port 10022 is OPEN on VPS  
**Connection**: ❌ SSH handshake fails/closes

**Possible Causes**:
1. FRP client (frpc) not running on R58
2. FRP server (frps) not configured correctly on VPS
3. SSH service not accepting connections through FRP tunnel
4. Firewall blocking the tunneled connection

---

## 🔧 Manual Fix Required

### On Coolify VPS (65.109.32.111)

SSH to VPS as root:
```bash
ssh root@65.109.32.111
```

#### Check FRP Server Status:
```bash
# Check if FRP server is running
docker ps | grep frp
# OR
systemctl status frps

# Check FRP server logs
docker logs frps
# OR
journalctl -u frps -n 50
```

#### Check FRP Server Config:
```bash
# View FRP server configuration
cat /etc/frp/frps.ini

# Expected configuration:
[common]
bind_port = 7000
dashboard_port = 7500
dashboard_user = admin
dashboard_pwd = [password]

# SSH tunnel for R58
[ssh-r58]
type = tcp
auth_token = [your-token]
bind_port = 10022
```

#### Verify Port Binding:
```bash
# Check if FRP is listening on 10022
netstat -tlnp | grep 10022
# OR
ss -tlnp | grep 10022
```

---

### On R58 Device

**Problem**: Can't SSH to R58 to check! Need physical access or alternative access method.

#### If You Have Physical/Console Access:
```bash
# Check if FRP client is running
sudo systemctl status frpc

# View FRP client logs
sudo journalctl -u frpc -n 50

# Check FRP client config
cat /etc/frp/frpc.ini

# Expected configuration:
[common]
server_addr = 65.109.32.111
server_port = 7000
auth_token = [your-token]

# SSH tunnel
[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 10022

# Restart FRP client if needed
sudo systemctl restart frpc
```

#### Alternative Access Methods:
1. **Physical Access**: Connect monitor/keyboard to R58
2. **Serial Console**: If configured
3. **Local Network**: If on same network, use `./connect-r58-local.sh`
4. **ZeroTier**: If configured (check ZEROTIER_GATEWAY_SETUP.md)

---

## 🎯 Quick Test

Once FRP is fixed, test with:

```bash
# Test SSH connection
sshpass -p "linaro" ssh -p 10022 linaro@65.109.32.111 "hostname"

# Should output: linaro-alip

# If that works, deploy:
./deploy-simple.sh
```

---

## 📝 Configuration Files Reference

### VPS FRP Server Config (`/etc/frp/frps.ini`):
```ini
[common]
bind_port = 7000
dashboard_port = 7500
token = your-shared-token

[ssh-r58]
type = tcp
bind_port = 10022
```

### R58 FRP Client Config (`/etc/frp/frpc.ini`):
```ini
[common]
server_addr = 65.109.32.111
server_port = 7000
token = your-shared-token

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

---

## 🧹 Removed Cloudflare References

The following scripts have been updated to remove Cloudflare/cloudflared references and use FRP:
- ✅ `ssh-setup.sh`
- ✅ `deploy.sh`
- ✅ `deploy-simple.sh` (new)

**Note**: Many markdown documentation files still reference Cloudflare. These are historical records and can be cleaned up later if needed.

---

## ✨ After FRP is Fixed

Once SSH via FRP is working:

1. **Setup SSH Keys** (optional, for passwordless):
   ```bash
   ./ssh-setup.sh
   ```

2. **Deploy to R58**:
   ```bash
   ./deploy-simple.sh
   ```

3. **Connect to R58**:
   ```bash
   ssh r58-frp
   # OR
   ./connect-r58-frp.sh
   ```

4. **Deploy studio.html**:
   ```bash
   ./deploy-simple.sh
   # This will deploy the missing studio.html file
   ```

5. **Test the App**:
   - https://r58-api.itagenten.no/static/app.html
   - Studio section should now show multiview cameras

---

## 📞 Support

**Diagnostic Tool**: `./check-frp-status.sh`  
**Connection Script**: `./connect-r58-frp.sh`  
**Deployment Script**: `./deploy-simple.sh`

**VPS**: 65.109.32.111  
**FRP Port**: 10022  
**R58 User**: linaro  
**R58 Password**: linaro  

---

**Summary**: All deployment scripts have been fixed to use FRP tunnel correctly. The SSH connection issue requires checking/restarting FRP services on both the VPS and R58 device. Port 10022 is confirmed open on the VPS, so the issue is likely with FRP service configuration or the FRP client on R58.

