# Dynamic Signal Detection - Implementation Complete

**Date**: December 19, 2025  
**Status**: ✅ Implemented and Ready for Testing

---

## Summary

Added dynamic camera signal detection with visual indicators across all interfaces, plus critical resource optimization to prevent disabled cameras from wasting CPU cycles.

---

## Changes Made

### 1. Backend Optimization (src/ingest.py)

**File**: `src/ingest.py` (lines 397-406)

**Change**: Skip disabled cameras in health check loop

```python
def _check_all_pipelines_health(self):
    """Check health of all active pipelines and monitor signal status."""
    for cam_id, state in list(self.states.items()):
        # Skip disabled cameras entirely to save resources
        cam_config = self.config.cameras.get(cam_id)
        if not cam_config or not cam_config.enabled:
            continue
        
        # Check signal status for enabled cameras only
        signal_res = self._check_signal_status(cam_id)
        # ... rest of method
```

**Impact**:
- Reduces subprocess calls from 4 to 2 per health check cycle (10 seconds)
- Saves ~2 `v4l2-ctl` calls every 10 seconds for disabled cameras
- Prevents unnecessary device queries for cam0 and cam3

---

### 2. Switcher Interface (src/static/switcher.html)

**Changes**:

#### A. Added Signal Indicator CSS
- `.compact-signal-indicator` - Small dot in top-left of camera inputs
- `.signal-live` - Green with glow (camera has signal)
- `.signal-none` - Red with pulse animation (no signal)
- `.signal-disabled` - Gray (camera disabled in config)

#### B. Refactored `initCompactInputs()` Function
- Now `async` - fetches camera status before connecting streams
- Only connects WebRTC/HLS for cameras that are:
  - Enabled in config (`enabled: true`)
  - Have active HDMI signal (`has_signal: true`)
- Shows appropriate status for disabled/no-signal cameras
- Removed hardcoded `if (i === 0)` check

#### C. Added `updateSignalIndicators()` Function
- Polls `/api/ingest/status` every 3 seconds
- Updates signal indicator dots in real-time
- Shows resolution in tooltip on hover

#### D. Updated `preloadHLSManifests()` Function
- Now fetches camera status dynamically
- Only preloads manifests for enabled cameras with signal
- Prevents failed manifest fetches for disabled cameras

**Impact**:
- No failed WebRTC connection attempts for disabled cameras
- No failed HLS manifest fetches for disconnected cameras
- Operators see which cameras have active signals before switching
- Config-driven behavior (respects `enabled: false`)

---

### 3. Control Interface (src/static/control.html)

**Changes**:

#### A. Added Signal Indicator CSS
- `.camera-signal` - Container for signal indicator
- `.signal-dot` - Small dot indicator
- `.live`, `.no-signal`, `.disabled` - Status classes

#### B. Added `updateCameraSignalStatus()` Function
- Fetches `/api/ingest/status` to get signal information
- Stores in `cameraSignalStatus` global variable

#### C. Modified `updateCameraGrid()` Function
- Adds signal indicator to each camera card
- Shows signal status with colored dot
- Displays resolution when signal is present

#### D. Updated Polling
- Added signal status update to existing 2-second polling interval
- Initial call on page load

**Impact**:
- Operators see signal status on control panel
- Consistent UX across all interfaces

---

## Resource Savings

### Before
- Health check: 4 cameras × `v4l2-ctl` call every 10 seconds = **24 subprocess calls/minute**
- Switcher: 4 WebRTC connection attempts on load (2 fail for disabled cameras)
- Switcher: 4 HLS manifest preload attempts (2 fail for disabled cameras)

### After
- Health check: 2 cameras × `v4l2-ctl` call every 10 seconds = **12 subprocess calls/minute**
- Switcher: 2 WebRTC connection attempts on load (only for enabled cameras)
- Switcher: 2 HLS manifest preload attempts (only for enabled cameras)

**Result**: ~50% reduction in subprocess calls and zero failed connection attempts

---

## Testing Checklist

### Backend Testing
- [ ] SSH to R58: `ssh linaro@r58.itagenten.no`
- [ ] Watch logs: `sudo journalctl -u preke-recorder -f`
- [ ] Verify no v4l2-ctl calls for cam0/cam3 in logs
- [ ] Check CPU usage: `top` (should be lower)

### Main Dashboard (index.html)
- [ ] Open: https://recorder.itagenten.no/
- [ ] Verify signal indicators still work (already implemented)
- [ ] Check cam1 and cam2 show green dots (if connected)
- [ ] Check cam0 and cam3 show gray/red dots (disabled/no signal)

### Switcher Interface (switcher.html)
- [ ] Open: https://recorder.itagenten.no/switcher
- [ ] Verify only Input 2 and Input 3 show video (cam1, cam2)
- [ ] Verify Input 1 and Input 4 show "Disabled" or "No Signal"
- [ ] Check signal indicator dots appear in top-left of each input
- [ ] Hover over dots to see resolution tooltip
- [ ] Verify no WebRTC/HLS errors in browser console for disabled cameras

