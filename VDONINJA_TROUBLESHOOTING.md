# VDO.ninja Troubleshooting - Cameras Not Visible

**Issue**: Director view loads but cameras don't appear  
**Status**: Publishers connecting but not staying visible

---

## Current Status

### ✅ What's Working
- VDO.ninja server running (port 8443)
- Publishers connecting to WebSocket
- Director interface loads
- No console errors

### ⚠️ What's Not Working
- Cameras not visible in director view
- Publishers connect then receive interrupt signal
- WebRTC peer connections not establishing

---

## Observed Behavior

Publisher logs show this pattern:
```
✅ Connected successfully!
=> joining room (hashed)
✅ WebSocket ready
🛑 Received interrupt signal, shutting down gracefully...
```

The publishers connect and join the room, but then immediately shut down.

---

## Possible Causes

### 1. Publishers Waiting for Peer Connection
- Publishers may be timing out waiting for a peer (director)
- Director may not be sending connection requests

### 2. Room Name Mismatch
- Publishers use room: `r58studio`
- Director must use exact same room name

### 3. WebSocket Server Issue
- Local VDO.ninja server may not be relaying messages correctly
- Check server logs for errors

### 4. Camera Signal Issue
- Camera has signal (640x480 detected)
- But may not be streaming correctly

---

## Troubleshooting Steps

### Step 1: Test Individual Camera View

On the Windows PC, try viewing a single camera:
```
https://192.168.1.24:8443/?view=r58-cam1&room=r58studio
```

This bypasses the director and connects directly to the camera stream.

### Step 2: Check VDO.ninja Server Logs

```bash
./connect-r58.sh "sudo journalctl -u vdo-ninja -f"
```

Look for:
- Connection messages
- Room join messages
- Any errors

### Step 3: Try Public VDO.ninja

To isolate if it's a local server issue, temporarily test with public VDO.ninja:

```bash
# Reconfigure to use public server
./connect-r58.sh "sudo systemctl stop ninja-publish-cam1"
./connect-r58.sh "sudo -u linaro /opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py --server wss://wss.vdo.ninja:443 --room r58studio-test --streamid r58-cam1 --v4l2 /dev/video60 --h264 --bitrate 4000 --width 1920 --height 1080 --framerate 30 --noaudio &"
```

Then open:
```
https://vdo.ninja/?director=r58studio-test&wss=wss.vdo.ninja:443
```

### Step 4: Check Camera Signal

```bash
./connect-r58.sh "v4l2-ctl --device=/dev/video60 --get-fmt-video"
```

Verify camera has active signal.

### Step 5: Test Without TURN

Try without TURN parameters to see if TURN is causing issues:

```bash
# Remove TURN temporarily
./connect-r58.sh "sudo sed -i 's/--turn-server.*--stun-server.*--v4l2/--v4l2/' /etc/systemd/system/ninja-publish-cam1.service"
./connect-r58.sh "sudo systemctl daemon-reload && sudo systemctl restart ninja-publish-cam1"
```

---

## Quick Test Commands

### Restart All Publishers
```bash
./connect-r58.sh "sudo systemctl restart ninja-publish-cam{1..3}"
```

### Check All Publisher Status
```bash
./connect-r58.sh "sudo systemctl status ninja-publish-cam* --no-pager"
```

### View Live Logs
```bash
./connect-r58.sh "sudo journalctl -u ninja-publish-cam1 -f"
```

---

## Alternative: Use MediaMTX Instead

The R58 already has MediaMTX working perfectly with HLS. You could:

1. Use the existing R58 recorder interface: `https://recorder.itagenten.no`
2. View cameras via HLS (1-3 second latency)
3. Mix using the built-in switcher

This is proven to work and doesn't require VDO.ninja troubleshooting.

---

## Next Steps

1. Try viewing individual camera: `https://192.168.1.24:8443/?view=r58-cam1&room=r58studio`
2. Check if camera appears
3. If yes: Issue is with director view
4. If no: Issue is with publisher/server connection

Let me know what you see!

