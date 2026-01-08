# Companion Bridge Service Setup

## Overview

The Companion Bridge Service allows you to use existing Companion modules (like Sony VISCA) while maintaining centralized control through the R58 API.

## How It Works

```
Companion (Sony VISCA Module) 
    ↓ (VISCA UDP commands)
Bridge Service (port 52381)
    ↓ (translates to API calls)
R58 API
    ↓
Camera
```

## Installation

### Option 1: Run as Standalone Service

```bash
cd /opt/preke-r58-recorder
python3 -m src.camera_control.companion_bridge
```

### Option 2: Create Systemd Service

Create `/etc/systemd/system/companion-bridge.service`:

```ini
[Unit]
Description=Companion Bridge Service for R58 Camera Control
After=network.target

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/preke-r58-recorder
ExecStart=/usr/bin/python3 -m src.camera_control.companion_bridge
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable companion-bridge
sudo systemctl start companion-bridge
```

## Configuration

### 1. Configure Companion

**For OBSbot Tail 2 with Sony VISCA Module:**

1. Install `companion-module-sony-visca` in Companion
2. Configure instance:
   - **Host**: R58 device IP (not camera IP directly)
   - **Port**: `52381` (bridge service port)
   - **Protocol**: UDP

**Note**: The bridge service will:
- Receive VISCA commands from Companion
- Look up camera by source IP (if configured)
- Translate to R58 API calls
- Execute via centralized API

### 2. Camera IP Mapping

The bridge service automatically loads camera configuration from `config.yml`. It maps camera IPs to camera names for API calls.

**Example config.yml:**
```yaml
external_cameras:
  - name: "OBSbot PTZ"
    type: obsbot_tail2
    ip: 192.168.1.110
    port: 52381
    enabled: true
```

The bridge will route VISCA commands from Companion to the correct camera via the R58 API.

## Supported Commands

### VISCA Commands → R58 API

| VISCA Command | R58 API Endpoint | Notes |
|---------------|-----------------|-------|
| Pan/Tilt (0x06) | `/api/v1/cameras/{name}/settings/ptz` | Converts speed to normalized values |
| Zoom (0x04 0x07) | `/api/v1/cameras/{name}/settings/ptz` | Converts speed to normalized values |
| Focus (0x04 0x08) | `/api/v1/cameras/{name}/settings/focus` | Converts speed to manual focus value |

## Testing

### Test VISCA Bridge

```bash
# Send test VISCA command (PTZ move)
echo -ne '\x81\x01\x06\x01\x08\x08\x03\x01\xFF' | nc -u localhost 52381
```

### Check Bridge Logs

```bash
# If running as service
sudo journalctl -u companion-bridge -f

# If running manually
# Check console output
```

## Troubleshooting

### Bridge Not Receiving Commands

1. **Check service is running:**
   ```bash
   sudo systemctl status companion-bridge
   ```

2. **Check port is open:**
   ```bash
   sudo netstat -ulnp | grep 52381
   ```

3. **Check firewall:**
   ```bash
   sudo ufw status
   # Allow port 52381 if needed
   ```

### Commands Not Executing

1. **Check camera config:**
   ```bash
   cat config.yml | grep -A 5 external_cameras
   ```

2. **Check R58 API:**
   ```bash
   curl http://localhost:8000/api/v1/cameras/
   ```

3. **Check bridge logs** for translation errors

### Camera IP Mapping Issues

The bridge identifies cameras by source IP. If Companion is on a different machine:

1. **Option A**: Configure bridge to accept commands from Companion IP
2. **Option B**: Use HTTP module instead of VISCA module
3. **Option C**: Modify bridge to use camera name from command

## Advanced Configuration

### Custom Port

Edit bridge service:
```python
bridge = CompanionBridge(
    r58_api_url="http://localhost:8000",
    visca_port=52382  # Custom port
)
```

### Multiple Camera Support

The bridge automatically supports multiple cameras. Just configure them in `config.yml` and the bridge will route commands based on camera IP.

## Benefits

✅ Use standard Companion modules (Sony VISCA)  
✅ Maintain centralized control through R58 API  
✅ Unified logging and monitoring  
✅ Easy to add more camera types  

## Limitations

- Currently supports VISCA commands for PTZ and basic focus
- Advanced VISCA features may need additional translation
- Requires camera IP mapping in config.yml

## Next Steps

1. Install and start bridge service
2. Configure Companion with R58 device IP
3. Test PTZ controls
4. Add more VISCA command translations as needed
