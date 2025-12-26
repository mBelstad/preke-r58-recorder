# Deploy Remote VDO.ninja Access

## Changes Implemented

1. **nginx Configuration**: Added server block for `r58-vdo.itagenten.no` to proxy to local VDO.ninja via FRP tunnel
2. **WHEP for Remote**: Updated `index.html` to use WHEP instead of HLS for remote access
3. **Redirect Route**: Added `/static/r58_remote_mixer` redirect in `main.py`
4. **Cleanup**: Removed unused raspberry.ninja references and vdo-signaling directory
5. **ModeManager**: Simplified to single recorder mode (VDO.ninja now works via WHEP)

---

## Deployment Steps

### Step 1: Add DNS Record

Add this A record in your DNS provider (Cloudflare):

```
Type: A
Name: r58-vdo
Content: 65.109.32.111
Proxy: No (DNS only)
TTL: Auto
```

### Step 2: Deploy nginx Configuration to VPS

SSH to your Coolify VPS and update the nginx config:

```bash
# SSH to VPS
ssh root@65.109.32.111

# Navigate to nginx config directory
cd /opt/r58-proxy/nginx/conf.d/

# Backup existing config
cp r58.conf r58.conf.backup

# Update the config (copy from deployment/nginx.conf in the repo)
# Or manually add the new server block for r58-vdo.itagenten.no

# Reload nginx
docker exec r58-proxy nginx -s reload

# Verify
docker exec r58-proxy nginx -t
```

### Step 3: Deploy Code to R58 Device

SSH to R58 and pull the latest code:

```bash
# SSH to R58 (use your preferred method)
ssh linaro@r58.itagenten.no
# OR via FRP: ssh -p 10022 linaro@65.109.32.111

# Navigate to project directory
cd /opt/preke-r58-recorder

# Pull latest changes
sudo git fetch origin
sudo git checkout feature/remote-access-v2
sudo git pull origin feature/remote-access-v2

# Fix permissions
sudo chown -R linaro:linaro .

# Restart the service
sudo systemctl restart preke-recorder

# Wait for service to start
sleep 8

# Check status
sudo systemctl status preke-recorder --no-pager | head -40
```

### Step 4: Verify FRP Tunnel

Ensure the FRP tunnel has port 8443 mapped. Check `/etc/frp/frpc.ini` on R58:

```ini
[vdo-ninja]
type = tcp
local_ip = 127.0.0.1
local_port = 8443
remote_port = 18443
```

If not present, add it and restart FRP:

```bash
sudo systemctl restart frpc
```

---

## Testing

### Test 1: Main Dashboard with WHEP

Open: https://r58-api.itagenten.no/

**Expected**: Cameras should load via WHEP (not HLS) with low latency

### Test 2: Remote Mixer Page

Open: https://r58-api.itagenten.no/static/r58_remote_mixer

**Expected**: Should redirect to `.html` and auto-connect to all 4 cameras

### Test 3: Remote VDO.ninja Access

Open: https://r58-vdo.itagenten.no/?director=r58studio

**Expected**: Full VDO.ninja director interface loads with all features

### Test 4: Camera View

Open: https://r58-vdo.itagenten.no/?view=r58-cam1

**Expected**: Individual camera feed displays

---

## Troubleshooting

### DNS not resolving

```bash
# Check DNS propagation
nslookup r58-vdo.itagenten.no
dig r58-vdo.itagenten.no
```

Wait a few minutes for DNS to propagate.

### nginx errors

```bash
# Check nginx logs
docker logs r58-proxy

# Test config
docker exec r58-proxy nginx -t
```

### VDO.ninja not loading

1. Verify FRP tunnel is running: `ssh -p 10022 linaro@65.109.32.111 "sudo systemctl status frpc"`
2. Check if port 8443 is accessible locally on R58: `curl -k https://localhost:8443`
3. Verify nginx proxy_pass uses HTTPS and has `proxy_ssl_verify off`

### WHEP not working

1. Check MediaMTX is running: `sudo systemctl status mediamtx`
2. Verify cameras are publishing: `curl https://r58-mediamtx.itagenten.no/v3/paths/list`
3. Check browser console for CORS or WebRTC errors

---

## Architecture Summary

```
Remote Browser
    ↓
Traefik (Coolify VPS - SSL termination)
    ↓
Nginx (Coolify VPS - Proxy)
    ↓
FRP Tunnel
    ↓
R58 Device
    ├─ Port 8000: Preke Recorder API
    ├─ Port 8443: VDO.ninja (local instance)
    └─ Port 8889: MediaMTX (WHEP endpoints)
```

**Domains**:
- `r58-api.itagenten.no` → Preke Recorder API (port 8000)
- `r58-mediamtx.itagenten.no` → MediaMTX WHEP (port 8889)
- `r58-vdo.itagenten.no` → VDO.ninja (port 8443) **[NEW]**

---

## Success Criteria

- ✅ DNS record added for r58-vdo.itagenten.no
- ✅ nginx configuration updated on VPS
- ✅ Code deployed to R58
- ✅ preke-recorder service restarted
- ✅ Main dashboard uses WHEP for remote access
- ✅ VDO.ninja accessible remotely at r58-vdo.itagenten.no
- ✅ All camera sources auto-load in mixer

---

**Status**: Ready for deployment and testing

