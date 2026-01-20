# Local VDO.Ninja Setup on R58

This guide explains how to run VDO.Ninja locally on the R58 device for resilient program streaming that doesn't depend on internet connectivity.

## Overview

By running VDO.Ninja locally, you get:
- **Resilience**: Program stream continues even if internet drops
- **Local Control**: Control the mixer from any device on the local network
- **Remote Backup**: Can still connect to remote VDO.Ninja when internet is available
- **Low Latency**: Local WebRTC connections have minimal delay

## Architecture Options

### Option A: R58 Built-in Mixer (Simplest)

The R58 already has a built-in mixer that works without internet:

```
┌─────────────────────────────────────────────────────────────────┐
│                    R58 Local Network                             │
│                                                                  │
│  HDMI Inputs ──→ R58 Mixer ──→ MediaMTX ──→ Local WebRTC/HLS   │
│                      ↓                            ↓              │
│              Web Interface              Local PC/Tablet          │
│           (192.168.1.25:8000)              Browser              │
└─────────────────────────────────────────────────────────────────┘
```

**Access locally**: `http://192.168.1.25:8000`
**Program stream**: `http://192.168.1.25:8888/mixer_program/index.m3u8` (HLS)
**WebRTC**: `http://192.168.1.25:8889/mixer_program/whep`

### Option B: Self-Hosted VDO.Ninja (Full VDO.Ninja Features)

```
┌─────────────────────────────────────────────────────────────────┐
│                    R58 Device                                    │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ VDO.Ninja    │    │ coturn       │    │ nginx        │      │
│  │ (Node.js)    │────│ (TURN/STUN)  │────│ (HTTPS)      │      │
│  │ Signaling    │    │ NAT Traverse │    │ Web Server   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         ↓                                        ↓              │
│    WebSocket                              https://r58.local     │
│    Signaling                              VDO.Ninja Interface   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
              Local clients connect via WebRTC
              (no internet required for local network)
```

## Option A: Using R58 Built-in Mixer (Recommended)

This is already working! The built-in mixer provides:

### Features
- Scene-based switching (quad, pip, fullscreen, etc.)
- Web-based control interface
- HLS and WebRTC streaming
- No internet dependency

### How to Use

1. **Access the Switcher Interface**:
   ```
   Local: http://192.168.1.25:8000/switcher.html
   Remote: https://recorder.itagenten.no/switcher.html
   ```

2. **Start the Mixer**:
   - Click "START" in the switcher interface
   - Or use API: `curl -X POST http://192.168.1.25:8000/api/mixer/start`

3. **View Program Output**:
   - HLS: `http://192.168.1.25:8888/mixer_program/index.m3u8`
   - WebRTC: Use MediaMTX WHEP endpoint

4. **Control from Multiple Devices**:
   - Any device on the local network can open the switcher interface
   - Changes sync automatically

### Simultaneous Local + Remote Control

You can control from both local PC and remote location:

```bash
# Local PC
open http://192.168.1.25:8000/switcher.html

# Remote (via Cloudflare Tunnel)
open https://recorder.itagenten.no/switcher.html
```

Both interfaces control the same mixer - changes are reflected immediately.

## Option B: Self-Hosted VDO.Ninja

### Prerequisites

- R58 with network access
- Domain name (optional, can use IP)
- ~500MB free storage

### Step 1: Install Dependencies

```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js (v18+)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install build tools
sudo apt install -y git build-essential

# Install coturn (TURN/STUN server)
sudo apt install -y coturn

# Install nginx for HTTPS
sudo apt install -y nginx certbot python3-certbot-nginx
```

### Step 2: Clone VDO.Ninja

```bash
# Create directory
sudo mkdir -p /opt/vdo-ninja
sudo chown linaro:linaro /opt/vdo-ninja
cd /opt/vdo-ninja

# Clone the repository
git clone https://github.com/steveseguin/vdo.ninja.git .

# Install dependencies
npm install
```

### Step 3: Configure coturn (TURN Server)

Edit `/etc/turnserver.conf`:

```conf
# Basic settings
listening-port=3478
tls-listening-port=5349

# Realm (use your domain or IP)
realm=r58.itagenten.no

# Authentication
lt-cred-mech
user=vdoninja:your-secure-password

# Network
listening-ip=0.0.0.0
external-ip=YOUR_PUBLIC_IP/YOUR_LOCAL_IP

# Enable verbose logging (for debugging)
verbose

# Disable CLI
no-cli
```

