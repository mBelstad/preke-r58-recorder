# R58 Direct Access Implementation Status

**Date**: December 21, 2025  
**Plan**: R58 Direct Access Architecture  
**Status**: 🟡 Scripts Created - Awaiting User Actions

---

## Overview

This implementation enables the R58 to work as a standalone unit with:
- **Local WiFi network** for on-site control PCs
- **Dynamic DNS** for remote access
- **VDO.ninja** for low-latency WebRTC mixing
- **Local recording** of both camera feeds and mix output
- **ZeroTier backup access** (instead of Tailscale due to kernel limitations)

---

## Phase 0: Backup Access ✅ COMPLETE

### ZeroTier Installation

✅ **R58**: ZeroTier installed and running
- ZeroTier Address: `3ebbb67a22`
- Service: Active

⏳ **Mac**: Requires manual installation (needs sudo password)

⏳ **Network Setup**: Requires user action

### Required User Actions

1. **Create ZeroTier Network**:
   - Go to https://my.zerotier.com/
   - Create a free account
   - Create a new network
   - Note the Network ID (16 characters)

2. **Join R58 to Network**:
   ```bash
   ./connect-r58.sh "sudo zerotier-cli join YOUR_NETWORK_ID"
   ```

3. **Authorize R58** in ZeroTier dashboard

4. **Install ZeroTier on Mac**:
   ```bash
   brew install --cask zerotier-one
   # Enter password when prompted
   ```

5. **Join Mac to same network** and authorize

6. **Test SSH**:
   ```bash
   ssh linaro@<ZEROTIER_IP>
   ```

**Documentation**: See `ZEROTIER_SETUP.md` for detailed instructions

---

## Phase 1: Local Network & Remote Access

### Scripts Created ✅

| Script | Purpose | Status |
|--------|---------|--------|
| `scripts/setup-wifi-ap.sh` | Configure WiFi access point | ✅ Ready |
| `scripts/setup-dyndns.sh` | Configure Dynamic DNS | ✅ Ready |
| `scripts/setup-letsencrypt.sh` | SSL certificates | ✅ Ready |
| `scripts/update-ninja-turn.sh` | Update publishers with TURN | ✅ Ready |

### Execution Plan

**IMPORTANT**: Do NOT run these scripts until ZeroTier SSH is verified working!

#### 1. WiFi Access Point Setup

```bash
# Copy script to R58
scp scripts/setup-wifi-ap.sh linaro@r58.itagenten.no:/tmp/

# Run on R58
./connect-r58.sh "sudo bash /tmp/setup-wifi-ap.sh"
```

**Result**:
- WiFi SSID: `R58-Studio`
- Password: `r58studio2025`
- IP: `10.58.0.1`
- DHCP: `10.58.0.100-200`

#### 2. Dynamic DNS Setup

**Prerequisites**:
- Register at https://www.duckdns.org
- Create subdomain (e.g., `r58-studio`)
- Get your token

```bash
# Copy script to R58
scp scripts/setup-dyndns.sh linaro@r58.itagenten.no:/tmp/

# Run on R58
./connect-r58.sh "sudo bash /tmp/setup-dyndns.sh r58-studio YOUR_TOKEN"
```

**Result**:
- Domain: `r58-studio.duckdns.org`
- Auto-updates every 5 minutes

#### 3. Port Forwarding (Manual)

Configure on your router:
- Port 443 → R58:8443 (VDO.ninja)
- Port 8000 → R58:8000 (API, optional)

#### 4. Let's Encrypt SSL

```bash
# Copy script to R58
scp scripts/setup-letsencrypt.sh linaro@r58.itagenten.no:/tmp/

# Run on R58
./connect-r58.sh "sudo bash /tmp/setup-letsencrypt.sh r58-studio.duckdns.org"
```

**Result**:
- Trusted SSL certificate
- Auto-renewal configured

#### 5. Update Publishers with TURN

```bash
# Copy script to R58
scp scripts/update-ninja-turn.sh linaro@r58.itagenten.no:/tmp/

# Run on R58
./connect-r58.sh "sudo bash /tmp/update-ninja-turn.sh"
```

**Result**:
- Publishers use local VDO.ninja server
- TURN configured for remote access
- Credentials auto-fetched from Coolify API

#### 6. Set Up TURN Auto-Refresh

```bash
# Add cron job on R58
./connect-r58.sh "echo '0 */12 * * * root /opt/preke-r58-recorder/scripts/update-ninja-turn.sh' | sudo tee /etc/cron.d/ninja-turn-update"
```

---

## Architecture After Implementation

