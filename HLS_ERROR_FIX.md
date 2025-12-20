# HLS Error Fix - December 20, 2025

## Problem

The multiview page was experiencing continuous HLS errors in the console, causing:
- Excessive console spam
- Infinite recovery attempts
- Poor performance
- Unstable video playback

## Root Cause Analysis

### Issue 1: Untracked Media Error Recovery
**Location:** `src/static/index.html` line ~1901

The code was calling `hls.recoverMediaError()` on every MEDIA_ERROR without tracking attempts:

```javascript
else if (data.type === window.Hls.ErrorTypes.MEDIA_ERROR) {
    console.log(`HLS media error for ${camId}, recovering...`);
    hls.recoverMediaError();  // ❌ Called infinitely!
}
```

**Problem:** If recovery fails, HLS.js fires another MEDIA_ERROR, which triggers another recovery attempt, creating an infinite loop.

### Issue 2: Aggressive Stalled Handler
**Location:** `src/static/index.html` line ~1858

```javascript
video.onstalled = () => {
    console.warn(`Video stalled for ${camId}, attempting recovery...`);
    if (hlsPlayers[camId]) {
        hlsPlayers[camId].recoverMediaError();  // ❌ No throttling!
    }
};
```

**Problem:** `onstalled` events can fire frequently during buffering, causing unnecessary recovery attempts.

### Issue 3: Non-Fatal Error Logging
All errors (fatal and non-fatal) were logged as errors, creating console spam. HLS.js handles most non-fatal errors automatically.

## Solution

### 1. Implement Proper Media Error Recovery Strategy

Following HLS.js best practices:

```javascript
if (!hls.mediaErrorCount) hls.mediaErrorCount = 0;
if (!hls.lastMediaErrorTime) hls.lastMediaErrorTime = 0;

// Track errors with time-based reset
const now = Date.now();
if (now - hls.lastMediaErrorTime > 10000) {
    hls.mediaErrorCount = 0;  // Reset after 10 seconds
}
hls.lastMediaErrorTime = now;
hls.mediaErrorCount++;

if (hls.mediaErrorCount <= 2) {
    // Attempt 1-2: Try standard recovery
    hls.recoverMediaError();
} else if (hls.mediaErrorCount === 3) {
    // Attempt 3: Try swapping audio codec
    hls.swapAudioCodec();
    hls.recoverMediaError();
} else {
    // Attempt 4+: Destroy and recreate player
    hls.destroy();
    delete hlsPlayers[camId];
    setTimeout(() => {
        startHLSPreview(video, camId, placeholder);
    }, 1000);
}
```

**Benefits:**
- Limits recovery attempts to prevent infinite loops
- Escalates recovery strategy progressively
- Resets counter after 10 seconds of stability
- Destroys and recreates player as last resort

### 2. Remove Aggressive Stalled Handler

```javascript
video.onstalled = () => {
    // Don't spam recovery attempts - let the error handler deal with it
    console.debug(`Video stalled for ${camId} (will be handled by error handler if needed)`);
};
```

**Benefits:**
- Prevents duplicate recovery attempts
- Lets HLS.js error handler manage recovery
- Reduces console noise

### 3. Filter Non-Fatal Errors

```javascript
hls.on(window.Hls.Events.ERROR, (event, data) => {
    if (data.fatal) {
        console.error(`HLS fatal error for ${camId}:`, data.type, data.details);
    } else {
        console.debug(`HLS non-fatal error for ${camId}:`, data.type, data.details);
        return; // Let HLS.js handle non-fatal errors automatically
    }
    
    // Only process fatal errors...
});
```

**Benefits:**
- Reduces console spam significantly
- Only logs actionable errors
- Lets HLS.js handle minor issues automatically

## Results

✅ **No more infinite recovery loops**
✅ **Cleaner console output** (only fatal errors logged)
✅ **Better error handling** (progressive recovery strategy)
✅ **Improved stability** (proper throttling and resets)
✅ **Automatic recovery** from transient issues

## Technical Details

### HLS.js Error Types

1. **NETWORK_ERROR** - Failed to load manifest or segments
   - Strategy: Retry with exponential backoff (max 3 attempts)

2. **MEDIA_ERROR** - Failed to decode or play media
   - Strategy: Progressive recovery (recoverMediaError → swapAudioCodec → recreate player)

3. **OTHER_ERROR** - Other fatal errors
   - Strategy: Single retry after 3 seconds

### Recovery Timeline

```
Media Error 1: recoverMediaError() → Continue
Media Error 2: recoverMediaError() → Continue
Media Error 3: swapAudioCodec() + recoverMediaError() → Continue
Media Error 4+: Destroy and recreate player

[10 seconds of stability]
Counter resets to 0
```

## Testing

1. Open https://recorder.itagenten.no/
2. Check browser console
3. Verify:
   - No repeated error messages
   - Only fatal errors are logged
   - Videos recover gracefully from transient issues
   - No infinite loops

## Additional Fixes (December 20, 2025)

### Issue: HTTP 500 Errors on Segments

**Symptoms:**
- `GET https://recorder.itagenten.no/hls/cam0/xxx_seg1288.mp4` returns HTTP 500
- `NS_BINDING_ABORTED` errors
- `Media resource blob:... could not be decoded` errors

**Root Cause:**
MediaMTX was failing to generate HLS segments, likely due to:
1. H.265 codec compatibility issues (browsers don't support H.265 in HLS)
2. Segment expiration before delivery
3. High CPU load during transcoding

**Solution:**

1. **Distinguish Manifest vs Fragment Errors**
   ```javascript
   const isManifestError = data.details === window.Hls.ErrorDetails.MANIFEST_LOAD_ERROR;
   const isFragmentError = data.details === window.Hls.ErrorDetails.FRAG_LOAD_ERROR;
   
   if (isManifestError && HTTP 500) {
       // No signal - don't retry
   } else if (isFragmentError && HTTP 500) {
       // Transient error - let HLS.js retry
   }
   ```

2. **Enhanced HLS Configuration**
   - Increased fragment loading timeout to 20 seconds
   - Increased max retry attempts to 6 for fragments
   - Added `maxFragLookUpTolerance` to handle missing segments
   - Enabled worker threads for better performance

3. **Buffer Stall Handling**
   ```javascript
   if (data.details === window.Hls.ErrorDetails.BUFFER_STALLED_ERROR) {
       // Skip problematic segment and continue
       hls.startLoad();
   }
   ```

**Benefits:**
- ✅ Transient 500 errors are retried automatically
- ✅ Buffer stalls are handled gracefully
- ✅ Manifest errors (no signal) are distinguished from segment errors
- ✅ More robust fragment loading with longer timeouts

## References

- [HLS.js Error Handling Documentation](https://github.com/video-dev/hls.js/blob/master/docs/API.md#errors)
- [HLS.js Recovery Methods](https://github.com/video-dev/hls.js/blob/master/docs/API.md#recoverMediaError)
- [HLS.js Error Details](https://github.com/video-dev/hls.js/blob/master/docs/API.md#fifth-step-error-handling)
