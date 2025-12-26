# R58 Headless Setup for Preke Studio App

This guide configures the R58 to work headless with the Preke Studio app, enabling remote control of recording, mixing, and streaming.

## Overview

The R58 will run:
1. **R58 Recorder** - HTTP API for recording control (port 5000)
2. **VDO.Ninja** - Self-hosted mixer/conference (port 8443)
3. **MediaMTX** - RTSP/RTMP/SRT streaming server (ports 8554, 1935, 8890)
4. **Cloudflared** - Secure tunnel for remote access

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    R58 Device                        │
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ R58 Recorder │  │  VDO.Ninja   │  │ MediaMTX  │ │
│  │   :5000      │  │   :8443      │  │  :8554    │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
│         │                 │                 │        │
│         └─────────────────┴─────────────────┘        │
│                         │                            │
│                  ┌──────────────┐                    │
│                  │  Cloudflared │                    │
│                  │    Tunnel    │                    │
│                  └──────────────┘                    │
└─────────────────────────┬───────────────────────────┘
                          │
                          │ HTTPS
                          ▼
                ┌──────────────────┐
                │  Preke Studio    │
                │  (Your Laptop)   │
                └──────────────────┘
```

## Prerequisites

- R58 device with Ubuntu/Debian
- Root/sudo access
- Internet connection
- Cloudflare account (for tunnel)

## Installation Steps

### 1. Install R58 Recorder

```bash
# SSH into R58
ssh user@r58-ip

# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    python3-pip python3-venv \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    python3-gi python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    git

# Clone repository
sudo mkdir -p /opt/preke-r58-recorder
sudo chown $USER:$USER /opt/preke-r58-recorder
cd /opt/preke-r58-recorder
git clone <your-repo-url> .

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install systemd service
sudo cp preke-recorder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable preke-recorder.service
sudo systemctl start preke-recorder.service

# Verify it's running
sudo systemctl status preke-recorder.service
curl http://localhost:5000/api/status
```

### 2. Install VDO.Ninja (Self-hosted)

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone VDO.Ninja
cd /opt
sudo git clone https://github.com/steveseguin/vdo.ninja.git
sudo chown -R $USER:$USER vdo.ninja
cd vdo.ninja

# Install dependencies
npm install

# Create SSL certificates (self-signed for local use)
mkdir -p ssl
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=r58.local"

# Create systemd service
sudo tee /etc/systemd/system/vdo-ninja.service > /dev/null <<EOF
[Unit]
Description=VDO.Ninja Self-hosted
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/vdo.ninja
Environment="NODE_ENV=production"
ExecStart=/usr/bin/node server.js --port 8443 --ssl-cert ssl/cert.pem --ssl-key ssl/key.pem
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start VDO.Ninja
sudo systemctl daemon-reload
sudo systemctl enable vdo-ninja.service
sudo systemctl start vdo-ninja.service

# Verify it's running
sudo systemctl status vdo-ninja.service
curl -k https://localhost:8443
```

### 3. Install MediaMTX

```bash
# Download MediaMTX
cd /opt
sudo wget https://github.com/bluenviron/mediamtx/releases/download/v1.5.0/mediamtx_v1.5.0_linux_arm64v8.tar.gz
sudo tar -xzf mediamtx_v1.5.0_linux_arm64v8.tar.gz
sudo mkdir -p /opt/mediamtx
sudo mv mediamtx /opt/mediamtx/
sudo mv mediamtx.yml /opt/mediamtx/

# Configure MediaMTX
sudo tee /opt/mediamtx/mediamtx.yml > /dev/null <<EOF
# MediaMTX Configuration for R58

# API
api: yes
apiAddress: 127.0.0.1:9997

# RTSP
rtspAddress: :8554
protocols: [tcp]
encryption: no
rtspAddress: :8554

# RTMP
rtmp: yes
rtmpAddress: :1935

# HLS
hls: yes
hlsAddress: :8888
hlsEncryption: no
hlsServerKey: server.key
hlsServerCert: server.crt

# WebRTC
webrtc: yes
webrtcAddress: :8889

# SRT
srt: yes
srtAddress: :8890

# Paths (streams)
paths:
  all:
    source: publisher
    
  # R58 Recorder streams
  cam0:
    source: publisher
  cam1:
    source: publisher
  cam2:
    source: publisher
  cam3:
    source: publisher
  mixer:
    source: publisher
EOF

# Install systemd service
sudo cp /opt/preke-r58-recorder/mediamtx.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mediamtx.service
sudo systemctl start mediamtx.service

# Verify it's running
sudo systemctl status mediamtx.service
curl http://localhost:9997/v3/config/get
```

