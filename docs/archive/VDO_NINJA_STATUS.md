# VDO.ninja Integration Status

**Date:** December 22, 2025  
**Status:** ✅ Publishers Running - Ready for Testing

---

## Current System State

### ✅ Running Services

- **VDO.ninja Signaling Server**: `wss://192.168.1.24:8443`
- **Publisher 1** (CAM1): `/dev/video60` → Stream ID: `r58-cam1`
- **Publisher 2** (CAM2): `/dev/video11` → Stream ID: `r58-cam2`
- **Publisher 3** (CAM3): `/dev/video22` → Stream ID: `r58-cam3`

### 🔧 Configuration

- **Room**: `r58studio`
- **Encoding**: H.264 @ 8Mbps
- **Resolution**: 1920x1080 @ 30fps
- **TURN Server**: Cloudflare (for NAT traversal)
- **STUN Server**: Cloudflare

### ⚠️ Important Changes

- **preke-recorder service**: Currently **STOPPED** to free video devices for VDO.ninja publishers
- **Architecture**: Using `raspberry.ninja` publishers instead of MediaMTX

---

## Testing Instructions

### Simple Test Page (Recommended First)

1. **Open the test page**:
   ```
   https://192.168.1.24:8443/static/test_vdo_simple.html
   ```

2. **Accept the self-signed certificate** (if prompted again)

3. **Click each camera link** to test individual streams:
   - Camera 1: `https://192.168.1.24:8443/?view=r58-cam1&room=r58studio&wss=192.168.1.24:8443`
   - Camera 2: `https://192.168.1.24:8443/?view=r58-cam2&room=r58studio&wss=192.168.1.24:8443`
   - Camera 3: `https://192.168.1.24:8443/?view=r58-cam3&room=r58studio&wss=192.168.1.24:8443`

4. **Check the browser console** (F12) for any errors

### Director View

- **URL**: `https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443`
- **Purpose**: Control panel showing all cameras in the room
- **Expected**: Should show 3 camera tiles (r58-cam1, r58-cam2, r58-cam3)

### Mixer View (Goal)

- **URL**: `https://192.168.1.24:8443/mixer?push=MIXOUT&room=r58studio&wss=192.168.1.24:8443`
- **Purpose**: Mix multiple camera sources with transitions and effects
- **Expected**: Can add camera sources and create a mixed output

---

## Known Issues & Observations

### Issue: Publishers Receive Interrupt Signals

**Symptoms:**
- Publishers connect successfully
- They send "seed" messages to the signaling server
- Immediately receive interrupt signal and shut down
- Systemd restarts them (Restart=on-failure)
- Cycle repeats

**Possible Causes:**
1. **Multiple viewer connections**: Each time a viewer (director page) connects, it triggers the publisher to create a new pipeline. Multiple tabs or rapid reconnections could overwhelm the publisher.
2. **WebRTC negotiation timeout**: The publisher might be timing out waiting for ICE negotiation to complete.
3. **Resource constraints**: Creating multiple GStreamer pipelines might exceed available memory or CPU.

**Current Status:**
- Publishers are in a restart loop but staying "active"
- They ARE visible to the signaling server (sending seeds)
- Need to verify if viewers can actually connect and receive video

### Console Log Analysis

Your console showed:
```
📨 Request: seed (multiple times)
🛑 Received interrupt signal, shutting down gracefully...
🛑 Stopping pipeline for viewer (3 times)
```

This suggests the publishers tried to create 3 viewer pipelines (one for each "seed" request from the director), then crashed.

---

## Troubleshooting

### Check Publisher Logs

```bash
# SSH to R58
ssh linaro@r58.itagenten.no
# Password: linaro

# Check individual publisher logs
sudo journalctl -u ninja-publish-cam1 -f
sudo journalctl -u ninja-publish-cam2 -f
sudo journalctl -u ninja-publish-cam3 -f

# Check signaling server logs
sudo journalctl -u vdo-ninja -f
```

### Check Video Device Usage

```bash
# Should show python3 processes using /dev/video60, /dev/video11, /dev/video22
sudo lsof /dev/video* 2>/dev/null | grep python3
```

### Restart Services

```bash
# Restart all publishers
sudo systemctl restart ninja-publish-cam{1,2,3}

# Restart signaling server
sudo systemctl restart vdo-ninja
```

---

## Next Steps

1. **Test individual camera views** using the simple test page
2. **Report what you see** in the browser:
   - Do camera videos load?
   - Any errors in console?
   - Does the video play or freeze?

3. **If viewers connect successfully**, the interrupt issue might resolve itself (it could be transient during startup)

4. **If viewers fail to connect**, we need to investigate:
   - WebRTC ICE negotiation logs
   - TURN server connectivity
   - Certificate trust issues

---

## Architecture Decision Point

We currently have two architectures available:

### Option A: VDO.ninja (Current)
- ✅ Native VDO.ninja integration
- ✅ Works with `mixer.html` 
- ✅ Room-based collaboration
- ❌ Publishers seem unstable (interrupt loop)
- ❌ Conflicts with preke-recorder

### Option B: MediaMTX + preke-recorder
- ✅ Stable RTSP/HLS/WHEP streaming
- ✅ Works with preke-recorder ecosystem
- ✅ No interrupt issues
- ❌ Requires custom integration with VDO.ninja
- ❌ `mixer.html` needs adaptation

**Recommendation**: Let's test Option A thoroughly first. If the interrupt issue prevents viewers from connecting, we'll pivot to Option B with a custom WHEP-to-VDO.ninja bridge.

---

## Quick Reference

| Service | Status | Command |
|---------|--------|---------|
| VDO.ninja Server | Active | `systemctl status vdo-ninja` |
| Publisher CAM1 | Active | `systemctl status ninja-publish-cam1` |
| Publisher CAM2 | Active | `systemctl status ninja-publish-cam2` |
| Publisher CAM3 | Active | `systemctl status ninja-publish-cam3` |
| preke-recorder | **Stopped** | `systemctl status preke-recorder` |

**Test URLs:**
- Simple Test: `https://192.168.1.24:8443/static/test_vdo_simple.html`
- Director: `https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443`
- Mixer: `https://192.168.1.24:8443/mixer?push=MIXOUT&room=r58studio&wss=192.168.1.24:8443`

