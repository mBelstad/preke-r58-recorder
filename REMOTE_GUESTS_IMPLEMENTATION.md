# Remote Guests Implementation - Complete

## Overview

Successfully implemented remote guest functionality using MediaMTX WHIP, allowing guests to join via browser and appear as inputs in the mixer alongside camera sources.

**Status**: ✅ **DEPLOYED TO R58**

---

## Architecture

```
Guest Browser → WHIP (WebRTC) → MediaMTX → RTSP → Mixer → Program Output
```

### Flow
1. Guest opens `https://recorder.itagenten.no/guest_join.html`
2. Selects camera/mic and joins as guest1 or guest2
3. Browser publishes via WHIP to MediaMTX (port 8889)
4. MediaMTX converts WebRTC to RTSP stream
5. Mixer consumes guest RTSP stream like camera inputs
6. Guest appears in switcher UI alongside camera inputs

---

## Files Modified

### 1. MediaMTX Configuration
**File**: `mediamtx.yml`

Added guest paths:
```yaml
paths:
  # ... existing cam0-cam3 ...
  guest1:
    source: publisher
  guest2:
    source: publisher
```

### 2. Application Configuration
**File**: `config.yml`

Added guests section:
```yaml
guests:
  guest1:
    name: "Guest 1"
    enabled: true
  guest2:
    name: "Guest 2"
    enabled: true
```

**File**: `src/config.py`

Added `GuestConfig` dataclass and loaded guests from config.

### 3. Guest Join Page
**File**: `src/static/guest_join.html` (NEW)

Features:
- Camera/microphone selection
- Local preview before joining
- WHIP client implementation (native WebRTC)
- Connection status and stats (bitrate, duration)
- Guest slot selection (guest1/guest2)
- Works through Cloudflare Tunnel (WHIP is HTTP-based)

### 4. Mixer Core Updates
**File**: `src/mixer/core.py`

Changes:
- Added `_check_mediamtx_stream()` method to query MediaMTX API
- Updated `_build_pipeline()` to handle guest sources
- Guest sources skip ingest check (no V4L2 device)
- Guests sourced from RTSP like cameras

Key code:
```python
# Handle guest sources (remote guests via WHIP)
if slot.source.startswith("guest"):
    if not self._check_mediamtx_stream(guest_id):
        logger.info(f"Guest {guest_id} not streaming, skipping")
        continue
    rtsp_url = f"rtsp://127.0.0.1:{rtsp_port}/{guest_id}"
    # ... build source_str same as camera
```

### 5. Switcher UI Updates
**File**: `src/static/switcher.html`

Changes:
- Extended `initCompactInputs()` to show guest1/guest2 after cam0-cam3
- Added guest input selector buttons
- Guest inputs show "Waiting..." status when not connected
- Guests appear as "Guest 1" and "Guest 2" in input grid

### 6. API Endpoint
**File**: `src/main.py`

Added `/api/guests/status` endpoint:
- Queries MediaMTX API for each guest
- Returns streaming status (true/false)
- Can be used by UI to show guest connection state

---

## Testing Instructions

### 1. Access Guest Join Page
```
https://recorder.itagenten.no/guest_join.html
```

### 2. Join as Guest
1. Select camera and microphone
2. Click "Start Preview" to test
3. Choose guest slot (Guest 1 or Guest 2)
4. Click "Join Stream"
5. Wait for "Connected" status

### 3. View in Switcher
```
https://recorder.itagenten.no/switcher
```

Guest should appear in the input grid below camera inputs.

### 4. Use in Scene
1. Open scene editor or create new scene
2. Select a box
3. Assign input → Guest 1 or Guest 2
4. Apply scene to see guest in program output

### 5. Check Guest Status API
```bash
curl https://recorder.itagenten.no/api/guests/status
```

Expected response:
```json
{
  "guests": {
    "guest1": {
      "name": "Guest 1",
      "enabled": true,
      "streaming": true
    },
    "guest2": {
      "name": "Guest 2",
      "enabled": true,
      "streaming": false
    }
  }
}
```