### 4. Install Cloudflared Tunnel

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64
sudo mv cloudflared-linux-arm64 /usr/local/bin/cloudflared
sudo chmod +x /usr/local/bin/cloudflared

# Login to Cloudflare (do this once)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create r58-preke

# Configure tunnel
mkdir -p ~/.cloudflared
tee ~/.cloudflared/config.yml > /dev/null <<EOF
tunnel: <your-tunnel-id>
credentials-file: /home/$USER/.cloudflared/<your-tunnel-id>.json

ingress:
  # R58 Recorder API
  - hostname: recorder.yourdomain.com
    service: http://localhost:5000
  
  # VDO.Ninja
  - hostname: vdo.yourdomain.com
    service: https://localhost:8443
    originRequest:
      noTLSVerify: true
  
  # MediaMTX HLS
  - hostname: stream.yourdomain.com
    service: http://localhost:8888
  
  # Catch-all
  - service: http_status:404
EOF

# Install as service
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Verify tunnel
cloudflared tunnel info r58-preke
```

### 5. Configure DNS

In your Cloudflare dashboard, add CNAME records:
- `recorder.yourdomain.com` → `<tunnel-id>.cfargotunnel.com`
- `vdo.yourdomain.com` → `<tunnel-id>.cfargotunnel.com`
- `stream.yourdomain.com` → `<tunnel-id>.cfargotunnel.com`

## Configuration

### R58 Recorder Config

Edit `/opt/preke-r58-recorder/config.yml`:

```yaml
cameras:
  cam0:
    device: /dev/video0
    name: "Camera 1"
    resolution: "1920x1080"
    framerate: 30
    enabled: true
  
  cam1:
    device: /dev/video1
    name: "Camera 2"
    resolution: "1920x1080"
    framerate: 30
    enabled: true
  
  cam2:
    device: /dev/video2
    name: "Camera 3"
    resolution: "1920x1080"
    framerate: 30
    enabled: true
  
  cam3:
    device: /dev/video3
    name: "Camera 4"
    resolution: "1920x1080"
    framerate: 30
    enabled: true

recording:
  output_dir: "/mnt/recordings"
  format: "mp4"
  codec: "h264"
  bitrate: "8000k"

streaming:
  enabled: true
  mediamtx_url: "rtsp://localhost:8554"
  
mixer:
  enabled: true
  default_scene: "quad"
  output:
    resolution: "1920x1080"
    framerate: 30
    bitrate: "8000k"

server:
  host: "0.0.0.0"
  port: 5000
  cors_origins:
    - "*"
```

## Testing

### 1. Test R58 Recorder API

```bash
# From your laptop
curl https://recorder.yourdomain.com/api/status

# Start recording
curl -X POST https://recorder.yourdomain.com/api/recording/start

# Check status
curl https://recorder.yourdomain.com/api/recording/status

# Stop recording
curl -X POST https://recorder.yourdomain.com/api/recording/stop
```

### 2. Test VDO.Ninja

```bash
# Open in browser
https://vdo.yourdomain.com

# Test director mode
https://vdo.yourdomain.com/?director=test

# Test scene viewer
https://vdo.yourdomain.com/?room=test&scene=0
```

### 3. Test MediaMTX

```bash
# Check stream list
curl http://localhost:9997/v3/paths/list

# Test RTSP stream (if R58 is streaming)
ffplay rtsp://localhost:8554/cam0
```

## Using with Preke Studio App

### 1. Connect to R58

In Preke Studio launcher:
1. Select "Connect to R58"
2. Enter hostname: `recorder.yourdomain.com`
3. Enter room ID: `your-room-name`
4. Click "Connect"

### 2. Available Features

**Recorder Tab** (when connected to R58):
- Start/stop recording
- Configure cameras
- View recording status
- Access settings

**Live Mixer Tab**:
- **Director View**: Control VDO.Ninja mixer
  - Add/remove guests
  - Manage scenes
  - Audio mixing
- **Mixer View**: Preview mixed output
  - See what's being recorded/streamed
  - Monitor all sources

**Conference Tab**:
- Join video conference
- Send/receive video
- Two-way communication

## Monitoring

### Check Service Status

```bash
# R58 Recorder
sudo systemctl status preke-recorder.service
sudo journalctl -u preke-recorder.service -f

# VDO.Ninja
sudo systemctl status vdo-ninja.service
sudo journalctl -u vdo-ninja.service -f

# MediaMTX
sudo systemctl status mediamtx.service
sudo journalctl -u mediamtx.service -f

