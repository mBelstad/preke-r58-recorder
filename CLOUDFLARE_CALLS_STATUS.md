# Cloudflare Calls SFU Integration - Status

## Current Implementation Status

### ✅ Phase 1: Cloudflare Calls Connection - COMPLETE

The guest can now connect to Cloudflare Calls SFU instead of directly to MediaMTX.

**What Works**:
- Guest browser connects to Cloudflare Calls via WHIP
- SDP offer/answer exchange through FastAPI proxy
- WebRTC connection established to Cloudflare's infrastructure
- Guest stream is now in Cloudflare Calls SFU

**Architecture**:
```
Remote Guest Browser
    ↓ WHIP (SDP offer)
FastAPI /api/calls/whip/{guestId}
    ↓ Forward to Cloudflare Calls
Cloudflare Calls SFU
    ↓ SDP answer
Guest Browser
    ↓ WebRTC media
Cloudflare Calls SFU (stream stored)
```

### ⏳ Phase 2: Relay to MediaMTX - TODO

**What's Missing**:
The stream is now in Cloudflare Calls, but we need to:
1. Subscribe to the track from Cloudflare (WHEP)
2. Relay it to MediaMTX (RTMP or WHIP)
3. Make it available to the Mixer

**Options for Phase 2**:

#### Option A: Backend WHEP Subscriber (Recommended)
Create a Python service that:
1. Subscribes to Cloudflare Calls tracks via WHEP
2. Receives WebRTC stream from Cloudflare
3. Transcodes and pushes to MediaMTX via RTMP

**Pros**: Complete control, works with existing architecture
**Cons**: Requires GStreamer WebRTC or aiortc implementation

#### Option B: Use Cloudflare Workers
Deploy a Cloudflare Worker that:
1. Subscribes to tracks in Cloudflare Calls
2. Relays to R58 MediaMTX via RTMP through tunnel

**Pros**: Runs on Cloudflare's edge
**Cons**: More complex deployment, Worker limitations

#### Option C: Browser-based Relay (Temporary)
Have the guest browser:
1. Connect to Cloudflare Calls (done)
2. Also connect directly to local MediaMTX (if on local network)
3. Dual-publish to both

**Pros**: Works immediately for testing
**Cons**: Wastes guest bandwidth, only works on local network

---

## What Was Implemented

### Files Created/Modified

1. **src/cloudflare_calls.py** (NEW)
   - `CloudflareCallsManager` class
   - Handles Cloudflare Calls API integration
   - Creates sessions with SDP offer/answer
   - Tracks active sessions per guest

2. **config.yml**
   - Added Cloudflare credentials section
   - Account ID, App ID, API Token configured

3. **src/config.py**
   - Added `CloudflareConfig` dataclass
   - Loads Cloudflare settings from config.yml

4. **src/main.py**
   - Added `calls_manager` initialization
   - Added `/api/calls/whip/{guest_id}` endpoint (WHIP proxy)
   - Added `/api/calls/session/{guest_id}` DELETE endpoint (cleanup)
   - Added `/api/calls/sessions` GET endpoint (list active)

5. **src/static/guest_join.html**
   - Updated to use Cloudflare Calls for remote access
   - Routes to `/api/calls/whip/{guestId}` when remote
   - Shows "Using Cloudflare Calls SFU" message
   - Session cleanup on disconnect

---

## Testing Instructions

### Test 1: Verify Cloudflare Calls Connection

1. Open: `https://recorder.itagenten.no/guest_join`
2. Should see: "🌐 Remote Access Mode - Using Cloudflare Calls SFU"
3. Click "Start Preview" → Grant permissions
4. Click "Join Stream"
5. Check browser console for:
   - "Connecting to Cloudflare Calls..."
   - "WHIP connection established"
   - "Connected to Cloudflare Calls SFU"
   - Connection state should reach "connected"

**Expected**: Guest successfully connects to Cloudflare Calls SFU

