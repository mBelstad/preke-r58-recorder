# R58 Stability Testing Summary

**Date:** December 30, 2025  
**Test Duration:** ~50 minutes (ongoing)

---

## ✅ Tests Completed

### 1. Single Camera Test
- ✅ cam2 connected to HDMI IN11
- ✅ Auto-detected 4K signal
- ✅ Stream started successfully
- ✅ Recording to MKV verified

### 2. Dual Camera Test  
- ✅ cam0 connected to HDMI IN0
- ✅ Both cameras streaming 4K simultaneously
- ✅ Dual recording tested - both files growing
- ✅ CPU at ~40% with dual cameras

### 3. Triple Camera Test
- ✅ cam3 connected to HDMI IN21 (1080p)
- ✅ All 3 cameras streaming
- ✅ Triple recording tested - all files verified
- ✅ CPU at ~40% with 3 cameras

### 4. Hot-Plug Test
- ✅ Disconnected cam0 - cam2 continued streaming
- ✅ No crashes or errors
- ✅ Reconnected cam0 - auto-recovered
- ✅ Service remained active throughout

### 5. Service Restart Test
- ✅ Multiple service restarts performed
- ✅ Cameras auto-start on service startup
- ✅ MediaMTX streams reconnect automatically

---

## 📊 Current Status

| Camera | Port | Resolution | Status |
|--------|------|------------|--------|
| cam0 | HDMI IN0 | 4K → 1080p | ✅ Streaming |
| cam1 | HDMI RX | - | ⏸ No signal |
| cam2 | HDMI IN11 | 4K → 1080p | ✅ Streaming |
| cam3 | HDMI IN21 | 1080p | ✅ Streaming |

**CPU Usage:** ~25-40% with 3 cameras  
**Memory:** ~1.4 GB / 7.9 GB  
**Service:** Active, no errors

---

## ⚠️ Browser Preview Issue

The Vue PWA from a previous session is cached in the browser. To view the camera preview page:

### Option 1: Clear PWA Cache
1. Open Chrome DevTools (F12)
2. Go to **Application** → **Service Workers**
3. Click **Unregister** on any service workers
4. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
5. Navigate to: `https://r58-api.itagenten.no/cameras`

### Option 2: Use Incognito Mode
Open in incognito: `https://r58-api.itagenten.no/cameras`

### Option 3: Use Direct WHEP
For individual camera streams:
- `https://r58-api.itagenten.no/cam0/whep`
- `https://r58-api.itagenten.no/cam2/whep`
- `https://r58-api.itagenten.no/cam3/whep`

---

## 🔧 Known Issues (Documented for Later)

See [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md):
1. **Bitrate lower than expected** (~3-5 Mbps vs 18 Mbps target)
2. **Unnecessary videoconvert** - could save ~10% CPU
3. **Vue PWA cached** - browser needs cache cleared

---

## 📋 Configuration Changes Made

1. **Enabled cam3** in config.yml
2. **Added /cameras endpoint** for camera preview
3. **Added /api/camera-preview** to bypass Vue cache
4. **Created camera-preview.html** - standalone WHEP viewer

---

## 🎯 Next Steps

1. **Stability Run:** Leave running for 15+ more minutes
2. **Connect cam1:** If you have a 4th camera, connect to HDMI RX port
3. **Clear Browser Cache:** Use incognito or clear PWA to see preview
4. **Recording Test:** Verify long-duration recording

---

## 📝 Commands Reference

```bash
# SSH to R58
ssh -i ~/.ssh/r58_key linaro@192.168.1.24

# Check camera status
curl http://localhost:8000/api/ingest/status | python3 -m json.tool

# Start recording all cameras
curl -X POST http://localhost:8000/record/start-all

# Stop recording all cameras
curl -X POST http://localhost:8000/record/stop-all

# View logs
journalctl -u r58-pipeline.service -f

# Restart service
sudo systemctl restart r58-pipeline.service
```

---

**System is stable and ready for continued testing!** 🎉

