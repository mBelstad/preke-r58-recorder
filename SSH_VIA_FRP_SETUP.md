# SSH via FRP - Replace Cloudflare Tunnel

**Date**: December 24, 2025  
**Status**: ✅ **CONFIGURED - FIREWALL UPDATE NEEDED**

---

## Summary

FRP can completely replace Cloudflare Tunnel for SSH access to R58. The configuration is complete and working from the VPS, but requires one more Hetzner Cloud Firewall update for external access.

---

## What's Been Configured

### ✅ 1. FRP Client on R58

Added SSH proxy to `/opt/frp/frpc.toml`:

```toml
[[proxies]]
name = "r58-ssh"
type = "tcp"
localIP = "127.0.0.1"
localPort = 22
remotePort = 10022
```

This tunnels R58's SSH (port 22) to VPS port 10022.

### ✅ 2. FRP Server

FRP server logs show:
```
[r58-ssh] tcp proxy listen port [10022]
[r58-ssh] new proxy [r58-ssh] type [tcp] success
[r58-ssh] get a user connection [127.0.0.1:40302]
```

**Status**: Working ✅

### ✅ 3. UFW Firewall on VPS

```bash
ufw allow 10022/tcp comment 'R58 SSH via FRP'
```

Port 10022 is open in UFW.

### ✅ 4. Connection Test from VPS

```bash
# From VPS
$ ssh -p 10022 linaro@localhost
linaro-alip
✅ SSH via FRP is working!
```

**Status**: Working from VPS ✅

---

## Current Status

| Test Location | Status | Details |
|---------------|--------|---------|
| **From VPS localhost** | ✅ Working | SSH connection successful |
| **From Mac (external)** | ⚠️ Timeout | Hetzner Cloud Firewall blocking |

---

## Hetzner Cloud Firewall Update Needed

Just like the other ports, port 10022 needs to be added to the Hetzner Cloud Firewall.

### Steps to Enable External SSH Access

1. Log into **Hetzner Cloud Console**: https://console.hetzner.cloud/
2. Select your server (65.109.32.111)
3. Go to **"Firewalls"** tab
4. Add inbound rule:
   - **Protocol**: TCP
   - **Port**: 10022
   - **Source**: 0.0.0.0/0 (or restrict to your IP)

---

## New SSH Access Method

### After Hetzner Firewall Update

**Old method (via Cloudflare Tunnel):**
```bash
ssh linaro@r58.itagenten.no
```

**New method (via FRP):**
```bash
ssh -p 10022 linaro@65.109.32.111
```

**Or use the helper script:**
```bash
./connect-r58-frp.sh
```

---

## Helper Script

Created: `connect-r58-frp.sh`

```bash
#!/bin/bash
# Connect to R58 via FRP tunnel

./connect-r58-frp.sh                    # Interactive SSH session
./connect-r58-frp.sh "hostname"         # Run single command
./connect-r58-frp.sh "systemctl status" # Check services
```

---

## Comparison: Cloudflare vs FRP

| Feature | Cloudflare Tunnel | FRP |
|---------|-------------------|-----|
| **SSH Access** | ✅ r58.itagenten.no | ✅ 65.109.32.111:10022 |
| **Setup Complexity** | Low | Medium |
| **Dependencies** | Cloudflared service | frpc + SSH tunnel |
| **Latency** | ~50-100ms | ~40-80ms |
| **Cost** | Free | VPS cost ($5/mo) |
| **WebRTC Support** | ❌ No UDP | ✅ Full UDP support |
| **Control** | Cloudflare managed | Self-hosted |

---

## Benefits of Switching to FRP

### 1. Single Solution for Everything

With FRP, you get:
- ✅ SSH access
- ✅ HTTPS API access
- ✅ WebRTC with UDP
- ✅ VDO.ninja with WebSocket
- ✅ All in one tunnel

### 2. No UDP Limitation

Unlike Cloudflare Tunnel, FRP supports UDP, which is **critical for WebRTC**.

### 3. Lower Latency

FRP is typically faster than Cloudflare Tunnel routing.

### 4. Full Control

