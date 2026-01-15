# R58 Recorder API Documentation

Base URL: `https://app.itagenten.no/api/`

## Overview

The R58 API provides comprehensive control over multi-camera recording, mixing, streaming, and WordPress booking integration. All endpoints return JSON responses.

## Authentication

Most endpoints do not require authentication. WordPress integration endpoints use WordPress Application Passwords configured in `config.yml`.

## Core Endpoints

### Health & Capabilities

#### `GET /health`
Health check endpoint - always responds even if GStreamer fails.

**Response:**
```json
{
  "status": "healthy",
  "platform": "r58",
  "gstreamer": "initialized"
}
```

#### `GET /api/v1/capabilities`
Get device capabilities manifest for adaptive UI.

**Response:**
```json
{
  "device_id": "r58-device",
  "device_name": "R58 Recorder",
  "platform": "r58",
  "api_version": "2.0.0",
  "mixer_available": true,
  "recorder_available": true,
  "inputs": [...],
  "storage_total_gb": 953.87,
  "storage_available_gb": 847.23,
  "storage_path": "/data"
}
```

## WordPress Integration

### Status

#### `GET /api/v1/wordpress/status`
Check WordPress connection status.

**Response:**
```json
{
  "enabled": true,
  "connected": true,
  "wordpress_url": "https://preke.no",
  "last_sync": "2026-01-15T22:00:00"
}
```

### Appointments/Bookings

#### `GET /api/v1/wordpress/appointments`
List appointments from JetAppointments.

**Query Parameters:**
- `date_from` (optional): YYYY-MM-DD
- `date_to` (optional): YYYY-MM-DD

**Response:**
```json
{
  "bookings": [
    {
      "id": 123,
      "status": "pending",
      "date": "2026-01-15",
      "slot_start": "10:00",
      "slot_end": "11:30",
      "customer": {
        "name": "John Doe",
        "email": "john@example.com"
      },
      "client": {
        "id": 5,
        "name": "Acme Corp",
        "slug": "acme-corp"
      }
    }
  ],
  "total": 1
}
```

#### `GET /api/v1/wordpress/appointments/today`
Get today's appointments.

#### `GET /api/v1/wordpress/appointments/{id}`
Get specific appointment details.

#### `POST /api/v1/wordpress/appointments/{id}/activate`
Activate a booking session.

**Response:**
```json
{
  "success": true,
  "booking": {...},
  "recording_path": "/data/recordings/clients/acme-corp/default/123",
  "access_token": "abc123...",
  "message": "Booking activated"
}
```

#### `GET /api/v1/wordpress/booking/current`
Get currently active booking.

### Clients & Projects

#### `GET /api/v1/wordpress/clients`
List all WordPress clients.

**Response:**
```json
{
  "clients": [
    {
      "id": 5,
      "slug": "acme-corp",
      "name": "Acme Corp"
    }
  ],
  "total": 1
}
```

#### `GET /api/v1/wordpress/clients/{id}/projects`
List projects for a specific client.

#### `POST /api/v1/wordpress/projects`
Create a new video project.

**Request:**
```json
{
  "client_id": 5,
  "name": "Q1 Marketing Campaign",
  "type": "podcast"
}
```

### Calendar (Kiosk)

#### `GET /api/v1/wordpress/calendar/today`
Get today's calendar with time slots (9 AM - 5 PM, 30-min intervals).

**Response:**
```json
{
  "date": "2026-01-15",
  "slots": [
    {
      "start_time": "09:00",
      "end_time": "09:30",
      "available": true,
      "booking": null,
      "is_lunch": false
    },
    {
      "start_time": "10:00",
      "end_time": "11:30",
      "available": false,
      "booking": {...},
      "is_lunch": false
    }
  ]
}
```

#### `POST /api/v1/wordpress/calendar/book`
Create a walk-in booking.

**Request:**
```json
{
  "slot_start": "14:00",
  "slot_end": "15:00",
  "customer_name": "Jane Smith",
  "customer_email": "jane@example.com",
  "customer_phone": "+47 123 45 678",
  "recording_type": "podcast"
}
```

### Customer Portal

#### `GET /api/v1/wordpress/customer/{token}/status`
Get customer portal status (requires access token from booking activation).

**Response:**
```json
{
  "booking": {...},
  "project": {...},
  "recording_active": false,
  "display_mode": "podcast"
}
```

#### `POST /api/v1/wordpress/customer/{token}/recording/start`
Start recording from customer portal.

#### `POST /api/v1/wordpress/customer/{token}/recording/stop`
Stop recording from customer portal.

#### `GET /api/v1/wordpress/customer/{token}/display-mode`
Get display mode for studio display.