Start coturn:
```bash
sudo systemctl enable coturn
sudo systemctl start coturn
```

### Step 4: Configure nginx (HTTPS)

Create `/etc/nginx/sites-available/vdo-ninja`:

```nginx
server {
    listen 80;
    server_name r58.local r58.itagenten.no;

    location / {
        root /opt/vdo-ninja;
        index index.html;
        try_files $uri $uri/ =404;
    }

    # WebSocket proxy for signaling
    location /ws {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

Enable and get SSL:
```bash
sudo ln -s /etc/nginx/sites-available/vdo-ninja /etc/nginx/sites-enabled/
sudo certbot --nginx -d r58.itagenten.no
sudo systemctl restart nginx
```

### Step 5: Run VDO.Ninja Signaling Server

Create systemd service `/etc/systemd/system/vdo-ninja.service`:

```ini
[Unit]
Description=VDO.Ninja Signaling Server
After=network.target

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/vdo-ninja
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vdo-ninja
sudo systemctl start vdo-ninja
```

### Step 6: Using Local VDO.Ninja

Access your local VDO.Ninja:
```
https://r58.itagenten.no/?wss=wss://r58.itagenten.no/ws&turn=turns:r58.itagenten.no:5349
```

Or for local network only:
```
https://r58.local/?wss=wss://r58.local/ws&turn=turn:r58.local:3478
```

## Hybrid Approach (Best of Both Worlds)

Use the R58 mixer as the primary mixing engine, with VDO.Ninja for remote contribution:

```
Remote Contributors ──→ vdo.ninja ──→ HDMI Output ──→ R58 HDMI Input
                                           ↓
                                    R58 Local Mixer
                                           ↓
                                   Program Output
                                    ├─→ Local HLS/WebRTC
                                    └─→ Stream to CDN
```

### Benefits
1. **Local Resilience**: R58 mixer continues even if VDO.Ninja connection drops
2. **Remote Control**: Both local and remote operators can control
3. **Quality Control**: R58 handles final output quality
4. **Backup Inputs**: Local cameras continue if remote feeds fail

## Performance on R58

### Resource Usage (Self-Hosted VDO.Ninja)
- **CPU**: ~5-15% (signaling is lightweight)
- **RAM**: ~300-500MB
- **Network**: Depends on number of streams
- **Storage**: ~100MB

### Simultaneous Operations
The R58 can handle:
- ✅ VDO.Ninja signaling server
- ✅ coturn TURN server
- ✅ R58 Mixer (4 cameras compositing)
- ✅ Recording (4 simultaneous streams)
- ✅ MediaMTX streaming

Total CPU usage estimate: 40-60% under full load

## Troubleshooting

### VDO.Ninja Connection Issues
```bash
# Check signaling server
sudo systemctl status vdo-ninja

# Check coturn
sudo systemctl status coturn

# Test TURN server
turnutils_stunclient r58.local
```

### WebRTC Connection Fails
1. Ensure TURN server is accessible
2. Check firewall allows UDP 3478, 5349, and 49152-65535
3. Verify SSL certificates are valid

### High Latency
- Use local network instead of internet
- Enable hardware acceleration
- Reduce resolution/bitrate if needed

## Quick Start Checklist

### For R58 Built-in Mixer (No Setup Needed)
- [ ] Access `http://192.168.1.25:8000/switcher.html`
- [ ] Click "START"
- [ ] Select scene
- [ ] View program at `http://192.168.1.25:8888/mixer_program/index.m3u8`

### For Self-Hosted VDO.Ninja
- [ ] Install Node.js, coturn, nginx
- [ ] Clone VDO.Ninja repository
- [ ] Configure TURN server
- [ ] Set up SSL certificates
- [ ] Create systemd services
- [ ] Test with local clients

## Recommended Setup

For most use cases, I recommend:

1. **Use R58 Built-in Mixer** for local program production
2. **Use public VDO.Ninja** for remote contributors (they send to vdo.ninja)
3. **Capture VDO.Ninja output** via HDMI into R58
4. **Distribute program** via R58's MediaMTX

This gives you:
- Internet-independent local mixing
- Easy remote contribution setup
- Professional program output control
- Resilience if any single component fails
