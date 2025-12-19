# H.265 VPU Testing Instructions

**Date**: 2025-12-19  
**Purpose**: Test mpph265enc (H.265 hardware encoder) stability before full migration  
**Background**: mpph264enc causes kernel panics, need to verify mpph265enc is stable

---

## Prerequisites

1. R58 device must be online and accessible
2. SSH access to `linaro@r58.itagenten.no` (password: `linaro`)
3. Service should be stopped before testing: `sudo systemctl stop preke-recorder`

---

## Test Script

A test script has been created at: `test_h265_vpu.sh`

### Manual Execution

SSH to the R58 and run these commands:

```bash
# Connect to R58
ssh linaro@r58.itagenten.no

# Stop the service to free up resources
sudo systemctl stop preke-recorder

# Test 1: Simple 30-second encode
echo "Test 1: Simple 30-second H.265 encode..."
gst-launch-1.0 videotestsrc num-buffers=900 ! \
  video/x-raw,width=1920,height=1080,framerate=30/1 ! \
  mpph265enc bps=8000000 ! \
  h265parse ! \
  matroskamux ! \
  filesink location=/tmp/test_h265.mkv

# Check if file was created
ls -lh /tmp/test_h265.mkv

# Test 2: Sustained 5-minute encode
echo "Test 2: Sustained 5-minute encode..."
gst-launch-1.0 videotestsrc num-buffers=9000 ! \
  video/x-raw,width=1920,height=1080,framerate=30/1 ! \
  mpph265enc bps=8000000 ! \
  h265parse ! \
  fakesink

# Test 3: RTSP push to MediaMTX
echo "Test 3: RTSP push with H.265..."
timeout 10 gst-launch-1.0 videotestsrc is-live=true ! \
  video/x-raw,width=1920,height=1080,framerate=30/1 ! \
  mpph265enc bps=5000000 ! \
  h265parse ! \
  rtspclientsink location=rtsp://127.0.0.1:8554/test_h265

# Verify stream in browser
# Open: http://r58.itagenten.no:8888/test_h265/
```

---

## Success Criteria

✅ **Test 1 PASS**: File `/tmp/test_h265.mkv` created, size > 0 bytes, no errors  
✅ **Test 2 PASS**: Command completes without kernel panic or segfault  
✅ **Test 3 PASS**: Stream visible in browser at HLS URL

❌ **Test FAIL**: Any kernel panic, segfault, or "Oops" error in dmesg

---

## What to Look For

### Signs of Success
- GStreamer pipeline runs without errors
- Output file is created and has reasonable size
- No kernel messages in `dmesg | tail -50`
- CPU usage stays reasonable (check with `top`)

### Signs of Failure
- Kernel panic messages (similar to mpph264enc)
- Segmentation fault
- GStreamer errors about encoder
- System becomes unresponsive

---

## If Tests Pass

1. Document results in `docs/fix-log.md`
2. Proceed with full H.265 migration:
   - Update `src/pipelines.py` to use `mpph265enc`
   - Switch from RTMP to RTSP push
   - Update `config.yml` defaults to h265
3. Deploy and test with real cameras

---

## If Tests Fail

1. Document failure in `docs/fix-log.md`
2. Keep current x264enc (software) encoder
3. Investigate alternatives:
   - Check RK3588 forums for MPP driver issues
   - Consider firmware/driver updates
   - Evaluate external encoding solutions

---

## Rollback Plan

If mpph265enc fails after deployment:

```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Stop service
sudo systemctl stop preke-recorder

# Revert code changes (will be in git)
cd /opt/preke-r58-recorder
git stash
git pull origin feature/webrtc-switcher-preview

# Restart service
sudo systemctl restart preke-recorder
```

---

## Next Steps After Testing

Based on test results, update the plan:

- ✅ **If stable**: Proceed with Phase 2 (Implementation)
- ❌ **If unstable**: Document findings and keep software encoder
