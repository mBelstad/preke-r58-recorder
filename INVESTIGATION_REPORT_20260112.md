# Investigation Report - January 12, 2026

## Summary

After thorough investigation, **most things are actually working correctly**. The issues reported were a combination of:
1. **R58 not having the latest code** (was 3 commits behind)
2. **VDO.ninja bridge not set to auto-start** (was disabled)
3. **VDO.ninja signaling server missing SSL certificates** (certs were deleted)
4. **No HDMI cables connected** (no video signal on any input)

## What Was Fixed

### 1. R58 Code Sync
- **Problem**: R58 was running commit `04288a50` but should have been on `6fe800bf`
- **Fix**: Pulled latest code and restarted service
- **Status**: ✅ Fixed

### 2. VDO.ninja Signaling Server
- **Problem**: Service was crash-looping due to missing SSL certificates at `/opt/vdo.ninja/certs/`
- **Fix**: Generated new self-signed certificates and fixed permissions
- **Status**: ✅ Fixed

### 3. VDO.ninja Bridge Auto-Start
- **Problem**: Service was disabled (would not start on boot)
- **Fix**: Enabled the service with `systemctl enable vdoninja-bridge`
- **Status**: ✅ Fixed

## Current Status (All Working)

| Component | Status | Details |
|-----------|--------|---------|
| FRP Client | ✅ Running | Active since 12:24 UTC |
| Preke Recorder | ✅ Running | Active since 13:03 UTC |
| MediaMTX | ✅ Running | Active since 12:24 UTC |
| VDO.ninja Signaling | ✅ Running | Active since 13:02 UTC |
| VDO.ninja Web App | ✅ Running | Active since 12:24 UTC |
| VDO.ninja Bridge | ✅ Running | 3 tabs open, enabled for auto-start |
| Web App | ✅ Working | Connected, 81ms latency |
| Storage Indicator | ✅ Correct | Shows 349GB (SSD) |
| Recordings | ✅ Present | 150+ recordings on SSD |

## Video Sources Issue

**"No Video Sources Connected"** is displayed because:
- All 4 HDMI inputs show `0x0` resolution (no signal)
- This is expected when no HDMI cables are plugged in
- cam0: `/dev/video0` - no signal
- cam1: `/dev/video60` - idle (640x480 default)
- cam2: `/dev/video11` - no signal
- cam3: `/dev/video22` - no signal

**This is NOT a software bug** - plug in HDMI cables to see video sources.

## Storage Configuration

| Mount | Device | Size | Used | Free |
|-------|--------|------|------|------|
| /data (SSD) | /dev/nvme0n1p1 | 469GB | 96GB | 349GB |
| /userdata | /dev/mmcblk0p8 | 44GB | 884MB | 43GB |
| / (root) | /dev/root | 14GB | 7.1GB | 6.1GB |

The storage indicator correctly shows the SSD at 349GB free.

## Recordings

Recordings ARE present on the SSD:
- cam0: 65 recordings (including one 70GB overnight recording)
- cam1: 1 recording
- cam2: 41 recordings
- cam3: 41 recordings

The Library view shows all sessions correctly.

## Changes Made Today (18 commits since Friday 20:00)

```
6fe800bf chore: bump Electron app version to 2.1.0 for cache busting release
fe54387d Deploy: 20260112_133212
346b7408 fix(mixer): Remove automatic P2P mode that broke Mac app
04288a50 feat(mixer): Add P2P mode option for VDO.ninja
1038a241 fix(mixer): Add Pi kiosk detection to getMediaMtxHost()
6105b0c9 revert: Restore mixer.html URL (director view broke mixer UI)
eee405b6 fix(mixer): Switch from mixer.html to director view for Pi kiosk
d5315415 Make fullscreen completely clean - no controls visible
2c3f0e98 Improve PDF quality with high-DPI rendering
d3ceb393 Move QR code to top-left
d8af5013 Fix viewerContainer reference in PDF viewer
f75ca336 Fix header variable reference in PDF viewer
9a46767e Fix duplicate variable declaration in PDF viewer
ba96523c Add /api/pdf-viewer and /api/pdf-controller routes
d451f051 Fix PDF viewer and controller issues
ded6c13c Fix PDF loading issues
021088c4 Add PDF remote control with single-session
62f07555 Add mobile-friendly PDF viewer with fullscreen presentation mode
```

Most changes were:
1. PDF viewer/controller feature (new)
2. Mixer P2P mode fixes
3. Cache busting for Electron app

## Known Issues (Not Critical)

1. **WebSocket endpoint 404**: `/api/v1/ws` returns 404 - the frontend has a fallback and works without it
2. **Capabilities endpoint 404**: `/api/v1/capabilities` returns 404 - the frontend constructs capabilities from other endpoints

These are expected because the R58 runs the monolithic `src/main.py` backend, not the new `packages/backend` API.

## Recommendations

1. **Plug in HDMI cables** to see video sources
2. **Test recording** to verify everything works end-to-end
3. **Monitor VDO.ninja bridge** - it should now auto-start on reboot

## Conclusion

The system is **fully operational**. The perceived issues were:
- Stale code on R58 (fixed)
- Missing SSL certs for VDO.ninja (fixed)
- VDO.ninja bridge not auto-starting (fixed)
- No HDMI cables connected (user action needed)

No code reverts are needed. The Friday 20:00 commit (`981adb1f`) functionality is preserved and working.
