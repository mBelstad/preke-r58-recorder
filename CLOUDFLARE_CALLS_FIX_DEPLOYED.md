# Cloudflare Calls Fix - DEPLOYED

## Status: ✅ DEPLOYED AND READY FOR TESTING

The Cloudflare Calls integration has been fixed to use the correct two-step API flow for publishing and subscribing to tracks.

---

## What Was Fixed

### Problem
The previous implementation used incorrect API endpoints:
- ❌ `GET /sessions/{sessionId}/tracks` (returned 405)
- ❌ `POST /sessions/{sessionId}/tracks/subscribe` (doesn't exist)
- ❌ Single-step session creation with SDP in initial request

### Solution
Implemented the correct Cloudflare Calls API flow:

#### Guest Publishing (Two-Step)
1. **Step 1**: `POST /sessions/new` with empty body → Get `sessionId`
2. **Step 2**: `POST /sessions/{id}/tracks/new` with SDP + track names → Get SDP answer

#### Backend Subscription (Two-Step)
1. **Step 1**: `POST /sessions/new` with empty body → Get subscriber `sessionId`
2. **Step 2**: `POST /sessions/{subId}/tracks/new` with remote location → Subscribe to tracks

---

## Architecture Flow

```
Guest Browser
    ↓ SDP offer
FastAPI /api/calls/whip/guest1
    ↓
Cloudflare Calls Manager
    ├─ POST /sessions/new (empty) → sessionId
    └─ POST /sessions/{id}/tracks/new (SDP + local tracks)
        → SDP answer
    ↓ SDP answer
Guest Browser (WebRTC connected)
    ↓ Media stream
Cloudflare Calls SFU
    ↓
Backend Relay (after 2 seconds)
    ├─ POST /sessions/new (empty) → subscriberSessionId
    ├─ POST /sessions/{subId}/tracks/new (remote tracks)
    │   → SDP answer
    ├─ aiortc RTCPeerConnection
    └─ Receive WebRTC media
        ↓ Transcode
    FFmpeg (H.264 + AAC)
        ↓ RTMP
MediaMTX (rtmp://127.0.0.1:1935/guest1)
        ↓ RTSP
Mixer Core
```

---

## Files Modified

### 1. [src/cloudflare_calls.py](src/cloudflare_calls.py)
- Added `_create_empty_session()` - Step 1 of API flow
- Added `_add_tracks_to_session()` - Step 2 of API flow
- Renamed `create_session_with_sdp()` to `create_guest_session()`
- Now returns `track_names` for relay subscription
- Stores full session info including track names

**Key Changes**:
```python
# Old (Wrong)
POST /sessions/new with { sessionDescription: { sdp: "..." } }

# New (Correct)
session = await _create_empty_session()  # POST /sessions/new with {}
result = await _add_tracks_to_session(   # POST /sessions/{id}/tracks/new
    session_id, 
    sdp_offer, 
    ["video", "audio"]
)
```

### 2. [src/calls_relay.py](src/calls_relay.py)
- Added `_create_subscriber_session()` - Create subscriber session
- Added `_subscribe_to_tracks()` - Subscribe with remote location
- Updated `subscribe_and_relay()` to use correct flow
- Removed `get_session_tracks()` (doesn't work)

**Key Changes**:
```python
# Old (Wrong)
tracks = await get_session_tracks(session_id)  # 405 error

# New (Correct)
sub_session = await _create_subscriber_session()
await _subscribe_to_tracks(
    subscriber_session_id=sub_session["sessionId"],
    publisher_session_id=guest_session_id,
    track_names=["video", "audio"],
    sdp_offer=pc.localDescription.sdp
)
```

### 3. [src/main.py](src/main.py)
- Updated `/api/calls/whip/{guest_id}` endpoint
- Now calls `create_guest_session()` instead of `create_session_with_sdp()`
- Passes `track_names` to relay service

**Key Changes**:
```python
# Old
session_data = await calls_manager.create_session_with_sdp(guest_id, sdp_offer)
await calls_relay.subscribe_and_relay(session_id, guest_id, rtmp_url)

# New
session_data = await calls_manager.create_guest_session(guest_id, sdp_offer)
await calls_relay.subscribe_and_relay(
    guest_session_id=session_data['session_id'],
    track_names=session_data['track_names'],
    guest_id=guest_id,
    rtmp_url=rtmp_url
)
```

---

## Testing Instructions

### Test 1: Guest Connection

1. Open: `https://recorder.itagenten.no/guest_join`
2. Click "Start Preview" → Grant permissions
3. Click "Join Stream"
4. **Expected**: Connection state shows "connected"

### Test 2: Check Logs

```bash
ssh linaro@r58.itagenten.no
sudo journalctl -u preke-recorder -f
```

Look for:
- ✅ "Created empty session: {sessionId}"
- ✅ "Added 2 tracks to session {sessionId}: ['video', 'audio']"
- ✅ "Successfully created session for guest1: {sessionId} with tracks ['video', 'audio']"
- ✅ "Created subscriber session: {subSessionId}"
- ✅ "Subscribing to tracks ['video', 'audio'] from session {sessionId}"
- ✅ "Successfully subscribed to tracks"
- ✅ "Received video track from Cloudflare Calls"
- ✅ "Starting RTMP relay"
- ✅ "RTMP relay started successfully"

### Test 3: Verify Stream in MediaMTX

```bash
curl http://127.0.0.1:9997/v3/paths/get/guest1
```

Should show:
```json
{
  "sourceReady": true,
  ...
}
```

### Test 4: View in Switcher

1. Open: `https://recorder.itagenten.no/switcher`
2. Look at "GUEST 1" input
3. **Expected**: Guest video appears!

### Test 5: Assign to Scene

1. In switcher, select a scene
2. Assign "Guest 1" to an input
3. Start mixer
4. **Expected**: Guest appears in program output

---

## Expected Log Sequence

When a guest connects, you should see this sequence:

```
1. Creating Cloudflare Calls session for guest1 (two-step flow)
2. Created empty session: abc123
3. Added 2 tracks to session abc123: ['video', 'audio']
4. Successfully created session for guest1: abc123 with tracks ['video', 'audio']
5. Cloudflare Calls session created for guest1: abc123 with tracks ['video', 'audio']
6. [After 2 seconds]
7. Starting relay for guest1: session abc123 -> rtmp://127.0.0.1:1935/guest1
8. Created subscriber session: def456
9. Subscribing to tracks ['video', 'audio'] from session abc123
10. Successfully subscribed to tracks from abc123
11. Relay established for guest1
12. Received video track from Cloudflare Calls for guest1
13. Starting RTMP relay for guest1
14. Starting RTMP relay to rtmp://127.0.0.1:1935/guest1
15. RTMP relay started successfully
16. Relay started for guest1: Cloudflare -> MediaMTX
```

---

## Troubleshooting

### If Guest Connects But No Relay

**Check logs for errors**:
```bash
sudo journalctl -u preke-recorder -n 100 | grep -i "error\|failed"
```

**Common issues**:
- API token invalid → Check config.yml
- Session creation fails → Check Cloudflare Calls API status
- Subscription fails → Check track names match

### If Relay Starts But No Video in Mixer

**Check MediaMTX**:
```bash
curl http://127.0.0.1:9997/v3/paths/get/guest1
```

**Check FFmpeg process**:
```bash
ps aux | grep ffmpeg
```

**Common issues**:
- FFmpeg not installed
- RTMP port blocked
- Video format incompatible

### If Connection Fails Immediately

**Check Cloudflare Calls API**:
- Verify API token has correct permissions
- Check app ID is correct
- Ensure account ID is valid

---

## API Endpoints Reference

### Cloudflare Calls API

**Create Session**:
```
POST https://rtc.live.cloudflare.com/v1/apps/{appId}/sessions/new
Body: {}
Response: { "sessionId": "..." }
```

**Add Tracks (Publish)**:
```
POST https://rtc.live.cloudflare.com/v1/apps/{appId}/sessions/{sessionId}/tracks/new
Body: {
  "sessionDescription": { "type": "offer", "sdp": "..." },
  "tracks": [
    { "location": "local", "trackName": "video" },
    { "location": "local", "trackName": "audio" }
  ]
}
Response: { "sessionDescription": { "sdp": "..." }, "tracks": [...] }
```

**Subscribe to Tracks**:
```
POST https://rtc.live.cloudflare.com/v1/apps/{appId}/sessions/{subscriberSessionId}/tracks/new
Body: {
  "sessionDescription": { "type": "offer", "sdp": "..." },
  "tracks": [
    { "location": "remote", "sessionId": "publisherSessionId", "trackName": "video" },
    { "location": "remote", "sessionId": "publisherSessionId", "trackName": "audio" }
  ]
}
Response: { "sessionDescription": { "sdp": "..." } }
```

---

## Next Steps

1. **Test with real remote guest** - The critical test!
2. **Monitor logs** - Watch for complete sequence
3. **Verify in switcher** - Check guest appears
4. **Test in production** - Use in actual production

---

## Summary

✅ **Fixed**: Cloudflare Calls API integration
✅ **Deployed**: All changes to R58
✅ **Ready**: For end-to-end testing

**Status**: READY FOR TESTING

**What to do**: Connect as guest and check logs for success sequence!


