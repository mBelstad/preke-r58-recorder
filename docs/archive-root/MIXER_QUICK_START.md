# VDO.ninja Mixer Quick Start Guide

**Date**: December 22, 2025

## Prerequisites

You need to be on the **local network** (same network as R58 at 192.168.1.24) to access the VDO.ninja interface.

---

## Step 1: Accept SSL Certificate

⚠️ **IMPORTANT**: The first time you access the VDO.ninja server, you must accept the self-signed SSL certificate.

1. Open your browser (Chrome recommended)
2. Navigate to: `https://192.168.1.24:8443/`
3. Click "Advanced" → "Proceed to 192.168.1.24 (unsafe)"
4. You should see the VDO.ninja main page

---

## Step 2: Test Director View

The Director gives you control over all camera streams.

**URL**: 
```
https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443
```

**What you should see**:
- 3 camera feeds appearing (r58-cam1, r58-cam2, r58-cam3)
- Click on any feed to preview
- Right-click for options (add to scene, solo, etc.)

---

## Step 3: Open Mixer

The Mixer allows you to compose and arrange video feeds.

**URL**:
```
https://192.168.1.24:8443/mixer.html?room=r58studio&wss=192.168.1.24:8443
```

**Features**:
- Drag and drop video sources
- Resize and position feeds
- Create layouts/scenes
- Export scene URL for OBS

---

## Step 4: View Individual Cameras

**Camera 1**:
```
https://192.168.1.24:8443/?view=r58-cam1&room=r58studio&wss=192.168.1.24:8443
```

**Camera 2**:
```
https://192.168.1.24:8443/?view=r58-cam2&room=r58studio&wss=192.168.1.24:8443
```

**Camera 3**:
```
https://192.168.1.24:8443/?view=r58-cam3&room=r58studio&wss=192.168.1.24:8443
```

---

## Step 5: Scene Output (for OBS)

Create a browser source in OBS with:

**URL**:
```
https://192.168.1.24:8443/?scene&room=r58studio&wss=192.168.1.24:8443
```

**Settings**:
- Width: 1920
- Height: 1080
- Custom CSS: Leave blank
- ✅ Control audio via OBS

---

## Troubleshooting

### Cameras not appearing

1. **Check services are running**:
   ```bash
   ssh linaro@r58.itagenten.no
   sudo systemctl status ninja-publish-cam{1,2,3}
   ```

2. **Check signaling server**:
   ```bash
   sudo journalctl -u vdo-ninja -f
   ```
   
   Should show "Publisher joined" messages.

### Certificate error

- Must accept certificate at `https://192.168.1.24:8443/` first
- In Chrome: Settings → Privacy → Manage Certificates → Import

### No video, only black

- Check browser console (F12) for WebRTC errors
- Ensure HDMI cables are connected
- Check camera signal with: `v4l2-ctl -d /dev/video60 --all`

### Connection drops

- VDO.ninja uses peer-to-peer WebRTC
- Ensure no firewall blocking UDP ports
- Try restarting publisher services

---

## URL Parameter Reference

| Parameter | Description | Example |
|-----------|-------------|---------|
| `room=` | Room name to join | `room=r58studio` |
| `wss=` | WebSocket server | `wss=192.168.1.24:8443` |
| `director=` | Director mode | `director=r58studio` |
| `scene` | Scene output mode | `?scene&room=...` |
| `view=` | View specific stream | `view=r58-cam1` |
| `cover` | Video covers container | `&cover` |
| `solo` | Single stream focus | `&solo` |
| `noaudio` | Disable audio | `&noaudio` |
| `autostart` | Auto-play video | `&autostart` |
| `cleanoutput` | Hide UI controls | `&cleanoutput` |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        R58 Device                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  HDMI Inputs              Publishers              Signaling  │
│  ┌─────────┐    ┌─────────────────┐    ┌────────────────┐   │
│  │/dev/60  │───→│ninja-publish-1  │───→│                │   │
│  └─────────┘    └─────────────────┘    │   VDO.ninja    │   │
│  ┌─────────┐    ┌─────────────────┐    │   Signaling    │   │
│  │/dev/11  │───→│ninja-publish-2  │───→│   Port 8443    │   │
│  └─────────┘    └─────────────────┘    │                │   │
│  ┌─────────┐    ┌─────────────────┐    │   Room:        │   │
│  │/dev/21  │───→│ninja-publish-3  │───→│   r58studio    │   │
│  └─────────┘    └─────────────────┘    └───────┬────────┘   │
│                                                 │            │
└─────────────────────────────────────────────────┼────────────┘
                                                  │
                              WebRTC Peer-to-Peer │
                                                  ▼
                               ┌────────────────────────┐
                               │   Browser Clients      │
                               │                        │
                               │   • Director View      │
                               │   • Mixer View         │
                               │   • Scene Output       │
                               │   • Camera View        │
                               └────────────────────────┘
```

---

## Services Reference

| Service | Command | Description |
|---------|---------|-------------|
| VDO.ninja | `systemctl status vdo-ninja` | Signaling server |
| Cam 1 | `systemctl status ninja-publish-cam1` | HDMI 1 publisher |
| Cam 2 | `systemctl status ninja-publish-cam2` | HDMI 2 publisher |
| Cam 3 | `systemctl status ninja-publish-cam3` | HDMI 3 publisher |
| MediaMTX | `systemctl status mediamtx` | HLS/RTSP server |
| Recorder | `systemctl status preke-recorder` | Main app |

---

## Need Help?

- Check logs: `journalctl -u SERVICE_NAME -f`
- Restart all: `sudo systemctl restart vdo-ninja ninja-publish-cam{1,2,3}`
- See detailed plan: `R58_VDO_NINJA_MIXER_PLAN.md`


