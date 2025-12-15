# Lessons Learned: R58 4x4 3S Multi-Camera Recording System

## Overview
This document captures key learnings, successful solutions, and best practices discovered during the development and troubleshooting of the R58 4x4 3S multi-camera recording system.

---

## Hardware Architecture Discoveries

### HDMI Input Port Mapping
The R58 4x4 3S has **four dedicated HDMI input ports** with a hybrid architecture:

| Physical Port | Device Node | Device Type | Controller/Bridge | Notes |
|---------------|-------------|-------------|-------------------|-------|
| **HDMI N0** | `/dev/video0` | rkcif | LT6911UXE (I2C 7-002b) | Requires format initialization |
| **HDMI N60** | `/dev/video60` | rk_hdmirx | Direct (fdee0000.hdmirx-controller) | Native HDMI RX, works out of box |
| **HDMI N11** | `/dev/video11` | rkcif | LT6911UXE (I2C 4-002b) | Requires format initialization |
| **HDMI N21** | `/dev/video22` | rkcif | LT6911UXE (I2C 2-002b) | **Note: video22, NOT video21** |

**Key Finding**: The device uses a hybrid approach:
- **One direct HDMI RX controller** (`/dev/video60`) - native RK3588 SoC capability
- **Three HDMI-to-MIPI bridge chips** (LT6911UXE) that convert HDMI to MIPI CSI, feeding into `rkcif` devices

### Format Requirements by Device Type

#### Direct HDMI RX (`/dev/video60`)
- **Format**: NV16 (4:2:2) at native resolution
- **Behavior**: Works immediately, no initialization needed
- **Pipeline**: Can use `io-mode=mmap` for better performance

#### rkcif Devices (`/dev/video0`, `/dev/video11`, `/dev/video22`)
- **Format**: UYVY (4:2:2) after initialization
- **Critical Requirement**: **Must explicitly set format** using `v4l2-ctl` before use
- **Initialization Process**:
  1. Query V4L2 subdev (`/dev/v4l-subdev2`, `/dev/v4l-subdev7`, `/dev/v4l-subdev12`) for detected resolution
  2. Explicitly set format on video device: `v4l2-ctl -d /dev/videoX --set-fmt-video=width=W,height=H,pixelformat=UYVY`
  3. Without this step, devices report 0x0 resolution even when LT6911 detects signal

**Subdev Mapping**:
- `/dev/video0` → `/dev/v4l-subdev2`
- `/dev/video11` → `/dev/v4l-subdev7`
- `/dev/video22` → `/dev/v4l-subdev12`

---

## Software Solutions That Worked

### 1. Device Initialization Script
**Problem**: rkcif devices report 0x0 resolution until format is explicitly set.

**Solution**: Created `scripts/init_hdmi_inputs.sh` that:
- Queries subdev for actual detected resolution
- Sets format on video device using `v4l2-ctl`
- Runs on system startup via `systemd` `ExecStartPre`

**Key Code Pattern**:
```bash
# Get resolution from subdev
resolution_output=$(v4l2-ctl -d $subdev --get-subdev-fmt pad=0 2>/dev/null)
width=$(echo "$resolution_output" | grep "Width/Height" | awk -F': ' '{print $2}' | cut -d'/' -f1)
height=$(echo "$resolution_output" | grep "Width/Height" | awk -F': ' '{print $2}' | cut -d'/' -f2)

# Set format on video device
v4l2-ctl -d $video_dev --set-fmt-video=width=$width,height=$height,pixelformat=UYVY
```

### 2. GStreamer Pipeline Format Handling

**For rkcif devices** (video0, video11, video22):
```python
# Initialize device first
caps = initialize_rkcif_device(device)

# Use explicit format in pipeline
source_str = (
    f"v4l2src device={device} ! "
    f"video/x-raw,format=UYVY,width={caps['width']},height={caps['height']} ! "
    f"videoconvert ! videoscale ! video/x-raw,width={width},height={height},format=NV12"
)
```