You control the VPS and can customize routing, ports, and configuration.

---

## Migration Plan

### Phase 1: Test FRP SSH (Current)

1. ✅ Add SSH proxy to FRP config
2. ✅ Test from VPS localhost
3. ⏳ **Update Hetzner Cloud Firewall** (port 10022)
4. ⏳ Test from external network (your Mac)

### Phase 2: Verify All Services

Before disabling Cloudflared, verify these work via FRP:
- ✅ R58 API: `https://r58-api.itagenten.no`
- ✅ MediaMTX: `https://r58-mediamtx.itagenten.no`
- ✅ VDO.ninja: `https://r58-vdo.itagenten.no`
- ⏳ SSH: `ssh -p 10022 linaro@65.109.32.111`

### Phase 3: Disable Cloudflare Tunnel

Once FRP SSH is confirmed working:

```bash
# On R58
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared

# Test FRP SSH still works
ssh -p 10022 linaro@65.109.32.111

# If all good, optionally remove Cloudflared
sudo systemctl mask cloudflared
```

### Phase 4: Update Scripts

Update any deployment or connection scripts to use:
```bash
ssh -p 10022 linaro@65.109.32.111
```

Instead of:
```bash
ssh linaro@r58.itagenten.no
```

---

## DNS Considerations

### Option A: Keep Current Setup

```
r58.itagenten.no → Cloudflare Tunnel (can disable Cloudflared)
65.109.32.111:10022 → FRP SSH
```

### Option B: Point DNS to VPS

Update DNS:
```
r58.itagenten.no A 65.109.32.111
```

Then SSH with:
```bash
ssh -p 10022 linaro@r58.itagenten.no
```

This gives you the same domain-based access but via FRP.

---

## Testing After Hetzner Firewall Update

### 1. Test SSH Connection

```bash
ssh -p 10022 linaro@65.109.32.111
# Should connect to R58
```

### 2. Test with Helper Script

```bash
./connect-r58-frp.sh "hostname"
# Should return: linaro-alip
```

### 3. Verify Services Still Work

```bash
./connect-r58-frp.sh "systemctl status mediamtx --no-pager"
```

---

## Rollback Plan

If you need to revert to Cloudflare Tunnel:

```bash
# On R58
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Verify Cloudflare SSH works
ssh linaro@r58.itagenten.no
```

The FRP SSH proxy can run alongside Cloudflared without conflicts.

---

## Current Complete Port Mapping

| Service | R58 Port | VPS Port | Access |
|---------|----------|----------|--------|
| **SSH** | 22 | **10022** | `65.109.32.111:10022` |
| R58 API | 8000 | 18000 | `https://r58-api.itagenten.no` |
| MediaMTX WHEP | 8889 | 18889 | `https://r58-mediamtx.itagenten.no` |
| WebRTC UDP | 8189 | 18189 | (UDP for media) |
| VDO.ninja | 8443 | 18443 | `https://r58-vdo.itagenten.no` |
| MediaMTX API | 9997 | 19997 | (via r58-mediamtx) |

---

## Summary

### ✅ What's Working Now

- SSH via FRP from VPS localhost ✅
- FRP proxy configured correctly ✅
- All other services via FRP working ✅

### ⏳ What's Needed

- **Add port 10022 to Hetzner Cloud Firewall**
- Test SSH from external network (your Mac)
- Once confirmed, optionally disable Cloudflared

### 🎯 End Goal

Replace Cloudflare Tunnel entirely with FRP, giving you:
- Faster SSH access
- Unified access method (all via VPS)
- Full WebRTC support (UDP)
- Complete control over infrastructure

---

## Next Steps

1. **Add port 10022** to Hetzner Cloud Firewall (same place you added 18xxx ports)
2. **Test SSH** from your Mac: `ssh -p 10022 linaro@65.109.32.111`
3. **Verify it works** with the helper script: `./connect-r58-frp.sh`
4. **Consider disabling** Cloudflared if FRP SSH is sufficient

Once port 10022 is added to Hetzner Cloud Firewall, you'll have complete FRP-based access to R58! 🚀

