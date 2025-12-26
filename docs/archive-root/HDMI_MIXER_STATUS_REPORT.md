# HDMI Mixer Status Report - December 25, 2025

## 🎯 Current Status

### ✅ Working

1. **WHEP Streaming (cam2, cam3)**
   - cam2 and cam3 successfully streaming to MediaMTX
   - WHEP endpoints accessible and functional
   - User confirmed: "video feeds look good" ✅

2. **Fixed Links**
   - `r58_remote_mixer.html` now uses public `vdo.ninja` with WHEP
   - All quick links updated to use WHEP endpoints
   - Mixer URL correctly configured with 4 camera slots

3. **Service Conflicts Resolved**
   - Stopped and disabled `ninja-publish-cam1/2/3` services
   - Only MediaMTX mode active (no competing WebRTC publishers)
   - Prevents camera device conflicts

4. **CORS Fixed**
   - Nginx allows PATCH method for WHEP ICE trickle
   - All required headers properly configured

### ⚠️ Known Issues

1. **cam0 and cam1 Not Streaming**
   - Pipelines attempt to start but never send RTSP data
   - MediaMTX logs show: "i/o timeout" after connection
   - GStreamer memory errors: `gst_memory_resize: assertion failed`
   - High CPU usage (132%) suggests stuck pipeline

2. **Director View Empty**
   - **Expected behavior**: Director view shows WebRTC peers via signaling
   - **Current setup**: Using WHEP (no signaling, direct MediaMTX pull)
   - **Solution**: Director view won't show WHEP sources - use Mixer instead

---

## 🔧 What Was Fixed

### 1. r58_remote_mixer.html Links
**Before:**
```html
<a href="https://r58-vdo.itagenten.no/mixer?room=r58studio...">
```

**After:**
```html
<a href="https://vdo.ninja/mixer?room=r58studio&slots=4&automixer&whep=...">
```

**Why**: `r58-vdo.itagenten.no` only hosts the signaling server, not the full VDO.ninja web app. Must use public `vdo.ninja` for the mixer interface.

### 2. Stopped Conflicting Services
```bash
sudo systemctl stop ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3
sudo systemctl disable ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3
```

**Why**: raspberry.ninja publishers were competing with MediaMTX for camera device access.

### 3. Nginx CORS Configuration
Added `PATCH` to allowed methods:
```nginx
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE, PATCH" always;
```

**Why**: WHEP uses PATCH for ICE candidate trickle updates.

---

## 📊 Architecture Understanding

### WHEP vs VDO.ninja Signaling

**Two Different Approaches:**

#### Option A: VDO.ninja with Signaling (raspberry.ninja)
```
Camera → raspberry.ninja (GStreamer WebRTC) 
       → VDO.ninja Signaling Server 
       → Director/Mixer (WebRTC P2P)
```
- ✅ Shows in Director view
- ✅ Full VDO.ninja features (director control, scenes)
- ❌ Doesn't work reliably through FRP tunnel
- ❌ Complex NAT traversal

#### Option B: MediaMTX with WHEP (Current)
```
Camera → GStreamer RTSP 
       → MediaMTX 
       → WHEP (HTTP pull) 
       → VDO.ninja Mixer
```
- ✅ Works through FRP tunnel
- ✅ Simple, reliable
- ✅ Lower complexity
- ❌ Doesn't show in Director view (no signaling)
- ❌ Must use Mixer directly

---

## 🎯 Working URLs

### ✅ Mixer (WHEP - Recommended)
```
https://vdo.ninja/mixer?room=r58studio&slots=4&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam1/whep&label=CAM1&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3
```

**Notes:**
- cam2 and cam3 will show video ✅
- cam0 and cam1 slots will be empty (not publishing)

### ✅ Single Camera Views
```
https://vdo.ninja/?whep=https://r58-mediamtx.itagenten.no/cam2/whep
https://vdo.ninja/?whep=https://r58-mediamtx.itagenten.no/cam3/whep
```

