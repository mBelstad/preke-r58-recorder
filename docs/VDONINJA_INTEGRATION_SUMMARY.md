# VDO.ninja Integration Summary

**Date**: December 27, 2025  
**Purpose**: Comprehensive summary for continuing development in a new session

---

## Project Goal

Get HDMI cameras connected to an R58 (RK3588 ARM device) visible in VDO.ninja mixer/director rooms, accessible remotely through FRP tunnels.

---

## Current Infrastructure

### R58 Device
- **OS**: Debian-based Linux on RK3588 ARM
- **GStreamer**: 1.22.9 with `webrtcbin` (no `whipsink`)
- **Hardware Encoder**: `mpph264enc` (Rockchip MPP H.264)
- **MediaMTX**: Running on ports 8889 (WebRTC), 8554 (RTSP), 9997 (API)
- **VDO.ninja**: Self-hosted at `/opt/vdo.ninja/`
  - Web app: port 8444
  - Signaling server: port 8443 (WebSocket)

### FRP Tunnels (via VPS 65.109.32.111)
| Service | Public URL |
|---------|-----------|
| MediaMTX WebRTC | `https://app.itagenten.no` |
| VDO.ninja | `https://r58-vdo.itagenten.no` |
| FastAPI | `https://app.itagenten.no` |

### Camera Pipeline
```
HDMI Input → GStreamer → mpph264enc → RTSP → MediaMTX → WHEP endpoint
```

Working cameras: cam2, cam3 (cam0, cam1 have hardware issues)

---

## What Works ✅

### 1. MediaMTX WHEP Through FRP
```
https://app.itagenten.no/cam3/whep
```
- HTTP-based protocol works through FRP TCP tunnels
- Confirmed working December 27, 2025

### 2. VDO.ninja `&whepplay=` Parameter
```
https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam3/whep
```
- Pulls WHEP stream directly into VDO.ninja player
- Works remotely through FRP
- Video confirmed showing studio with microphones

### 3. VDO.ninja WHIP/WHEP Tool Page
```
https://r58-vdo.itagenten.no/whip.html
```
- "Play a remote video stream via WHEP" section works
- Useful for testing

---

## What Doesn't Work ❌

### 1. VDO.ninja Rooms with P2P
- Room-based signaling connects, but video doesn't flow
- P2P WebRTC requires UDP which FRP doesn't tunnel properly
- ICE candidates show `.local` mDNS addresses that don't resolve remotely

### 2. Our Python aiortc Bridge (`src/whep_vdo_bridge.py`)
**Critical Bug Found**:
```
ERROR: Cannot handle answer in signaling state "stable"
```
- Fails even locally on R58 (not just through FRP)
- Signaling state machine error when handling multiple viewers
- Connections close immediately after this error

### 3. Headless Chromium on ARM
- `--headless` mode crashes with "Invalid ozone platform: headless"
- Resource-intensive even if it worked
- Not recommended

### 4. raspberry.ninja P2P Publishers
- Services: `ninja-publish-cam1/2/3.service`
- Status: DISABLED and DEPRECATED
- Conflicts with MediaMTX for V4L2 device access

---

## Key Technical Findings

### Why P2P WebRTC Fails Through FRP
1. FRP tunnels TCP only, not UDP
2. WebRTC ICE negotiation requires UDP for media transport
3. mDNS `.local` addresses don't resolve across tunnel
4. STUN/TURN can help but adds complexity

### The `&mediamtx=` Parameter Misconception
- `&mediamtx=app.itagenten.no` is for NEW guests publishing TO MediaMTX
- Does NOT auto-import existing MediaMTX streams
- Cameras are already in MediaMTX via GStreamer, not through VDO.ninja flow

### The Solution: Direct WHEP Playback
- Use `&whepplay=` URLs directly in OBS/browser
- Bypasses room-based P2P entirely
- Each camera = one WHEP URL

---

## Alternatives for Getting Cameras into VDO.ninja Rooms

### Option 1: Raspberry.Ninja (Recommended for v2)
```bash
python3 publish.py --v4l2 /dev/video0 --room r58studio --server wss://r58-vdo.itagenten.no:8443
```
- Uses GStreamer `webrtcbin` (available on R58)
- Battle-tested, maintained by VDO.ninja creator
- Has built-in SFU for multiple viewers
- Needs testing on R58

**Install**:
```bash
pip install websockets aiohttp cryptography
git clone https://github.com/steveseguin/raspberry_ninja
```

