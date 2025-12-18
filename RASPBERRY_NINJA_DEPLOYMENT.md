# Raspberry.Ninja Deployment Summary

## ✅ Installation Complete

Raspberry.Ninja has been successfully installed and configured on the R58 device.

### What Was Installed

| Component | Location | Status |
|-----------|----------|--------|
| Raspberry.Ninja | `/opt/raspberry_ninja` | ✅ Installed |
| Python Dependencies | `/opt/preke-r58-recorder/venv` | ✅ Installed (websockets, cryptography) |
| GStreamer Plugins | System | ✅ Verified (webrtcbin, nice, dtls) |
| Publisher Services | `/etc/systemd/system/ninja-publish-cam*.service` | ✅ Created (4 services) |
| Receiver Services | `/etc/systemd/system/ninja-receive-guest*.service` | ✅ Created (2 services) |

### Systemd Services Created

#### Publishers (HDMI Cameras → VDO.Ninja)
- `ninja-publish-cam0.service` - Camera 0 (HDMI N0, /dev/video0) - **Disabled by default**
- `ninja-publish-cam1.service` - Camera 1 (HDMI N60, /dev/video60)
- `ninja-publish-cam2.service` - Camera 2 (HDMI N11, /dev/video11)
- `ninja-publish-cam3.service` - Camera 3 (HDMI N21, /dev/video22)

#### Receivers (VDO.Ninja Guests → MediaMTX)
- `ninja-receive-guest1.service` - Receives guest1 stream → `rtsp://127.0.0.1:8554/ninja_guest1`
- `ninja-receive-guest2.service` - Receives guest2 stream → `rtsp://127.0.0.1:8554/ninja_guest2`

## ⚠️ VDO.Ninja Server Configuration Required

### Issue Discovered

Your self-hosted VDO.Ninja at `vdo.itagenten.no` is serving the web interface correctly, but the **WebSocket signaling server is not responding** on the expected path.

When Raspberry.Ninja tries to connect:
```
wss://vdo.itagenten.no → HTTP 200 (not WebSocket)
```

### What's Needed

VDO.Ninja requires a separate **WebSocket signaling server** running alongside the web interface. This is typically:

1. **Steve Seguin's WebSocket Server**: https://github.com/steveseguin/websocket_server
2. **Default port**: 443 (or custom port)
3. **Path**: Usually root path `/` accepting WebSocket upgrade requests

### Two Options

#### Option 1: Use Public VDO.Ninja (Tested ✅)

The services are currently configured to use public VDO.Ninja, which works:

```bash
# Start publishing cam1 to public VDO.Ninja
sudo systemctl start ninja-publish-cam1

# View at: https://vdo.ninja/?view=r58-cam1
```

**Pros:**
- Works immediately
- No server setup needed
- Reliable infrastructure

**Cons:**
- Streams go through public servers
- Less control
- Requires internet

#### Option 2: Configure Your Self-Hosted Server

To use `vdo.itagenten.no`, you need to:

1. **Set up WebSocket signaling server**:
   ```bash
   git clone https://github.com/steveseguin/websocket_server.git
   cd websocket_server
   npm install
   node server.js
   ```

2. **Configure nginx/reverse proxy** to route WebSocket connections:
   ```nginx
   location / {
       proxy_pass http://localhost:8080;  # WebSocket server
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
   }
   ```

3. **Update services** to use your server:
   ```bash
   --server wss://vdo.itagenten.no
   ```

## Service Management

### Start Publishing Cameras

```bash
# Start individual cameras
sudo systemctl start ninja-publish-cam1
sudo systemctl start ninja-publish-cam2
sudo systemctl start ninja-publish-cam3

# Enable on boot
sudo systemctl enable ninja-publish-cam1
sudo systemctl enable ninja-publish-cam2
sudo systemctl enable ninja-publish-cam3

# Check status
sudo systemctl status ninja-publish-cam1
```

### View Streams

With public VDO.Ninja:
- **Camera 1**: https://vdo.ninja/?view=r58-cam1
- **Camera 2**: https://vdo.ninja/?view=r58-cam2
- **Camera 3**: https://vdo.ninja/?view=r58-cam3

With self-hosted (once WebSocket server is configured):
- **Camera 1**: https://vdo.itagenten.no/?view=r58-cam1&wss=vdo.itagenten.no
- **Camera 2**: https://vdo.itagenten.no/?view=r58-cam2&wss=vdo.itagenten.no
- **Camera 3**: https://vdo.itagenten.no/?view=r58-cam3&wss=vdo.itagenten.no

### Receive Remote Guests

```bash
# Start guest receivers
sudo systemctl start ninja-receive-guest1
sudo systemctl start ninja-receive-guest2

# Guests publish to VDO.Ninja with stream IDs:
# - guest1
# - guest2

# Streams appear in MediaMTX at:
# - rtsp://127.0.0.1:8554/ninja_guest1
# - rtsp://127.0.0.1:8554/ninja_guest2
```

