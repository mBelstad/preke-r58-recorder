# VDO.ninja Room Setup Guide

## Current Status (Dec 27, 2025) - SIMPLIFIED! 🎉

### The `&whepshare` Solution

**We discovered a much simpler approach!** VDO.ninja's `&whepshare` parameter allows sharing WHEP streams directly to rooms without screen sharing or complex automation.

### What Works ✅

1. **`&whepshare` Parameter** (NEW - Recommended!)
   - Share any WHEP stream to a VDO.ninja room with a single URL
   - No screen sharing, no Puppeteer, no xdotool needed
   - Works from any browser (on R58 or remotely)

2. **WHEP Viewing**: Direct HDMI camera viewing via WHEP:
   ```
   https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/whep/cam2
   ```

3. **MediaMTX Streaming**: Active cameras stream via WHEP/HLS

4. **VDO.ninja Integration**: Full director/mixer functionality

## Quick Start with `&whepshare`

### Option 1: Use the Web Manager (Easiest)

Open the camera manager page:
```
https://app.itagenten.no/static/vdoninja-manager.html
```

This provides:
- One-click buttons to add cameras to rooms
- Director and Scene URLs
- Camera status monitoring

### Option 2: Direct URL

To add cam2 to room "r58studio":
```
https://r58-vdo.itagenten.no/?push=hdmi1&room=r58studio&whepshare=https%3A%2F%2Fapp.itagenten.no%2Fwhep%2Fcam2&label=HDMI-Camera&webcam
```

Then:
1. Click "Join Room with Camera"
2. Click "START"
3. The WHEP stream is now shared to the room!

### Option 3: API Endpoint

Get ready-to-use URLs via API:
```bash
# Get all URLs for a room
curl https://app.itagenten.no/api/vdoninja/room-urls?room=r58studio

# Get URL for a specific camera
curl https://app.itagenten.no/api/vdoninja/whepshare-url/cam2?room=r58studio&label=Camera-1
```

## Auto-Start Service

The R58 can automatically set up the VDO.ninja room on boot.

### Configuration

Edit `/etc/systemd/system/vdoninja-bridge.service`:
```ini
# Camera configuration - comma-separated
# Format: stream_id:push_id:label
Environment=CAMERAS=cam2:hdmi1:HDMI-Camera

# For multiple cameras:
# Environment=CAMERAS=cam2:hdmi1:Camera-1,cam3:hdmi2:Camera-2

Environment=VDONINJA_ROOM=r58studio
```

### Service Commands

```bash
# Start the bridge
sudo systemctl start vdoninja-bridge

# Enable auto-start on boot
sudo systemctl enable vdoninja-bridge

# View logs
journalctl -u vdoninja-bridge -f
tail -f /var/log/vdoninja-bridge.log
```

## URL Reference

| Purpose | URL |
|---------|-----|
| **Camera Manager** | `https://app.itagenten.no/static/vdoninja-manager.html` |
| Director | `https://r58-vdo.itagenten.no/?director=r58studio` |
| Scene (OBS) | `https://r58-vdo.itagenten.no/?scene&room=r58studio` |
| Guest Invite | `https://r58-vdo.itagenten.no/?room=r58studio` |
| View cam2 (WHEP) | `https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/whep/cam2` |

## How `&whepshare` Works

The `&whepshare` parameter tells VDO.ninja:
> "Instead of streaming my camera, tell viewers to fetch video from this WHEP URL"

This means:
- The browser joining the room doesn't need to encode/stream video
- Viewers connect directly to the WHEP source (MediaMTX)
- Lower CPU usage on the joining device
- No need for screen sharing or virtual webcams

### Technical Flow

```
[HDMI Camera] → [MediaMTX on R58] ← WHEP ← [VDO.ninja Viewers]
                     ↑
              Browser joins with &whepshare
              (just signals, doesn't stream)
```

## Comparison: Old vs New Approach

| Aspect | Screen Share (Old) | &whepshare (New) |
|--------|-------------------|------------------|
| Complexity | High (Puppeteer, xdotool) | Low (just URL) |
| CPU Usage | High (screen capture) | Low (signaling only) |
| Automation | Complex | Simple |
| Browser Required | On R58 only | Anywhere |
| Multiple Cameras | Complex | Easy (multiple URLs) |

## Notes

- Only **cam2** (`/dev/video11`, HDMI N11) is currently active
- cam0 and cam3 are disabled in config
- cam1 (`/dev/video60`, hdmirx) has no HDMI signal
- WHEP URL must be URL-encoded in the `&whepshare` parameter

## Legacy: Screen Share Method

The original screen share approach is still available in the startup script but is no longer recommended. It:
1. Opens WHEP viewer in a tab
2. Opens screen share page
3. Uses Chrome's `--auto-select-tab-capture-source-by-title` flag to auto-select

This method still works but is more complex than `&whepshare`.
