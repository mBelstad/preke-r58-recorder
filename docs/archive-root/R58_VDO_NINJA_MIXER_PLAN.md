# R58 Development Access Plan: HDMI → VDO.ninja Mixer Integration

**Date**: December 22, 2025  
**Status**: ✅ Ready for Testing

---

## Latest Update (01:35 UTC)

Deployed improved signaling server with **Universal Room Handling**:
- Automatically normalizes different room hash variants
- Publishers (with `--salt`) and browsers (without salt) can now communicate
- All 3 cameras successfully connected and broadcasting
- Server logs confirm room normalization working correctly

---

## Executive Summary

**Goal**: Ingest HDMI inputs from R58 device into a local VDO.ninja instance and use `mixer.html` for scene composition and mixing.

---

## Current Architecture

### What's Working ✅

1. **MediaMTX Server** - Running on port 8889 (WebRTC/WHEP), 8888 (HLS), 8554 (RTSP), 1935 (RTMP)
2. **VDO.ninja Signaling Server** - Running on port 8443 with room-based routing
3. **Raspberry Ninja Publishers** - 3 cameras publishing via WebRTC:
   - `ninja-publish-cam1.service` - `/dev/video60` (HDMI N60) → `r58-cam1`
   - `ninja-publish-cam2.service` - `/dev/video11` (HDMI N11) → `r58-cam2`
   - `ninja-publish-cam3.service` - `/dev/video21` (HDMI N21) → `r58-cam3`
4. **Preke Recorder Service** - Main application service
5. **Local VDO.ninja** - Static files served from `/opt/vdo.ninja/`

### Current Data Flow

```
HDMI Input → V4L2 Device → raspberry.ninja (publish.py)
                          → GStreamer H.264 hardware encode
                          → WebRTC → Local VDO.ninja Signaling (wss://localhost:8443)
                          → Peer-to-peer WebRTC to viewers
```

### Current URLs Available

| URL | Purpose |
|-----|---------|
| `https://192.168.1.24:8443/?director=r58studio` | Director view (manage streams) |
| `https://192.168.1.24:8443/?view=r58-cam1&room=r58studio` | View cam1 only |
| `https://192.168.1.24:8443/?scene&room=r58studio` | Scene output (OBS) |
| `https://192.168.1.24:8443/mixer.html` | Mixer interface (needs config) |

---

## Problem Statement

The current setup uses:
1. **raspberry.ninja** publishers with VDO.ninja signaling for WebRTC
2. **MediaMTX** for RTSP/HLS/WebRTC (WHEP) independent of VDO.ninja

These are **two separate paths** that need to be integrated for mixer.html to work:

**Current Issue**: mixer.html requires proper stream IDs and room configuration to display and mix the camera feeds.

---

## Architecture Options

### Option A: Pure VDO.ninja with raspberry.ninja (Current Path) ⭐ RECOMMENDED

**Flow**:
```
HDMI → V4L2 → raspberry.ninja → VDO.ninja signaling → mixer.html
```

**Pros**:
- Already partially working (publishers connected)
- Full VDO.ninja features (scenes, layouts, director control)
- Low latency peer-to-peer WebRTC
- Native support for mixer.html

**Cons**:
- Need to fix signaling for proper room-based viewing
- Browser must accept self-signed certificate

**Required Changes**:
1. Fix VDO.ninja signaling to properly route room-based messages
2. Configure mixer.html with correct parameters
3. Test director view to ensure all cameras visible

---

### Option B: MediaMTX + VDO.ninja &mediamtx parameter

**Flow**:
```
HDMI → V4L2 → GStreamer → MediaMTX (WHIP) → VDO.ninja &mediamtx=... → mixer.html
```

**Pros**:
- Uses proven MediaMTX infrastructure
- Single source of truth for video
- VDO.ninja can pull streams via WHEP

**Cons**:
- More complex setup
- Requires modifying ingest pipelines
- May have higher latency

**Required Changes**:
1. Publish to MediaMTX via WHIP instead of VDO.ninja signaling
2. Configure VDO.ninja with `&mediamtx=localhost:8889`
3. Update mixer.html to use WHEP sources

---

### Option C: Hybrid - Keep Both Paths

**Flow**:
```
HDMI → V4L2 → raspberry.ninja → VDO.ninja signaling → mixer.html (for mixing)
                              ↘ GStreamer → MediaMTX → HLS/WHEP (for recording/remote)
```

**Pros**:
- Best of both worlds
- VDO.ninja for mixing, MediaMTX for distribution
- Already partially implemented

**Cons**:
- Most complex
- Dual encoding (higher CPU)
- Need synchronization

---

## Recommended Implementation: Option A (Fix Current Setup)

### Step 1: Verify VDO.ninja Signaling

The current signaling server has hardcoded room hash. We need to ensure it properly handles:
- Publisher join requests
- Viewer join requests  
- SDP offer/answer exchange
- ICE candidate exchange

**Test Command**:
```bash
# Check publishers are connected
journalctl -u ninja-publish-cam1 -n 20

# Check signaling logs
journalctl -u vdo-ninja -n 30
```

