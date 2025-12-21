# R58 Remote Access Deployment Guide v2

**Branch**: `feature/remote-access-v2`  
**Status**: Ready for DNS configuration and testing

---

## Overview

This guide walks through deploying the new remote access architecture using Coolify as the central infrastructure.

### Architecture

```
Remote Controller (Browser)
    ↓ HTTPS
Coolify Server (65.109.32.111)
    ├── TURN API (api.r58.itagenten.no)
    │   └── Provides Cloudflare TURN credentials
    └── WebSocket Relay (relay.r58.itagenten.no)
        └── Bridges signaling between R58 and controllers
    ↓ WebSocket
R58 Device (Venue)
    ├── Connects outbound to relay
    ├── Uses TURN for NAT traversal
    └── Publishes camera streams with TURN
```

---

## Prerequisites

- [x] R58 backup created
- [x] Git branch `feature/remote-access-v2` created
- [x] Coolify services deployed
- [ ] DNS records configured (next step)
- [ ] R58 code updated
- [ ] Testing completed

---

## Step 1: Configure DNS (MANUAL STEP)

### Action Required

Add these DNS records in Cloudflare for `itagenten.no`:

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|--------------|-----|
| A | api.r58 | 65.109.32.111 | DNS only (gray) | Auto |
| A | relay.r58 | 65.109.32.111 | DNS only (gray) | Auto |

**Important**: Use "DNS only" mode, NOT "Proxied" mode!

### Verification

Wait 5-10 minutes for DNS propagation, then test:

```bash
# Check DNS resolution
dig api.r58.itagenten.no
dig relay.r58.itagenten.no

# Test services (after DNS propagates)
curl https://api.r58.itagenten.no/health
curl https://api.r58.itagenten.no/turn-credentials
curl https://relay.r58.itagenten.no/health
```

Expected responses:
- Health: `{"status":"ok","service":"r58-turn-api"}`
- Credentials: JSON with `iceServers` array
- Relay: `{"status":"ok","service":"r58-relay","units":0,"controllers":0}`

---

## Step 2: Update R58 Camera Publishers

### Deploy Publisher Update Script

```bash
# From your Mac
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./connect-r58.sh "mkdir -p /opt/preke-r58-recorder/scripts"

# Copy script to R58
scp scripts/update-publishers-with-turn.sh linaro@r58.itagenten.no:/tmp/

# Run on R58
./connect-r58.sh "sudo bash /tmp/update-publishers-with-turn.sh"
```

### What This Does

- Backs up existing service files
- Creates helper script that fetches TURN credentials
- Updates all 4 camera publisher services
- Configures publishers to use Cloudflare TURN

### Restart Publishers

```bash
./connect-r58.sh "sudo systemctl restart ninja-publish-cam1"
./connect-r58.sh "sudo systemctl restart ninja-publish-cam2"
./connect-r58.sh "sudo systemctl restart ninja-publish-cam3"
./connect-r58.sh "sudo systemctl restart ninja-publish-cam4"
```

### Verify

```bash
./connect-r58.sh "sudo systemctl status ninja-publish-cam1"
./connect-r58.sh "sudo journalctl -u ninja-publish-cam1 -n 50"
```

Look for: "TURN credentials obtained"

---

## Step 3: Update Frontend (Optional for Now)

The frontend updates are prepared but not yet deployed. Current frontend will continue to work via Cloudflare Tunnel.

### Files Ready for Update

- `src/static/js/turn-client.js` - New TURN client library
- Frontend files can be updated to use this library

### To Deploy Frontend Updates

1. Include `turn-client.js` in HTML files
2. Replace existing TURN fetch code with:
   ```javascript
   const turnClient = new TURNClient();
   const iceServers = await turnClient.getIceServers();
   ```

---

## Step 4: Test Remote Access

### Test TURN API

```bash
curl https://api.r58.itagenten.no/turn-credentials | jq
```

Should return Cloudflare TURN credentials with 24h TTL.

### Test Camera Streams

1. Open VDO.ninja director: `https://vdo.ninja/?director=r58-production`
2. Check if cameras appear with TURN relay
3. Verify video quality and latency

### Test from Remote Location

1. Connect from a different network (mobile hotspot, etc.)
2. Access R58 via `https://recorder.itagenten.no`
3. Verify mixer works
4. Check camera streams load correctly

---

## Step 5: Monitor and Verify

### Check Coolify Services

```bash
ssh root@65.109.32.111

# Check containers
docker ps | grep r58

# Check logs
docker logs -f r58-turn-api
docker logs -f r58-relay

# Check Traefik routing
docker logs coolify-proxy | grep r58
```