### Option 2: GStreamer whipsink
- Requires building `gst-plugins-rs` (Rust crate)
- Would allow: `... ! whipsink whip-endpoint="https://whip.vdo.ninja/cam3"`
- High effort, no SFU

### Option 3: Fix Python Bridge
- Fix signaling state machine in `src/whep_vdo_bridge.py`
- Track per-peer connection state
- Medium effort, uncertain outcome

---

## Documentation References

### VDO.ninja Official
- [WHIP/WHEP Tooling](https://docs.vdo.ninja/steves-helper-apps/whip-and-whep-tooling)
- [Deploy MediaMTX Guide](https://docs.vdo.ninja/guides/deploy-your-own-meshcast-like-service)
- [OBS WHIP Settings](https://docs.vdo.ninja/guides/recommended-obs-whip-settings)
- [Hardware Accelerated Encoding](https://docs.vdo.ninja/guides/hardware-accelerated-video-encoding)
- [IFrame API](https://docs.vdo.ninja/guides/iframe-api-documentation)

### VDO.ninja Tools
- [WHIP/WHEP Test Page](https://vdo.ninja/whip)
- [Alpha Mixer](https://vdo.ninja/alpha/mixer)
- [Link Generator](https://linkgen.vdo.ninja/)

### Raspberry.Ninja
- [GitHub Repository](https://github.com/steveseguin/raspberry_ninja)
- [Documentation](https://raspberry.ninja/)

### Key Insight from Docs
> "if your WHIP server's response header includes a WHEP URL in it, VDO.Ninja will automatically provide that URL to connected viewers"

---

## File Locations

### On R58 Device
| Path | Description |
|------|-------------|
| `/opt/preke-r58-recorder/` | Main application |
| `/opt/vdo.ninja/` | VDO.ninja web app |
| `/opt/vdo-signaling/` | Signaling server |
| `/etc/mediamtx/mediamtx.yml` | MediaMTX config |
| `/etc/systemd/system/` | Service files |

### Key Source Files
| File | Description |
|------|-------------|
| `src/whep_vdo_bridge.py` | Python bridge (buggy) |
| `src/pipelines.py` | GStreamer pipeline builders |
| `src/ingest_manager.py` | Camera management |
| `src/main.py` | FastAPI endpoints |
| `docs/VDONINJA_WHEP_INTEGRATION.md` | Detailed integration guide |
| `docs/CURRENT_ARCHITECTURE.md` | System architecture |

---

## SSH Access

```bash
# Via FRP tunnel
./connect-r58-frp.sh "command here"

# Direct (from script)
sshpass -p 'linaro' ssh -o StrictHostKeyChecking=no -p 10022 linaro@65.109.32.111 "command"
```

---

## Working URLs for Testing

### Direct Camera View (Working)
```
https://r58-vdo.itagenten.no/?whepplay=https://app.itagenten.no/cam3/whep
```

### WHEP Test Page (Working)
```
https://r58-vdo.itagenten.no/whip.html
# Enter: https://app.itagenten.no/cam3/whep
```

### Director Room (Signaling works, video doesn't)
```
https://r58-vdo.itagenten.no/?director=r58studio&wss=wss://r58-vdo.itagenten.no
```

### MediaMTX API
```
curl https://app.itagenten.no/v3/paths/list
```

---

## Next Steps (Recommended)

1. **Immediate**: Use `&whepplay=` URLs for OBS browser sources
2. **Short-term**: Test Raspberry.Ninja on R58 with cam3
3. **Medium-term**: Integrate Raspberry.Ninja with FastAPI for unified control
4. **Long-term**: Build v2 app with room + camera management

---

## Commands for Quick Testing

### Check MediaMTX Status
```bash
./connect-r58-frp.sh "curl -s http://localhost:9997/v3/paths/list | python3 -c 'import sys,json; d=json.load(sys.stdin); [print(p[\"name\"], p[\"ready\"]) for p in d.get(\"items\",[]) if p[\"ready\"]]'"
```

### Check Services
```bash
./connect-r58-frp.sh "systemctl status mediamtx vdo-ninja vdo-webapp preke-r58-api --no-pager"
```

### View Bridge Logs
```bash
./connect-r58-frp.sh "sudo journalctl -u r58-whep-bridge -f"
```

---

**Summary**: HDMI cameras work via MediaMTX WHEP (`&whepplay=`). Getting them into VDO.ninja rooms requires either Raspberry.Ninja or fixing our Python bridge. P2P WebRTC doesn't work through FRP tunnels, but the `&whepplay=` approach bypasses this entirely.

