# R58 4x4 3S Multi-Camera Recorder - Project Summary

## Project Overview
Multi-camera video recording and streaming system for the Mekotronics R58 4x4 3S device. Records from 4 HDMI inputs simultaneously, provides live preview via web interface, and streams to MediaMTX.

## Current Status: ✅ Fully Operational
- **All 4 HDMI inputs working** for both recording and preview
- **Web GUI functional** with WebRTC and HLS streaming
- **Recording to SD card** (`/mnt/sdcard/recordings/`)
- **Remote access** via Cloudflare Tunnel (`https://recorder.itagenten.no`)

## Hardware Architecture

### HDMI Input Ports
| Port Label | Device Node | Type | Bridge/Ctrl | Status |
|------------|-------------|------|-------------|--------|
| HDMI N0 | `/dev/video0` | rkcif | LT6911UXE (7-002b) | ✅ Working |
| HDMI N60 | `/dev/video60` | rk_hdmirx | Direct HDMI RX | ✅ Working |
| HDMI N11 | `/dev/video11` | rkcif | LT6911UXE (4-002b) | ✅ Working |
| HDMI N21 | `/dev/video22` | rkcif | LT6911UXE (2-002b) | ✅ Working |

**Critical**: rkcif devices (`video0`, `video11`, `video22`) **require explicit format initialization** before use. See `scripts/init_hdmi_inputs.sh`.

### Device Format Requirements
- **Direct HDMI RX** (`video60`): NV16 format, works immediately
- **rkcif devices** (`video0`, `video11`, `video22`): UYVY format, must initialize via subdev

## Key Technical Details

### Platform
- **Device**: Mekotronics R58 4x4 3S
- **SoC**: Rockchip RK3588
- **OS**: Custom Debian build
- **Python**: 3.x with venv at `/opt/preke-r58-recorder/venv`
- **Service**: `preke-recorder.service` (systemd)

### Technology Stack
- **Backend**: FastAPI (Python)
- **Video Processing**: GStreamer 1.0
- **Streaming**: MediaMTX (RTSP/HLS/WebRTC)
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Remote Access**: Cloudflare Tunnel (`cloudflared`)

### Key Files
- `src/main.py` - FastAPI application, API routes, HLS proxy
- `src/pipelines.py` - GStreamer pipeline builders (recording & preview)
- `src/preview.py` - Preview pipeline manager
- `src/recorder.py` - Recording pipeline manager
- `src/device_detection.py` - Device type detection and initialization
- `config.yml` - Camera configuration
- `scripts/init_hdmi_inputs.sh` - Device initialization script (runs on boot)
- `preke-recorder.service` - systemd service file

## Configuration

### Camera Mapping (`config.yml`)
```yaml
cameras:
  cam0: device: /dev/video0    # HDMI N0
  cam1: device: /dev/video60   # HDMI N60
  cam2: device: /dev/video11   # HDMI N11
  cam3: device: /dev/video22   # HDMI N21
```

### Recording Path
- **Location**: `/mnt/sdcard/recordings/camX/recording_%Y%m%d_%H%M%S.mp4`
- **SD Card**: Mounted at `/mnt/sdcard` (ext4)

### Remote Access
- **Web GUI**: `https://recorder.itagenten.no`
- **SSH**: `r58.itagenten.no` (via Cloudflare Tunnel)
- **Local**: `http://192.168.1.24:8000`

## Critical Implementation Details

### 1. Device Initialization (REQUIRED)
rkcif devices must be initialized before use:
```bash
# Query subdev for resolution
v4l2-ctl -d /dev/v4l-subdev2 --get-subdev-fmt pad=0

# Set format on video device
v4l2-ctl -d /dev/video0 --set-fmt-video=width=W,height=H,pixelformat=UYVY
```
This is automated via `scripts/init_hdmi_inputs.sh` on boot.

### 2. GStreamer Pipeline Patterns
- **rkcif devices**: Use `UYVY` format, initialize first
- **hdmirx devices**: Use `NV16` format, can use `io-mode=mmap`
- **Always query capabilities** before building pipeline
- **Scale 4K → 1080p** for preview streams

### 3. WebRTC vs HLS
- **Local access**: Uses WebRTC (ultra-low latency)
- **Remote access**: Uses HLS via FastAPI proxy (`/hls/*`)
- **Fallback**: HLS if WebRTC fails

### 4. Video Display
- **Aspect ratio**: Maintained with `object-fit: contain`
- **Container**: 16:9 aspect ratio
- **Scaling**: HD and 4K sources appear same size in GUI

## Recent Work Completed

1. ✅ **Fixed all 4 HDMI inputs** - Discovered rkcif devices need initialization
2. ✅ **Fixed WebRTC reconnection loop** - Increased timeout, better error handling
3. ✅ **Fixed video aspect ratio** - Changed from `cover` to `contain`
4. ✅ **Remote access setup** - Cloudflare Tunnel for web and SSH
5. ✅ **SD card integration** - Recording to external storage
6. ✅ **Service stability** - Fixed stuck service issues, cleanup scripts

## Known Issues / Limitations

1. **HDMI cable quality matters** - Faulty cables can cause invalid resolution detection (e.g., 720x240)
2. **Device busy errors** - Can occur if device not properly released between recording/preview
3. **Service restart required** - After HDMI cable changes, service restart needed to detect new signal
4. **4K sources** - Automatically downscaled to 1080p for preview (recording keeps 4K)

## Common Commands

### Service Management
```bash
sudo systemctl restart preke-recorder
sudo systemctl status preke-recorder
journalctl -u preke-recorder -f
```

### Device Status
```bash
# Check device format
v4l2-ctl -d /dev/video0 --get-fmt-video

# Check subdev signal
v4l2-ctl -d /dev/v4l-subdev2 --get-subdev-fmt pad=0

# Check dmesg for bridge detection
dmesg | grep LT6911UXE
```

### API Endpoints
- `GET /status` - Camera status
- `GET /preview/status` - Preview status
- `POST /preview/start-all` - Start all previews
- `POST /record/start/{cam_id}` - Start recording
- `POST /record/stop/{cam_id}` - Stop recording

### Deployment
```bash
# Deploy to device (from local)
./deploy.sh

# Or manually
ssh linaro@192.168.1.24
cd /opt/preke-r58-recorder
sudo git pull
sudo systemctl restart preke-recorder
```

## Documentation Files
- `docs/lessons-learned.md` - Comprehensive lessons and solutions
- `docs/hdmi-port-mapping.md` - Detailed port mapping reference
- `docs/environment.md` - System environment details
- `docs/remote-access.md` - Remote access setup and troubleshooting
- `docs/fix-log.md` - Historical fixes and issues

## Important Notes

1. **Never skip device initialization** - rkcif devices will report 0x0 without it
2. **Always query capabilities** - Don't assume device format
3. **Use explicit formats** - Don't rely on GStreamer negotiation for rkcif devices
4. **Service cleanup** - Kills stuck `gst-plugin-scanner` processes on startup
5. **Lazy GStreamer init** - Uses timeout protection to prevent hangs

## Development Workflow

1. **Make changes locally**
2. **Test locally** (if possible)
3. **Commit and push** to GitHub
4. **Deploy to device**: `./deploy.sh` or manual `git pull` + service restart
5. **Test on device** via web GUI or SSH

## Next Steps / Future Improvements

- Automatic device re-initialization on signal change
- Dynamic resolution adaptation
- Better error recovery with retry logic
- Performance optimization for CPU usage
- Signal quality monitoring

---

**Last Updated**: 2025-12-15
**Project Status**: Production Ready ✅