**For direct HDMI RX** (video60):
```python
source_str = (
    f"v4l2src device={device} io-mode=mmap ! "
    f"video/x-raw,format=NV16,width={caps['width']},height={caps['height']} ! "
    f"videoconvert ! video/x-raw,format=NV12 ! "
    f"videoscale ! video/x-raw,width={width},height={height}"
)
```

**Key Learnings**:
- **Always query device capabilities** before building pipeline
- **Explicit format specification** prevents negotiation failures
- **UYVY for rkcif, NV16 for hdmirx** - format must match device type
- **Use `io-mode=mmap`** for better performance on hdmirx devices

### 3. WebRTC Reconnection Loop Fix

**Problem**: Frontend WebRTC connections kept reconnecting every 2 seconds for some cameras.

**Root Cause**: Dimension check timeout was too short (2 seconds), causing false reconnects when video dimensions took longer to initialize.

**Solution**:
- Increased timeout from 2s to 5s (20 checks → 50 checks)
- Track if dimensions were ever detected to avoid false reconnects
- Fall back to HLS instead of reconnecting WebRTC endlessly
- Don't reconnect if video is actively playing (currentTime > 0)

**Key Code Pattern**:
```javascript
let dimensionsDetected = false;
const checkDimensions = setInterval(() => {
    dimensionCheckCount++;
    if (video.videoWidth > 2 && video.videoHeight > 2) {
        if (!dimensionsDetected) {
            dimensionsDetected = true;
        }
        // Success - clear interval
        clearInterval(checkDimensions);
    } else if (dimensionCheckCount > 50) {
        // Only reconnect if we never got valid dimensions
        if (!dimensionsDetected && video.currentTime === 0) {
            // Fall back to HLS instead of reconnecting
            startHLSPreview(video, camId, placeholder);
        }
    }
}, 100);
```

### 4. Video Aspect Ratio Display

**Problem**: Videos were cropped (`object-fit: cover`) instead of showing full image.

**Solution**: Changed to `object-fit: contain` to maintain aspect ratio.

**Result**:
- HD (1920x1080) and 4K (3840x2160) sources scale to same container size
- Original aspect ratio preserved (letterboxing/pillarboxing instead of cropping)
- All cameras use same 16:9 container with `aspect-ratio: 16/9` CSS

---

## Common Issues and Solutions

### Issue: "Device or resource busy"
**Cause**: Device is already in use by another pipeline (recording or preview).

**Solution**:
- Stop existing pipeline before starting new one
- Add delay after stopping to allow device to release
- Check pipeline state before attempting to use device

### Issue: "Internal data stream error"
**Causes**:
1. Format mismatch between device and pipeline
2. Device not initialized (rkcif devices)
3. Resolution mismatch (capturing at 4K but pipeline expects 1080p)

**Solutions**:
- Always initialize rkcif devices before use
- Query device capabilities and use explicit format
- Ensure pipeline scales correctly (4K → 1080p for preview)

### Issue: Black screen / No signal
**Causes**:
1. No HDMI cable connected
2. Faulty HDMI cable (can cause invalid resolution detection like 720x240)
3. Device not initialized (rkcif devices)
4. Camera output settings incorrect

**Solutions**:
- Check `dmesg` for LT6911 detection messages
- Verify subdev reports valid resolution
- Try different HDMI cable
- Check camera output settings (should be 1080p60 or 4K30)

### Issue: Service stuck in "deactivating" state
**Cause**: GStreamer processes (`gst-plugin-scanner`) stuck during shutdown.

**Solution**:
- Add cleanup in `systemd` service:
  ```ini
  ExecStartPre=-/usr/bin/pkill -9 gst-plugin-scanner
  ExecStartPre=-/bin/sleep 1
  ```
- Use `-` prefix to ignore failures (allows service to start even if no processes to kill)

### Issue: Recording cannot be stopped
**Cause**: Pipeline already stopped or in error state.

**Solution**: Make `stop_recording()` idempotent - return success if already idle:
```python
def stop_recording(self, cam_id: str) -> bool:
    if self.states.get(cam_id) != "recording":
        # Already stopped - goal achieved
        return True
    # ... stop pipeline
```

---

## Best Practices

### 1. GStreamer Initialization
- **Lazy initialization**: Don't initialize GStreamer at import time
- **Timeout protection**: Use `ensure_gst_initialized()` with timeout
- **Error handling**: Check initialization status before using GStreamer

