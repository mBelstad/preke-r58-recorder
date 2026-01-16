# Professional Companion Integration Guide

## Overview

This guide provides professional setup instructions for integrating Bitfocus Companion with the R58 camera control system. Companion allows you to control cameras via Stream Deck or other hardware controllers.

## Supported Cameras

- **Sony FX30**: Full control via REST API and VISCA over IP
- **Blackmagic Design Studio Camera 4K Pro**: Full control via REST API
- **OBSbot Tail 2**: PTZ control via VISCA over IP

## Installation

### Option 1: Install Companion on R58 Device (Recommended for Local Control)

```bash
# Clone Companion repository
cd /opt
sudo -u linaro git clone https://github.com/bitfocus/companion.git companion-app
cd companion-app

# Install dependencies
sudo -u linaro npm install

# Build Companion
sudo -u linaro npm run build
```

### Option 2: Install Companion on Separate Machine

Install Companion on a Windows/Mac/Linux machine on the same network as the R58 device.

## Configuration

### 1. Add HTTP Instance in Companion

1. Open Companion
2. Go to **Instances** → **Add Instance**
3. Search for **"HTTP"** and add it
4. Configure:
   - **Base URL**: `https://app.itagenten.no` (or `http://<device-ip>:8000` for local)
   - **Default Method**: `PUT`
   - **Default Headers**: `Content-Type: application/json`

### 2. Configure Camera in R58

Edit `config.yml` on the R58 device:

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

Restart the R58 service:
```bash
sudo systemctl restart preke-recorder
```

## Companion Button Configurations

### Sony FX30 Controls

#### Focus Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/focus`
- **Body** (Auto): `{"mode":"auto"}`
- **Body** (Manual): `{"mode":"manual","value":0.5}`

#### White Balance
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/whiteBalance`
- **Body** (Auto): `{"mode":"auto"}`
- **Body** (Manual): `{"mode":"manual","temperature":5600}`

#### ISO Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/iso`
- **Body**: `{"value":400}`

#### Shutter Speed
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/shutter`
- **Body**: `{"value":0.0167}` (1/60 second)

#### PTZ Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/ptz`
- **Body**: `{"pan":0.5,"tilt":-0.3,"zoom":0.2}`

#### PTZ Preset Recall
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/Sony FX30/settings/ptz/preset/1`
- **Body**: `{}`

### Blackmagic Studio 4K Pro Controls

#### Focus Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/BMD Studio 4K Pro/settings/focus`
- **Body** (Auto): `{"mode":"auto"}`
- **Body** (Manual): `{"mode":"manual","value":0.5}`

#### Iris Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/BMD Studio 4K Pro/settings/iris`
- **Body** (Auto): `{"mode":"auto"}`
- **Body** (Manual): `{"mode":"manual","value":2.8}`

#### ISO Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/BMD Studio 4K Pro/settings/iso`
- **Body**: `{"value":400}`

#### Shutter Speed
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/BMD Studio 4K Pro/settings/shutter`
- **Body**: `{"value":0.0167}`

#### Gain Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/BMD Studio 4K Pro/settings/gain`
- **Body**: `{"value":0}`

#### Color Correction
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/BMD Studio 4K Pro/settings/colorCorrection`
- **Body**: `{"lift":[0,0,0],"gamma":[1,1,1],"gain":[1,1,1],"offset":[0,0,0]}`

### OBSbot Tail 2 Controls

#### Focus Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/OBSbot PTZ/settings/focus`
- **Body** (Auto): `{"mode":"auto"}`
- **Body** (Manual): `{"mode":"manual","value":0.5}`

#### Exposure Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/OBSbot PTZ/settings/exposure`
- **Body** (Auto): `{"mode":"auto"}`
- **Body** (Manual): `{"mode":"manual","value":0.5}`

