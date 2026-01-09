# VDO.ninja Mixer Controls

**Last Updated**: January 8, 2026  
**Status**: ✅ IMPLEMENTED

---

## Overview

The R58 mixer includes a simple control panel overlay for quick access to VDO.ninja mixer controls. The panel integrates with existing camera controls and provides Companion/Stream Deck API endpoints for external automation.

## Features

### Frontend UI Controls

- **Scene Switching**: Quick buttons for scenes 1-9
- **Recording Control**: Start/stop recording with visual indicator
- **Audio Controls**: Per-source mute toggle and volume sliders
- **Camera Controls**: Direct access to external camera control modals
- **Collapsible**: Can be minimized to show full VDO.ninja mixer

### Backend API (Companion/Stream Deck)

- `POST /api/v1/vdo-ninja/scene/{sceneId}` - Switch to scene
- `POST /api/v1/vdo-ninja/guest/{guestId}/mute` - Toggle mute
- `POST /api/v1/vdo-ninja/guest/{guestId}/volume` - Set volume (0-200)
- `POST /api/v1/vdo-ninja/recording/start` - Start recording
- `POST /api/v1/vdo-ninja/recording/stop` - Stop recording
- `GET /api/v1/vdo-ninja/guests` - List connected guests

## Configuration

### config.yml

```yaml
vdo_ninja:
  api_key: "preke-r58-2024-secure-key"  # Must match &api= in VDO.ninja URL
  api_url: "https://r58-vdo.itagenten.no"  # VDO.ninja host
  room: "r58studio"
  password: "preke-r58-2024"
```

**Important**: The `api_key` must match the `&api=` parameter in the VDO.ninja mixer URL. This is automatically added by `buildMixerUrl()`.

## Using the Control Panel

1. **Open Mixer View**: Navigate to the mixer in the app
2. **Toggle Controls**: Click the settings icon (top-left) to show/hide the control panel
3. **Switch Scenes**: Click scene buttons (1-9) to switch layouts
4. **Control Audio**: Use mute buttons and volume sliders for each source
5. **Start Recording**: Click the recording button to start/stop
6. **Camera Controls**: Click camera names to open full camera control modal

## Companion/Stream Deck Setup

### Using HTTP Module

1. **Add HTTP Module** in Companion
2. **Base URL**: `https://app.itagenten.no` (or your R58 API URL)
3. **Configure Buttons**:

#### Scene Switching
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/scene/1` (change number for different scenes)
- **Headers**: `Content-Type: application/json`

#### Toggle Mute
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/guest/{guestId}/mute`
- Replace `{guestId}` with actual guest stream ID or slot number

#### Set Volume
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/guest/{guestId}/volume`
- **Body**: `{"volume": 100}` (0-200, where 100 = normal)

#### Recording
- **Start**: `POST /api/v1/vdo-ninja/recording/start`
- **Stop**: `POST /api/v1/vdo-ninja/recording/stop`

#### Get Guest List (for feedback)
- **Method**: `GET`
- **URL**: `/api/v1/vdo-ninja/guests`
- Returns JSON array of guest objects with `id`, `label`, `slot`, etc.

### Example Stream Deck Button Configurations

**Scene 1 Button**:
```
Method: POST
URL: https://app.itagenten.no/api/v1/vdo-ninja/scene/1
```

**Mute Guest 1**:
```
Method: POST
URL: https://app.itagenten.no/api/v1/vdo-ninja/guest/1/mute
```

**Start Recording**:
```
Method: POST
URL: https://app.itagenten.no/api/v1/vdo-ninja/recording/start
```

## Architecture

### Frontend
- **MixerControlPanel.vue**: Simple overlay panel using `useVdoNinja` composable
- **MixerView.vue**: Main mixer view with toggleable control panel
- Uses iframe postMessage API (no WebSocket needed for UI)

### Backend
- **src/vdo_ninja/api_client.py**: Minimal HTTP client for VDO.ninja API
- **packages/backend/r58_api/control/vdo_ninja/router.py**: FastAPI router
- **src/main.py**: Legacy API integration

## API Reference

### VDO.ninja HTTP API Format

VDO.ninja uses the format: `https://vdo.ninja/api/{apiID}/{action}`

Our backend proxies these calls, so you use: `https://app.itagenten.no/api/v1/vdo-ninja/{action}`

### Response Format

All endpoints return JSON:

```json
{
  "success": true,
  "scene_id": 1
}
```

Or for errors:

```json
{
  "detail": "VDO.ninja API not configured"
}
```

## Troubleshooting

### Control Panel Not Appearing
- Ensure iframe has loaded (wait for "Loading VDO.ninja mixer..." to disappear)
- Check browser console for errors
- Verify VDO.ninja iframe is accessible

### API Endpoints Not Working
- Verify `vdo_ninja.api_key` is set in `config.yml`
- Check that API key matches `&api=` parameter in mixer URL
- Ensure VDO.ninja instance supports HTTP API (v22+)
- Check backend logs for errors

### Companion Buttons Not Working
- Verify base URL is correct (use FRP URL if remote)
- Check that guest IDs match actual stream IDs
- Use `GET /api/v1/vdo-ninja/guests` to list available guests
- Ensure HTTP module is configured with correct method (POST/GET)

## Notes

- **API Key Security**: The API key is included in the VDO.ninja URL. Use a secure, unique key in production.
- **Iframe vs HTTP API**: Frontend UI uses iframe postMessage (faster, real-time). Backend API uses HTTP (for external tools).
- **Camera Controls**: External camera controls (BMD, OBSbot, Sony) are separate from VDO.ninja guest controls.
- **Scene Numbers**: VDO.ninja scenes are 0-8 (0 = auto grid). Our UI uses 1-9 for user-friendliness (maps to 0-8 internally).

## Future Enhancements (Backlog)

- WebSocket API for real-time state updates
- Advanced guest management UI
- Custom layout editor
- Transition effects control
- Audio mixer with meters
- Scene preset management