### ❌ Director View (Not Compatible)
```
https://vdo.ninja/?director=r58studio
```
**Issue**: Director shows WebRTC peers via signaling. WHEP bypasses signaling entirely.  
**Solution**: Use Mixer instead of Director for WHEP streams.

---

## 🔧 Next Steps to Fix cam0/cam1

### Diagnostics Needed
1. **Check GStreamer Pipeline Health**
   ```bash
   sudo journalctl -u preke-recorder -n 200 | grep -E 'cam0|cam1|gst_memory_resize'
   ```

2. **Test Manual Pipeline**
   ```bash
   gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-raw,format=UYVY,width=1920,height=1080 ! videoconvert ! mpph264enc ! h264parse ! rtspclientsink location=rtsp://127.0.0.1:8554/cam0
   ```

3. **Check Device Status**
   ```bash
   v4l2-ctl --device=/dev/video0 --all
   fuser /dev/video0 /dev/video60
   ```

### Possible Causes
1. **Memory Allocation Issues**
   - `gst_memory_resize` assertions failing
   - May be buffer size mismatch with 4K resolution
   - Solution: Reduce resolution or adjust buffer settings

2. **Device Busy**
   - Another process holding the device
   - Solution: `sudo fuser -k /dev/video0 /dev/video60`

3. **Format Incompatibility**
   - UYVY at 3840x2160 may be too large
   - BGR at 640x480 (cam1) may have color space issues
   - Solution: Adjust pipeline caps

---

## 📝 Test Results

### Test 1: Single Camera WHEP (cam3)
**Status**: ✅ **PASS**  
**User Feedback**: "This looks good. I can see the video feeds."

### Test 2: Mixer Links Fixed
**Status**: ✅ **DEPLOYED**  
**Changes**:
- Mixer now points to public vdo.ninja
- All camera links use WHEP
- Director link added (but won't show WHEP sources)

### Test 3: Service Conflicts
**Status**: ✅ **RESOLVED**  
**Action**: Disabled raspberry.ninja publishers

### Test 4: cam0/cam1 Streaming
**Status**: ❌ **FAIL**  
**Error**: GStreamer memory errors, RTSP timeout

---

## 🚀 For User to Test

### Test the Mixer
1. Open: https://r58-api.itagenten.no/static/r58_remote_mixer.html
2. Click "🎛️ Full Mixer (WHEP)"
3. Expected:
   - ✅ cam2 shows video
   - ✅ cam3 shows video
   - ❌ cam0, cam1 empty (known issue)

### Test Individual Cameras
Click the quick links:
- ✅ CAM 2 - should work
- ✅ CAM 3 - should work
- ❌ CAM 0 - will show "no stream available"
- ❌ CAM 1 - will show "no stream available"

### Why Director View is Empty
**Director view expects WebRTC publishers via signaling.** WHEP streams bypass signaling and are pulled directly into the mixer. This is by design - you can't control WHEP streams through director, only view them in the mixer.

---

## 📌 Summary

**Working**: cam2, cam3 via WHEP to VDO.ninja mixer ✅  
**Fixed**: All HTML links now use public vdo.ninja with WHEP ✅  
**Not Working**: cam0, cam1 (GStreamer pipeline issues) ❌  
**Director View**: Not compatible with WHEP approach (use Mixer instead) ℹ️

---

## 🎯 Recommendations

1. **Use Mixer, Not Director**
   - Director view won't work with WHEP
   - Mixer provides all the mixing/switching you need
   - Can still control layout and scenes in mixer

2. **Fix cam0/cam1 GStreamer Issues**
   - Investigate memory errors
   - May need to adjust resolution or buffer settings
   - Consider using different io-mode or format

3. **Add WHIP for Remote Speakers**
   - Configure MediaMTX WHIP endpoints
   - Update guest_join.html to publish via WHIP
   - Will show up in mixer as additional sources

---

**Report Time**: 2025-12-25 23:40 UTC  
**Deployed Commit**: 77f7e2c  
**System Status**: Partially Operational (2/4 cameras working)

