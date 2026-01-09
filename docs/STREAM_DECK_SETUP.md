# Stream Deck Setup for VDO.ninja Mixer Controls

**Last Updated**: January 9, 2026  
**Status**: ✅ API Endpoints Ready

---

## Overview

The R58 mixer provides HTTP API endpoints compatible with Bitfocus Companion and Stream Deck for controlling VDO.ninja mixer functions.

## Prerequisites

1. **Bitfocus Companion** installed on your computer
2. **Stream Deck** connected
3. **R58 device** accessible (local network or Tailscale)
4. **VDO.ninja API key** configured in `config.yml`

## API Base URL

- **Local Network**: `http://<R58_IP>:8000` (e.g., `http://192.168.1.24:8000`)
- **Tailscale**: `https://app.itagenten.no` (via FRP tunnel)
- **Remote**: `https://app.itagenten.no` (via FRP tunnel)

## Companion HTTP Module Setup

1. **Open Companion** and create a new instance
2. **Add HTTP Module**:
   - Click "Add Instance" → Search for "HTTP"
   - Select "HTTP Request/Webhook"
3. **Configure Base URL**:
   - **Base URL**: `https://app.itagenten.no` (or your R58 IP)
   - Leave other fields as default

## Stream Deck Button Configurations

### Scene Switching Buttons

**Button 1 - Scene 1**:
- **Type**: HTTP Request
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/scene/0` (Scene 0 = auto grid)
- **Headers**: `Content-Type: application/json`

**Button 2 - Scene 2**:
- **Type**: HTTP Request
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/scene/1`
- **Headers**: `Content-Type: application/json`

**Buttons 3-9**: Similar, incrementing scene number (0-8)

### Recording Control

**Start Recording**:
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/recording/start`

**Stop Recording**:
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/recording/stop`

### Audio Controls

**Toggle Mute (Guest 1)**:
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/guest/1/mute`

**Set Volume (Guest 1, 50%)**:
- **Method**: `POST`
- **URL**: `/api/v1/vdo-ninja/guest/1/volume`
- **Body**: `{"volume": 100}` (0-200, where 100 = normal)

**Note**: Guest IDs can be obtained from `/api/v1/vdo-ninja/guests` endpoint

## Getting Guest List (for Feedback)

**Get Guests**:
- **Method**: `GET`
- **URL**: `/api/v1/vdo-ninja/guests`
- **Response**: JSON array of guest objects with `id`, `label`, `slot`, etc.

Use this endpoint to:
- Get available guest IDs for mute/volume controls
- Set up dynamic buttons based on connected guests
- Display guest status on Stream Deck

## Testing Endpoints

### Using curl (Local Network)

```bash
# Scene switching
curl -X POST http://192.168.1.24:8000/api/v1/vdo-ninja/scene/1

# List guests
curl http://192.168.1.24:8000/api/v1/vdo-ninja/guests

# Toggle mute
curl -X POST http://192.168.1.24:8000/api/v1/vdo-ninja/guest/1/mute

# Set volume
curl -X POST http://192.168.1.24:8000/api/v1/vdo-ninja/guest/1/volume \
  -H "Content-Type: application/json" \
  -d '{"volume": 100}'

# Start recording
curl -X POST http://192.168.1.24:8000/api/v1/vdo-ninja/recording/start
```

### Using curl (Tailscale/Remote)

```bash
# Replace with your R58 Tailscale IP or use app.itagenten.no
curl -X POST https://app.itagenten.no/api/v1/vdo-ninja/scene/1
```

## Troubleshooting

### Buttons Not Working

1. **Check API Key**: Verify `vdo_ninja.api_key` in `config.yml` matches the `&api=` parameter in mixer URL
2. **Check Network**: Ensure Companion can reach R58 device
3. **Check Logs**: View backend logs for errors:
   ```bash
   ./connect-r58-frp.sh 'sudo journalctl -u preke-recorder -f'
   ```
4. **Test Endpoints**: Use curl to verify endpoints respond correctly

### Scene Switching Not Working

- **Verify API Key**: The mixer URL must include `&api=YOUR_API_KEY`
- **Check VDO.ninja Version**: HTTP API requires VDO.ninja v22+
- **Verify Room**: Ensure you're controlling the correct room
- **Check Browser Console**: Look for postMessage errors in mixer iframe

### Guest IDs Not Found

- Use `GET /api/v1/vdo-ninja/guests` to list available guests
- Guest IDs are typically slot numbers (1, 2, 3, etc.) or stream IDs
- Stream IDs are short alphanumeric strings (e.g., "4v6AX33")

## Example Companion Configuration

### Scene Strip (9 Buttons)

```
Button 1: POST /api/v1/vdo-ninja/scene/0  (Auto Grid)
Button 2: POST /api/v1/vdo-ninja/scene/1  (Scene 1)
Button 3: POST /api/v1/vdo-ninja/scene/2  (Scene 2)
...
Button 9: POST /api/v1/vdo-ninja/scene/8  (Scene 8)
```

### Audio Strip (Per Guest)

```
Button 1: POST /api/v1/vdo-ninja/guest/1/mute
Button 2: POST /api/v1/vdo-ninja/guest/2/mute
Button 3: POST /api/v1/vdo-ninja/guest/3/mute
```

### Recording Control

```
Button 1: POST /api/v1/vdo-ninja/recording/start
Button 2: POST /api/v1/vdo-ninja/recording/stop
```

## Advanced: Dynamic Guest Buttons

Use Companion's "HTTP Request" action with a variable URL:

1. **Get Guest List**: `GET /api/v1/vdo-ninja/guests`
2. **Parse Response**: Extract guest IDs
3. **Create Buttons Dynamically**: Use guest IDs in button URLs

## Notes

- **API Key Security**: The API key is included in the VDO.ninja URL. Use a secure, unique key in production.
- **Local vs Remote**: Local network access is faster. Use Tailscale for remote access.
- **Scene Numbers**: VDO.ninja uses 0-8 for scenes (0 = auto grid). Our UI maps 1-9 to 0-8 for user-friendliness.
- **Guest IDs**: Can be slot numbers (1, 2, 3...) or stream IDs. Use `/guests` endpoint to get actual IDs.