# Cloudflared
sudo systemctl status cloudflared.service
sudo journalctl -u cloudflared.service -f
```

### Check Logs

```bash
# R58 Recorder logs
tail -f /opt/preke-r58-recorder/logs/app.log

# System logs
sudo journalctl -xe
```

### Resource Usage

```bash
# CPU and Memory
htop

# Disk space
df -h

# Network
netstat -tulpn | grep -E '5000|8443|8554|1935'
```

## Troubleshooting

### R58 Recorder Not Accessible

```bash
# Check if service is running
sudo systemctl status preke-recorder.service

# Check if port is open
sudo netstat -tulpn | grep 5000

# Check firewall
sudo ufw status
sudo ufw allow 5000/tcp

# Restart service
sudo systemctl restart preke-recorder.service
```

### VDO.Ninja Not Loading

```bash
# Check service
sudo systemctl status vdo-ninja.service

# Check SSL certificates
ls -la /opt/vdo.ninja/ssl/

# Regenerate certificates if needed
cd /opt/vdo.ninja
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes

# Restart service
sudo systemctl restart vdo-ninja.service
```

### MediaMTX Streams Not Working

```bash
# Check service
sudo systemctl status mediamtx.service

# Check if R58 is publishing
curl http://localhost:9997/v3/paths/list

# Test stream locally
ffplay rtsp://localhost:8554/cam0

# Restart service
sudo systemctl restart mediamtx.service
```

### Cloudflared Tunnel Issues

```bash
# Check tunnel status
cloudflared tunnel info r58-preke

# Check service
sudo systemctl status cloudflared

# Check logs
sudo journalctl -u cloudflared -f

# Restart tunnel
sudo systemctl restart cloudflared
```

## Security Considerations

### 1. Change Default Credentials

```bash
# Add authentication to R58 Recorder
# Edit config.yml and add:
auth:
  enabled: true
  username: "admin"
  password: "your-secure-password"
```

### 2. Firewall Rules

```bash
# Only allow local access to services
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw enable

# Services are accessed via Cloudflare tunnel only
```

### 3. SSL Certificates

For production, use proper SSL certificates:
```bash
# Install certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d vdo.yourdomain.com

# Update VDO.Ninja service to use Let's Encrypt certs
```

## Backup and Recovery

### Backup Configuration

```bash
# Create backup script
sudo tee /usr/local/bin/backup-r58.sh > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR="/mnt/backups/r58-config"
DATE=$(date +%Y%m%d-%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configs
tar -czf $BACKUP_DIR/config-$DATE.tar.gz \
    /opt/preke-r58-recorder/config.yml \
    /opt/vdo.ninja/ssl/ \
    /opt/mediamtx/mediamtx.yml \
    ~/.cloudflared/config.yml \
    /etc/systemd/system/preke-recorder.service \
    /etc/systemd/system/vdo-ninja.service \
    /etc/systemd/system/mediamtx.service

echo "Backup created: $BACKUP_DIR/config-$DATE.tar.gz"
EOF

sudo chmod +x /usr/local/bin/backup-r58.sh

# Run backup
/usr/local/bin/backup-r58.sh
```

### Restore Configuration

```bash
# Extract backup
tar -xzf config-YYYYMMDD-HHMMSS.tar.gz -C /

# Reload services
sudo systemctl daemon-reload
sudo systemctl restart preke-recorder.service
sudo systemctl restart vdo-ninja.service
sudo systemctl restart mediamtx.service
sudo systemctl restart cloudflared.service
```

## Performance Tuning

### For 4K Recording

```yaml
# config.yml
cameras:
  cam0:
    resolution: "3840x2160"
    framerate: 30
    bitrate: "20000k"

recording:
  codec: "h265"  # Better compression for 4K
  bitrate: "20000k"
```

### For Low Latency Streaming

```yaml
# mediamtx.yml
paths:
  all:
    readTimeout: 5s
    writeTimeout: 5s
```

## Next Steps

1. ✅ Install all services
2. ✅ Configure Cloudflare tunnel
3. ✅ Test from Preke Studio app
4. ✅ Configure recording settings
5. ✅ Set up monitoring
6. ✅ Create backup routine

## Support

For issues:
1. Check service logs
2. Verify network connectivity
3. Test services locally first
4. Check Cloudflare tunnel status
5. Review firewall rules

## Summary

Your R58 is now configured to work headless with Preke Studio app:
- ✅ **Recording**: Control via HTTP API
- ✅ **Mixing**: VDO.Ninja for scene management
- ✅ **Streaming**: MediaMTX for RTSP/RTMP/SRT
- ✅ **Remote Access**: Cloudflare tunnel for secure connectivity
- ✅ **Monitoring**: Systemd services with logging