#### PTZ Control
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/OBSbot PTZ/settings/ptz`
- **Body**: `{"pan":0.5,"tilt":-0.3,"zoom":0.2}`

#### PTZ Preset Recall
- **Action**: HTTP Request
- **Method**: `PUT`
- **URL**: `/api/v1/cameras/OBSbot PTZ/settings/ptz/preset/1`
- **Body**: `{}`

## Professional Button Layouts

### Recommended Stream Deck Layout

#### Page 1: Camera Selection
- **Button 1**: Switch to Sony FX30
- **Button 2**: Switch to BMD Studio 4K Pro
- **Button 3**: Switch to OBSbot PTZ

#### Page 2: Focus Controls (per camera)
- **Button 1**: Focus Auto
- **Button 2**: Focus Manual (50%)
- **Button 3**: Focus Manual (75%)
- **Button 4**: Focus Manual (100%)

#### Page 3: Exposure Controls (per camera)
- **Button 1**: ISO 400
- **Button 2**: ISO 800
- **Button 3**: ISO 1600
- **Button 4**: ISO 3200
- **Button 5**: Shutter 1/60
- **Button 6**: Shutter 1/125
- **Button 7**: Shutter 1/250

#### Page 4: PTZ Controls (OBSbot/Sony)
- **Button 1**: PTZ Preset 1
- **Button 2**: PTZ Preset 2
- **Button 3**: PTZ Preset 3
- **Button 4**: PTZ Center
- **Button 5**: PTZ Left
- **Button 6**: PTZ Right
- **Button 7**: PTZ Up
- **Button 8**: PTZ Down

## Advanced: Using Companion Bridge Service

For advanced use cases where you want to use existing Companion modules (like Sony VISCA module) while maintaining centralized control:

1. **Start Bridge Service**:
```bash
cd /opt/preke-r58-recorder
python3 -m src.camera_control.companion_bridge
```

2. **Configure Companion VISCA Module**:
   - Host: R58 device IP (not camera IP)
   - Port: `52381`
   - Protocol: UDP

The bridge service will translate VISCA commands to R58 API calls automatically.

## Troubleshooting

### Camera Not Responding

1. Check camera is enabled in `config.yml`
2. Verify camera IP address is correct
3. Test camera connection:
   ```bash
   curl http://localhost:8000/api/v1/cameras/{camera_name}/status
   ```

### Companion Can't Connect

1. Verify R58 API is accessible:
   ```bash
   curl https://app.itagenten.no/api/v1/cameras/
   ```

2. Check firewall rules allow HTTP/HTTPS traffic

3. Verify Companion HTTP instance base URL is correct

### PTZ Not Working

1. For OBSbot/Sony: Verify VISCA port is correct (default: 52381)
2. Check camera supports PTZ (not all cameras do)
3. Test PTZ directly:
   ```bash
   curl -X PUT https://app.itagenten.no/api/v1/cameras/{camera_name}/settings/ptz \
     -H "Content-Type: application/json" \
     -d '{"pan":0.5,"tilt":0,"zoom":0}'
   ```

## API Reference

All camera control endpoints are documented in the R58 API documentation:
- Base URL: `https://app.itagenten.no/api/v1/cameras/`
- List cameras: `GET /api/v1/cameras/`
- Get status: `GET /api/v1/cameras/{camera_name}/status`
- Set focus: `PUT /api/v1/cameras/{camera_name}/settings/focus`
- Set white balance: `PUT /api/v1/cameras/{camera_name}/settings/whiteBalance`
- Set ISO: `PUT /api/v1/cameras/{camera_name}/settings/iso`
- Set shutter: `PUT /api/v1/cameras/{camera_name}/settings/shutter`
- Set PTZ: `PUT /api/v1/cameras/{camera_name}/settings/ptz`
- Recall PTZ preset: `PUT /api/v1/cameras/{camera_name}/settings/ptz/preset/{preset_id}`

## Professional Tips

1. **Use Variables**: Companion supports variables for dynamic camera names
2. **Feedback**: Use Companion's feedback system to show camera status
3. **Delays**: Add small delays (100-200ms) between rapid commands
4. **Error Handling**: Configure Companion to retry failed requests
5. **Logging**: Enable Companion logging to debug issues

## Support

For issues or questions:
- Check the R58 wiki: `/wiki` on the device
- Review API documentation: `/docs/API.md`
- Check Companion logs in Companion's interface
