# VPU Resource Limits on Rockchip RK3588

## Overview

The Rockchip RK3588 VPU (Video Processing Unit) is a powerful hardware accelerator for video encoding and decoding, but it has **finite resources** that must be carefully managed.

## Hardware Limits

### Maximum Concurrent Sessions
- **Theoretical Limit**: ~16 sessions
- **Practical Limit**: **6-8 sessions** for stability
- **Safe Limit**: **4-6 sessions** recommended

### Session Types
Each VPU operation counts as one session:
- **Hardware Encoder** (mpph264enc, mpph265enc): 1 session
- **Hardware Decoder** (mppvideodec): 1 session

## Resource Budgeting

### Example: 4-Camera Recording System

#### ❌ UNSAFE Configuration (12 sessions - WILL CRASH)
```
Camera 0: Recording (mpph264enc) + Preview (mpph264enc) + Mixer decode (mppvideodec) = 3
Camera 1: Recording (mpph264enc) + Preview (mpph264enc) + Mixer decode (mppvideodec) = 3  
Camera 2: Recording (mpph264enc) + Preview (mpph264enc) + Mixer decode (mppvideodec) = 3
Camera 3: Recording (mpph264enc) + Preview (mpph264enc) + Mixer decode (mppvideodec) = 3
─────────────────────────────────────────────────────────────────────────────────────────
TOTAL: 12 VPU sessions ⚠️ EXCEEDS LIMIT → KERNEL PANIC
```

#### ✅ SAFE Configuration (8 sessions - STABLE)
```
Camera 0: Recording (mpph264enc) + Preview (x264enc SW) + Mixer decode (mppvideodec) = 2
Camera 1: Recording (mpph264enc) + Preview (x264enc SW) + Mixer decode (mppvideodec) = 2  
Camera 2: Recording (mpph264enc) + Preview (x264enc SW) + Mixer decode (mppvideodec) = 2
Camera 3: Recording (mpph264enc) + Preview (x264enc SW) + Mixer decode (mppvideodec) = 2
─────────────────────────────────────────────────────────────────────────────────────────
TOTAL: 8 VPU sessions ✓ WITHIN LIMIT (4 encoders + 4 decoders)
```

## Design Guidelines

### 1. Prioritize VPU Usage
Use hardware acceleration only where it provides the most benefit:

| Use Case | Encoder Choice | Reasoning |
|----------|---------------|-----------|
| **Recording** | Hardware (mpph264enc/mpph265enc) | High quality, efficiency critical |
| **Preview/Streaming** | Software (x264enc) | Lower quality acceptable, saves VPU |
| **Mixer Input** | Hardware decoder (mppvideodec) | Low latency required |
| **Mixer Output** | Software (x264enc) | One encoder vs many, saves VPU |

### 2. Architecture Pattern
```
┌─────────────┐
│   Camera    │
└──────┬──────┘
       │ (raw video)
       ▼
   ┌───────┐
   │  tee  │ (split)
   └───┬───┘
       ├─────────────────┐
       │                 │
       ▼                 ▼
┌──────────────┐  ┌─────────────┐
│  Recording   │  │  Preview    │
│ (HW encoder) │  │ (SW encoder)│
│ mpph264enc   │  │  x264enc    │
└──────────────┘  └─────────────┘
       │                 │
       ▼                 ▼
  [File Storage]   [MediaMTX RTSP]
```

### 3. Avoid Dual Hardware Encoders
**NEVER** do this:
```gstreamer
tee name=t ! mpph264enc ! filesink  t. ! mpph264enc ! rtspclientsink
              ^^^^ HW                      ^^^^ HW
              ❌ BOTH HARDWARE - VPU OVERLOAD!
```

**ALWAYS** do this:
```gstreamer
tee name=t ! mpph264enc ! filesink  t. ! x264enc ! rtspclientsink
              ^^^^ HW                     ^^^^ SW  
              ✓ ONE HARDWARE, ONE SOFTWARE - SAFE!
```

## Monitoring VPU Usage

### Check Current VPU Sessions
```bash
# Requires root or debugfs access
sudo cat /sys/kernel/debug/mpp_service/session

# Count sessions
sudo cat /sys/kernel/debug/mpp_service/session | grep -c "session"
```

### Use VPU Health Check Script
```bash
./scripts/check_vpu_health.sh
```

### Monitor for Crashes
```bash
# Check kernel logs for VPU-related errors
sudo dmesg | grep -i "mpp\|rkvenc\|rkvdec\|rcu.*stall"

# Monitor in real-time
sudo dmesg -w | grep -i "mpp\|rkvenc\|rkvdec"
```

## Symptoms of VPU Overload

### System Behavior
1. **Kernel Panics**: System suddenly reboots
2. **RCU Stalls**: System becomes unresponsive
3. **Pipeline Failures**: GStreamer pipelines fail to start
4. **Device Busy Errors**: `/dev/video*` devices show "Device busy"

### Kernel Log Indicators
```
# RCU stall (VPU overload)
rcu: INFO: rcu_preempt self-detected stall on CPU

# MPP service errors
mpp_service: error: too many sessions

# VPU allocation failure  
rkvenc: failed to allocate encoder instance
```

## Optimization Strategies

