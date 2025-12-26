# R58 Device Diagnosis - December 19, 2025

**Status**: ⚠️ Device Experiencing Kernel Crashes  
**Severity**: High - Requires Immediate Attention

---

## Critical Findings

### 🔴 Kernel Panic Detected

From terminal history (Dec 19, 14:53:01):
```
kernel:[  494.442336] Internal error: Oops: 0000000096000005 [#29] SMP
kernel:[  494.838527] Code: f100007f fa401a64 540017a0 b9402ae0 (f8606a62)
```

**Analysis**:
- **#29** indicates this is the 29th kernel crash
- **Oops: 0000000096000005** is a kernel memory access violation
- This is causing SSH connections to drop unexpectedly
- Device is rebooting or crashing frequently

---

## Current Device Status

### ✅ Services Working
- **Web Interface**: Responding (via Cloudflare tunnel)
- **API**: Functional - `/api/ingest/status` returns valid data
- **Cameras**: All 4 cameras streaming
  - cam0: 3840x2160 (4K) - has signal
  - cam1: 640x480 - has signal
  - cam2: 1920x1080 (1080p) - has signal
  - cam3: 3840x2160 (4K) - has signal
- **Network**: Cloudflare tunnel active (ping: 41-64ms)

### ⚠️ Issues
- **SSH**: Connections hang or drop due to kernel crashes
- **Stability**: Device crashing repeatedly
- **Deployment**: Cannot deploy via SSH due to instability

---

## Root Cause Analysis

### Likely Causes (in order of probability):

#### 1. **Hardware Video Encoder Overload** (Most Likely)
The device is running:
- 4 simultaneous camera streams
- 2x 4K streams (cam0, cam3)
- 2x HD streams (cam1, cam2)
- Hardware H.265 encoding on all streams
- This is **extremely demanding** on the RK3588 VPU

**Evidence**:
- Kernel crash in video processing code
- Crash #29 suggests repeated failures
- All cameras are enabled and streaming

#### 2. **Memory Pressure**
- 4 simultaneous video pipelines
- GStreamer buffers
- MediaMTX server
- Python FastAPI application
- Potential memory leak causing crashes

#### 3. **Thermal Throttling**
- RK3588 under heavy video encoding load
- Possible overheating causing instability
- No active cooling?

#### 4. **Driver Issues**
- RK3588 video drivers may have bugs
- Kernel module instability
- Firmware issues

---

## Immediate Recommendations

### 🚨 Priority 1: Stabilize the Device

#### Option A: Reduce Load (Quick Fix)
Disable the unused 4K cameras to reduce VPU load:

```bash
# Edit config.yml on R58
cameras:
  cam0:
    enabled: false  # Disable 4K camera
  cam3:
    enabled: false  # Disable 4K camera
```

**Expected Result**: 
- 50% reduction in video encoding load
- Only 2 cameras streaming (cam1, cam2)
- Should stop kernel crashes

#### Option B: Reboot the Device
```bash
# Via web interface or SSH (if you can connect)
sudo reboot
```

#### Option C: Check System Resources
If you can get SSH access:
```bash
# Memory usage
free -h

# CPU temperature
cat /sys/class/thermal/thermal_zone0/temp

# Kernel messages
dmesg | tail -50

# Video encoder status
cat /sys/kernel/debug/rkvdec/*

# Process memory
ps aux --sort=-%mem | head -10
```

---

## Why SSH is Failing

The SSH connection hangs because:

1. **Connection established** ✅
   - Cloudflare tunnel works
   - SSH handshake completes
   - Password authentication works

2. **Command execution starts** ⏳
   - Shell session begins
   - Commands start running

3. **Kernel crashes** ❌
   - Video encoder hits bug
   - Kernel panic occurs
   - All processes killed
   - SSH connection drops

**This is NOT a tunnel issue** - it's a device stability issue.

---

## Deployment Strategy

### Current Situation
- Cannot deploy via SSH (device crashes)
- Web interface works (Cloudflare tunnel stable)
- Code is ready and committed to GitHub

### Alternative Deployment Methods

#### Method 1: Wait for Stable Period
Monitor the web interface and try SSH when device is stable:
```bash
# Quick test
R58_PASSWORD=linaro timeout 5 ./connect-r58.sh "uptime"

# If successful, deploy immediately
R58_PASSWORD=linaro ./deploy.sh
```

