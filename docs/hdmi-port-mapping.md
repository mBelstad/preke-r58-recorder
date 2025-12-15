# R58 4x4 3S HDMI Port Mapping Reference

## Physical Port to Device Node Mapping

| Physical Port Label | Device Node | V4L2 Subdev | Device Type | Controller/Bridge | Format |
|---------------------|-------------|-------------|-------------|-------------------|--------|
| **HDMI N0** | `/dev/video0` | `/dev/v4l-subdev2` | rkcif | LT6911UXE (I2C 7-002b) | UYVY/YVYU |
| **HDMI N60** | `/dev/video60` | N/A (direct) | rk_hdmirx | Direct (fdee0000.hdmirx-controller) | NV16 |
| **HDMI N11** | `/dev/video11` | `/dev/v4l-subdev7` | rkcif | LT6911UXE (I2C 4-002b) | UYVY |
| **HDMI N21** | `/dev/video22` | `/dev/v4l-subdev12` | rkcif | LT6911UXE (I2C 2-002b) | UYVY |

## Camera Configuration Mapping

| Camera ID | Device Node | Physical Port | Notes |
|-----------|-------------|---------------|-------|
| `cam0` | `/dev/video0` | HDMI N0 | rkcif via LT6911 bridge (7-002b) |
| `cam1` | `/dev/video60` | HDMI N60 | Direct hdmirx controller |
| `cam2` | `/dev/video11` | HDMI N11 | rkcif via LT6911 bridge (4-002b) |
| `cam3` | `/dev/video22` | HDMI N21 | rkcif via LT6911 bridge (2-002b) |

## Critical: Format Initialization Required

The LT6911 HDMI-to-MIPI bridge devices (`video0`, `video11`, `video22`) report **0x0 resolution** until the format is explicitly set. This is a driver quirk.

### Solution: Initialize from Subdev

The V4L2 subdevs (`v4l-subdev2`, `v4l-subdev7`, `v4l-subdev12`) correctly report the detected HDMI resolution. The application:

1. Queries the subdev for the actual resolution
2. Sets that format on the video device using `v4l2-ctl --set-fmt-video`
3. Then starts the GStreamer pipeline

This is handled automatically by:
- **`initialize_rkcif_device()`** function in `src/device_detection.py`
- **`scripts/init_hdmi_inputs.sh`** script run at service startup

### Manual Initialization

```bash
# Example: Initialize video11 from its subdev
resolution=$(v4l2-ctl -d /dev/v4l-subdev7 --get-subdev-fmt pad=0 | grep "Width/Height" | awk -F': ' '{print $2}')
width=$(echo $resolution | cut -d'/' -f1)
height=$(echo $resolution | cut -d'/' -f2)
v4l2-ctl -d /dev/video11 --set-fmt-video=width=$width,height=$height,pixelformat=UYVY
```

## Hardware Architecture

### Direct HDMI Input
- **HDMI N60** uses the RK3588 SoC's built-in HDMI RX controller
  - Controller: `fdee0000.hdmirx-controller`
  - Driver: `rk_hdmirx`
  - Format: NV16 (4:2:2) at 1080p 60fps
  - No initialization required - works out of the box

### HDMI-to-MIPI Bridge Inputs
- **HDMI N0, N11, N21** use LT6911UXE HDMI-to-MIPI bridge chips
  - Bridge chips convert HDMI signals to MIPI CSI
  - MIPI signals feed into Rockchip CIF (Camera Interface) devices
  - **Format must be set explicitly** before streaming
  - Recommended format: UYVY (works reliably for all bridges)

| Port | Bridge I2C Address | Media Controller | Primary Video Device | Subdev |
|------|-------------------|------------------|---------------------|--------|
| HDMI N0 | 7-002b | /dev/media0 | /dev/video0 | /dev/v4l-subdev2 |
| HDMI N11 | 4-002b | /dev/media1 | /dev/video11 | /dev/v4l-subdev7 |
| HDMI N21 | 2-002b | /dev/media2 | /dev/video22 | /dev/v4l-subdev12 |

## Format Specifications

### video0 (HDMI N0)
- **Supported Formats**: UYVY, YVYU, YUYV, NV16, NV12
- **Recommended Format**: UYVY
- **Resolution Range**: Up to 4K (depends on HDMI source)

### video11 (HDMI N11)
- **Supported Formats**: UYVY, YVYU, YUYV, NV16, NV12
- **Recommended Format**: UYVY
- **Resolution Range**: Up to 4K (depends on HDMI source)

### video22 (HDMI N21)
- **Supported Formats**: UYVY, YVYU, YUYV, NV16, NV12
- **Recommended Format**: UYVY
- **Resolution Range**: Up to 4K (depends on HDMI source)

### video60 (HDMI N60)
- **Supported Formats**: BGR3, NV24, NV16, NV12
- **Recommended Format**: NV16 (4:2:2)
- **Resolution**: 1920x1080 at 60fps (or source resolution)

## Verification Commands

### Check Device Status
```bash
# Check all HDMI devices
for dev in /dev/video0 /dev/video11 /dev/video22 /dev/video60; do
  echo "=== $dev ==="
  v4l2-ctl -d $dev --get-fmt-video 2>&1 | grep -E "(Width|Pixel)"
done
```

### Check Subdev Status (shows detected HDMI signal)
```bash
# Check subdev resolution (actual HDMI signal)
for subdev in /dev/v4l-subdev2 /dev/v4l-subdev7 /dev/v4l-subdev12; do
  echo "=== $subdev ==="
  v4l2-ctl -d $subdev --get-subdev-fmt pad=0 2>&1 | grep "Width/Height"
done
```

### Run Initialization Script Manually
```bash
/opt/preke-r58-recorder/scripts/init_hdmi_inputs.sh
```

### Test All 4 Cameras Simultaneously
```bash
# Stream 5 frames from each device
for dev in /dev/video0 /dev/video11 /dev/video22 /dev/video60; do
  timeout 3 v4l2-ctl -d $dev --stream-mmap --stream-count=5 &
done
wait
```

## Troubleshooting

### No Signal on Port (0x0 resolution)
- **Symptom**: Device shows 0x0 resolution
- **Check**: Query the subdev to see if HDMI signal is detected
- **Solution**: If subdev shows valid resolution, run init script to set format

### Format Negotiation Errors
- **Symptom**: Pipeline errors about format negotiation
- **Cause**: Format not set on video device
- **Solution**: Run `scripts/init_hdmi_inputs.sh` before starting pipelines

### Device Busy Errors
- **Symptom**: "Device is busy" errors
- **Cause**: Another process is using the device
- **Solution**: `sudo systemctl restart preke-recorder`

### Intermittent Signal Issues
- **Symptom**: Signal works sometimes, not others
- **Cause**: Bridge initialization timing
- **Solution**: The app now retries initialization automatically

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
- See `docs/cam3-cam4-diagnostic-report.md` for diagnostic investigation
- See `config.yml` for current camera configuration
