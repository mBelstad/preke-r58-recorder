# R58 Remote Access Implementation Status

**Date**: December 21, 2025  
**Branch**: `feature/remote-access-v2`  
**Status**: Phase 1 Complete, Phase 2 In Progress

---

## Summary

Successfully implemented Coolify-based infrastructure for R58 remote access. Services are deployed and tested on the Coolify server. Next steps require DNS configuration and R58 device updates.

---

## Phase 0: Safety and Backup ✅ COMPLETE

### Completed Tasks

1. ✅ **R58 Backup Created**
   - Location: `/home/linaro/r58-backup-20251221.tar.gz`
   - Size: 844KB
   - Includes: systemd services, VDO.ninja config, network config, cloudflared config

2. ✅ **Git Branch Created**
   - Branch: `feature/remote-access-v2`
   - Pushed to GitHub
   - All changes isolated from main branch

3. ⚠️ **Tailscale Installation - BLOCKED**
   - Issue: R58 kernel lacks TUN module support
   - Error: `modprobe: FATAL: Module tun not found in directory /lib/modules/6.1.99`
   - Impact: Cannot use Tailscale as development access backup
   - Workaround: Continue using Cloudflare Tunnel for development access
   - Documentation: See `TAILSCALE_LIMITATION.md`

---

## Phase 1: Coolify Infrastructure ✅ COMPLETE

### Deployed Services

#### 1. TURN Credentials API
- **Status**: ✅ Deployed and running
- **Location**: Coolify server (65.109.32.111:3000)
- **Container**: `r58-turn-api`
- **Image**: `r58-turn-api:latest`
- **Health**: http://localhost:3000/health → `{"status":"ok","service":"r58-turn-api"}`
- **Credentials**: http://localhost:3000/turn-credentials → Returns Cloudflare TURN ICE servers
- **Environment**:
  - `CF_TURN_ID=79d61c83455a63d11a18c17bedb53d3f`
  - `CF_TURN_TOKEN=9054653545421be55e42219295b74b1036d261e1c0259c2cf410fb9d8a372984`

#### 2. WebSocket Signaling Relay
- **Status**: ✅ Deployed and running
- **Location**: Coolify server (65.109.32.111:8081 → internal 8080)
- **Container**: `r58-relay`
- **Image**: `r58-relay:latest`
- **Health**: http://localhost:8081/health → `{"status":"ok","service":"r58-relay","units":0,"controllers":0}`
- **Endpoints**:
  - `/unit/{unit-id}` - For R58 devices to connect
  - `/control/{unit-id}` - For remote controllers

#### 3. Traefik Integration
- **Status**: ✅ Configured with SSL labels
- **Network**: `coolify` (Traefik network)
- **SSL**: Let's Encrypt certificates (auto-issued after DNS)
- **Domains**:
  - `api.r58.itagenten.no` → r58-turn-api:3000
  - `relay.r58.itagenten.no` → r58-relay:8080

### Repository Structure

```
coolify/
├── r58-turn-api/
│   ├── package.json
│   ├── index.js
│   ├── Dockerfile
│   └── README.md
├── r58-relay/
│   ├── package.json
│   ├── index.js
│   ├── Dockerfile
│   └── README.md
├── deploy-with-traefik.sh    # Automated deployment script
├── manual-deploy.sh           # Manual Docker deployment
├── DEPLOYMENT_GUIDE.md        # Deployment instructions
└── DNS_SETUP.md              # DNS configuration guide
```

---

## Phase 2: R58 Configuration ⏳ IN PROGRESS

### Pending Tasks

#### 1. ⏳ DNS Configuration (Manual Step Required)
**Action needed**: Configure Cloudflare DNS records

Add these A records in Cloudflare for `itagenten.no`:
| Name | Type | Content | Proxy |
|------|------|---------|-------|
| api.r58 | A | 65.109.32.111 | DNS only (gray) |
| relay.r58 | A | 65.109.32.111 | DNS only (gray) |

**Important**: Use "DNS only" mode, not "Proxied"

**Verification**:
```bash
dig api.r58.itagenten.no
dig relay.r58.itagenten.no
```

**Test after DNS propagates** (5-10 minutes):
```bash
curl https://api.r58.itagenten.no/health
curl https://api.r58.itagenten.no/turn-credentials
curl https://relay.r58.itagenten.no/health
```

#### 2. ⏸️ Local Network Setup (Deferred)
- Requires physical network changes
- Script created: `scripts/setup-phase1-local-network.sh`
- Can be done later when R58 is physically accessible

#### 3. 📝 Update VDO.ninja for Relay Connection
**Files to modify**:
- `/opt/vdo-signaling/vdo-server.js`