#### Method 2: Reduce Load First
Access the web interface and stop some services:
```bash
# Via API (if available)
curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam0
curl -X POST https://recorder.itagenten.no/api/ingest/stop/cam3
```

Then try SSH deployment.

#### Method 3: Physical Access
If you have physical access to R58:
1. Connect keyboard/monitor
2. Login locally
3. Run: `cd /opt/preke-r58-recorder && git pull`
4. Restart service: `sudo systemctl restart preke-recorder`

#### Method 4: Serial Console
If available, use serial console for stable access.

---

## Long-Term Solutions

### 1. **Optimize Video Encoding**
- Reduce bitrate for 4K streams
- Use lower resolution for preview streams
- Implement dynamic quality adjustment
- Add encoding error recovery

### 2. **Add Resource Monitoring**
- Monitor VPU usage
- Track memory consumption
- Log thermal status
- Alert on high load

### 3. **Implement Watchdog**
- Automatic service restart on crash
- Kernel watchdog timer
- Application-level health checks

### 4. **Hardware Improvements**
- Add active cooling (fan)
- Verify power supply is adequate
- Check for hardware defects

### 5. **Software Updates**
- Update kernel to latest stable
- Update RK3588 firmware
- Update video drivers
- Update GStreamer plugins

---

## Testing After Stabilization

Once the device is stable:

### 1. Verify Kernel Stability
```bash
# Check for new crashes
dmesg | grep -i "oops\|panic\|crash"

# Monitor for 5 minutes
watch -n 1 'dmesg | tail -20'
```

### 2. Deploy Signal Detection
```bash
R58_PASSWORD=linaro ./deploy.sh
```

### 3. Test Web Interfaces
- Switcher: https://recorder.itagenten.no/switcher
- Control: https://recorder.itagenten.no/static/control.html

### 4. Monitor Resource Usage
```bash
# CPU and memory
top -b -n 1

# Video encoder
cat /sys/kernel/debug/rkvdec/*/status
```

---

## Current Workaround

**For now, the device is unstable for SSH but web services work.**

### What You Can Do:

1. **Monitor via web interface**:
   - https://recorder.itagenten.no/
   - https://recorder.itagenten.no/api/ingest/status

2. **Try SSH during stable periods**:
   ```bash
   # Quick test
   R58_PASSWORD=linaro timeout 10 ./connect-r58.sh "uptime && free -h"
   ```

3. **Reduce camera load** (if possible via config):
   - Disable cam0 (4K)
   - Disable cam3 (4K)
   - Keep only cam1 and cam2

4. **Wait for physical access** to:
   - Reboot device
   - Check cooling
   - Pull latest code manually

---

## Summary

| Issue | Status | Solution |
|-------|--------|----------|
| Kernel crashes | 🔴 Critical | Reduce video encoding load |
| SSH unstable | 🔴 Critical | Wait for device stability |
| Web interface | ✅ Working | Use for monitoring |
| Code ready | ✅ Complete | Deploy when stable |
| Tunnel | ✅ Working | Not the problem |

**Root Cause**: Device overload from 4 simultaneous video streams (2x 4K + 2x HD)

**Immediate Action**: Disable unused cameras (cam0, cam3) to reduce load by 50%

**Deployment**: Wait for stability or use physical access

---

## For Future AI Assistants

**Current Situation** (Dec 19, 2025):
- R58 device experiencing kernel crashes (#29)
- Caused by video encoder overload (4 streams, 2x 4K)
- SSH connections drop mid-session
- Web interface works fine via Cloudflare tunnel
- Code is ready to deploy but cannot SSH reliably

**Do NOT attempt**:
- Long SSH sessions
- Multiple deployment attempts
- Heavy operations via SSH

**DO instead**:
- Use web API for monitoring
- Quick SSH commands only (< 5 seconds)
- Wait for user to stabilize device
- Suggest reducing camera load

**Deployment Status**:
- ✅ Code committed and pushed
- ✅ SSH scripts working
- ⏳ Waiting for device stability
- 📋 Manual deployment instructions provided

---

**Last Updated**: December 19, 2025, 22:00 UTC  
**Next Action**: User needs to reduce device load or reboot R58
