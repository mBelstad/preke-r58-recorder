# 🔒 HTTPS Setup for R58 WebRTC Services

**Date**: December 24, 2025  
**Status**: ✅ **CONFIGURED - DNS SETUP REQUIRED**

---

## Summary

I've set up an nginx reverse proxy on your Coolify VPS that integrates with Traefik for automatic HTTPS certificates via Let's Encrypt. This solves the WebRTC SSL requirement.

---

## Architecture

```
Browser (HTTPS)
    ↓
Coolify Traefik (port 443) - Automatic Let's Encrypt
    ↓
nginx reverse proxy (r58-proxy container)
    ↓
frp exposed ports (localhost:18889, 18443, 19997)
    ↓
frp tunnel
    ↓
R58 Device (MediaMTX, VDO.ninja)
```

---

## New HTTPS URLs

Once DNS is configured, you'll access your services via:

### MediaMTX WHEP (WebRTC Streams)
```
https://r58-mediamtx.itagenten.no/cam0
https://r58-mediamtx.itagenten.no/cam1
https://r58-mediamtx.itagenten.no/cam2
https://r58-mediamtx.itagenten.no/cam3
```

### VDO.ninja Director
```
https://r58-vdo.itagenten.no/?director=r58studio&wss=r58-vdo.itagenten.no
```

### MediaMTX API
```
https://r58-api.itagenten.no/v3/paths/list
```

---

## DNS Configuration Required

You need to add these DNS A records to `itagenten.no`:

| Subdomain | Type | Value | TTL |
|-----------|------|-------|-----|
| `r58-mediamtx` | A | `65.109.32.111` | 300 |
| `r58-vdo` | A | `65.109.32.111` | 300 |
| `r58-api` | A | `65.109.32.111` | 300 |

### How to Add DNS Records

1. Log into your DNS provider (where `itagenten.no` is registered)
2. Go to DNS management
3. Add three A records as shown above
4. Wait 5-10 minutes for DNS propagation

### Test DNS Propagation

```bash
# From your Mac
dig r58-mediamtx.itagenten.no +short
# Should return: 65.109.32.111

dig r58-vdo.itagenten.no +short
# Should return: 65.109.32.111

dig r58-api.itagenten.no +short
# Should return: 65.109.32.111
```

---

## How It Works

### 1. Traefik Integration

The nginx container has Traefik labels that tell Coolify's Traefik to:
- Route requests for `r58-*.itagenten.no` to the nginx container
- Automatically obtain Let's Encrypt SSL certificates
- Handle HTTPS termination

### 2. nginx Reverse Proxy

nginx forwards requests to the frp-exposed ports:
- `r58-mediamtx.itagenten.no` → `localhost:18889` (MediaMTX)
- `r58-vdo.itagenten.no` → `localhost:18443` (VDO.ninja)
- `r58-api.itagenten.no` → `localhost:19997` (API)

### 3. frp Tunnel

frp forwards the requests through the SSH tunnel to R58's local services.

---

## Files Created

### On Coolify VPS

| File | Purpose |
|------|---------|
| `/opt/r58-proxy/docker-compose.yml` | nginx container with Traefik labels |
| `/opt/r58-proxy/nginx/conf.d/r58.conf` | nginx reverse proxy configuration |

---

## Service Management

### Check nginx proxy status

```bash
# On Coolify VPS
docker ps | grep r58-proxy
docker logs r58-proxy
```

### Restart nginx proxy

```bash
cd /opt/r58-proxy
docker compose restart
```

### View nginx access logs

```bash
docker exec r58-proxy tail -f /var/log/nginx/access.log
```

---

## Testing After DNS Setup

### 1. Test API Access

```bash
curl https://r58-api.itagenten.no/v3/paths/list
```

Should return JSON with camera paths.

### 2. Test MediaMTX WHEP

Open in browser:
```
https://r58-mediamtx.itagenten.no/cam0
```

### 3. Test VDO.ninja

Open in browser:
```
https://r58-vdo.itagenten.no/?director=r58studio&wss=r58-vdo.itagenten.no
```

---

## WebRTC with HTTPS

### MediaMTX Configuration Update

MediaMTX on R58 needs to know about the HTTPS domain. Update `/opt/mediamtx/mediamtx.yml`:

```yaml
# Current config (works with HTTP)
webrtcICEHostNAT1To1IPs: 
  - 65.109.32.111

# For HTTPS access, MediaMTX will work as-is because:
# - Traefik handles HTTPS termination
# - nginx forwards to HTTP backend
# - WebRTC media still uses UDP (port 18189)
```

**No changes needed!** The current setup will work with HTTPS.

---

## Certificate Management

### Automatic Renewal

Traefik automatically renews Let's Encrypt certificates before they expire (every 90 days).

### Check Certificates

```bash
# On Coolify VPS
docker exec coolify-proxy find /traefik/caddy/data/caddy/certificates -name 'r58-*.itagenten.no'
```

---

## Troubleshooting

### DNS not resolving

```bash
# Check if DNS is propagated
dig r58-mediamtx.itagenten.no

# If not, wait 5-10 minutes and try again
```

### Certificate not issued

```bash
# Check Traefik logs
docker logs coolify-proxy 2>&1 | grep -i 'r58'

# Common issue: DNS not pointing to VPS yet
# Solution: Wait for DNS propagation
```

### nginx can't reach frp ports

```bash
# Test from inside nginx container
docker exec r58-proxy wget -O- http://host.docker.internal:18889

# If fails, check frp is running
docker exec r58-proxy ping host.docker.internal
```

### WebRTC still requires HTTPS

If browsers complain about insecure context:
1. Ensure you're using `https://` URLs
2. Check certificate is valid in browser
3. Verify DNS points to correct IP

---

## Security Notes

### HTTPS Everywhere

All traffic between browser and VPS is encrypted via HTTPS/WSS.

### WebRTC Media (UDP)

WebRTC media (UDP port 18189) is encrypted by WebRTC's DTLS, separate from HTTPS.

### Certificate Validation

Let's Encrypt certificates are automatically validated and trusted by all major browsers.

---

## Next Steps

1. **Add DNS records** for the three subdomains
2. **Wait 5-10 minutes** for DNS propagation
3. **Test HTTPS access** to `https://r58-api.itagenten.no/v3/paths/list`
4. **Update VDO.ninja URLs** to use HTTPS domains
5. **Test WebRTC** with `https://r58-mediamtx.itagenten.no/cam0`

---

## Summary

✅ nginx reverse proxy configured  
✅ Traefik integration with automatic HTTPS  
✅ Let's Encrypt certificate resolver configured  
✅ WebSocket support for VDO.ninja  
⏳ **Waiting for DNS records to be added**

Once DNS is configured, you'll have:
- 🔒 **Secure HTTPS** access to all services
- 🎥 **WebRTC-compatible** SSL certificates
- 🔄 **Automatic certificate renewal**
- 🚀 **Low-latency** streaming via frp

Add the DNS records and you're ready to go!


