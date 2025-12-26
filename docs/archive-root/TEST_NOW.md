# 🎥 Test VDO.ninja + MediaMTX Now!

**Status**: ✅ **READY - All services configured and running**

---

## Quick Start (3 Steps)

### Step 1: Accept Certificate
Open in browser on your Windows PC (192.168.1.40):
```
https://192.168.1.24:8443/
```
Click "Advanced" → "Proceed to 192.168.1.24 (unsafe)"

### Step 2: Open Test Page
```
https://192.168.1.24:8443/vdo_mediamtx_test.html
```

### Step 3: Click "Open Director with MediaMTX"
Or go directly to:
```
https://192.168.1.24:8443/?director=r58studio&mediamtx=192.168.1.24:8889
```

---

## What to Expect

1. **Wait 10-15 seconds** for WebRTC to connect
2. **Camera tiles will appear** showing:
   - cam0 (4K camera)
   - cam2 (1080p camera)
   - cam3 (4K camera)
3. **Click tiles** to view full screen
4. **Video should play** smoothly

---

## If It Doesn't Work

1. **Check browser console** (F12 → Console tab)
2. **Copy any errors** and share them
3. **Try refreshing** the page
4. **Try a single camera** first:
   ```
   https://192.168.1.24:8443/?view=cam2&mediamtx=192.168.1.24:8889
   ```

---

## What Changed

- ❌ **Stopped**: raspberry.ninja publishers (were causing interrupt loops)
- ✅ **Started**: preke-recorder (stable MediaMTX streaming)
- ✅ **Using**: Native VDO.ninja `&mediamtx=` parameter (no custom signaling)

This is the **native, documented way** to use VDO.ninja with MediaMTX!

---

## Test URLs

**Director**: `https://192.168.1.24:8443/?director=r58studio&mediamtx=192.168.1.24:8889`

**Mixer**: `https://192.168.1.24:8443/mixer?room=r58studio&mediamtx=192.168.1.24:8889`

**Camera 2** (1080p, good for testing): `https://192.168.1.24:8443/?view=cam2&mediamtx=192.168.1.24:8889`

---

**Full documentation**: See `MEDIAMTX_INTEGRATION_COMPLETE.md`

