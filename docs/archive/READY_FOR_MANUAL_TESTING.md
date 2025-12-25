# Ready for Manual Testing - H.265 VPU Migration

**Date**: 2025-12-19  
**Status**: ⏸️ PAUSED - Awaiting Manual Device Access  
**Blocker**: SSH commands being aborted by system

---

## What's Been Prepared

All code and documentation is ready for H.265 migration. Only manual stability testing remains.

### Files Created

1. ✅ **test_h265_vpu.sh** - Automated test script
2. ✅ **H265_VPU_TEST_INSTRUCTIONS.md** - Step-by-step manual testing guide
3. ✅ **h265_migration_changes.patch** - All code changes ready to apply
4. ✅ **H265_MIGRATION_STATUS.md** - Current status and decision tree
5. ✅ **ENCODER_INVESTIGATION_DEC19.md** - Complete investigation report
6. ✅ **READY_FOR_MANUAL_TESTING.md** - This file

---

## Quick Start: What You Need to Do

### Step 1: SSH to R58 (Manual)

```bash
ssh linaro@r58.itagenten.no
# Password: linaro
```

### Step 2: Stop the Service

```bash
sudo systemctl stop preke-recorder
```

### Step 3: Run Test 1 (Simple Encode)

```bash
gst-launch-1.0 videotestsrc num-buffers=900 ! \
  video/x-raw,width=1920,height=1080,framerate=30/1 ! \
  mpph265enc bps=8000000 ! \
  h265parse ! \
  matroskamux ! \
  filesink location=/tmp/test_h265.mkv
```

**Expected**: Command completes, file created, no kernel panic

### Step 4: Check Results

```bash
# Check if file was created
ls -lh /tmp/test_h265.mkv

# Check for kernel errors
dmesg | tail -20
```

### Step 5: Run Test 2 (Sustained Encode)

```bash
gst-launch-1.0 videotestsrc num-buffers=9000 ! \
  video/x-raw,width=1920,height=1080,framerate=30/1 ! \
  mpph265enc bps=8000000 ! \
  h265parse ! \
  fakesink
```

**Expected**: 5 minutes of encoding, no crashes

### Step 6: Run Test 3 (RTSP Push)

```bash
timeout 10 gst-launch-1.0 videotestsrc is-live=true ! \
  video/x-raw,width=1920,height=1080,framerate=30/1 ! \
  mpph265enc bps=5000000 ! \
  h265parse ! \
  rtspclientsink location=rtsp://127.0.0.1:8554/test_h265
```

**Expected**: 10 seconds of streaming, no errors

---

## Decision Point

### ✅ If ALL Tests Pass

**You'll see**:
- All commands complete successfully
- Files are created with reasonable sizes
- No "Oops" or "kernel panic" messages in dmesg
- System remains responsive

**Next steps** (automated):
1. Tell the AI: "Tests passed, proceed with implementation"
2. AI will apply changes from `h265_migration_changes.patch`
3. AI will deploy to R58
4. AI will test with real cameras

### ❌ If ANY Test Fails

**You'll see**:
- Kernel panic messages (like mpph264enc)
- Segmentation fault
- System becomes unresponsive
- "Oops" errors in dmesg

**Next steps**:
1. Tell the AI: "Tests failed, mpph265enc is unstable"
2. AI will document the failure
3. AI will keep current x264enc (software) encoder
4. System will remain limited to 2 cameras

---

## Why This Matters

### Current State (x264enc - Software)
- 2 cameras max before CPU overload
- ~40% CPU per camera
- High power consumption

### If Tests Pass (mpph265enc - Hardware)
- 4 cameras simultaneously
- ~10% CPU per camera
- Low power consumption
- Better video quality

### If Tests Fail (Stay with x264enc)
- Keep 2-camera limitation
- Document MPP driver issues
- Investigate firmware updates

---

## Detailed Instructions

For complete step-by-step instructions, see:
- **H265_VPU_TEST_INSTRUCTIONS.md**

For understanding the investigation, see:
- **ENCODER_INVESTIGATION_DEC19.md**

For implementation details, see:
- **h265_migration_changes.patch**

---

## Time Estimate

- **Testing**: 10-15 minutes
- **Implementation** (if tests pass): 30 minutes
- **Total**: ~45 minutes to production-ready 4-camera system

---

## What Happens After Testing

### Scenario A: Tests Pass ✅

```
1. You: "Tests passed"
2. AI applies h265_migration_changes.patch
3. AI commits changes
4. AI deploys to R58
5. AI tests with real cameras
6. AI monitors for stability
7. AI enables all 4 cameras
8. Done! 4-camera system with hardware encoding
```

### Scenario B: Tests Fail ❌

```
1. You: "Tests failed, got kernel panic"
2. AI documents failure in fix-log.md
3. AI updates ENCODER_SELECTION.md
4. AI confirms current 2-camera config
5. Done! Documented why hardware encoding can't be used
```

---

## Summary

**Everything is prepared**. The only remaining step is manual testing on the R58 device to verify mpph265enc stability.

**Critical**: Do NOT skip testing. mpph264enc kernel panics prove the MPP driver has issues. We must verify mpph265enc is safe before deploying.

**Ready to proceed**: Once you have SSH access and can run the 3 tests (10-15 minutes total).
