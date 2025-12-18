# Raspberry.Ninja Quick Start Guide

## 🚀 Quick Commands

### Start Publishing Cameras

```bash
# Start all active cameras (cam1, cam2, cam3)
sudo systemctl start ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3

# Or individually
sudo systemctl start ninja-publish-cam1
sudo systemctl start ninja-publish-cam2
sudo systemctl start ninja-publish-cam3
```

### View Live Streams

Open these URLs in any web browser:

- **Camera 1**: https://vdo.ninja/?view=r58-cam1
- **Camera 2**: https://vdo.ninja/?view=r58-cam2
- **Camera 3**: https://vdo.ninja/?view=r58-cam3

### Stop Publishing

```bash
# Stop all
sudo systemctl stop ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3

# Or individually
sudo systemctl stop ninja-publish-cam1
```

### Enable Auto-Start on Boot

```bash
sudo systemctl enable ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3
```

### Check Status

```bash
# Check all services
sudo systemctl status ninja-publish-cam*

# Check specific camera
sudo systemctl status ninja-publish-cam1

# View logs
sudo journalctl -u ninja-publish-cam1 -f
```

## 📹 Camera Mapping

| Service | Camera | Device | HDMI Port | Status |
|---------|--------|--------|-----------|--------|
| `ninja-publish-cam0` | cam0 | /dev/video0 | HDMI N0 | Disabled (no source) |
| `ninja-publish-cam1` | cam1 | /dev/video60 | HDMI N60 | ✅ Active |
| `ninja-publish-cam2` | cam2 | /dev/video11 | HDMI N11 | ✅ Active |
| `ninja-publish-cam3` | cam3 | /dev/video22 | HDMI N21 | ✅ Active |

## 🎭 Remote Guests (Receiving)

### Start Guest Receivers

```bash
# Start receivers for guests
sudo systemctl start ninja-receive-guest1 ninja-receive-guest2
```

### Guest Instructions

Tell remote guests to:

1. Go to https://vdo.ninja/
2. Click "Create a Room" or "Share your Camera"
3. Use stream ID:
   - `guest1` for first guest
   - `guest2` for second guest
4. Share the link or stream ID

### Guest Streams in MediaMTX

Once guests connect, their streams appear at:
- `rtsp://127.0.0.1:8554/ninja_guest1`
- `rtsp://127.0.0.1:8554/ninja_guest2`

Your mixer can consume these streams as inputs.

## 🔧 Configuration

### Video Settings

Current settings (per camera):
- **Resolution**: 1920x1080
- **Framerate**: 30fps
- **Bitrate**: 8000 kbps (8 Mbps)
- **Codec**: H.264

To change, edit: `/etc/systemd/system/ninja-publish-cam*.service`

### Server Settings

Currently using: **Public VDO.Ninja** (wss://wss.vdo.ninja:443)

To switch to self-hosted server:
1. Configure WebSocket signaling server on `vdo.itagenten.no`
2. Edit service files: Add `--server wss://vdo.itagenten.no`
3. Reload: `sudo systemctl daemon-reload`
4. Restart services

## 📊 Monitoring

### Check if cameras are streaming

```bash
# Quick status check
systemctl is-active ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3

# Detailed status
sudo systemctl status ninja-publish-cam*
```

### View logs

```bash
# Live logs for cam1
sudo journalctl -u ninja-publish-cam1 -f

# Last 50 lines
sudo journalctl -u ninja-publish-cam1 -n 50

# All Ninja services
sudo journalctl -u 'ninja-*' -f
```

### Check resource usage

```bash
# CPU and memory
ps aux | grep publish.py

# Detailed process info
top -p $(pgrep -f 'publish.py.*r58-cam')
```

## 🐛 Troubleshooting

### Service won't start

```bash
# Check service status
sudo systemctl status ninja-publish-cam1

# View detailed logs
sudo journalctl -u ninja-publish-cam1 -n 100

# Test manually
cd /opt/raspberry_ninja
/opt/preke-r58-recorder/venv/bin/python3 publish.py --v4l2 /dev/video60 --streamid test --h264
```

### No video in browser

1. Check service is running: `systemctl is-active ninja-publish-cam1`
2. Check HDMI source is connected and powered on
3. Try viewing with different browser
4. Check network connectivity

### Device busy error

```bash
# Stop all services using the device
sudo systemctl stop preke-recorder ninja-publish-cam1

# Wait 2 seconds
sleep 2

# Start in correct order
sudo systemctl start preke-recorder
sudo systemctl start ninja-publish-cam1
```

### High CPU usage

- Reduce bitrate: Edit service file, change `--bitrate 8000` to `--bitrate 4000`
- Reduce resolution: Change `--width 1920 --height 1080` to `--width 1280 --height 720`
- Reload and restart: `sudo systemctl daemon-reload && sudo systemctl restart ninja-publish-cam1`

## 📁 File Locations

| Item | Location |
|------|----------|
| Raspberry.Ninja | `/opt/raspberry_ninja/` |
| Service files | `/etc/systemd/system/ninja-*.service` |
| Configuration | `/opt/raspberry_ninja/ninja-config.env` |
| Python venv | `/opt/preke-r58-recorder/venv/` |
| Documentation | `/opt/preke-r58-recorder/RASPBERRY_NINJA_*.md` |

## 🔗 Useful Links

- **VDO.Ninja**: https://vdo.ninja/
- **Raspberry.Ninja GitHub**: https://github.com/steveseguin/raspberry_ninja
- **Documentation**: https://docs.vdo.ninja/

## 💡 Tips

1. **Share view links** with remote viewers - they can watch without any software
2. **Use rooms** for multiple viewers: `https://vdo.ninja/?room=r58-studio`
3. **Enable on boot** for production use: `sudo systemctl enable ninja-publish-cam*`
4. **Monitor logs** during first use to ensure everything works
5. **Test with one camera** before enabling all

---

**Quick Test**: Start cam1 and open https://vdo.ninja/?view=r58-cam1 in your browser!