### 1. Use H.265 for Recording (Better Compression)
```python
# Recording: H.265 hardware (30-40% smaller files)
encoder_str = "mpph265enc bps=5000000 bps-max=10000000"

# Preview: H.264 software (browser compatible)
encoder_str = "x264enc tune=zerolatency bitrate=2000"
```

### 2. Reduce Concurrent Pipelines
- **Limit active cameras**: Don't record all 4 cameras if not needed
- **Stop inactive pipelines**: Close pipelines when cameras are disabled
- **Use recording valve**: Control recording without stopping pipeline

### 3. Optimize Mixer Input Count
- **Limit scene complexity**: Use 2-3 cameras per scene, not 4+
- **Fallback to software decoding**: If VPU is full, use software decoders

### 4. Buffer Management
```python
# Use smaller buffers to reduce memory pressure
queue_size = 10  # Not 60!

pipeline = (
    f"queue max-size-buffers={queue_size} "
    f"max-size-time=0 max-size-bytes=0 leaky=downstream ! "
    f"mpph264enc ..."
)
```

## Performance Characteristics

### Hardware vs Software Encoding

| Metric | Hardware (mpph264enc) | Software (x264enc) |
|--------|----------------------|-------------------|
| **CPU Usage** | ~2-5% | ~15-25% |
| **Latency** | ~30-50ms | ~50-100ms |
| **Quality** | Good | Excellent |
| **VPU Sessions** | 1 | 0 |
| **Scalability** | Limited (4-6 max) | Unlimited (CPU bound) |

### Decision Matrix
```
Recording:     Always use hardware (quality + efficiency)
Preview:       Use software (saves VPU, acceptable quality)
Transcoding:   Use software (usually offline, not latency-critical)  
Mixer Output:  Use software (one stream, many viewers)
```

## Error Recovery

### If System Crashes
```bash
# 1. Check kernel logs
sudo dmesg | tail -100 | grep -i "panic\|rcu\|mpp"

# 2. Kill stuck GStreamer processes
sudo pkill -9 -f gst-launch

# 3. Check VPU sessions
sudo cat /sys/kernel/debug/mpp_service/session

# 4. Restart pipeline service with fewer cameras
sudo systemctl restart r58-pipeline
```

### Emergency VPU Reset
```bash
# Stop all pipeline services
sudo systemctl stop r58-pipeline r58-api

# Wait for VPU to clear
sleep 2

# Verify no VPU sessions
sudo cat /sys/kernel/debug/mpp_service/session

# Restart with reduced load
sudo systemctl start r58-api
# Start cameras one by one
```

## Code Examples

### Correct TEE Pipeline (Fixed)
```python
def build_tee_pipeline(cam_id, device, recording_path, preview_url):
    """Build split pipeline with hardware for recording, software for preview."""
    
    source = f"v4l2src device={device} ! videoconvert ! videoscale ! video/x-raw,format=NV12"
    
    # Recording: Hardware encoder (high quality)
    recording = (
        f"queue max-size-buffers=15 leaky=downstream ! "
        f"mpph264enc qp-init=20 gop=30 profile=high bps=8000000 ! "
        f"h264parse ! matroskamux ! filesink location={recording_path}"
    )
    
    # Preview: Software encoder (saves VPU)
    preview = (
        f"queue max-size-buffers=10 leaky=downstream ! "
        f"x264enc tune=zerolatency bitrate=2000 speed-preset=superfast ! "
        f"h264parse ! rtspclientsink location={preview_url}"
    )
    
    return f"{source} ! tee name=t ! {recording}  t. ! {preview}"
```

### VPU Session Counter
```python
def get_vpu_session_count():
    """Get current VPU session count."""
    try:
        with open("/sys/kernel/debug/mpp_service/session", "r") as f:
            return f.read().count("session")
    except (FileNotFoundError, PermissionError):
        return None  # VPU info not available

def can_use_hardware_encoder():
    """Check if VPU has capacity for another encoder."""
    session_count = get_vpu_session_count()
    if session_count is None:
        return True  # Assume OK if we can't check
    
    MAX_SAFE_SESSIONS = 6
    return session_count < MAX_SAFE_SESSIONS
```

## Testing Checklist

Before deploying multi-camera configuration:

- [ ] Run VPU health check: `./scripts/check_vpu_health.sh`
- [ ] Verify session count < 6: `sudo cat /sys/kernel/debug/mpp_service/session | grep -c session`
- [ ] Test with 1 camera (should use 2 VPU sessions)
- [ ] Test with 2 cameras (should use 4 VPU sessions)
- [ ] Test with 4 cameras (should use 8 VPU sessions)
- [ ] Monitor for 10 minutes without crashes
- [ ] Check kernel logs: `sudo dmesg | grep -i "panic\|rcu"`
- [ ] Verify recording quality
- [ ] Verify preview stream quality

## References

- [Rockchip MPP Documentation](https://github.com/rockchip-linux/mpp)
- [RK3588 Technical Reference Manual](https://rockchip.fr/RK3588%20TRM/)
- [GStreamer Hardware Acceleration](https://gstreamer.freedesktop.org/documentation/additional/design/hw-acceleration.html)

---

**Last Updated**: 2025-12-30  
**Applies To**: Rockchip RK3588, RK3588S hardware platforms
