# Companion Integration Summary

## Quick Decision Guide

### For OBSbot Tail 2

**Option 1: Direct VISCA Module (Recommended for PTZ)**
- ✅ Use `companion-module-sony-visca` 
- ✅ Connect directly to camera IP (192.168.1.110:52381)
- ✅ Works immediately, no setup needed
- ❌ Bypasses R58 API (no centralized logging)
- ✅ Best for: Quick PTZ control setup

**Option 2: HTTP Module with R58 API (Recommended for Full Control)**
- ✅ Use Companion's built-in HTTP module
- ✅ Connect to R58 API endpoints
- ✅ Full centralized control and logging
- ✅ Access to all camera features (exposure, WB, etc.)
- ✅ Best for: Production use with full feature set

**Option 3: Bridge Service (Advanced)**
- ✅ Use VISCA module → Bridge → R58 API
- ✅ Best of both worlds
- ❌ Requires additional service setup
- ✅ Best for: When you need VISCA module UI but want centralized control

### For Blackmagic Design Studio Camera 4K Pro

**Option 1: HTTP Module with R58 API (Recommended)**
- ✅ Use Companion's built-in HTTP module
- ✅ Connect to R58 API endpoints
- ✅ Full control (focus, iris, ISO, shutter, gain, color correction)
- ✅ Centralized logging and monitoring
- ✅ Best for: All use cases

**Option 2: Middle Control Module (Not Recommended)**
- ❌ Requires Middle Control Software
- ❌ Additional software dependency
- ❌ More complex setup
- ⚠️ Only use if you already have Middle Control

## Recommended Setup

### Quick Start (OBSbot PTZ Only)

1. Install `companion-module-sony-visca` in Companion
2. Configure:
   - Host: `192.168.1.110` (OBSbot camera IP)
   - Port: `52381`
3. Done! PTZ controls work immediately

### Production Setup (Full Control)

1. **For OBSbot:**
   - Install HTTP module in Companion
   - Base URL: `https://app.itagenten.no`
   - Create buttons for:
     - PTZ: `PUT /api/v1/cameras/OBSbot PTZ/settings/ptz`
     - Focus: `PUT /api/v1/cameras/OBSbot PTZ/settings/focus`
     - Exposure: `PUT /api/v1/cameras/OBSbot PTZ/settings/exposure`
     - White Balance: `PUT /api/v1/cameras/OBSbot PTZ/settings/whiteBalance`

2. **For Blackmagic:**
   - Install HTTP module in Companion
   - Base URL: `https://app.itagenten.no`
   - Create buttons for:
     - Focus: `PUT /api/v1/cameras/BMD Cam 1/settings/focus`
     - ISO: `PUT /api/v1/cameras/BMD Cam 1/settings/iso`
     - Shutter: `PUT /api/v1/cameras/BMD Cam 1/settings/shutter`
     - Iris: `PUT /api/v1/cameras/BMD Cam 1/settings/iris`
     - Gain: `PUT /api/v1/cameras/BMD Cam 1/settings/gain`
     - White Balance: `PUT /api/v1/cameras/BMD Cam 1/settings/whiteBalance`

## Files Created

1. **`docs/COMPANION_EXISTING_MODULES.md`** - Guide for using existing modules
2. **`docs/COMPANION_BRIDGE_SETUP.md`** - Advanced bridge service setup
3. **`docs/COMPANION_SETUP.md`** - General HTTP module setup guide
4. **`src/camera_control/companion_bridge.py`** - Bridge service (optional)

## Next Steps

1. **Choose your approach** based on needs:
   - Quick PTZ? → Direct VISCA module
   - Full control? → HTTP module with R58 API
   - Advanced? → Bridge service

2. **Test with your cameras** to verify functionality

3. **Create button layouts** in Companion for your workflow

## Support

- API endpoints: See `docs/CAMERA_CONTROLS.md`
- HTTP module setup: See `docs/COMPANION_SETUP.md`
- Bridge service: See `docs/COMPANION_BRIDGE_SETUP.md`
