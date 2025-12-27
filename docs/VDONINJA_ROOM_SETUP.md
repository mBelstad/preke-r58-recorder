# VDO.ninja Room Setup Guide

## Current Status (Dec 27, 2025) - FULLY WORKING! 🎉

### What Works ✅

1. **HDMI Camera in VDO.ninja Room**: Successfully tested and working!
   - HDMI camera (cam2) streams to MediaMTX via WHEP
   - Screen share from R58 pushes the WHEP viewer tab to VDO.ninja room
   - Video appears in Director with full controls (mute, highlight, add to scene, etc.)

2. **WHEP Viewing**: HDMI cameras can be viewed via VDO.ninja using WHEP:
   ```
   https://r58-vdo.itagenten.no/?whepplay=https://r58-api.itagenten.no/whep/cam2
   ```
   - Video is live and streaming (confirmed: studio setup with microphone, headphones, teleprompter)
   - Works remotely through FRP tunnel

2. **MediaMTX Streaming**: cam2 is streaming to MediaMTX
   - Path: `/cam2`
   - WHEP endpoint: `https://r58-api.itagenten.no/whep/cam2`
   - HLS endpoint: `https://r58-api.itagenten.no/cam2/`

3. **VDO.ninja Director/Mixer**: Accessible at:
   - Director: `https://r58-vdo.itagenten.no/?director=ROOMNAME`
   - Scene: `https://r58-vdo.itagenten.no/?scene&room=ROOMNAME`

### Limitations

1. **Combining `&whepplay=` with `&room=` or `&push=`**: VDO.ninja ignores WHEP when joining rooms
2. **`&mediamtx=` parameter**: Routes P2P traffic through MediaMTX, but doesn't PULL streams from MediaMTX into rooms

## Automated Setup (Tested Working!)

The screen share can be automated using `xdotool` on R58. The process:

1. Open WHEP viewer tab → plays the HDMI camera
2. Open Director tab → claims the room
3. Open screen share page → triggers getDisplayMedia
4. xdotool/Puppeteer clicks through the native picker dialog

```bash
# Install xdotool if not present
sudo apt-get install -y xdotool

# The automation is handled by Puppeteer scripts in /opt/preke-r58-recorder
```

## Manual Screen Share Setup (Alternative)

### Step 1: Open WHEP Viewer on R58

On the R58 device (physically or via VNC), open Chromium and navigate to:
```
https://r58-vdo.itagenten.no/?whepplay=https://r58-api.itagenten.no/whep/cam2
```

This will display the HDMI camera feed in full screen.

### Step 2: Open VDO.ninja Guest Page

Open a new tab and navigate to:
```
https://r58-vdo.itagenten.no/?push=hdmicam2&room=YOUR_ROOM&screenshare&label=HDMI-Cam2
```

### Step 3: Select "Screenshare with Room"

Click the "Screenshare with Room" button.

### Step 4: Select the WHEP Tab

In the screen picker dialog:
1. Click "Chrome Tab" tab
2. Select the tab showing the WHEP video
3. Check "Share tab audio" if needed
4. Click "Share"

### Step 5: Verify in Director

Open the Director URL on your remote machine:
```
https://r58-vdo.itagenten.no/?director=YOUR_ROOM
```

You should see the HDMI camera as a guest in the room.

## Alternative: v4l2loopback Virtual Webcam

For a more automated solution, you can create a virtual webcam from the WHEP stream:

```bash
# Install v4l2loopback on R58
sudo apt install v4l2loopback-dkms

# Create virtual webcam
sudo modprobe v4l2loopback devices=1 video_nr=99 card_label="VDO-Camera" exclusive_caps=1

# Use ffmpeg to pipe WHEP stream to virtual webcam
# (Requires custom WHEP client implementation)
```

Then use `&vd=VDO-Camera` in VDO.ninja to select the virtual webcam.

## Quick Reference URLs

| Purpose | URL |
|---------|-----|
| View cam2 (WHEP) | `https://r58-vdo.itagenten.no/?whepplay=https://r58-api.itagenten.no/whep/cam2` |
| Director | `https://r58-vdo.itagenten.no/?director=r58studio` |
| Scene | `https://r58-vdo.itagenten.no/?scene&room=r58studio` |
| Guest Join | `https://r58-vdo.itagenten.no/?room=r58studio` |
| Screen Share Guest | `https://r58-vdo.itagenten.no/?push=hdmicam&room=r58studio&screenshare&label=HDMI-Camera` |

## Notes

- Only **cam2** (`/dev/video11`, HDMI N11) is currently working
- cam0 and cam3 are disabled in config
- cam1 (`/dev/video60`, hdmirx) has no HDMI signal connected
- The R58 Chromium browser has remote debugging enabled on port 9222

