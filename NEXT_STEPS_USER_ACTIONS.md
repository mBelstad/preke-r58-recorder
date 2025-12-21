# Next Steps - User Actions Required

**Date**: December 21, 2025  
**Status**: WiFi AP configured, awaiting user actions for remote access

---

## ✅ What's Complete

1. **Cloudflare Tunnel Verified** ✅
   - VDO.ninja (port 8443) is NOT routed through tunnel
   - Only SSH and Web UI go through tunnel
   - Perfect for WebRTC!

2. **WiFi Access Point Configured** ✅
   - SSID: `R58-Studio`
   - Password: `r58studio2025`
   - IP: `10.58.0.1`
   - DHCP: `10.58.0.100-200`

3. **All Setup Scripts Ready** ✅
   - `scripts/setup-dyndns.sh`
   - `scripts/setup-letsencrypt.sh`
   - `scripts/update-ninja-turn.sh`

---

## 📋 Required User Actions

### Action 1: Test WiFi AP (5 minutes)

**On your Mac**:
1. Open **System Settings** → **WiFi**
2. Look for network: **`R58-Studio`**
3. Connect with password: **`r58studio2025`**
4. Verify you get IP in range `10.58.0.100-200`
5. Test access: Open `https://10.58.0.1:8443` in browser

**Expected**: You should see VDO.ninja interface (may have SSL warning with self-signed cert)

---

### Action 2: Register DynDNS Domain (10 minutes)

For remote access, you need a Dynamic DNS domain:

1. **Go to**: https://www.duckdns.org
2. **Sign in** (free account via GitHub/Google/etc)
3. **Create subdomain**: Choose a name (e.g., `r58-studio`, `preke-r58`, etc.)
4. **Copy your token** from the top of the page

**Example**:
- Domain: `r58-studio.duckdns.org`
- Token: `abc123def456-7890-...`

Once you have these, run:
```bash
./connect-r58.sh "sudo bash /tmp/setup-dyndns.sh r58-studio YOUR_TOKEN"
```

---

### Action 3: Configure Port Forwarding (10 minutes)

**On your venue router** (or wherever R58 is deployed):

Forward these ports to R58:
- **Port 8443** → R58:8443 (VDO.ninja HTTPS/WSS)
- **Port 443** → R58:8443 (optional, if you want standard HTTPS port)

**Do NOT forward**:
- Port 22 (SSH stays via Cloudflare Tunnel only)
- Port 8000 (Web UI stays via tunnel)

**How to find router**:
- Usually at `192.168.1.1` or `192.168.0.1`
- Look for "Port Forwarding" or "Virtual Server" settings

---

### Action 4: Install SSL Certificates (After DynDNS + Port Forwarding)

Once DynDNS is configured and port forwarding is set up:

```bash
./connect-r58.sh "sudo bash /tmp/setup-letsencrypt.sh r58-studio.duckdns.org"
```

This will:
- Get a trusted SSL certificate from Let's Encrypt
- Update VDO.ninja to use it
- Configure auto-renewal

---

### Action 5: Update Publishers with TURN

After SSL is configured:

```bash
./connect-r58.sh "sudo bash /tmp/update-ninja-turn.sh"
```

This will:
- Fetch TURN credentials from Coolify API
- Update raspberry.ninja publishers
- Configure them to use local VDO.ninja server
- Enable TURN for remote access

---

## 🎯 Expected Results

### Local Access (via WiFi)
- Connect to `R58-Studio` WiFi
- Open: `https://10.58.0.1:8443/?director=r58studio`
- See cameras with low latency
- Direct WebRTC (no TURN needed)

### Remote Access (via DynDNS)
- Open: `https://r58-studio.duckdns.org/?director=r58studio`
- See cameras with TURN relay
- Trusted SSL certificate (no warning)
- WebRTC through TURN (not Cloudflare Tunnel!)

### SSH/Management (via Tunnel)
- SSH: `ssh linaro@r58.itagenten.no`
- Web UI: `https://recorder.itagenten.no`
- Always works, doesn't interfere with WebRTC

---

## 📊 Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     R58 Device                               │
│                                                              │
│  SSH (22) ──────────┐                                       │
│  Web UI (8000) ─────┼──→ Cloudflare Tunnel (Management)    │
│                     │                                        │
│  VDO.ninja (8443) ──┼──→ Direct Access (WiFi/DynDNS)       │
│                     │     ├─ Local: WiFi 10.58.0.1 ✅      │
│                     │     └─ Remote: DynDNS (pending)       │
└─────────────────────┴──────────────────────────────────────┘
```

**Key Point**: VDO.ninja WebRTC never goes through Cloudflare Tunnel!

---

## ⏰ Estimated Time

| Task | Time | Status |
|------|------|--------|
| Test WiFi AP | 5 min | ⏳ Next |
| Register DynDNS | 10 min | ⏳ Pending |
| Port forwarding | 10 min | ⏳ Pending |
| SSL certificates | 5 min | ⏳ Pending |
| Update publishers | 2 min | ⏳ Pending |
| **Total** | **~30 min** | |

---

## 🔄 Quick Start

**Right now, you can**:
1. Connect to `R58-Studio` WiFi
2. Open `https://10.58.0.1:8443/?director=r58studio`
3. Start mixing locally!

**For remote access, complete**:
1. DynDNS registration
2. Port forwarding
3. SSL setup
4. Publisher TURN update

---

**Current Status**: Local WiFi access ready to test! 🎉