### Check R58 Publishers

```bash
./connect-r58.sh "sudo systemctl status ninja-publish-cam*"
./connect-r58.sh "sudo journalctl -u ninja-publish-cam1 -f"
```

### Monitor TURN Usage

Check Cloudflare dashboard for TURN usage statistics.

---

## Step 6: Disable Cloudflare Tunnel (After Testing)

**⚠️ ONLY after confirming everything works!**

```bash
./connect-r58.sh "sudo systemctl stop cloudflared"
./connect-r58.sh "sudo systemctl disable cloudflared"
```

### Verify R58 Still Accessible

- Via local network: `https://10.58.0.1:8443` (if local network configured)
- Via relay: Through Coolify relay connection
- Cameras should still stream via TURN

---

## Troubleshooting

### DNS Not Resolving

**Symptoms**: `curl: (6) Could not resolve host`

**Solutions**:
1. Wait longer (DNS can take up to 24 hours)
2. Check Cloudflare DNS settings
3. Verify proxy status is "DNS only" (gray cloud)
4. Try `dig @8.8.8.8 api.r58.itagenten.no` to check Google DNS

### SSL Certificate Not Issued

**Symptoms**: `curl: (60) SSL certificate problem`

**Solutions**:
1. Check Traefik logs: `docker logs coolify-proxy | grep -i error`
2. Verify DNS resolves correctly
3. Ensure ports 80/443 are open on Coolify server
4. Wait a few minutes for Let's Encrypt issuance

### TURN API Returns Error

**Symptoms**: `{"error":"Failed to get TURN credentials"}`

**Solutions**:
1. Check container logs: `docker logs r58-turn-api`
2. Verify environment variables are set
3. Test Cloudflare API directly
4. Check Cloudflare TURN service status

### Publishers Not Using TURN

**Symptoms**: Streams work locally but fail remotely

**Solutions**:
1. Check publisher logs: `journalctl -u ninja-publish-cam1 -n 100`
2. Verify TURN API is accessible from R58
3. Check if TURN credentials are being fetched
4. Restart publishers: `systemctl restart ninja-publish-cam*`

### Relay Connection Failed

**Symptoms**: Remote controller can't connect

**Solutions**:
1. Check relay logs: `docker logs r58-relay`
2. Verify WebSocket connection: `wscat -c wss://relay.r58.itagenten.no/control/test`
3. Check firewall rules
4. Verify Traefik WebSocket configuration

---

## Rollback Procedures

### Restore R58 Publishers

```bash
./connect-r58.sh "sudo cp /etc/systemd/system/ninja-publish-cam1.service.backup /etc/systemd/system/ninja-publish-cam1.service"
./connect-r58.sh "sudo systemctl daemon-reload"
./connect-r58.sh "sudo systemctl restart ninja-publish-cam1"
```

### Re-enable Cloudflare Tunnel

```bash
./connect-r58.sh "sudo systemctl enable cloudflared"
./connect-r58.sh "sudo systemctl start cloudflared"
```

### Revert Git Changes

```bash
git checkout main
```

### Remove Coolify Services

```bash
ssh root@65.109.32.111
docker stop r58-turn-api r58-relay
docker rm r58-turn-api r58-relay
```

---

## Success Criteria

- [ ] DNS resolves for both api.r58 and relay.r58
- [ ] SSL certificates issued automatically
- [ ] TURN API returns valid credentials
- [ ] Relay accepts WebSocket connections
- [ ] Camera publishers fetch TURN credentials
- [ ] Cameras stream successfully via TURN
- [ ] Remote access works from external network
- [ ] Mixer functions correctly
- [ ] Latency is acceptable (<2 seconds)

---

## Next Steps

After successful deployment:

1. **Monitor Performance**
   - Track TURN usage in Cloudflare
   - Monitor relay connection stability
   - Check camera stream quality

2. **Optimize**
   - Adjust TURN credential TTL if needed
   - Configure relay reconnection logic
   - Tune camera bitrates for TURN

3. **Phase 3: Fleet Management** (Future)
   - Deploy fleet dashboard
   - Add R58 registration agent
   - Implement self-hosted Coturn backup

---

## Support

- **Documentation**: See `IMPLEMENTATION_STATUS.md` for current status
- **Coolify Access**: `ssh root@65.109.32.111`
- **R58 Access**: `ssh linaro@r58.itagenten.no`
- **Backup Location**: `/home/linaro/r58-backup-20251221.tar.gz`

