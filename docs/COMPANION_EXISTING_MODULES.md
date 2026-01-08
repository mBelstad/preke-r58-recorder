# Using Existing Companion Modules with R58 Camera Control

## Overview

This guide explains how to use existing Bitfocus Companion modules with your R58 camera control system. We'll bridge existing modules to work with our centralized API.

## Available Modules

### 1. Sony VISCA Module (for OBSbot Tail 2)

**Module**: `companion-module-sony-visca`  
**Compatibility**: OBSbot Tail 2 uses VISCA over IP (UDP port 52381)

**Direct Connection Option:**
- OBSbot cameras can be controlled directly using the Sony VISCA module
- The module sends VISCA commands over UDP to the camera's IP
- This bypasses the R58 API but works immediately

**Setup:**
1. Install `companion-module-sony-visca` in Companion
2. Configure with OBSbot camera IP and port 52381
3. Use standard VISCA controls (PTZ, focus, etc.)

**R58 API Bridge Option:**
- Use our bridge service (see below) to route VISCA commands through R58 API
- Maintains centralized control and logging

### 2. Middle Control Module (for Blackmagic Cameras)

**Module**: `companion-module-middlethings-middlecontrol`  
**Compatibility**: Works with Blackmagic cameras through Middle Control Software

**Limitation**: Requires Middle Control Software to be running, which may not be ideal for our use case.

**Alternative**: Use Companion's HTTP module to call our R58 API directly (recommended).

## Recommended Approach: Bridge Service

We'll create a bridge service that:
1. Accepts commands from existing Companion modules
2. Translates them to our R58 API format
3. Maintains centralized control and logging

### Bridge Architecture

```
Companion Module → Bridge Service → R58 API → Camera
```

## Implementation Options

### Option A: Direct Module Connection (Simplest)

**For OBSbot Tail 2:**
- Use Sony VISCA module directly
- Configure camera IP:port in Companion
- Works immediately, no bridge needed

**For Blackmagic:**
- Use Companion HTTP module
- Point to R58 API endpoints
- Full control through our API

### Option B: Bridge Service (Centralized)

Create a bridge service that:
- Listens for Companion module commands
- Translates to R58 API calls
- Provides unified control interface

## Setup Instructions

### OBSbot Tail 2 with Sony VISCA Module

1. **Install Module in Companion:**
   ```
   Add Instance → Search "Sony VISCA" → Install
   ```

2. **Configure:**
   - **Host**: OBSbot camera IP (e.g., `192.168.1.110`)
   - **Port**: `52381` (VISCA UDP port)
   - **Protocol**: UDP

3. **Available Controls:**
   - Pan/Tilt/Zoom
   - Focus (if supported)
   - Presets
   - Auto Focus

4. **Note**: This connects directly to the camera, bypassing R58 API. For centralized control, use Option B.

### Blackmagic Design with HTTP Module

1. **Install HTTP Module in Companion:**
   ```
   Add Instance → Search "HTTP" → Install
   ```

2. **Configure:**
   - **Base URL**: `https://app.itagenten.no` (or `http://<r58-ip>:8000`)
   - **Default Method**: `PUT`
   - **Headers**: `Content-Type: application/json`

3. **Create Buttons:**
   - Focus: `/api/v1/cameras/{camera_name}/settings/focus`
   - ISO: `/api/v1/cameras/{camera_name}/settings/iso`
   - White Balance: `/api/v1/cameras/{camera_name}/settings/whiteBalance`
   - etc.

## Bridge Service Implementation

If you want centralized control with existing modules, we can create a bridge service. This would:

1. **Listen for VISCA commands** (from Sony VISCA module)
2. **Translate to R58 API calls**
3. **Route through our camera control system**

### Bridge Service Structure

```python
# Bridge service that translates Companion module commands to R58 API
class CompanionBridge:
    - Accept VISCA commands (UDP)
    - Translate to R58 API format
    - Call R58 API endpoints
    - Return responses
```

## Comparison

| Approach | Pros | Cons |
|----------|------|------|
| **Direct VISCA (OBSbot)** | Simple, works immediately | Bypasses R58 API, no centralized logging |
| **HTTP Module (BMD)** | Full API control, centralized | Requires manual button setup |
| **Bridge Service** | Best of both worlds | Requires additional service |

## Recommendation

**For OBSbot Tail 2:**
- Use Sony VISCA module directly for immediate PTZ control
- Use R58 API for advanced features (exposure, white balance via HTTP)

**For Blackmagic Design:**
- Use Companion HTTP module with R58 API endpoints
- Full control through centralized API

**For Unified Control:**
- Implement bridge service (see next section)

## Next Steps

1. Test Sony VISCA module with OBSbot camera
2. Set up HTTP module for Blackmagic cameras
3. Optionally implement bridge service for unified control
