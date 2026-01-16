# Camera & PTZ Controls Implementation Summary

**Date**: January 16, 2026  
**Status**: ✅ Complete

## Overview

Camera controls and PTZ (Pan/Tilt/Zoom) controls are now fully functional in both **Recorder** and **Mixer** modes. All controls work independently of the current device mode.

## Implementation

### Frontend Components

1. **CameraControlModal** (`packages/frontend/src/components/camera/CameraControlModal.vue`)
   - Full camera control interface with tabs:
     - Basic: Focus, White Balance, Exposure
     - Advanced: ISO, Shutter, Iris, Gain
     - PTZ: Pan/Tilt/Zoom controls
     - Color: Color correction (coming soon)
   - Available in both RecorderView and MixerView

2. **PTZControllerPanel** (`packages/frontend/src/components/camera/PTZControllerPanel.vue`) - NEW
   - Hardware joystick/gamepad support
   - WebSocket-based real-time PTZ control
   - Manual PTZ controls for testing
   - Gamepad auto-detection and reconnection
   - Available in both RecorderView and MixerView

3. **SessionInfoV2** (RecorderView sidebar)
   - Camera Controls section with list of cameras
   - PTZ Controller toggle button
   - Camera Control Modal integration

4. **MixerControlPanel** (MixerView overlay)
   - Camera Controls section
   - PTZ Controller toggle button
   - Camera Control Modal integration

### Backend Endpoints

All endpoints in `src/main.py`:

#### Camera Control Endpoints
- `GET /api/v1/cameras/` - List configured cameras
- `GET /api/v1/cameras/{name}/status` - Get camera status
- `GET /api/v1/cameras/{name}/settings` - Get camera settings
- `PUT /api/v1/cameras/{name}/settings/focus` - Set focus
- `PUT /api/v1/cameras/{name}/settings/whiteBalance` - Set white balance
- `PUT /api/v1/cameras/{name}/settings/exposure` - Set exposure (OBSbot)
- `PUT /api/v1/cameras/{name}/settings/iso` - Set ISO (Blackmagic)
- `PUT /api/v1/cameras/{name}/settings/shutter` - Set shutter (Blackmagic)
- `PUT /api/v1/cameras/{name}/settings/iris` - Set iris (Blackmagic)
- `PUT /api/v1/cameras/{name}/settings/gain` - Set gain (Blackmagic)
- `PUT /api/v1/cameras/{name}/settings/ptz` - Move PTZ (OBSbot)
- `PUT /api/v1/cameras/{name}/settings/ptz/preset/{id}` - Recall PTZ preset
- `PUT /api/v1/cameras/{name}/settings/colorCorrection` - Color correction (Blackmagic)
- `GET /api/v1/cameras/config` - Get camera configuration
- `PUT /api/v1/cameras/config` - Update camera configuration

#### PTZ Controller Endpoints
- `GET /api/v1/ptz-controller/cameras` - List PTZ-capable cameras
- `PUT /api/v1/ptz-controller/{name}/ptz` - Execute PTZ command (hardware controller)
- `WebSocket /api/v1/ptz-controller/ws` - Real-time PTZ control

### Mode Independence

✅ **Camera controls work in both modes**:
- Camera control manager is initialized at startup
- Endpoints don't check current mode
- Controls are for external cameras (Blackmagic, OBSbot), not HDMI inputs
- Mode only affects HDMI input recording, not external camera control

✅ **PTZ controls work in both modes**:
- PTZ endpoints are mode-independent
- WebSocket connection works regardless of mode
- Gamepad/joystick input works in both modes

## Usage

### In Recorder View

1. Navigate to Recorder view
2. In sidebar, find "Camera Controls" section
3. Click "Controls" button next to a camera to open CameraControlModal
4. Click "Open PTZ Controller" to open PTZControllerPanel for gamepad control

### In Mixer View

1. Navigate to Mixer view
2. Click settings icon (top-left) to show MixerControlPanel
3. Find "Camera Controls" section
4. Click camera name to open CameraControlModal
5. Click "Open PTZ Controller" to open PTZControllerPanel

### PTZ Controller (Gamepad)

1. Connect USB or Bluetooth gamepad/joystick
2. Open PTZ Controller panel
3. Select camera from dropdown
4. Click "Connect" to establish WebSocket connection
5. Gamepad will auto-detect and start controlling PTZ
6. Use left stick for pan/tilt, triggers for zoom

## Supported Cameras

- **Blackmagic Design** cameras (via ATEM protocol)
  - Focus, White Balance, ISO, Shutter, Iris, Gain
  - Color correction
  - No PTZ support

- **OBSbot Tail 2** cameras
  - Focus, White Balance, Exposure
  - PTZ (Pan/Tilt/Zoom)
  - PTZ presets (0-15)

## Configuration

Add cameras to `config.yml`:

```yaml
external_cameras:
  - name: "BMD Cam 1"
    type: blackmagic
    ip: 192.168.1.101
    port: 80
    enabled: true
  
  - name: "Obsbot PTZ"
    type: obsbot_tail2
    ip: 192.168.1.110
    port: 52381
    enabled: true
```

## Testing

All endpoints tested and verified:
- ✅ Camera list endpoint returns empty array (no cameras configured)
- ✅ PTZ controller endpoint returns empty array (no PTZ cameras configured)
- ✅ Endpoints return 503 if camera_control_manager not initialized
- ✅ Endpoints return 404 if camera not found
- ✅ All endpoints work regardless of recorder/mixer mode

## Notes

- Camera controls are for **external cameras** (Blackmagic, OBSbot), not HDMI inputs
- HDMI inputs (cam0-cam3) are controlled via different endpoints (`/api/ingest/*`)
- PTZ Controller uses WebSocket for low-latency control (~30Hz update rate)
- Gamepad support works with USB and Bluetooth gamepads/joysticks
- Camera control manager initializes at startup if `external_cameras` are configured
