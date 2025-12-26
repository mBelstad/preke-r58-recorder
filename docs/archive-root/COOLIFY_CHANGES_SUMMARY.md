# Coolify Server Changes Summary

**Date**: December 24, 2025  
**Status**: ✅ **VERIFIED SAFE - NO CORE FILES MODIFIED**

---

## Changes Made to Coolify Server

### ✅ 1. New Directories (Isolated)

```
/opt/frp/                    # frp server installation
├── frps                     # frp server binary
├── frps.toml                # frp server config
└── frpc (not used on VPS)

/opt/r58-proxy/              # nginx reverse proxy
├── docker-compose.yml       # Container definition
├── nginx/conf.d/r58.conf    # nginx config
└── r58-frp.yaml.backup      # Backup of removed file
```

**Impact**: None on Coolify. These are standalone directories.

---

### ✅ 2. New Systemd Service

```
/etc/systemd/system/frps.service
```

**Purpose**: Runs frp server (port 7000)  
**Impact**: Independent service, doesn't affect Coolify

---

### ✅ 3. New Docker Container

```
Container: r58-proxy
Image: nginx:alpine
Network: coolify (shared)
Ports: None exposed (Traefik handles routing)
```

**Purpose**: Reverse proxy for R58 services  
**Impact**: Connected to Coolify network but isolated via Traefik labels

---

### ✅ 4. Firewall Rules Added

```
UFW Rules:
- 7000/tcp   # frp control
- 7500/tcp   # frp dashboard
- 18889/tcp  # MediaMTX WHEP
- 18189/udp  # WebRTC UDP
- 18443/tcp  # VDO.ninja
- 19997/tcp  # MediaMTX API
```

**Impact**: Opens new ports, doesn't affect existing services

---

### ✅ 5. SSH Key Added

```
/root/.ssh/authorized_keys
+ ssh-ed25519 AAAAC3Nza...CyLH r58-frp-tunnel
```

**Purpose**: Allows R58 to create SSH tunnel for frp  
**Impact**: Minimal, key-based auth only

---

### ✅ 6. Removed Files

```
❌ /data/coolify/proxy/dynamic/r58-frp.yaml (REMOVED)
```

**Reason**: Unused static Traefik config that could cause conflicts  
**Backup**: Saved to `/opt/r58-proxy/r58-frp.yaml.backup`

---

## What Was NOT Modified

### ✅ Coolify Core Files (Untouched)

```
/data/coolify/proxy/dynamic/
├── Caddyfile                    ✅ Original
├── coolify.yaml                 ✅ Original
└── default_redirect_503.yaml    ✅ Original
```

### ✅ Coolify Services (Unaffected)

- All existing Coolify applications continue to work
- Traefik routing unchanged for other apps
- No port conflicts (R58 uses different ports)

### ✅ Coolify Settings (Unchanged)

- No modifications to Coolify database
- No changes to Coolify configuration
- No changes to Traefik main config

---

## How R58 Services Integrate

### Traefik Integration (Safe Method)

R58 services use **Docker labels** (not static config files):

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.r58-mediamtx.rule=Host(`r58-mediamtx.itagenten.no`)"
  - "traefik.http.routers.r58-mediamtx.entrypoints=https"
  - "traefik.http.routers.r58-mediamtx.tls.certresolver=letsencrypt"
```

This is the **same method Coolify uses** for all its services. It's:
- ✅ Safe
- ✅ Isolated
- ✅ Doesn't affect other apps
- ✅ Managed by Docker, not static files

---

## Verification

### Check Coolify Dynamic Configs

```bash
ls -la /data/coolify/proxy/dynamic/
# Should only show:
# - Caddyfile
# - coolify.yaml
# - default_redirect_503.yaml
```

### Check R58 Container

```bash
docker ps | grep r58-proxy
# Should show: r58-proxy running
```

### Check Traefik Health

```bash
docker ps | grep coolify-proxy
# Should show: Up X days (healthy)
```

---

## Rollback Instructions (If Needed)

If you want to remove all R58 changes:

```bash
# 1. Stop and remove r58-proxy
cd /opt/r58-proxy && docker compose down

# 2. Stop and disable frps
systemctl stop frps
systemctl disable frps
rm /etc/systemd/system/frps.service

# 3. Remove directories
rm -rf /opt/frp
rm -rf /opt/r58-proxy

# 4. Remove firewall rules
ufw delete allow 7000/tcp
ufw delete allow 7500/tcp
ufw delete allow 18889/tcp
ufw delete allow 18189/udp
ufw delete allow 18443/tcp
ufw delete allow 19997/tcp

# 5. Remove SSH key (optional)
# Edit /root/.ssh/authorized_keys and remove the r58-frp-tunnel line
```

---

## Impact Assessment

| Area | Impact | Risk Level |
|------|--------|------------|
| **Coolify Core** | None | ✅ Zero |
| **Existing Apps** | None | ✅ Zero |
| **Traefik** | New routes added | ✅ Safe (isolated) |
| **Firewall** | New ports opened | ⚠️ Low (specific ports) |
| **System Resources** | +1 container, +1 service | ✅ Minimal |

---

## Conclusion

✅ **All changes are safe and isolated**  
✅ **No Coolify core files modified**  
✅ **No impact on existing applications**  
✅ **Uses standard Coolify integration methods**  
✅ **Easy to rollback if needed**

The R58 integration follows Coolify's best practices and doesn't interfere with the platform's operation.