### 2. Device Management
- **Always initialize rkcif devices** before building pipelines
- **Query capabilities** before setting format
- **Release devices** properly when stopping pipelines
- **Check device state** before attempting to use

### 3. Pipeline Construction
- **Use explicit formats** - don't rely on negotiation
- **Query device capabilities** first
- **Handle different device types** (hdmirx vs rkcif) differently
- **Scale appropriately** - 4K sources should be downscaled for preview

### 4. Error Handling
- **Idempotent operations** - starting/stopping should be safe to call multiple times
- **Graceful degradation** - fall back to HLS if WebRTC fails
- **Health monitoring** - detect and restart stalled pipelines
- **Logging** - comprehensive logging for troubleshooting

### 5. Frontend Design
- **Maintain aspect ratio** - use `object-fit: contain` not `cover`
- **Handle slow connections** - increase timeouts for slower streams
- **Fallback mechanisms** - WebRTC → HLS → placeholder
- **User feedback** - show clear status (ready, disconnected, loading)

---

## Hardware-Specific Notes

### RK3588 SoC Capabilities
- **MPP (Media Process Platform)**: Hardware-accelerated H.264/H.265 encoding
- **Direct HDMI RX**: One native controller (`/dev/video60`)
- **MIPI CSI**: Multiple interfaces for camera/bridge inputs

### LT6911UXE Bridge Chips
- **Function**: Convert HDMI to MIPI CSI
- **Detection**: Check `dmesg` for detection messages
- **Resolution Support**: Various resolutions (1080p, 4K, etc.)
- **Format**: Outputs UYVY after initialization

### DMA Buffer Limitations
- **Potential issue**: Concurrent captures may hit DMA buffer limits
- **Mitigation**: Proper pipeline cleanup and device release
- **Monitoring**: Watch for "Device or resource busy" errors

---

## Configuration Patterns

### Camera Configuration
```yaml
cameras:
  cam0:
    device: "/dev/video0"    # HDMI N0 (rkcif)
    resolution: 1920x1080    # Target resolution
    codec: h264              # Recording codec
    mediamtx_enabled: true   # Enable streaming
```

### Pipeline Resolution Handling
- **Recording**: Use source resolution (4K if available)
- **Preview**: Scale to 1080p for performance
- **Streaming**: H.264 at 1080p (HLS/WebRTC)

---

## Testing and Validation

### Device Signal Verification
```bash
# Check device format
v4l2-ctl -d /dev/video0 --get-fmt-video

# Check subdev for signal detection
v4l2-ctl -d /dev/v4l-subdev2 --get-subdev-fmt pad=0

# Check dmesg for bridge detection
dmesg | grep LT6911UXE
```

### Pipeline Testing
```bash
# Test GStreamer pipeline directly
gst-launch-1.0 -v v4l2src device=/dev/video0 ! \
  'video/x-raw,format=UYVY,width=1920,height=1080' ! \
  fakesink
```

### Service Status
```bash
# Check service status
systemctl status preke-recorder

# Check logs
journalctl -u preke-recorder -f

# Check preview status
curl http://localhost:8000/preview/status
```

---

## Future Improvements

1. **Automatic device initialization**: Detect and initialize devices on signal change
2. **Dynamic resolution adaptation**: Handle resolution changes without restart
3. **Better error recovery**: Automatic retry with exponential backoff
4. **Performance optimization**: Tune GStreamer pipeline parameters for better CPU usage
5. **Signal quality monitoring**: Detect and report signal quality issues

---

## Key Takeaways

1. **rkcif devices require explicit format initialization** - this is critical for proper operation
2. **Always query device capabilities** before building pipelines
3. **Different device types need different pipeline configurations**
4. **WebRTC needs longer timeouts** for slower streams
5. **Maintain aspect ratio** in UI for proper video display
6. **Proper cleanup** prevents resource leaks and stuck services
7. **Comprehensive logging** is essential for troubleshooting hardware issues

---

*Last Updated: 2025-12-15*
*Based on R58 4x4 3S with custom Debian build*

