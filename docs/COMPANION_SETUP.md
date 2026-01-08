# Bitfocus Companion Setup for Camera Control

## Overview

This guide explains how to configure Bitfocus Companion to control cameras via the R58 API. You can use Companion's built-in **HTTP** module to send commands to the camera control API.

## Option 1: Using Companion's HTTP Module (Recommended)

Companion has a built-in HTTP module that can send HTTP requests. This is the simplest way to control cameras without creating a custom module.

### Setup Steps

1. **Add HTTP Instance in Companion**
   - Open Companion
   - Go to Instances → Add Instance
   - Search for "HTTP" and add it
   - Configure:
     - **Base URL**: `https://app.itagenten.no` (or `http://<device-ip>:8000` for local)
     - **Default Method**: PUT
     - **Default Headers**: `Content-Type: application/json`

2. **Create Camera Control Buttons**

   For each camera control, create a button with an HTTP action:

   **Example: Set Focus (Manual)**
   - Action: HTTP Request
   - Method: `PUT`
   - URL: `/api/v1/cameras/{camera_name}/settings/focus`
   - Body:
     ```json
     {
       "mode": "manual",
       "value": 0.5
     }
     ```

   **Example: Set White Balance (Auto)**
   - Action: HTTP Request
   - Method: `PUT`
   - URL: `/api/v1/cameras/{camera_name}/settings/whiteBalance`
   - Body:
     ```json
     {
       "mode": "auto"
     }
     ```

   **Example: Set ISO**
   - Action: HTTP Request
   - Method: `PUT`
   - URL: `/api/v1/cameras/{camera_name}/settings/iso`
   - Body:
     ```json
     {
       "value": 400
     }
     ```

   **Example: PTZ Move (OBSbot)**
   - Action: HTTP Request
   - Method: `PUT`
   - URL: `/api/v1/cameras/{camera_name}/settings/ptz`
   - Body:
     ```json
     {
       "pan": 0.5,
       "tilt": -0.3,
       "zoom": 0.2
     }
     ```

   **Example: Recall PTZ Preset**
   - Action: HTTP Request
   - Method: `PUT`
   - URL: `/api/v1/cameras/{camera_name}/settings/ptz/preset/1`
   - Body: `{}`

### Available Camera Controls

#### Blackmagic Design Studio Camera 4K Pro

| Control | URL | Body |
|---------|-----|------|
| Focus (Auto) | `/api/v1/cameras/{name}/settings/focus` | `{"mode": "auto"}` |
| Focus (Manual) | `/api/v1/cameras/{name}/settings/focus` | `{"mode": "manual", "value": 0.5}` |
| White Balance (Auto) | `/api/v1/cameras/{name}/settings/whiteBalance` | `{"mode": "auto"}` |
| White Balance (Manual) | `/api/v1/cameras/{name}/settings/whiteBalance` | `{"mode": "manual", "temperature": 5600}` |
| ISO | `/api/v1/cameras/{name}/settings/iso` | `{"value": 400}` |
| Shutter | `/api/v1/cameras/{name}/settings/shutter` | `{"value": 0.016}` |
| Iris (Auto) | `/api/v1/cameras/{name}/settings/iris` | `{"mode": "auto"}` |
| Iris (Manual) | `/api/v1/cameras/{name}/settings/iris` | `{"mode": "manual", "value": 2.8}` |
| Gain | `/api/v1/cameras/{name}/settings/gain` | `{"value": 0}` |

#### OBSbot Tail 2

| Control | URL | Body |
|---------|-----|------|
| Focus (Auto) | `/api/v1/cameras/{name}/settings/focus` | `{"mode": "auto"}` |
| Focus (Manual) | `/api/v1/cameras/{name}/settings/focus` | `{"mode": "manual", "value": 0.5}` |
| Exposure (Auto) | `/api/v1/cameras/{name}/settings/exposure` | `{"mode": "auto"}` |
| Exposure (Manual) | `/api/v1/cameras/{name}/settings/exposure` | `{"mode": "manual", "value": 0.5}` |
| White Balance (Auto) | `/api/v1/cameras/{name}/settings/whiteBalance` | `{"mode": "auto"}` |
| PTZ Move | `/api/v1/cameras/{name}/settings/ptz` | `{"pan": 0, "tilt": 0, "zoom": 0}` |
| PTZ Preset | `/api/v1/cameras/{name}/settings/ptz/preset/{id}` | `{}` |

### Button Feedback

To get button feedback (e.g., show if camera is connected), you can:

1. **Add a GET request button** to check camera status:
   - Method: `GET`
   - URL: `/api/v1/cameras/{camera_name}/status`
   - Use Companion's variable parsing to extract `connected` status

2. **Use Companion's WebSocket module** (if available) to connect to:
   - `wss://app.itagenten.no/api/v1/companion/ws`
   - This provides real-time state updates

## Option 2: Custom Companion Module (Advanced)

If you want a dedicated Companion module with better integration, you would need to create a Companion module file. This requires:

1. Creating a module in Companion's module format
2. Publishing it to Companion's module registry (or installing locally)

The WebSocket endpoint at `/api/v1/companion/ws` is ready for this, but a module file would need to be created separately.

### WebSocket Protocol

If creating a custom module, the WebSocket protocol is:

**Connect**: `wss://app.itagenten.no/api/v1/companion/ws?instance_id=<id>`

**Send Button Press**:
```json
{
  "type": "button_press",
  "action": "camera_control",
  "button_id": "cam1_focus",
  "payload": {
    "camera_id": "BMD Cam 1",
    "parameter": "focus",
    "mode": "manual",
    "value": 0.5
  }
}
```

**Receive Feedback**:
```json
{
  "type": "button_feedback",
  "button_id": "cam1_focus",
  "success": true,
  "camera": "BMD Cam 1",
  "parameter": "focus"
}
```

**Request State**:
```json
{
  "type": "get_state"
}
```

## Testing

1. **Test API Endpoint**:
   ```bash
   curl -X PUT https://app.itagenten.no/api/v1/cameras/BMD%20Cam%201/settings/focus \
     -H "Content-Type: application/json" \
     -d '{"mode": "manual", "value": 0.5}'
   ```

2. **Test WebSocket** (if using custom module):
   ```bash
   wscat -c wss://app.itagenten.no/api/v1/companion/ws
   ```

## Troubleshooting

- **Connection Issues**: Verify the base URL is correct and accessible
- **401/403 Errors**: Check if authentication is required (currently not implemented)
- **404 Errors**: Verify camera name matches exactly (case-sensitive)
- **Camera Not Responding**: Check camera is powered on and on the network

## Next Steps

1. Set up HTTP instance in Companion
2. Create buttons for your most-used camera controls
3. Test with physical cameras
4. Optionally create a custom module for better integration
