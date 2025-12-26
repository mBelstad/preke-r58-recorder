# Deploy CORS Fix - Simple Instructions

## 🎯 Quick Fix (Copy & Paste)

### Option 1: One-Line Command (Easiest!)

Copy and paste this entire command into your terminal:

```bash
ssh root@65.109.32.111 'docker exec r58-proxy sh -c "sed -i \"/add_header Access-Control-Allow-Origin/d\" /etc/nginx/conf.d/r58.conf && sed -i \"/add_header Access-Control-Allow-Methods/d\" /etc/nginx/conf.d/r58.conf && sed -i \"/add_header Access-Control-Allow-Headers/d\" /etc/nginx/conf.d/r58.conf && nginx -t && nginx -s reload" && echo "✅ CORS fix applied successfully!"'
```

That's it! The fix will be applied immediately.

---

### Option 2: Step-by-Step (If you prefer)

1. **SSH to VPS:**
   ```bash
   ssh root@65.109.32.111
   ```

2. **Run these commands:**
   ```bash
   docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Origin/d' /etc/nginx/conf.d/r58.conf
   docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Methods/d' /etc/nginx/conf.d/r58.conf
   docker exec r58-proxy sed -i '/add_header Access-Control-Allow-Headers/d' /etc/nginx/conf.d/r58.conf
   docker exec r58-proxy nginx -t
   docker exec r58-proxy nginx -s reload
   ```

3. **Exit SSH:**
   ```bash
   exit
   ```

---

## 🧪 Test the Fix

After applying the fix, open this URL:

```
https://vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3
```

**Expected Result:** All 3 cameras should load! ✅

---

## 🔍 Verify (Optional)

Check that there's only ONE CORS header:

```bash
curl -I https://r58-mediamtx.itagenten.no/cam0/whep | grep -i access-control
```

Should show only one line with `Access-Control-Allow-Origin`.

---

## 📋 What This Does

- Removes duplicate CORS headers from nginx
- Lets MediaMTX handle CORS exclusively
- Fixes the "multiple values '*, *'" error
- Takes effect immediately (no restart needed)

---

## 🔄 Rollback (if needed)

If something goes wrong, restore the backup:

```bash
ssh root@65.109.32.111 'docker exec r58-proxy sh -c "cp /tmp/r58.conf.backup /etc/nginx/conf.d/r58.conf && nginx -s reload"'
```

---

## 📱 Quick Access Links

After the fix is applied:

**Remote Mixer Dashboard:**
```
https://r58-api.itagenten.no/static/r58_remote_mixer.html
```

**VDO.ninja Mixer (Direct):**
```
https://vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3
```

---

## 🎉 Success Criteria

✅ No CORS errors in browser console  
✅ All 3 cameras visible in VDO.ninja mixer  
✅ HTTPS connections working  
✅ Remote mixing fully operational  

---

## Need Help?

If the one-line command doesn't work:

1. Make sure you can SSH to the VPS: `ssh root@65.109.32.111`
2. Check if the container is running: `docker ps | grep r58-proxy`
3. Try Option 2 (step-by-step) instead

---

**Ready?** Just copy the one-line command and paste it into your terminal! 🚀