### Test 2: Verify Stream NOT Yet in Mixer

1. Open: `https://recorder.itagenten.no/switcher`
2. Look at "GUEST 1" input
3. Should show "Waiting..." or no video

**Expected**: Guest is NOT yet visible in mixer (Phase 2 not implemented)

---

## Current Limitations

### What Works ✅
- Guest connects to Cloudflare Calls successfully
- WebRTC connection established through Cloudflare Tunnel
- No NAT/firewall issues
- Session management working

### What Doesn't Work Yet ❌
- Guest stream not relayed to MediaMTX
- Guest not visible in mixer/switcher
- No WHEP subscriber implemented

---

## Next Steps (Phase 2 Options)

### Recommended: Implement Backend WHEP Relay

Create `src/calls_relay.py` with:

```python
class CloudflareCallsRelay:
    """Subscribe to Cloudflare Calls tracks and relay to MediaMTX."""
    
    async def subscribe_and_relay(self, session_id: str, track_id: str, guest_id: str):
        # 1. Get WHEP endpoint for track
        # 2. Create WebRTC connection to Cloudflare
        # 3. Receive media stream
        # 4. Transcode to RTMP
        # 5. Push to MediaMTX rtmp://127.0.0.1:1935/{guest_id}
```

**Implementation requires**:
- Python WebRTC library (aiortc or GStreamer webrtcbin)
- WHEP client implementation
- Media transcoding pipeline
- Background task management

**Estimated effort**: 4-6 hours

### Alternative: Use Local Network for Now

For immediate production use:
- Remote guests connect to Cloudflare Calls (works)
- But they need to be on local network for mixer visibility
- Or use local URL: `http://192.168.1.58:8000/guest_join`

---

## Architecture Comparison

### Current (Phase 1 Complete)
```
Guest → Cloudflare Calls SFU ✅
                ↓
            (stream stored in Cloudflare)
                ↓
            ❌ NOT relayed to R58 yet
```

### Target (Phase 2 Needed)
```
Guest → Cloudflare Calls SFU ✅
                ↓
        R58 Backend (WHEP subscriber)
                ↓
        MediaMTX (RTMP)
                ↓
        Mixer ✅
```

---

## Cloudflare Calls API Details

### Credentials Configured
- **Account ID**: 909fc2cd90c5fa19833110165ccb9bd7
- **App ID**: 56f5d93b573a427c45663a15cf5606a5
- **API Token**: 25f9d97cdfaee83d141811fc07a87679ca521660b3eb59615f7d4bf3293c65e8
- **App Name**: r58-1

### API Endpoints Used
- **Create Session**: `POST https://rtc.live.cloudflare.com/v1/apps/{appId}/sessions/new`
- **Close Session**: `PUT https://rtc.live.cloudflare.com/v1/apps/{appId}/sessions/{sessionId}/close`
- **List Tracks**: `GET https://rtc.live.cloudflare.com/v1/apps/{appId}/sessions/{sessionId}/tracks`

### Session Flow
1. Guest generates SDP offer
2. POST to `/api/calls/whip/{guestId}` with SDP
3. Backend forwards to Cloudflare `/sessions/new`
4. Cloudflare returns SDP answer + session ID + track IDs
5. Guest completes WebRTC handshake
6. Stream flows to Cloudflare

---

## Summary

**Phase 1 (Cloudflare Connection)**: ✅ COMPLETE
- Guests can connect to Cloudflare Calls from anywhere
- No NAT/firewall issues
- WebRTC working through Cloudflare Tunnel

**Phase 2 (Relay to Mixer)**: ⏳ TODO
- Need WHEP subscriber to pull from Cloudflare
- Need relay to push to MediaMTX
- Requires additional Python WebRTC implementation

**Current Workaround**: Use local network URL for guests who need to appear in mixer immediately.

**Production Path**: Implement Phase 2 relay service for full remote guest functionality.
