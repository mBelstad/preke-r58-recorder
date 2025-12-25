# 🔧 Fix nginx Configuration - Add Missing Domains

## Problem
The nginx reverse proxy on Coolify VPS is only configured for `r58-mediamtx.itagenten.no` but is missing configurations for:
- ❌ `r58-vdo.itagenten.no` (VDO.ninja)
- ❌ `r58-api.itagenten.no` (FastAPI)

This is why all requests to these domains return 404.

## Solution
Run the automated fix script on the Coolify VPS.

---

## Step 1: Copy Script to VPS

From your Mac terminal:

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
scp -P 10022 fix_nginx_all_domains.sh root@65.109.32.111:/tmp/
```

**Enter root password when prompted**

---

## Step 2: Run the Fix Script

SSH to the VPS:

```bash
ssh -p 10022 root@65.109.32.111
```

Run the script:

```bash
cd /tmp
chmod +x fix_nginx_all_domains.sh
./fix_nginx_all_domains.sh
```

---

## What the Script Does

1. ✅ Backs up current nginx configuration
2. ✅ Adds server block for `r58-vdo.itagenten.no` → port 18443
3. ✅ Adds server block for `r58-api.itagenten.no` → port 18000
4. ✅ Keeps existing `r58-mediamtx.itagenten.no` configuration
5. ✅ Tests nginx configuration before applying
6. ✅ Reloads nginx with new configuration

---

## Expected Output

```
🔧 Adding missing server blocks for r58-vdo and r58-api...

Step 1: Backing up current nginx config...
✅ Backup saved

Step 2: Creating updated nginx configuration...
✅ New configuration created

Step 3: Copying new configuration to nginx container...
✅ Configuration copied

Step 4: Testing nginx configuration...
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
✅ nginx config is valid

Step 5: Reloading nginx...
✅ nginx reloaded successfully

Step 6: Verifying all server blocks...
✅ All server blocks configured!

📝 What was added:
   ✅ r58-mediamtx.itagenten.no → port 18889 (MediaMTX)
   ✅ r58-vdo.itagenten.no → port 18443 (VDO.ninja) [NEW]
   ✅ r58-api.itagenten.no → port 18000 (FastAPI) [NEW]

🎉 Configuration complete!
```

---

## Step 3: Test the Fix

After running the script, test all three domains:

```bash
# Test MediaMTX (should work - was already configured)
curl -I https://r58-mediamtx.itagenten.no/cam0

# Test VDO.ninja (should now work - NEW)
curl -I https://r58-vdo.itagenten.no/

# Test API (should now work - NEW)
curl -I https://r58-api.itagenten.no/static/r58_control.html
```

All three should return `HTTP/2 200` or similar success codes (not 404).

---

## Step 4: Test in Browser

Once the fix is applied, these URLs should work:

### Control Dashboard (NEW!)
```
https://r58-api.itagenten.no/static/r58_control.html
```

### Remote Mixer Dashboard
```
https://r58-api.itagenten.no/static/r58_remote_mixer.html
```

### VDO.ninja Mixer
```
https://r58-vdo.itagenten.no/mixer?room=r58studio&slots=5&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3
```

---

## Troubleshooting

### If script fails:
The script automatically restores the backup if nginx config test fails.

### Manual rollback:
```bash
docker exec r58-proxy cat /tmp/r58.conf.backup.* > /tmp/r58_restore.conf
docker cp /tmp/r58_restore.conf r58-proxy:/etc/nginx/conf.d/r58.conf
docker exec r58-proxy nginx -s reload
```

### Check nginx logs:
```bash
docker logs r58-proxy
```

---

## Why This Fixes the Problem

**Before:**
- nginx only had configuration for `r58-mediamtx.itagenten.no`
- Requests to `r58-vdo` and `r58-api` had no matching server block
- nginx returned 404 for these domains

**After:**
- nginx has server blocks for all three domains
- Each domain routes to the correct FRP-exposed port
- All services accessible via HTTPS with Let's Encrypt certificates

---

## Architecture After Fix

```
Browser (HTTPS)
    ↓
Traefik (SSL termination)
    ↓
nginx (reverse proxy)
    ├─→ r58-mediamtx.itagenten.no → localhost:18889 → FRP → MediaMTX
    ├─→ r58-vdo.itagenten.no → localhost:18443 → FRP → VDO.ninja
    └─→ r58-api.itagenten.no → localhost:18000 → FRP → FastAPI
```

---

**Ready to fix? Run the commands above!** 🚀

