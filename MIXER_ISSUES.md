# Mixer Core - Known Issues and Status

## Current Status

**Mixer Core Implementation:** ✅ Complete
- Scene Manager: ✅ Working (7 scenes loaded)
- API Endpoints: ✅ Working (all 6 endpoints functional)
- Pipeline Building: ✅ Working (pipeline builds successfully)
- Pipeline Start: ❌ **FAILING** - Device format negotiation error

## Critical Bug: Device Format Negotiation Failure

### Error
```
Device '/dev/video60' has no supported format
Call to TRY_FMT failed for NV24 @ 1920x1080: Invalid argument
```

### Root Cause Analysis

1. **Working Recorder Pipeline:**
   - Uses: `v4l2src device=/dev/video60 io-mode=mmap ! video/x-raw,format=NV24,width=1920,height=1080,framerate=60/1`
   - **This works** when used in single-camera recording pipeline

2. **Failing Mixer Pipeline:**
   - Uses: **EXACT SAME** format specification
   - **Fails** when used in multi-source compositor pipeline
   - Error occurs on first v4l2src element (v4l2src0 for cam0)

### Possible Causes

1. **Device Access Conflict:**
   - Multiple v4l2src elements in same pipeline may conflict
   - Device might not support concurrent format negotiation
   - Even though device shows "not in use", format negotiation might fail

2. **Format Negotiation Timing:**
   - In compositor pipeline, all sources negotiate simultaneously
   - Device might need sequential negotiation
   - GStreamer might be trying to set format before device is ready

3. **Device State:**
   - Device might need to be "opened" in a specific way for compositor
   - Previous pipeline might have left device in a state that prevents format setting
   - Need to ensure device is fully released before mixer starts

### Investigation Needed

1. Test if single-source mixer pipeline works (cam0_full scene)
2. Check if device needs explicit format query before use
3. Verify if device supports the format at the requested resolution
4. Test if adding delays between source initialization helps
5. Check if device needs to be "reset" between pipeline uses

### Workaround Options

1. **Use only active cameras:** Skip cameras that aren't configured/connected
2. **Sequential source initialization:** Start sources one at a time with delays
3. **Format query first:** Query device capabilities before building pipeline
4. **Device reset:** Explicitly close/reopen device before mixer starts

## What Works

✅ **Scene Management:**
- All 7 default scenes load correctly
- Scene API endpoints work
- Scene switching works (when pipeline not running)

✅ **API Integration:**
- `/api/scenes` - Lists all scenes
- `/api/scenes/{id}` - Gets scene definition
- `/api/mixer/set_scene` - Applies scene
- `/api/mixer/start` - Attempts to start (fails on device)
- `/api/mixer/stop` - Stops pipeline
- `/api/mixer/status` - Returns status and error info

✅ **Pipeline Building:**
- Pipeline string construction works
- GStreamer parse_launch succeeds
- Pipeline structure is correct

✅ **Error Handling:**
- Bus message capture works
- Error messages are logged and returned via API
- Timeout protection works (10s timeout)

## Next Steps

1. **Test device format negotiation:**
   ```bash
   v4l2-ctl --device=/dev/video60 --set-fmt-video=width=1920,height=1080,pixelformat=NV24
   ```

2. **Test single-source pipeline manually:**
   ```bash
   gst-launch-1.0 v4l2src device=/dev/video60 io-mode=mmap ! \
     video/x-raw,format=NV24,width=1920,height=1080,framerate=60/1 ! \
     videoconvert ! compositor name=c ! fakesink
   ```

3. **Check if device needs explicit format setting:**
   - Use `v4l2-ctl` to set format before GStreamer access
   - Or use GStreamer's `v4l2src` format negotiation differently

4. **Consider alternative approach:**
   - Use separate pipelines per camera, then combine
   - Or use different device access method for compositor

## Files Modified

- `src/mixer/core.py` - Main mixer implementation
- `src/mixer/scenes.py` - Scene management
- `src/mixer/watchdog.py` - Health monitoring
- `src/config.py` - Added MixerConfig
- `src/main.py` - Added mixer API endpoints
- `config.yml` - Added mixer configuration section
- `mediamtx.yml` - Added mixer_program path

## Testing Commands

```bash
# List scenes
curl http://localhost:8000/api/scenes

# Get mixer status
curl http://localhost:8000/api/mixer/status

# Set scene
curl -X POST http://localhost:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id":"quad"}'

# Start mixer (currently fails)
curl -X POST http://localhost:8000/api/mixer/start
```