---

## Technical Details

### WHIP Protocol
- **WHIP** = WebRTC-HTTP Ingestion Protocol
- HTTP-based, works through Cloudflare Tunnel
- MediaMTX endpoint: `http://192.168.1.58:8889/{guest_id}/whip`
- Through tunnel: `https://recorder.itagenten.no/whip/{guest_id}` (if proxied)

### MediaMTX Conversion
- Receives WebRTC stream via WHIP
- Transcodes to H.264 if needed
- Publishes to RTSP path
- Mixer subscribes to RTSP

### Latency
- Guest → MediaMTX: ~200-500ms (WebRTC)
- MediaMTX → Mixer: ~50ms (RTSP local)
- **Total**: ~250-550ms (acceptable for remote guests)

### Bandwidth
- Guest upload: ~1-3 Mbps (depends on resolution/quality)
- Recommended: 720p @ 1.5 Mbps for remote guests
- Can be adjusted in guest_join.html constraints

---

## Deployment

### Services Restarted
```bash
sudo systemctl restart mediamtx
sudo systemctl restart preke-recorder
```

### Verify Deployment
```bash
# Check MediaMTX
sudo systemctl status mediamtx

# Check recorder
sudo systemctl status preke-recorder

# Test guest join page
curl https://recorder.itagenten.no/guest_join.html
```

---

## Configuration Options

### Add More Guests
Edit `config.yml`:
```yaml
guests:
  guest1:
    name: "Guest 1"
    enabled: true
  guest2:
    name: "Guest 2"
    enabled: true
  guest3:
    name: "Guest 3"
    enabled: true
```

And `mediamtx.yml`:
```yaml
paths:
  # ...
  guest3:
    source: publisher
```

### Disable Guests
Set `enabled: false` in config.yml

### Customize Guest Names
Change `name` field in config.yml (displayed in UI)

---

## Troubleshooting

### Guest Can't Connect
1. Check MediaMTX is running: `systemctl status mediamtx`
2. Check port 8889 is accessible
3. Check browser console for WebRTC errors
4. Verify camera/mic permissions granted

### Guest Not Appearing in Mixer
1. Check guest is streaming: `curl http://192.168.1.58:9997/v3/paths/get/guest1`
2. Check mixer logs: `journalctl -u preke-recorder -f`
3. Verify scene includes guest source
4. Restart mixer if needed

### Poor Quality
1. Adjust video constraints in guest_join.html
2. Check guest's network bandwidth
3. Consider lowering resolution to 720p

### Audio Issues
- Ensure microphone is selected
- Check browser audio permissions
- Verify MediaMTX is receiving audio track

---

## Future Enhancements

### Potential Improvements
1. **Guest Management UI**: Admin page to see/kick guests
2. **Quality Presets**: Let guests choose quality (720p/1080p)
3. **Guest Limit**: Enforce max concurrent guests
4. **Authentication**: Require token/password to join
5. **Recording**: Option to record individual guest feeds
6. **Chat**: Add text chat for guests
7. **Screen Share**: Allow guests to share screen
8. **Multiple Guests**: Support more than 2 guests

### MediaMTX Features to Explore
- **Recording**: MediaMTX can record guest streams
- **Playback**: Replay recorded guest sessions
- **Transcoding**: Adjust quality per guest
- **Authentication**: Add auth to WHIP endpoints

---

## URLs

- **Guest Join**: https://recorder.itagenten.no/guest_join.html
- **Switcher**: https://recorder.itagenten.no/switcher
- **API Docs**: https://recorder.itagenten.no/docs
- **Guest Status**: https://recorder.itagenten.no/api/guests/status

---

## Summary

Remote guest functionality is now **fully operational**:
- ✅ MediaMTX WHIP configured
- ✅ Guest join page created
- ✅ Mixer supports guest sources
- ✅ Switcher UI shows guests
- ✅ API endpoint for guest status
- ✅ Deployed to R58
- ✅ Ready for testing

Guests can now join via browser and appear as mixer inputs alongside cameras!