### Stop Services

```bash
# Stop all publishers
sudo systemctl stop ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3

# Stop all receivers
sudo systemctl stop ninja-receive-guest1 ninja-receive-guest2
```

## Integration with Existing Mixer

The Ninja guest streams are published to MediaMTX paths that are already configured in `mediamtx.yml`:

```yaml
ninja_guest1:
  source: publisher
ninja_guest2:
  source: publisher
```

Your existing mixer can consume these streams just like any other camera input.

## Testing Results

### ✅ Verified Working

| Test | Result |
|------|--------|
| Raspberry.Ninja installation | ✅ Pass |
| GStreamer WebRTC plugins | ✅ Pass |
| Test source publishing | ✅ Pass |
| Real camera (cam1) publishing | ✅ Pass |
| Public VDO.Ninja connection | ✅ Pass |
| Service creation | ✅ Pass |

### ⚠️ Requires Configuration

| Test | Status | Notes |
|------|--------|-------|
| Self-hosted server connection | ⚠️ Blocked | WebSocket signaling server not configured |
| Guest receiving | ⚠️ Untested | Requires working signaling server |
| End-to-end with mixer | ⚠️ Untested | Requires guest streams |

## Performance Configuration

Current settings (per camera):
- **Resolution**: 1920x1080
- **Framerate**: 30fps
- **Bitrate**: 8000 kbps (8 Mbps)
- **Codec**: H.264
- **Error correction**: Disabled (`--nored`)

To adjust, edit the service files in `/etc/systemd/system/ninja-publish-cam*.service`

## Logs and Troubleshooting

```bash
# View publisher logs
sudo journalctl -u ninja-publish-cam1 -f

# View receiver logs
sudo journalctl -u ninja-receive-guest1 -f

# Test manually
cd /opt/raspberry_ninja
/opt/preke-r58-recorder/venv/bin/python3 publish.py --test

# Check WebSocket server connectivity
curl -I https://vdo.itagenten.no/
```

## Next Steps

1. **Option A - Use Public VDO.Ninja**:
   - Services are ready to use
   - Start services: `sudo systemctl start ninja-publish-cam1`
   - Share view URLs with remote viewers

2. **Option B - Configure Self-Hosted Server**:
   - Set up WebSocket signaling server on `vdo.itagenten.no`
   - Update nginx configuration for WebSocket proxying
   - Test connection: `python3 publish.py --test --server wss://vdo.itagenten.no`
   - Update service files to use your server

3. **Test Guest Receiving**:
   - Have a remote guest publish to stream ID `guest1`
   - Start receiver: `sudo systemctl start ninja-receive-guest1`
   - Verify stream in MediaMTX: `ffplay rtsp://127.0.0.1:8554/ninja_guest1`

4. **Integrate with Mixer**:
   - Configure mixer to use `ninja_guest1` and `ninja_guest2` as inputs
   - Test scene switching with remote guests

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         R58 Device                           │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ HDMI N0  │  │ HDMI N60 │  │ HDMI N11 │  │ HDMI N21 │   │
│  │  cam0    │  │  cam1    │  │  cam2    │  │  cam3    │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│       ▼             ▼             ▼             ▼          │
│  ┌────────────────────────────────────────────────────┐    │
│  │        Raspberry.Ninja Publishers                  │    │
│  │   (4x publish.py instances via systemd)            │    │
│  └────────────────────┬───────────────────────────────┘    │
│                       │ WebRTC                             │
└───────────────────────┼────────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │    VDO.Ninja Signaling        │
        │  (vdo.itagenten.no or public) │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │    Remote Viewers/Guests       │
        │  (Web browsers anywhere)       │
        └───────────────┬───────────────┘
                        │ WebRTC
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         R58 Device                           │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Raspberry.Ninja Receivers                      │    │
│  │   (2x publish.py --view via systemd)               │    │
│  └────────────────────┬───────────────────────────────┘    │
│                       │ RTSP                               │
│                       ▼                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │              MediaMTX                              │    │
│  │  • ninja_guest1                                    │    │
│  │  • ninja_guest2                                    │    │
│  └────────────────────┬───────────────────────────────┘    │
│                       │                                    │
│                       ▼                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Existing Mixer                           │    │
│  │  (Consumes guest streams as inputs)                │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Files Modified

- Created: `/opt/raspberry_ninja/` (cloned repository)
- Created: `/etc/systemd/system/ninja-publish-cam*.service` (4 files)
- Created: `/etc/systemd/system/ninja-receive-guest*.service` (2 files)
- Existing: `/opt/preke-r58-recorder/mediamtx.yml` (already has ninja_guest paths)
- Existing: `/opt/preke-r58-recorder/venv` (added websockets, cryptography)

---

**Status**: Installation complete, ready for use with public VDO.Ninja. Self-hosted server requires WebSocket signaling configuration.

**Last Updated**: 2025-12-18