### Control Interface (control.html)
- [ ] Open: https://recorder.itagenten.no/static/control.html
- [ ] Navigate to Dashboard tab
- [ ] Verify signal indicators appear on camera cards
- [ ] Check cam1/cam2 show green dots with resolution
- [ ] Check cam0/cam3 show gray dots with "Disabled"

### Signal Loss Testing
- [ ] Disconnect HDMI cable from cam1
- [ ] Wait 10-15 seconds
- [ ] Verify red indicator appears in all interfaces
- [ ] Verify toast notification in main dashboard
- [ ] Reconnect HDMI cable
- [ ] Verify green indicator returns
- [ ] Verify toast notification for recovery

---

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `src/ingest.py` | +5 | Skip disabled cameras in health check |
| `src/static/switcher.html` | +139 -38 | Signal indicators + smart stream connection |
| `src/static/control.html` | +78 | Signal indicators on camera cards |

**Total**: 3 files, 252 insertions, 38 deletions

---

## API Usage

All interfaces now use `/api/ingest/status` which returns:

```json
{
  "cameras": {
    "cam0": {
      "status": "idle",
      "has_signal": false,
      "resolution": null
    },
    "cam1": {
      "status": "streaming",
      "has_signal": true,
      "resolution": {
        "width": 1920,
        "height": 1080,
        "formatted": "1920x1080"
      }
    }
  }
}
```

---

## Visual Indicators

### Signal Indicator States

| State | Color | Animation | Meaning |
|-------|-------|-----------|---------|
| Live | Green | Glow | Camera has active HDMI signal |
| No Signal | Red | Pulse | Camera enabled but no HDMI signal |
| Disabled | Gray | None | Camera disabled in config |
| Idle | Gray | None | Camera not initialized |

### Where Indicators Appear

- **Main Dashboard**: Signal dot + text below each camera preview
- **Switcher**: Small dot in top-left corner of each compact input
- **Control Panel**: Signal dot + text on each camera card

---

## Configuration

Cameras are controlled via `config.yml`:

```yaml
cameras:
  cam0:
    device: /dev/video0
    enabled: false  # Disabled - no camera connected
  
  cam1:
    device: /dev/video60
    enabled: true   # Enabled - primary camera
  
  cam2:
    device: /dev/video11
    enabled: true   # Enabled - secondary camera
  
  cam3:
    device: /dev/video22
    enabled: false  # Disabled - will be enabled after testing
```

---

## Deployment

### Deploy to R58

```bash
./deploy.sh r58.itagenten.no linaro
```

### Restart Service

```bash
ssh linaro@r58.itagenten.no
sudo systemctl restart preke-recorder
```

### Watch Logs

```bash
ssh linaro@r58.itagenten.no
sudo journalctl -u preke-recorder -f
```

---

## Verification Commands

### Check Backend Optimization

```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Watch logs for v4l2-ctl calls
sudo journalctl -u preke-recorder -f | grep "v4l2-ctl\|signal\|cam0\|cam3"

# Should NOT see v4l2-ctl calls for cam0 or cam3
```

### Check API Response

```bash
# Get ingest status
curl -s https://recorder.itagenten.no/api/ingest/status | python3 -m json.tool

# Expected: cam0 and cam3 show status: "idle"
# Expected: cam1 and cam2 show status: "streaming" with has_signal: true
```

### Check Browser Console

```bash
# Open switcher: https://recorder.itagenten.no/switcher
# Open browser console (F12)

# Expected logs:
# "Camera status fetched: {cam0: {...}, cam1: {...}, ...}"
# "Connecting cam1: enabled and has signal"
# "Connecting cam2: enabled and has signal"
# "Skipping cam0: disabled in config"
# "Skipping cam3: disabled in config"

# Should NOT see:
# "WebRTC connection failed for cam0"
# "HLS manifest 404 for cam0"
```

---

## Benefits Summary

### Performance
- ✅ 50% reduction in subprocess calls (12 vs 24 per minute)
- ✅ No wasted WebRTC connection attempts
- ✅ No failed HLS manifest fetches
- ✅ Lower CPU usage on R58 device

### User Experience
- ✅ Visual signal indicators in all interfaces
- ✅ Know which cameras are active before switching
- ✅ Quick troubleshooting (see disconnected cables immediately)
- ✅ Professional broadcast equipment look

### Maintainability
- ✅ Config-driven (respects `enabled: false`)
- ✅ No hardcoded camera skips
- ✅ Consistent behavior across interfaces
- ✅ Easy to enable/disable cameras in config

---

## Next Steps

1. **Deploy to R58**: Run `./deploy.sh`
2. **Test signal indicators**: Open all interfaces and verify indicators
3. **Test signal loss**: Disconnect HDMI cable and verify red indicators
4. **Monitor performance**: Check CPU usage is lower
5. **Test signal recovery**: Reconnect HDMI and verify automatic recovery

---

**Status**: ✅ Ready for deployment and testing!
