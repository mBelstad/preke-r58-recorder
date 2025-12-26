# CORS Duplicate Headers Fix

## Problem

VDO.ninja mixer is failing with:
```
Access to XMLHttpRequest at 'https://r58-mediamtx.itagenten.no/cam0/whep' 
from origin 'https://vdo.ninja' has been blocked by CORS policy: 
The 'Access-Control-Allow-Origin' header contains multiple values '*, *', 
but only one is allowed.
```

**Root Cause**: Both nginx (`r58-proxy` container) and MediaMTX are adding CORS headers, causing duplication.

---

## Solution

Remove CORS headers from nginx and let MediaMTX handle them exclusively.

---

## Method 1: Run Script on VPS (Recommended)

### Step 1: Copy script to VPS

```bash
scp fix_cors_on_vps.sh root@65.109.32.111:/tmp/
```

### Step 2: SSH to VPS

```bash
ssh root@65.109.32.111
```

### Step 3: Run the fix script

```bash
chmod +x /tmp/fix_cors_on_vps.sh
/tmp/fix_cors_on_vps.sh
```

---

## Method 2: Manual Fix via SSH

### Step 1: SSH to VPS

```bash
ssh root@65.109.32.111
```

### Step 2: Backup current config

```bash
docker exec r58-proxy cat /etc/nginx/conf.d/r58.conf > /tmp/r58.conf.backup
```

### Step 3: Remove CORS headers

```bash
docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Origin/d' /etc/nginx/conf.d/r58.conf
docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Methods/d' /etc/nginx/conf.d/r58.conf
docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Headers/d' /etc/nginx/conf.d/r58.conf
```

### Step 4: Test and reload

```bash
docker exec r58-proxy nginx -t
docker exec r58-proxy nginx -s reload
```

### Step 5: Verify

```bash
docker exec r58-proxy grep -A 20 "location / {" /etc/nginx/conf.d/r58.conf | head -25
```

You should see the `location /` block WITHOUT any `add_header Access-Control-*` lines.

---

## Method 3: Update Source Config (Permanent Fix)

Update the local nginx config file and redeploy:

### Step 1: Edit local config

Edit `deployment/nginx.conf` and remove these lines from the `location /` block:

```nginx
# REMOVE THESE LINES (around lines 52-54):
add_header Access-Control-Allow-Origin * always;
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
```

### Step 2: Update on VPS

```bash
scp deployment/nginx.conf root@65.109.32.111:/opt/r58-proxy/nginx/conf.d/r58.conf
ssh root@65.109.32.111 "docker exec r58-proxy nginx -s reload"
```

---

## Testing

After applying the fix, test with:

```bash
# Check for duplicate headers
curl -I https://r58-mediamtx.itagenten.no/cam0/whep

# Should see only ONE Access-Control-Allow-Origin header
```

Then open VDO.ninja mixer:
```
https://vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3
```

---

## What Changed

**Before:**
- nginx adds: `Access-Control-Allow-Origin: *`
- MediaMTX adds: `Access-Control-Allow-Origin: *`
- Result: Duplicate header → CORS error

**After:**
- nginx: No CORS headers
- MediaMTX adds: `Access-Control-Allow-Origin: *`
- Result: Single header → Works! ✅

---

## Rollback (if needed)

```bash
ssh root@65.109.32.111
docker exec r58-proxy cp /tmp/r58.conf.backup /etc/nginx/conf.d/r58.conf
docker exec r58-proxy nginx -s reload
```

---

## Files Modified

- **Container**: `r58-proxy` (nginx)
- **File**: `/etc/nginx/conf.d/r58.conf`
- **Lines removed**: 52-54 (CORS headers in `location /` block)

---

## Next Steps

1. Apply the fix using one of the methods above
2. Test the VDO.ninja mixer
3. Update the source `deployment/nginx.conf` file for permanent fix
4. Commit changes to git

