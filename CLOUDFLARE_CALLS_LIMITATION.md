# Cloudflare Calls API Limitation Discovered

## Issue

The relay implementation cannot work as designed because:

**Cloudflare Calls does not support server-side WHEP subscriptions.**

### Error Encountered
```
GET /sessions/{sessionId}/tracks
Response: 405 - reserved for future WHIP/WHEP
```

The `/tracks` endpoint and `/tracks/subscribe` endpoint return 405 Method Not Allowed, indicating these features are not yet available in Cloudflare Calls.

## What This Means

1. **Phase 1 Works**: Guest → Cloudflare Calls connection ✅
2. **Phase 2 Blocked**: Cannot pull stream from Cloudflare to R58 ❌

Cloudflare Calls is designed for **peer-to-peer browser communication**, not for server-side relay scenarios.

## Current Workaround

### For Local Network Guests (WORKS NOW)

Guests on the same network as R58 should use:
```
http://192.168.1.58:8000/guest_join
```

This connects directly to MediaMTX via WHIP, bypassing Cloudflare entirely.

**Status**: ✅ **FULLY FUNCTIONAL**

### For Remote Guests (NOT WORKING YET)

Remote guests can connect to Cloudflare Calls, but the stream cannot be relayed to R58 automatically.

**Status**: ❌ **BLOCKED BY API LIMITATION**

## Alternative Solutions

### Option 1: Browser-Based Dual Publish (Quick Fix)

Modify `guest_join.html` to publish to **both**:
1. Cloudflare Calls (for remote connectivity)
2. MediaMTX directly (for mixer visibility)

**Pros**: Works immediately, uses existing infrastructure
**Cons**: Doubles guest upload bandwidth, only works if guest can reach R58

### Option 2: Use Cloudflare Stream Instead

Cloudflare Stream (different product) supports RTMP output:
- Guest publishes to Cloudflare Stream
- Cloudflare Stream pushes RTMP to R58
- R58 receives in MediaMTX

**Pros**: Official Cloudflare solution for this use case
**Cons**: Different API, may have costs, requires migration

### Option 3: Custom TURN/STUN Server

Run own TURN server on R58:
- Configure MediaMTX with public TURN server
- Guests connect directly to MediaMTX with TURN assistance
- No Cloudflare Calls needed

**Pros**: Full control, no external dependencies
**Cons**: Requires public IP or port forwarding, TURN server setup

### Option 4: Wait for Cloudflare Calls API

Cloudflare may add server-side WHEP subscription in the future.

**Status**: "reserved for future WHIP/WHEP" suggests it's planned

## Recommended Path Forward

### Immediate (Today)

**Use Local Network URL for guests:**
```
http://192.168.1.58:8000/guest_join
```

This works perfectly right now with zero changes needed.

### Short Term (This Week)

**Implement Option 1: Browser Dual Publish**

Modify `guest_join.html` to:
1. Detect if MediaMTX is reachable
2. If yes: publish to MediaMTX directly
3. Also publish to Cloudflare Calls as backup
4. Show status of both connections

This gives best of both worlds:
- Remote guests connect via Cloudflare (for NAT traversal)
- Stream also goes to MediaMTX (for mixer)
- Works even if one path fails

### Long Term (Future)

**Option 2 or 3** depending on requirements:
- If budget allows: Cloudflare Stream
- If self-hosted preferred: Custom TURN server
- If patient: Wait for Cloudflare Calls API updates

## Technical Details

### What Cloudflare Calls Currently Supports

✅ Browser → Cloudflare (WHIP publish)
✅ Browser → Browser (peer-to-peer via Cloudflare SFU)
❌ Server → Cloudflare (WHEP subscribe)
❌ Cloudflare → Server (RTMP/RTSP push)

### What We Need

We need **one of**:
1. Server-side WHEP subscription (to pull from Cloudflare)
2. RTMP/RTSP output from Cloudflare (to push to MediaMTX)
3. Direct browser → MediaMTX connection (bypass Cloudflare)

Currently, only #3 works.

## Code Status

### What Was Implemented

- ✅ `src/cloudflare_calls.py` - Cloudflare Calls manager (works)
- ✅ `src/calls_relay.py` - Relay service (blocked by API)
- ✅ Integration in `src/main.py` (ready but can't function)

### What Works

- Local network guests: **FULLY FUNCTIONAL**
- Remote guest → Cloudflare connection: **WORKS**
- Cloudflare → R58 relay: **BLOCKED**

## Summary

**Current Reality**:
- Local guests work perfectly ✅
- Remote guests connect to Cloudflare but don't appear in mixer ❌

**Root Cause**:
- Cloudflare Calls API doesn't support server-side subscriptions yet

**Best Solution Right Now**:
- Use local network URL: `http://192.168.1.58:8000/guest_join`
- Or implement browser dual-publish for remote guests

**Future**:
- Monitor Cloudflare Calls API for updates
- Or migrate to Cloudflare Stream
- Or implement custom TURN server


