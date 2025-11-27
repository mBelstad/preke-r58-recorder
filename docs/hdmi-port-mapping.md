# R58 4x4 3S HDMI Port Mapping Reference

## Physical Port to Device Node Mapping

| Physical Port Label | Device Node | Device Type | Controller/Bridge | Status |
|---------------------|-------------|-------------|-------------------|--------|
| **HDMI N0** | `/dev/video0` | rkcif | LT6911UXE (I2C 7-002b) | ✅ Configured |
| **HDMI N60** | `/dev/video60` | rk_hdmirx | Direct (fdee0000.hdmirx-controller) | ✅ Working |
| **HDMI N11** | `/dev/video11` | rkcif | LT6911UXE (I2C 4-002b) | ✅ Working |
| **HDMI N21** | `/dev/video21` | rkcif | LT6911UXE (I2C 2-002b) | ✅ Configured |

## Camera Configuration Mapping

| Camera ID | Device Node | Physical Port | Notes |
|-----------|-------------|---------------|-------|
| `cam0` | `/dev/video0` | HDMI N0 | rkcif via LT6911 bridge |
| `cam1` | `/dev/video60` | HDMI N60 | Direct hdmirx controller |
| `cam2` | `/dev/video11` | HDMI N11 | rkcif via LT6911 bridge |
| `cam3` | `/dev/video21` | HDMI N21 | rkcif via LT6911 bridge |

## Hardware Architecture

### Direct HDMI Input
- **HDMI N60** uses the RK3588 SoC's built-in HDMI RX controller
  - Controller: `fdee0000.hdmirx-controller`
  - Driver: `rk_hdmirx`
  - Format: NV16 (4:2:2) at 1080p 60fps
  - Symlink: `/dev/v4l/by-path/platform-fdee0000.hdmirx-controller-video-index0`

### HDMI-to-MIPI Bridge Inputs
- **HDMI N0, N11, N21** use LT6911UXE HDMI-to-MIPI bridge chips
  - Bridge chips convert HDMI signals to MIPI CSI
  - MIPI signals feed into Rockchip CIF (Camera Interface) devices
  - Bridges on I2C buses: `2-002b`, `4-002b`, `7-002b`
  - Format: NV16 (4:2:2) for video0/video11, Bayer (RGGB) for video21

## Format Specifications

### video0 (HDMI N0)
- **Supported Formats**: NV16, NV61, NV12, NV21, YUYV, YVYU, UYVY, VYUY
- **Recommended Format**: NV16 (4:2:2)
- **Resolution Range**: 64x64 to 3842x3805 (stepwise 8x8)
- **Pipeline Format**: NV16 → NV12 (for encoding)

### video11 (HDMI N11)
- **Supported Formats**: NV16, NV61, NV12, NV21, YUYV, YVYU, UYVY, VYUY
- **Recommended Format**: NV16 (4:2:2)
- **Resolution Range**: 64x64 to 1920x1080 (stepwise 8x8)
- **Pipeline Format**: NV16 → NV12 (for encoding)

### video21 (HDMI N21)
- **Supported Formats**: RGGB (Bayer), GRBG (Bayer)
- **Recommended Format**: RGGB (requires bayer2rgb conversion)
- **Resolution**: Discrete 1920x1080
- **Pipeline Format**: RGGB → bayer2rgb → NV12 (for encoding)

### video60 (HDMI N60)
- **Supported Formats**: BGR3, NV24, NV16, NV12
- **Recommended Format**: NV16 (4:2:2)
- **Resolution**: 1920x1080 at 60fps
- **Pipeline Format**: NV16 → NV12 (for encoding)

## Verification Commands

### Check Device Status
```bash
# Check all HDMI devices
for dev in /dev/video0 /dev/video11 /dev/video21 /dev/video60; do
  echo "=== $dev ==="
  v4l2-ctl -d $dev --all | grep -E "(Driver name|Width/Height|Pixel Format)"
done
```

### Test Device Detection
```bash
cd /opt/preke-r58-recorder
python3 test_device_detection.py
```

### Check Port Mapping
```bash
cd /opt/preke-r58-recorder
python3 -c "import sys; sys.path.insert(0, 'src'); from device_detection import get_hdmi_port_mapping; [print(f'{port}: {dev}') for port, dev in get_hdmi_port_mapping().items()]"
```

## Troubleshooting

### No Signal on Port
- **Symptom**: Device shows 0x0 or 64x64 resolution
- **Cause**: No HDMI source connected or source not powered
- **Solution**: Connect HDMI source and wait for signal detection

### Format Negotiation Errors
- **Symptom**: Pipeline errors about format negotiation
- **Cause**: Forced format doesn't match device capabilities
- **Solution**: Pipelines now use format negotiation (`video/x-raw !`) to handle this automatically

### Device Busy Errors
- **Symptom**: "Device is busy" errors
- **Cause**: Another process is using the device
- **Solution**: Check for stray `gst-launch` processes: `ps aux | grep gst-launch`

## I2C Bridge Detection

```bash
# List LT6911 bridges
ls -la /sys/bus/i2c/devices/*-002b

# Check bridge status
for bridge in /sys/bus/i2c/devices/*-002b; do
  echo "=== $(basename $bridge) ==="
  cat $bridge/name 2>/dev/null
done
```

## References

- See `docs/environment.md` for detailed environment information
- See `docs/fix-log.md` for troubleshooting history
- See `config.yml` for current camera configuration