## Camera Control

### PTZ Control

#### `GET /api/v1/ptz-controller/cameras`
List cameras that support PTZ control.

#### `PUT /api/v1/ptz-controller/{camera_name}/ptz`
Execute PTZ command.

**Request:**
```json
{
  "pan": 0.5,
  "tilt": -0.3,
  "zoom": 0.2
}
```

#### `WebSocket /api/v1/ptz-controller/ws`
Real-time PTZ control for hardware controllers.

### Camera Settings

#### `GET /api/v1/cameras/`
List available cameras.

#### `GET /api/v1/cameras/{name}/status`
Get camera status.

#### `GET /api/v1/cameras/{name}/settings`
Get camera settings.

#### `PUT /api/v1/cameras/{name}/settings/focus`
Set camera focus.

#### `PUT /api/v1/cameras/{name}/settings/exposure`
Set camera exposure.

## Streaming

### RTMP Streaming

#### `GET /api/streaming/status`
Get current streaming status.

#### `POST /api/streaming/rtmp/start`
Start RTMP relay to external platforms.

**Request:**
```json
{
  "destinations": [
    {
      "platform": "youtube",
      "rtmp_url": "rtmp://a.rtmp.youtube.com/live2/",
      "stream_key": "xxxx-xxxx-xxxx-xxxx",
      "enabled": true
    }
  ]
}
```

#### `POST /api/streaming/rtmp/stop`
Stop RTMP relay.

### HLS/WHEP Proxy

#### `GET /hls/{stream_path}`
Proxy HLS streams from MediaMTX.

#### `POST /whep/{stream_path}`
Proxy WHEP requests for WebRTC viewing.

## Recording

### Sessions

#### `GET /api/sessions`
List recording sessions.

#### `GET /api/sessions/{session_id}`
Get session details.

#### `DELETE /api/sessions/{session_id}`
Delete a recording session.

### Trigger Control

#### `POST /api/trigger/start`
Start recording on all active inputs.

**Request:**
```json
{
  "name": "Session 2026-01-15"
}
```

#### `POST /api/trigger/stop`
Stop all recordings.

#### `GET /api/trigger/status`
Get recording status.

## Device Mode

#### `GET /api/mode/status`
Get current device mode.

#### `POST /api/mode/recorder`
Switch to recorder mode.

#### `POST /api/mode/mixer`
Switch to mixer mode.

#### `POST /api/mode/vdoninja`
Switch to VDO.ninja mode.

## LAN Discovery

#### `GET /api/v1/lan-devices`
List discovered R58 devices on local network.

#### `POST /api/v1/lan-devices/scan`
Scan local network for R58 devices.

#### `GET /api/v1/lan-devices/{device_id}`
Get information about a specific device.

## VDO.ninja Integration

#### `POST /api/v1/vdo-ninja/scene/{scene_id}`
Switch to VDO.ninja scene.

#### `POST /api/v1/vdo-ninja/guest/{guest_id}/mute`
Toggle guest microphone mute.

#### `POST /api/v1/vdo-ninja/guest/{guest_id}/volume`
Set guest volume.

#### `GET /api/v1/vdo-ninja/guests`
List connected guests.

## System

#### `GET /api/system/info`
Get system information (CPU, memory, temperature, uptime).

#### `GET /api/system/logs`
Get recent system logs.

#### `POST /api/system/restart-service/{service}`
Restart a system service.

#### `POST /api/system/reboot`
Reboot the device.

## WebSocket

#### `WebSocket /ws`
Real-time status updates for recording, inputs, and system events.

**Message Format:**
```json
{
  "type": "recording_status",
  "data": {
    "status": "recording",
    "duration_ms": 12345,
    "session_id": "abc123"
  }
}
```

## Configuration

### WordPress Setup

Add to `config.yml`:

```yaml
wordpress:
  enabled: true
  url: "https://preke.no"
  username: "heimarius"
  app_password: "xxxx xxxx xxxx xxxx"
```

Generate Application Password in WordPress:
1. Go to Users → Profile
2. Scroll to "Application Passwords"
3. Enter name (e.g., "R58 Device")
4. Click "Add New Application Password"
5. Copy the generated password

### Device URL Configuration

The frontend automatically detects the device URL:
- **Electron App**: Configure in device settings
- **Web Browser**: Uses current hostname (e.g., app.itagenten.no)
- **FRP Fallback**: Configured per device for remote access

## Error Handling

All endpoints return standard HTTP status codes:
- `200` - Success
- `400` - Bad request
- `403` - Forbidden (invalid token)
- `404` - Not found
- `500` - Internal server error
- `503` - Service unavailable (feature not configured)

Error responses include a `detail` field with the error message.
