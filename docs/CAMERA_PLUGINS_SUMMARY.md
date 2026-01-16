# Camera Plugins Summary

## Overview

The R58 device supports professional camera control for three camera models:
- **Sony FX30**
- **Blackmagic Design Studio Camera 4K Pro**
- **OBSbot Tail 2**

All cameras are controlled via the unified R58 API, which can be accessed through:
- Web UI (Camera Control Modal)
- Bitfocus Companion (HTTP module)
- Direct API calls
- Hardware PTZ controllers (joystick/gamepad)

## Camera Support Matrix

| Feature | Sony FX30 | BMD Studio 4K Pro | OBSbot Tail 2 |
|---------|-----------|-------------------|---------------|
| Focus Control | ✅ | ✅ | ✅ |
| White Balance | ✅ | ✅ | ✅ |
| Exposure | ✅ | ❌ | ✅ |
| ISO | ✅ | ✅ | ❌ |
| Shutter Speed | ✅ | ✅ | ❌ |
| Iris | ❌ | ✅ | ❌ |
| Gain | ❌ | ✅ | ❌ |
| PTZ | ✅ (VISCA) | ❌ | ✅ (VISCA) |
| PTZ Presets | ✅ | ❌ | ✅ |
| Color Correction | ❌ | ✅ | ❌ |

## Configuration

### Enable Cameras in config.yml

```yaml
external_cameras:
  # Sony FX30
  - name: "Sony FX30"
    type: sony_fx30
    ip: 192.168.1.100
    port: 80
    visca_port: 52381
    enabled: true
  
  # Blackmagic Design Studio Camera 4K Pro
  - name: "BMD Studio 4K Pro"
    type: blackmagic
    ip: 192.168.1.101
    port: 80
    enabled: true
  
  # OBSbot Tail 2
  - name: "OBSbot PTZ"
    type: obsbot_tail2
    ip: 192.168.1.110
    port: 52381
    enabled: true
```

### Restart Service After Configuration

```bash
sudo systemctl restart preke-recorder
```

## API Endpoints

All cameras use the same API structure:

- **List cameras**: `GET /api/v1/cameras/`
- **Get status**: `GET /api/v1/cameras/{camera_name}/status`
- **Get settings**: `GET /api/v1/cameras/{camera_name}/settings`
- **Set focus**: `PUT /api/v1/cameras/{camera_name}/settings/focus`
- **Set white balance**: `PUT /api/v1/cameras/{camera_name}/settings/whiteBalance`
- **Set exposure**: `PUT /api/v1/cameras/{camera_name}/settings/exposure` (Sony/OBSbot only)
- **Set ISO**: `PUT /api/v1/cameras/{camera_name}/settings/iso` (Sony/BMD only)
- **Set shutter**: `PUT /api/v1/cameras/{camera_name}/settings/shutter` (Sony/BMD only)
- **Set iris**: `PUT /api/v1/cameras/{camera_name}/settings/iris` (BMD only)
- **Set gain**: `PUT /api/v1/cameras/{camera_name}/settings/gain` (BMD only)
- **Set PTZ**: `PUT /api/v1/cameras/{camera_name}/settings/ptz` (Sony/OBSbot only)
- **Recall PTZ preset**: `PUT /api/v1/cameras/{camera_name}/settings/ptz/preset/{preset_id}` (Sony/OBSbot only)
- **Set color correction**: `PUT /api/v1/cameras/{camera_name}/settings/colorCorrection` (BMD only)

## Testing Camera Connections

### Test Camera Status

```bash
curl http://localhost:8000/api/v1/cameras/Sony%20FX30/status
```

### Test Focus Control

```bash
curl -X PUT http://localhost:8000/api/v1/cameras/Sony%20FX30/settings/focus \
  -H "Content-Type: application/json" \
  -d '{"mode":"auto"}'
```

### Test PTZ Control

```bash
curl -X PUT http://localhost:8000/api/v1/cameras/OBSbot%20PTZ/settings/ptz \
  -H "Content-Type: application/json" \
  -d '{"pan":0.5,"tilt":-0.3,"zoom":0.2}'
```

## Companion Integration

See [COMPANION_PROFESSIONAL_SETUP.md](./COMPANION_PROFESSIONAL_SETUP.md) for detailed Companion integration instructions.

## UI Access

1. Open the R58 web interface
2. Navigate to **Recorder** or **Mixer** view
3. Click the **Camera Controls** button
4. Select a camera from the list
5. Use the tabs to access different control categories:
   - **Basic**: Focus, White Balance, Exposure
   - **Advanced**: ISO, Shutter, Iris, Gain
   - **PTZ**: Pan/Tilt/Zoom controls and presets
   - **Color**: Color correction (BMD only)
   - **Companion**: Companion integration endpoints and examples

## Troubleshooting

### Camera Not Appearing

1. Check `config.yml` has camera enabled: `enabled: true`
2. Verify camera IP address is correct
3. Restart service: `sudo systemctl restart preke-recorder`
4. Check logs: `sudo journalctl -u preke-recorder -n 50`

### Camera Not Responding

1. Verify camera is on the same network
2. Test camera connectivity: `ping <camera-ip>`
3. Check camera's network settings
4. Verify camera supports network control (some cameras require enabling this)

### PTZ Not Working

1. For Sony/OBSbot: Verify VISCA port is correct (default: 52381)
2. Check camera supports PTZ (not all models do)
3. Verify VISCA protocol is enabled on camera
4. Test with direct VISCA commands if available

## Professional Tips

1. **Use Presets**: Save common PTZ positions as presets for quick recall
2. **Monitor Status**: Check camera connection status before important recordings
3. **Test First**: Always test camera controls before live production
4. **Backup Settings**: Document your camera settings for quick restoration
5. **Network Stability**: Ensure stable network connection for reliable control

## Support

- API Documentation: `/docs/API.md`
- Companion Setup: `/docs/COMPANION_PROFESSIONAL_SETUP.md`
- R58 Wiki: Access via `/wiki` on the device
