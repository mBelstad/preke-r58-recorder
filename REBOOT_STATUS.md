# R58 Reboot Status - December 19, 2025

**Time**: 22:08 UTC  
**Action**: Device rebooted successfully  
**Result**: ⚠️ Same overload issue persists

---

## Reboot Results

### ✅ What Works
- **Device rebooted**: Successfully restarted
- **Web service**: Responding normally
- **API**: Functional and returning data
- **Cloudflare tunnel**: Stable connection
- **All cameras**: Automatically started on boot

### ❌ What Doesn't Work
- **SSH**: Still hangs/drops (kernel crashes continue)
- **Stability**: Device immediately overloaded again
- **Root cause**: All 4 cameras (including 2x 4K) auto-start on boot

---

## Current Camera Status (After Reboot)

```json
{
  "cam0": {
    "status": "streaming",
    "resolution": "3840x2160",  // 4K - HIGH LOAD
    "has_signal": true
  },
  "cam1": {
    "status": "streaming",
    "resolution": "640x480",
    "has_signal": true
  },
  "cam2": {
    "status": "streaming",
    "resolution": "1920x1080",
    "has_signal": true
  },
  "cam3": {
    "status": "streaming",
    "resolution": "3840x2160",  // 4K - HIGH LOAD
    "has_signal": true
  }
}
```

**Problem**: All 4 cameras started automatically, including both 4K cameras (cam0, cam3)

---

## Why Reboot Didn't Help

The reboot cleared the kernel crash counter, but:

1. **Service auto-starts** on boot
2. **All cameras enabled** in config.yml
3. **Immediately overloaded** with 4 video streams
4. **Kernel crashes resume** within minutes
5. **SSH becomes unstable** again

**Conclusion**: Reboot alone doesn't fix the problem - we need to reduce the camera load.

---

## Immediate Solutions

### Option 1: Stop Cameras via API (Try This First!)

Since the web API works, we can try to stop the 4K cameras:

```bash
# Stop cam0 (4K)
curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam0

# Stop cam3 (4K)
curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam3

# Verify
curl https://recorder.itagenten.no/api/ingest/status
```

**Expected Result**: 
- Only cam1 and cam2 streaming
- 50% reduction in VPU load
- SSH should become stable
- Kernel crashes should stop

### Option 2: Disable in Config (Requires SSH or Physical Access)

Edit `/opt/preke-r58-recorder/config.yml`:

```yaml
cameras:
  cam0:
    enabled: false  # Disable 4K camera
    device: /dev/video0
    # ... rest of config
  
  cam3:
    enabled: false  # Disable 4K camera
    device: /dev/video22
    # ... rest of config
```

Then restart: `sudo systemctl restart preke-recorder`

### Option 3: Physical Access

If you have console/keyboard access to R58:

```bash
# Login locally
cd /opt/preke-r58-recorder

# Edit config
nano config.yml
# Set cam0 and cam3 to enabled: false

# Restart service
sudo systemctl restart preke-recorder

# Deploy our optimizations
git pull origin feature/webrtc-switcher-preview
sudo systemctl restart preke-recorder
```

---

## Testing API Camera Stop

Let me try to stop the cameras via API:

```bash
# Check if stop endpoint exists
curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam0

# Alternative: check available endpoints
curl https://recorder.itagenten.no/docs
```

---

## Why Our Signal Detection Feature Will Help

Once deployed, our optimizations will:

1. **Skip disabled cameras** in health checks
   - 50% fewer subprocess calls
   - Less CPU overhead

2. **Respect config.yml** settings
   - `enabled: false` cameras won't be checked
   - No unnecessary resource usage

3. **Smart stream connection**
   - Frontend won't try to connect to disabled cameras
   - No failed WebRTC/HLS attempts

4. **Visual feedback**
   - Operators can see which cameras are active
   - Easy troubleshooting

**But first**, we need to reduce the load so the device is stable enough to deploy!

---

## Next Steps

### Immediate (Try Now)
1. **Stop 4K cameras via API**:
   ```bash
   curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam0
   curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam3
   ```

2. **Verify they stopped**:
   ```bash
   curl https://recorder.itagenten.no/api/ingest/status
   ```

3. **Test SSH** (should work if load reduced):
   ```bash
   R58_PASSWORD=linaro ./connect-r58.sh "uptime"
   ```

### If API Stop Works
1. **Deploy optimizations**:
   ```bash
   R58_PASSWORD=linaro ./deploy.sh
   ```

2. **Edit config.yml** to make it permanent:
   - Set cam0 and cam3 to `enabled: false`

3. **Test web interfaces**:
   - https://recorder.itagenten.no/switcher
   - https://recorder.itagenten.no/static/control.html

### If API Stop Doesn't Work
- Need physical/console access to edit config.yml
- Or wait for a stable window to SSH in
- Or use a different remote access method (serial console?)

---

## Summary

| Item | Status | Notes |
|------|--------|-------|
| Reboot | ✅ Complete | Device restarted successfully |
| Web service | ✅ Working | API responding normally |
| SSH | ❌ Still broken | Kernel crashes continue |
| Camera load | ❌ Still high | All 4 cameras streaming |
| Root cause | 🔴 Unchanged | 2x 4K cameras overloading VPU |

**Action Required**: Stop cam0 and cam3 to reduce load by 50%

**Best Approach**: Try API stop commands first (web service works!)

---

## Commands to Try Now

```bash
# 1. Stop the 4K cameras
curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam0
curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam3

# 2. Verify status
curl -s https://recorder.itagenten.no/api/ingest/status | python3 -m json.tool

# 3. Wait 30 seconds for system to stabilize
sleep 30

# 4. Try SSH
R58_PASSWORD=linaro ./connect-r58.sh "uptime && free -h"

# 5. If SSH works, deploy!
R58_PASSWORD=linaro ./deploy.sh
```

---

**Status**: Device rebooted but still overloaded. Need to stop 4K cameras via API or config.
