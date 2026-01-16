# Stream Deck Integration - Complete Summary

## ✅ What's Working

### Camera Support
- ✅ **Sony FX30**: Full control (Focus, WB, Exposure, ISO, Shutter, PTZ)
- ✅ **Blackmagic Studio 4K Pro**: Full control (Focus, Iris, WB, Gain, ISO, Shutter, Color Correction)
- ✅ **OBSbot Tail 2**: Full control (Focus, Exposure, WB, PTZ)

### Companion Integration
- ✅ **API Endpoints**: All camera controls accessible via HTTP API
- ✅ **Companion on PC**: Ready to use - just install Companion and configure HTTP instance
- ✅ **Companion on R58**: Installation script ready - run `scripts/install-companion.sh`
- ✅ **Stream Deck Support**: Works with both USB and network connections

### UI Components
- ✅ **Camera Control Modal**: Professional interface with tabs (Basic, Advanced, PTZ, Color, Companion)
- ✅ **Companion Integration Panel**: Shows all API endpoints with copy-to-clipboard
- ✅ **Status Indicators**: Real-time connection status for all cameras

## 🚀 Quick Start

### For PC Setup (Recommended for Most Users)

1. **Install Companion on PC:**
   - Download: https://bitfocus.io/companion/download/builds
   - Install and launch

2. **Connect Stream Deck:**
   - Plug Stream Deck into PC via USB

3. **Configure Companion:**
   - Add HTTP instance
   - Base URL: `https://app.itagenten.no`
   - Method: `PUT`
   - Headers: `Content-Type: application/json`

4. **Create Buttons:**
   - See [COMPANION_PROFESSIONAL_SETUP.md](./COMPANION_PROFESSIONAL_SETUP.md) for examples

**Done!** Stream Deck now controls cameras.

### For R58 Device Setup (Standalone)

1. **Install Companion:**
   ```bash
   ./connect-r58-frp.sh
   cd /opt/preke-r58-recorder
   sudo bash scripts/install-companion.sh
   ```

2. **Access Companion:**
   - Web UI: `https://app.itagenten.no:8080`

3. **Connect Stream Deck:**
   - USB: Plug into R58 device
   - Network: Enable network mode in Stream Deck

4. **Configure as above**

**Done!** Stream Deck works directly with device.

## 📋 API Endpoints

All endpoints use base URL: `https://app.itagenten.no`

### Camera List
```
GET /api/v1/cameras/
```

### Camera Status
```
GET /api/v1/cameras/{camera_name}/status
```

### Camera Controls
```
PUT /api/v1/cameras/{camera_name}/settings/focus
PUT /api/v1/cameras/{camera_name}/settings/whiteBalance
PUT /api/v1/cameras/{camera_name}/settings/exposure
PUT /api/v1/cameras/{camera_name}/settings/iso
PUT /api/v1/cameras/{camera_name}/settings/shutter
PUT /api/v1/cameras/{camera_name}/settings/iris
PUT /api/v1/cameras/{camera_name}/settings/gain
PUT /api/v1/cameras/{camera_name}/settings/ptz
PUT /api/v1/cameras/{camera_name}/settings/ptz/preset/{preset_id}
PUT /api/v1/cameras/{camera_name}/settings/colorCorrection
```

## 🧪 Testing

### Test API Connection
```bash
curl https://app.itagenten.no/api/v1/cameras/
```

### Test Camera Control
```bash
curl -X PUT https://app.itagenten.no/api/v1/cameras/Sony%20FX30/settings/focus \
  -H "Content-Type: application/json" \
  -d '{"mode":"auto"}'
```

### Run Test Script
```bash
bash scripts/test-companion-setup.sh
```

## 📚 Documentation

- **Quick Start**: [COMPANION_QUICK_START.md](./COMPANION_QUICK_START.md)
- **Complete Setup**: [STREAM_DECK_SETUP_COMPLETE.md](./STREAM_DECK_SETUP_COMPLETE.md)
- **Professional Setup**: [COMPANION_PROFESSIONAL_SETUP.md](./COMPANION_PROFESSIONAL_SETUP.md)
- **Camera Support**: [CAMERA_PLUGINS_SUMMARY.md](./CAMERA_PLUGINS_SUMMARY.md)
- **API Reference**: [API.md](./API.md)

## 🔧 Configuration

### Enable Cameras

Edit `config.yml`:
```yaml
external_cameras:
  - name: "Sony FX30"
    type: sony_fx30
    ip: 192.168.1.100
    port: 80
    visca_port: 52381
    enabled: true
  
  - name: "BMD Studio 4K Pro"
    type: blackmagic
    ip: 192.168.1.101
    port: 80
    enabled: true
  
  - name: "OBSbot PTZ"
    type: obsbot_tail2
    ip: 192.168.1.110
    port: 52381
    enabled: true
```

Restart service:
```bash
sudo systemctl restart preke-recorder
```

## 🎯 Example Button Configurations

### Focus Auto Button
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/focus`
- **Body**: `{"mode":"auto"}`

### ISO 400 Button
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/iso`
- **Body**: `{"value":400}`

### PTZ Preset 1 Button
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/OBSbot PTZ/settings/ptz/preset/1`
- **Body**: `{}`

## ⚙️ Service Management

### Companion Service (R58 Device)

```bash
# Start
sudo systemctl start companion

# Stop
sudo systemctl stop companion

# Restart
sudo systemctl restart companion

# Status
sudo systemctl status companion

# Logs
sudo journalctl -u companion -f

# Enable on boot
sudo systemctl enable companion
```

### R58 API Service

```bash
# Restart (after config changes)
sudo systemctl restart preke-recorder

# Status
sudo systemctl status preke-recorder

# Logs
sudo journalctl -u preke-recorder -f
```

## 🐛 Troubleshooting

### API Not Accessible
1. Check R58 device is online
2. Verify URL: `https://app.itagenten.no`
3. Test: `curl https://app.itagenten.no/api/v1/cameras/`

### Stream Deck Not Detected
1. Check USB connection
2. Restart Companion
3. Check Companion logs

### Camera Not Responding
1. Check camera is enabled in `config.yml`
2. Verify camera IP address
3. Test camera connection: `curl http://localhost:8000/api/v1/cameras/{name}/status`
4. Restart service: `sudo systemctl restart preke-recorder`

### Companion Web UI Not Accessible
1. Check service status: `sudo systemctl status companion`
2. Check port: Companion uses 8080 (R58 API uses 8000)
3. Check logs: `sudo journalctl -u companion -n 100`

## ✅ Verification Checklist

- [ ] R58 API is accessible: `curl https://app.itagenten.no/api/v1/cameras/`
- [ ] Cameras are configured in `config.yml` with `enabled: true`
- [ ] Companion is installed (on PC or R58 device)
- [ ] Companion HTTP instance is configured with correct base URL
- [ ] Stream Deck is connected (USB or network)
- [ ] Test button works (camera responds to command)
- [ ] All camera controls are accessible via Companion

## 🎉 Success!

Once all items are checked, your Stream Deck is fully integrated and ready to control cameras professionally!

For detailed button layouts and advanced configurations, see the full documentation files listed above.