### Step 2: Access mixer.html

The mixer.html is available at:
```
https://192.168.1.24:8443/mixer.html?room=r58studio&wss=192.168.1.24:8443
```

**Key URL Parameters for mixer.html**:
| Parameter | Description |
|-----------|-------------|
| `room=r58studio` | Join the room where cameras are publishing |
| `wss=192.168.1.24:8443` | WebSocket signaling server |
| `scene` | Enable scene output mode |
| `solo` | Solo mode for single stream |
| `cover` | Cover/contain video mode |
| `api` | Enable API control |

### Step 3: Configure Director View

Director URL for managing streams:
```
https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443
```

The director should show:
- r58-cam1 (with hash suffix)
- r58-cam2 (with hash suffix)
- r58-cam3 (with hash suffix)

### Step 4: Create Scene Outputs

For OBS/recording, create scene URLs:
```
# Scene 1 (all cameras in grid)
https://192.168.1.24:8443/?scene&room=r58studio&wss=192.168.1.24:8443

# Scene 2 (specific camera full screen)
https://192.168.1.24:8443/?view=r58-cam1&room=r58studio&wss=192.168.1.24:8443&cover
```

---

## Implementation Checklist

### Phase 1: Verify Current Setup
- [ ] Confirm all 3 ninja publishers are running
- [ ] Check VDO.ninja signaling logs for successful joins
- [ ] Test director view in browser
- [ ] Accept self-signed certificate in browser

### Phase 2: Test mixer.html
- [ ] Open mixer.html with room parameters
- [ ] Verify camera feeds appear in mixer
- [ ] Test layout controls
- [ ] Test scene switching

### Phase 3: Configure Scene Outputs
- [ ] Create scene URL for OBS
- [ ] Test scene in OBS Browser Source
- [ ] Verify latency is acceptable

### Phase 4: Integration with Recorder
- [ ] Configure preke-recorder to use VDO.ninja scenes
- [ ] Test recording with mixer output
- [ ] Document final URLs

---

## Troubleshooting

### Issue: Cameras not appearing in mixer/director

**Check 1**: Publisher status
```bash
systemctl status ninja-publish-cam{1,2,3}
```

**Check 2**: Signaling server logs
```bash
journalctl -u vdo-ninja -f
```

**Check 3**: Browser console for WebRTC errors

### Issue: Self-signed certificate rejected

**Solution**: Navigate to `https://192.168.1.24:8443` first and accept the certificate, then access mixer.html.

### Issue: Room hash mismatch

The current signaling server uses hardcoded hash `d2869f4ba7cc9ad6` for room "r58studio". If the browser uses a different hash, messages won't be routed correctly.

**Fix**: The signaling server rewrites all roomid fields to the expected hash.

---

## Test URLs

Open these in a browser (accept self-signed cert first):

1. **Accept Certificate**: `https://192.168.1.24:8443/`

2. **Director View**: 
   ```
   https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443
   ```

3. **Mixer View**:
   ```
   https://192.168.1.24:8443/mixer.html?room=r58studio&wss=192.168.1.24:8443
   ```

4. **Scene Output** (for OBS):
   ```
   https://192.168.1.24:8443/?scene&room=r58studio&wss=192.168.1.24:8443
   ```

5. **Single Camera View**:
   ```
   https://192.168.1.24:8443/?view=r58-cam1&room=r58studio&wss=192.168.1.24:8443
   ```

---

## Remote Access (via Cloudflare Tunnel)

For remote access, the Cloudflare tunnel proxies to the VDO.ninja server:

```
https://recorder.itagenten.no/
```

However, WebSocket connections may not work through Cloudflare tunnel properly. For remote access, consider:

1. **Use Tailscale/ZeroTier VPN** for direct access
2. **Use MediaMTX WHEP** which works through HTTPS
3. **Port forward** WebSocket port if behind NAT

---

## Next Steps

1. **Test locally** from Windows PC on same network
2. **Accept certificate** at `https://192.168.1.24:8443`
3. **Open director view** to see all cameras
4. **Open mixer.html** to test mixing
5. **Report results** for further debugging

---

## Files Reference

| File | Location | Purpose |
|------|----------|---------|
| VDO.ninja static files | `/opt/vdo.ninja/` | Web interface |
| Signaling server | `/opt/vdo-signaling/vdo-server.js` | WebSocket relay |
| SSL certificates | `/opt/vdo-signaling/key.pem`, `cert.pem` | HTTPS/WSS |
| Publisher service | `/etc/systemd/system/ninja-publish-cam*.service` | Camera publishers |
| MediaMTX config | `/opt/mediamtx/mediamtx.yml` | Media server config |

---

## Research Resources Used

- [raspberry.ninja documentation](https://raspberry.ninja)
- [VDO.ninja documentation](https://docs.vdo.ninja)
- [VDO.ninja WHIP/WHEP tools](https://vdo.ninja/beta/whip)
- [MediaMTX documentation](https://mediamtx.org)
- [Steve Seguin's GitHub](https://github.com/steveseguin)


