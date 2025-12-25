# CORS Fix Ready for Deployment

## Status: ✅ READY TO DEPLOY

---

## Problem Summary

VDO.ninja mixer at `https://vdo.ninja` cannot load WHEP streams from `https://r58-mediamtx.itagenten.no` due to duplicate CORS headers.

**Error:**
```
Access to XMLHttpRequest at 'https://r58-mediamtx.itagenten.no/cam0/whep' 
from origin 'https://vdo.ninja' has been blocked by CORS policy: 
The 'Access-Control-Allow-Origin' header contains multiple values '*, *', 
but only one is allowed.
```

**Root Cause:**
- nginx (`r58-proxy` container) adds: `Access-Control-Allow-Origin: *`
- MediaMTX also adds: `Access-Control-Allow-Origin: *`
- Result: Two headers with same name → CORS violation

---

## Solution Prepared

### Files Created:

1. **`fix_cors_on_vps.sh`** - Automated fix script (executable)
2. **`CORS_FIX_INSTRUCTIONS.md`** - Detailed manual instructions
3. **`deployment/nginx.conf`** - Updated source config (CORS headers removed)

### What the Fix Does:

Removes CORS headers from nginx configuration, allowing MediaMTX to handle CORS exclusively:

**Lines Removed from nginx:**
```nginx
add_header Access-Control-Allow-Origin * always;
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
```

---

## Deployment Options

### Option 1: Quick Fix (Recommended)

Run the automated script on the VPS:

```bash
# From your Mac
scp fix_cors_on_vps.sh root@65.109.32.111:/tmp/
ssh root@65.109.32.111 "chmod +x /tmp/fix_cors_on_vps.sh && /tmp/fix_cors_on_vps.sh"
```

### Option 2: Manual Commands

```bash
ssh root@65.109.32.111

# Backup
docker exec r58-proxy cat /etc/nginx/conf.d/r58.conf > /tmp/r58.conf.backup

# Remove CORS headers
docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Origin/d' /etc/nginx/conf.d/r58.conf
docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Methods/d' /etc/nginx/conf.d/r58.conf
docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Headers/d' /etc/nginx/conf.d/r58.conf

# Reload
docker exec r58-proxy nginx -t && docker exec r58-proxy nginx -s reload
```

### Option 3: Permanent Fix (Update Source)

```bash
# Deploy updated nginx.conf
scp deployment/nginx.conf root@65.109.32.111:/opt/r58-proxy/nginx/conf.d/r58.conf
ssh root@65.109.32.111 "docker exec r58-proxy nginx -s reload"
```

---

## Testing After Fix

### 1. Check Headers

```bash
curl -I https://r58-mediamtx.itagenten.no/cam0/whep
```

Should show **only ONE** `Access-Control-Allow-Origin` header.

### 2. Test VDO.ninja Mixer

Open this URL:
```
https://vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3
```

Expected result: All 3 cameras load successfully! ✅

### 3. Check Browser Console

Should see no CORS errors. Cameras should connect via WHEP.

---

## Quick Access

### VPS SSH
```bash
ssh root@65.109.32.111
```

### Check nginx Container
```bash
docker ps | grep r58-proxy
docker logs r58-proxy --tail 50
```

### View Current Config
```bash
docker exec r58-proxy cat /etc/nginx/conf.d/r58.conf
```

---

## What's Changed

| Component | Before | After |
|-----------|--------|-------|
| nginx | Adds CORS headers | No CORS headers |
| MediaMTX | Adds CORS headers | Adds CORS headers |
| Result | Duplicate → Error | Single → Works ✅ |

---

## Rollback Plan

If something goes wrong:

```bash
ssh root@65.109.32.111
docker exec r58-proxy cp /tmp/r58.conf.backup /etc/nginx/conf.d/r58.conf
docker exec r58-proxy nginx -s reload
```

---

## Files in This Repo

```
fix_cors_on_vps.sh           # Automated fix script (run on VPS)
CORS_FIX_INSTRUCTIONS.md     # Detailed manual instructions
CORS_FIX_READY.md            # This file
deployment/nginx.conf        # Updated source config
```

---

## Next Steps

1. **Deploy the fix** using one of the options above
2. **Test** the VDO.ninja mixer
3. **Verify** all 3 cameras load correctly
4. **Commit** the updated `deployment/nginx.conf` to git
5. **Celebrate** 🎉

---

## Expected Outcome

✅ VDO.ninja mixer loads all 3 cameras via HTTPS WHEP  
✅ No CORS errors in browser console  
✅ Cameras display in mixer with labels  
✅ Full remote mixing capability  

---

## Support

If you encounter issues:

1. Check nginx logs: `docker logs r58-proxy`
2. Check MediaMTX logs: `ssh -p 10022 linaro@65.109.32.111 "sudo journalctl -u mediamtx -n 50"`
3. Verify CORS headers: `curl -I https://r58-mediamtx.itagenten.no/cam0/whep`
4. Rollback if needed (see above)

---

## Architecture After Fix

```
Browser (https://vdo.ninja)
    ↓ HTTPS
Traefik (Coolify) - SSL termination
    ↓ HTTP
nginx (r58-proxy) - Reverse proxy (NO CORS headers)
    ↓ HTTP
frp (localhost:18889) - Tunnel
    ↓ SSH tunnel
R58 MediaMTX (localhost:8889) - CORS headers added here
    ↓
Camera streams (WHEP)
```

**Key Point**: CORS headers are added **only by MediaMTX**, avoiding duplication.

---

## Ready to Deploy! 🚀

Choose your deployment method and run it. The fix is simple, safe, and reversible.