**Changes needed**:
- Connect outbound to `wss://relay.r58.itagenten.no/unit/r58-001`
- Forward signaling messages through relay
- Handle relay disconnection/reconnection

#### 4. 📝 Update Camera Publishers with TURN
**Files to modify**:
- `/etc/systemd/system/ninja-publish-cam1.service`
- `/etc/systemd/system/ninja-publish-cam2.service`
- `/etc/systemd/system/ninja-publish-cam3.service`
- `/etc/systemd/system/ninja-publish-cam4.service`

**Changes needed**:
Add TURN parameters to `ExecStart`:
```bash
--turn-server "turns://username:credential@turn.cloudflare.com:5349"
--stun-server "stun://stun.cloudflare.com:3478"
```

Fetch credentials from: `https://api.r58.itagenten.no/turn-credentials`

#### 5. 📝 Update Frontend
**Files to modify**:
- `src/static/index.html`
- `src/static/guest_join.html`
- `src/static/control.html`
- `src/static/switcher.html`

**Changes needed**:
- Replace `itagenten.no` hostname detection with proper remote detection
- Fetch TURN from `https://api.r58.itagenten.no/turn-credentials`
- For remote access, connect via relay instead of direct

#### 6. ⏸️ Remove Cloudflare Tunnel
**Action**: Only after all above is working!
```bash
sudo systemctl stop cloudflared
sudo systemctl disable cloudflared
```

---

## Phase 3: Fleet Management ⏸️ DEFERRED

Tasks deferred to later:
- Fleet management dashboard
- R58 registration agent
- Self-hosted Coturn server
- Fallback relay mode

---

## Testing Checklist

### Phase 1 Tests ✅
- [x] TURN API health check
- [x] TURN API returns credentials
- [x] Relay health check
- [x] Containers restart automatically
- [x] Traefik labels configured

### Phase 2 Tests (Pending DNS)
- [ ] DNS resolves correctly
- [ ] SSL certificates issued
- [ ] TURN API accessible via HTTPS
- [ ] Relay accessible via WSS
- [ ] R58 connects to relay
- [ ] Remote controller connects via relay
- [ ] Camera publishers use TURN
- [ ] Video streaming works remotely

---

## Known Issues

### 1. Tailscale Not Available
- **Issue**: R58 kernel lacks TUN module
- **Impact**: No VPN fallback for development
- **Workaround**: Keep Cloudflare Tunnel active
- **Future**: Consider WireGuard or OpenVPN if kernel supports

### 2. DNS Configuration Required
- **Issue**: Manual step needed in Cloudflare
- **Impact**: Services not accessible via domain yet
- **Action**: User must configure DNS records

### 3. Local Network Setup Deferred
- **Issue**: Requires physical access to R58
- **Impact**: Cannot test local DHCP functionality
- **Action**: Deploy when R58 is physically accessible

---

## Rollback Procedures

### Restore R58 from Backup
```bash
ssh linaro@r58.itagenten.no
cd /home/linaro
tar -xzf r58-backup-20251221.tar.gz
# Restore files to original locations
```

### Revert Git Changes
```bash
git checkout main
git branch -D feature/remote-access-v2
```

### Remove Coolify Services
```bash
ssh root@65.109.32.111
docker stop r58-turn-api r58-relay
docker rm r58-turn-api r58-relay
docker rmi r58-turn-api:latest r58-relay:latest
```

---

## Next Steps

1. **Configure DNS** (manual step - see `coolify/DNS_SETUP.md`)
2. **Wait for DNS propagation** (5-10 minutes)
3. **Verify SSL certificates** issued by Let's Encrypt
4. **Update R58 code** for relay and TURN integration
5. **Test remote access** via relay
6. **Disable Cloudflare Tunnel** (only after testing)

---

## Files Created/Modified

### New Files
- `TAILSCALE_LIMITATION.md`
- `IMPLEMENTATION_STATUS.md` (this file)
- `coolify/r58-turn-api/*`
- `coolify/r58-relay/*`
- `coolify/deploy-with-traefik.sh`
- `coolify/manual-deploy.sh`
- `coolify/DEPLOYMENT_GUIDE.md`
- `coolify/DNS_SETUP.md`
- `coolify/traefik-config.yml`
- `scripts/setup-phase1-local-network.sh`

### Modified Files
- None yet (all changes in new branch)

---

## Resources

- **Coolify Server**: `ssh root@65.109.32.111` (password: PNnPtBmEKpiB23)
- **R58 Device**: `ssh linaro@r58.itagenten.no` (via Cloudflare Tunnel)
- **GitHub Branch**: https://github.com/mBelstad/preke-r58-recorder/tree/feature/remote-access-v2
- **Backup Location**: `/home/linaro/r58-backup-20251221.tar.gz` (844KB)

