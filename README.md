# Preke R58 Recorder

A simple, reliable recording application for the Mekotronics R58 4x4 3S (RK3588) using Python, GStreamer, FastAPI, and MediaMTX.

---

## 📚 Documentation

**→ [Interactive Wiki](https://r58-api.itagenten.no/static/wiki.html)** - Complete searchable documentation with diagrams  
**→ [Documentation Index](docs/README.md)** - Structured markdown documentation  
**→ [Quick Start Guide](#-quick-start-remote-access)** - Get started in 5 minutes

---

## 🚀 Quick Start (Remote Access)

**→ See [REMOTE_ACCESS.md](REMOTE_ACCESS.md) for complete guide**

### Connect to R58
```bash
./connect-r58-frp.sh
```

### Deploy Code
```bash
./deploy-simple.sh
```

### Access Web Interface
- **Studio (Multiview)**: https://r58-api.itagenten.no/static/studio.html
- **Main App**: https://r58-api.itagenten.no/static/app.html
- **Guest Portal**: https://r58-api.itagenten.no/static/guest.html

**Method**: FRP Tunnel (not Cloudflare)  
**Stability**: ✅ 100% stable & tested

---

## Features

- Records from up to 4 HDMI-IN devices (/dev/video0-3)
- Hardware-accelerated encoding on R58 (v4l2h264enc/v4l2h265enc or mpp encoders)
- Optional streaming to MediaMTX (RTSP/RTMP/SRT)
- WebRTC/WHIP/WHEP streaming support
- Modern web-based UI with multiview
- HTTP API for control
- Works on macOS (development) and R58 (production)

## Project Structure

```
preke-r58-recorder/
├── src/
│   ├── main.py          # FastAPI application
│   ├── recorder.py      # Pipeline manager
│   ├── pipelines.py     # GStreamer pipeline builders
│   └── config.py        # Configuration management
├── config.yml           # Configuration file
├── requirements.txt     # Python dependencies
├── start.sh            # Start script
├── deploy.sh           # Deployment script
├── preke-recorder.service  # Systemd service
└── mediamtx.service     # MediaMTX systemd service
```

## Installation

### On macOS (Development)

1. Install GStreamer:
```bash
brew install gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad gst-plugins-ugly gst-libav
```

2. Run setup script:
```bash
cd preke-r58-recorder
./setup.sh
```

Or manually install Python dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the application:
```bash
./start.sh
```

Or directly:
```bash
python -m src.main
```

### On R58 (Production)

1. Install system dependencies:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav python3-gi python3-gi-cairo gir1.2-gstreamer-1.0
```

2. Clone and setup:
```bash
sudo mkdir -p /opt/preke-r58-recorder
sudo chown $USER:$USER /opt/preke-r58-recorder
cd /opt/preke-r58-recorder
git clone <your-repo> .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Install systemd service:
```bash
sudo cp preke-recorder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable preke-recorder.service
sudo systemctl start preke-recorder.service
```

## Configuration

Edit `config.yml` to configure cameras, bitrates, resolutions, and MediaMTX settings.

### Example Configuration

```yaml
cameras:
  cam0:
    device: /dev/video0
    resolution: 1920x1080
    bitrate: 5000
    codec: h264
    output_path: /var/recordings/cam0/recording.mp4
    mediamtx_enabled: true
```

## API Endpoints

- `GET /health` - Health check
- `POST /record/start/{cam_id}` - Start recording for a camera
- `POST /record/stop/{cam_id}` - Stop recording for a camera
- `GET /status` - Get status of all cameras
- `GET /status/{cam_id}` - Get status of a specific camera

## Deployment

Use the `deploy.sh` script to deploy from macOS to R58:

```bash
# Remote deployment via Cloudflare Tunnel (recommended)
./deploy.sh r58.itagenten.no linaro

# Or local network deployment
export R58_PASSWORD=linaro
./deploy.sh 192.168.1.25 linaro
```

## Remote Access

The R58 device is accessible remotely via Cloudflare Tunnel. See [docs/remote-access.md](docs/remote-access.md) for detailed instructions.

**Quick connection:**
```bash
# Use the helper script (uses SSH keys)
./connect-r58.sh

# Or connect directly
ssh linaro@r58.itagenten.no

# First time setup: ssh-copy-id linaro@r58.itagenten.no
```

**Web Interface:**
- Remote: `https://recorder.itagenten.no`
- Local: `http://192.168.1.25:8000`

## MediaMTX Integration

To enable MediaMTX streaming:

1. Install MediaMTX on R58
2. Enable MediaMTX in `config.yml`:
```yaml
mediamtx:
  enabled: true
  rtsp_port: 8554
```

3. Enable MediaMTX for specific cameras:
```yaml
cameras:
  cam0:
    mediamtx_enabled: true
```

4. Install MediaMTX service:
```bash
sudo cp mediamtx.service /etc/systemd/system/
sudo systemctl enable mediamtx.service
sudo systemctl start mediamtx.service
```

## Troubleshooting

- Check service logs: `sudo journalctl -u preke-recorder.service -f`
- Verify GStreamer plugins: `gst-inspect-1.0 v4l2src`
- Test pipeline manually: `gst-launch-1.0 v4l2src device=/dev/video0 ! autovideosink`

## License

MIT

