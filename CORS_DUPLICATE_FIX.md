# 🔧 CORS Duplicate Headers Fix

**Date**: December 25, 2025  
**Issue**: `Access-Control-Allow-Origin` header contains multiple values `'*, *'`  
**Status**: ⏳ **READY TO APPLY**

---

## 🐛 Problem

VDO.ninja cannot access WHEP endpoints because of duplicate CORS headers:

```
Access to XMLHttpRequest at 'https://r58-mediamtx.itagenten.no/cam0/whep' 
from origin 'https://vdo.ninja' has been blocked by CORS policy: 
The 'Access-Control-Allow-Origin' header contains multiple values '*, *', 
but only one is allowed.
```

### Root Cause

**Both nginx AND MediaMTX are adding CORS headers:**
- nginx adds: `Access-Control-Allow-Origin: *`
- MediaMTX adds: `Access-Control-Allow-Origin: *`
- Result: Browser sees `*, *` and rejects it

---

## ✅ Solution

Remove CORS headers from nginx since MediaMTX already handles them properly.

---

## 📝 Fix Instructions

### Option 1: Via Coolify UI (Easiest)

1. Log into Coolify: https://your-coolify-url
2. Find the `r58-proxy` or nginx container
3. Edit the nginx configuration
4. Find the `r58-mediamtx.itagenten.no` server block
5. **Remove these lines:**
   ```nginx
   # CORS headers for WebRTC
   add_header Access-Control-Allow-Origin * always;
   add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
   add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
   ```
6. Save and reload nginx

### Option 2: Via SSH (Recommended)

```bash
# SSH to your Coolify VPS
ssh root@65.109.32.111

# Find the nginx container name
docker ps | grep nginx

# Edit the config (replace CONTAINER_NAME with actual name)
docker exec -it CONTAINER_NAME vi /etc/nginx/conf.d/r58-mediamtx.conf

# Or use this one-liner to fix it:
docker exec CONTAINER_NAME sed -i '/add_header Access-Control-Allow-Origin/d' /etc/nginx/conf.d/r58-mediamtx.conf
docker exec CONTAINER_NAME sed -i '/add_header Access-Control-Allow-Methods/d' /etc/nginx/conf.d/r58-mediamtx.conf
docker exec CONTAINER_NAME sed -i '/add_header Access-Control-Allow-Headers/d' /etc/nginx/conf.d/r58-mediamtx.conf

# Test config
docker exec CONTAINER_NAME nginx -t

# Reload nginx
docker exec CONTAINER_NAME nginx -s reload
```

---

## 📄 Corrected nginx Configuration

Here's what the `r58-mediamtx.itagenten.no` server block should look like:

```nginx
# r58-mediamtx.itagenten.no - MediaMTX WHEP/WebRTC
server {
    listen 80;
    server_name r58-mediamtx.itagenten.no;
    
    location / {
        proxy_pass http://host.docker.internal:18889;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # DO NOT add CORS headers here!
        # MediaMTX already adds proper CORS headers
        # Adding them here causes duplicate header errors
    }
}
```

**Key change**: Removed all `add_header Access-Control-*` directives.

---

## 🧪 Testing

### Before Fix
```bash
curl -I https://r58-mediamtx.itagenten.no/cam0/whep 2>&1 | grep -i access-control
# Shows duplicate headers or error
```

### After Fix
```bash
curl -I https://r58-mediamtx.itagenten.no/cam0/whep 2>&1 | grep -i access-control
# Should show single Access-Control-Allow-Origin: * header
```

### Test VDO.ninja
```
https://vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3
```

**Expected**: Cameras load without CORS errors

---

## 🔍 Why This Happens

### CORS Header Flow

**Without nginx (direct to MediaMTX):**
```
Browser → MediaMTX
MediaMTX adds: Access-Control-Allow-Origin: *
Browser receives: Access-Control-Allow-Origin: *
✅ Works!
```

**With nginx adding CORS headers:**
```
Browser → nginx → MediaMTX
MediaMTX adds: Access-Control-Allow-Origin: *
nginx adds: Access-Control-Allow-Origin: *
Browser receives: Access-Control-Allow-Origin: *, *
❌ Error: Multiple values not allowed
```

**With nginx NOT adding CORS headers (correct):**
```
Browser → nginx → MediaMTX
MediaMTX adds: Access-Control-Allow-Origin: *
nginx passes through: Access-Control-Allow-Origin: *
Browser receives: Access-Control-Allow-Origin: *
✅ Works!
```

---

## 📋 Alternative: Hide MediaMTX Headers (Not Recommended)

If you want nginx to handle CORS instead of MediaMTX:

```nginx
location / {
    proxy_pass http://host.docker.internal:18889;
    
    # Hide MediaMTX's CORS headers
    proxy_hide_header Access-Control-Allow-Origin;
    proxy_hide_header Access-Control-Allow-Methods;
    proxy_hide_header Access-Control-Allow-Headers;
    proxy_hide_header Access-Control-Expose-Headers;
    
    # Add nginx's CORS headers
    add_header Access-Control-Allow-Origin * always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE" always;
    add_header Access-Control-Allow-Headers "DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization" always;
    add_header Access-Control-Expose-Headers "Content-Length,Content-Range,Location" always;
}
```

**But this is more complex and unnecessary** - just let MediaMTX handle CORS!

---

## ✅ Verification Checklist

After applying the fix:

- [ ] SSH to Coolify VPS
- [ ] Edit nginx config to remove CORS headers
- [ ] Test nginx config: `nginx -t`
- [ ] Reload nginx: `nginx -s reload`
- [ ] Test WHEP endpoint: `curl -I https://r58-mediamtx.itagenten.no/cam0/whep`
- [ ] Verify single Access-Control-Allow-Origin header
- [ ] Test VDO.ninja mixer
- [ ] Verify cameras load without CORS errors

---

## 🎬 Expected Result

After fix:
- ✅ Single `Access-Control-Allow-Origin: *` header
- ✅ VDO.ninja can access WHEP endpoints
- ✅ All 3 cameras load in mixer
- ✅ No CORS errors in browser console

---

## 📞 Quick Fix Command

If you have SSH access to the VPS:

```bash
# One-liner to fix (replace CONTAINER_NAME)
docker exec CONTAINER_NAME sh -c "sed -i '/add_header Access-Control/d' /etc/nginx/conf.d/*.conf && nginx -t && nginx -s reload"
```

This removes all `add_header Access-Control` lines from all nginx configs and reloads.

---

**Status**: ⏳ Waiting for nginx config update on Coolify VPS  
**ETA**: 2-5 minutes to apply fix  
**Impact**: Will immediately fix VDO.ninja WHEP access