```
┌─────────────────────────────────────────────────────────────┐
│                     R58 Device (Venue)                       │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ VDO.ninja       │  │ Cameras         │                  │
│  │ Local Server    │  │ Publishers      │                  │
│  │ :8443           │  │                 │                  │
│  └────────┬────────┘  └────────┬────────┘                  │
│           │ Direct WebRTC      │                            │
│           ↓                    ↓                            │
│  ┌──────────────────────────────────────┐                  │
│  │ Local Network: 10.58.0.1             │                  │
│  │ Public Access: r58-studio.duckdns.org│                  │
│  └──────────────────────────────────────┘                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ↓               │               ↓
    ┌───────────────┐       │       ┌───────────────┐
    │ Local PC      │       │       │ Remote PC     │
    │ 10.58.0.100   │       │       │ (Anywhere)    │
    │ Direct WebRTC │       │       │ Uses TURN     │
    └───────────────┘       │       └───────────────┘
                            ↓
                    ┌───────────────┐
                    │ Cloudflare    │
                    │ TURN (only)   │
                    │ For NAT help  │
                    └───────────────┘
```

---

## Access URLs After Implementation

| Purpose | Local (WiFi) | Remote (Internet) |
|---------|--------------|-------------------|
| VDO.ninja Director | `https://10.58.0.1:8443/?director=r58studio` | `https://r58-studio.duckdns.org/?director=r58studio` |
| View Camera 1 | `https://10.58.0.1:8443/?view=r58-cam1` | `https://r58-studio.duckdns.org/?view=r58-cam1` |
| R58 Main UI | `http://10.58.0.1:8000/` | `http://r58-studio.duckdns.org:8000/` |

---

## What About Recording?

### Current Recording (Unchanged)

The existing MediaMTX-based recording continues to work:
- Individual camera feeds recorded via RTSP subscription
- Stored locally on R58
- Controlled via R58 web UI

### Mix Recording (To Be Implemented)

Phase 4 will add mix recording:
1. Remote mixer publishes mix output via WHIP
2. MediaMTX receives on `/mix` path
3. Recorder subscribes to `rtsp://localhost:8554/mix`
4. Mix recorded alongside camera feeds

---

## Cloudflare Tunnel Status

### Current State
- ✅ Still enabled and running
- ✅ Provides remote SSH access
- ✅ Provides remote web UI access

### Future Decision

After Phase 1 is complete and tested:

**Option A**: Keep tunnel for convenience
- Pros: Easy remote access, no port forwarding needed
- Cons: Blocks WebRTC WHEP (but we're using VDO.ninja now)

**Option B**: Disable tunnel
- Pros: Cleaner architecture, one less dependency
- Cons: Lose easy SSH access (but have ZeroTier backup)

**Recommendation**: Keep tunnel enabled until ZeroTier and DynDNS are proven reliable.

---

## Phase 2 & 3: Future Work

### Phase 2: Tailscale (Cancelled - Using ZeroTier Instead)

ZeroTier provides the same functionality without kernel TUN requirement.

### Phase 3: Coolify Fleet Management

This phase is documented in the Fleet Manager plan and can be implemented later for managing multiple R58 units.

---

## Testing Checklist

After running all scripts:

- [ ] Connect to R58-Studio WiFi
- [ ] Get IP from DHCP (10.58.0.100-200 range)
- [ ] Access VDO.ninja locally: `https://10.58.0.1:8443`
- [ ] Verify DynDNS resolves: `dig r58-studio.duckdns.org`
- [ ] Access VDO.ninja remotely: `https://r58-studio.duckdns.org`
- [ ] No SSL warning (trusted certificate)
- [ ] VDO.ninja director sees cameras
- [ ] Remote mixer works with TURN
- [ ] ZeroTier SSH still works

---

## Rollback Procedures

If anything breaks:

### 1. ZeroTier Access Still Works
```bash
ssh linaro@<ZEROTIER_IP>
```

### 2. Re-enable Cloudflare Tunnel
```bash
sudo systemctl start cloudflared
```

### 3. Disable WiFi AP
```bash
sudo systemctl stop hostapd dnsmasq
```

### 4. Restore Original Publisher Config
```bash
sudo cp /etc/systemd/system/ninja-publish-cam1.service.backup.* /etc/systemd/system/ninja-publish-cam1.service
sudo systemctl daemon-reload
sudo systemctl restart ninja-publish-cam1
```

---

## Next Steps

1. ✅ **Complete ZeroTier setup** (user action required)
2. ⏳ **Run WiFi AP setup script**
3. ⏳ **Configure DynDNS**
4. ⏳ **Set up port forwarding**
5. ⏳ **Install SSL certificates**
6. ⏳ **Update publishers with TURN**
7. ⏳ **Test local and remote access**
8. ⏳ **Implement mix recording** (Phase 4)

---

**Status**: Ready to proceed once ZeroTier backup access is verified.

**Documentation**:
- `ZEROTIER_SETUP.md` - ZeroTier setup instructions
- `scripts/setup-wifi-ap.sh` - WiFi AP setup
- `scripts/setup-dyndns.sh` - Dynamic DNS setup
- `scripts/setup-letsencrypt.sh` - SSL setup
- `scripts/update-ninja-turn.sh` - Publisher TURN configuration

