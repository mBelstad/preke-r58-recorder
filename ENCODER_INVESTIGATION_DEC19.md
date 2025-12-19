# Encoder Investigation & H.265 Migration Plan

**Date**: 2025-12-19  
**Author**: AI Assistant  
**Status**: Awaiting Stability Tests

---

## Executive Summary

Investigation revealed that the system was **already partially using hardware encoding** (mpph265enc for H.265), but **mpph264enc causes kernel panics**. A migration to H.265-only with hardware encoding could reduce CPU usage from ~40% to ~10% per stream, enabling 4-camera operation.

**Critical Discovery**: Previous developers deliberately avoided mpph264enc due to instability, as evidenced by code comments.

---

## Background: The Encoder Confusion

### What We Thought
- System was using software encoding (x264enc) for everything
- Hardware encoders (mpph264enc/mpph265enc) were never tried

### What We Found
1. **H.265 (mpph265enc)** was ALREADY in the code (lines 191, 1071)
2. **H.264 (mpph264enc)** was deliberately AVOIDED due to crashes
3. **Current state**: Software H.264 (x264enc) as fallback after mpph264enc failures

### Code Evidence

**src/pipelines.py** (line 196):
```python
# Use hardware mpph264enc (Rockchip VPU) for low CPU usage
encoder_str, caps_str = get_h264_encoder(bitrate, platform="r58")
```

**src/pipelines.py** (lines 21-22):
```python
# TEMPORARY: Revert to software encoder due to mpph264enc kernel crashes
# TODO: Investigate MPP driver stability before re-enabling hardware encoder
```

This shows someone tried mpph264enc, it crashed, and they reverted to software.

---

## Encoder Stability Matrix

| Encoder | Type | Status | Evidence |
|---------|------|--------|----------|
| **x264enc** | Software H.264 | ✅ STABLE | Currently in use, high CPU |
| **mpph264enc** | Hardware H.264 | ❌ UNSTABLE | Kernel panic: `Oops: 0000000096000005 [#29]` |
| **mpph265enc** | Hardware H.265 | ❓ UNTESTED | In code but never stress-tested |

---

## The Kernel Panic Evidence

**Terminal log** (Dec 19, 14:53:01):
```
Message from syslogd@linaro-alip at Dec 19 14:53:01 ...
 kernel:[  494.442336] Internal error: Oops: 0000000096000005 [#29] SMP

Message from syslogd@linaro-alip at Dec 19 14:53:01 ...
 kernel:[  494.838527] Code: f100007f fa401a64 540017a0 b9402ae0 (f8606a62)

Connection to r58.itagenten.no closed by remote host.
```

This occurred immediately after attempting to restart the service with mpph264enc enabled.

---

## Why H.265 Matters

### Current State (x264enc - Software H.264)
- **CPU Usage**: ~30-40% per 1080p stream
- **4 Cameras**: ~120-160% CPU → System overload
- **Max Cameras**: 2 cameras stable, 3-4 causes crashes
- **Quality**: Good, but CPU-limited

### Proposed State (mpph265enc - Hardware H.265)
- **CPU Usage**: ~5-10% per 1080p stream
- **4 Cameras**: ~20-40% CPU → Plenty of headroom
- **Max Cameras**: All 4 cameras simultaneously
- **Quality**: Better (H.265 compression)

### The Math
```
Current (x264enc):
- 2 cameras × 40% CPU = 80% CPU ✓ Stable
- 4 cameras × 40% CPU = 160% CPU ✗ Crashes

Proposed (mpph265enc):
- 4 cameras × 10% CPU = 40% CPU ✓ Stable
- Could handle 8+ cameras theoretically
```

---

## The RTMP/H.265 Incompatibility

### Current Architecture Problem

```
Camera → Encode (H.264/H.265) → RTMP + flvmux → MediaMTX → Browser
                                      ↑
                                   PROBLEM: flvmux doesn't support H.265
```

**flvmux limitation**: FLV container only supports H.264, not H.265

### Solution: Switch to RTSP

```
Camera → Encode (H.265) → RTSP push → MediaMTX → Browser
                              ↑
                           Supports H.265
```

**RTSP advantages**:
- Supports H.265 natively
- Already used in macOS dev pipeline (line 64: `rtspclientsink`)
- MediaMTX handles RTSP → HLS/WebRTC transcoding for browsers

---

## Testing Plan

### Phase 1: Stability Verification (REQUIRED)

**Why**: mpph264enc crashes prove MPP driver has issues. Must verify mpph265enc is stable.

**Tests**:
1. Simple 30-second encode → Verify no crashes
2. Sustained 5-minute encode → Stress test
3. RTSP push test → Verify MediaMTX compatibility

**Test Script**: `test_h265_vpu.sh`  
**Instructions**: `H265_VPU_TEST_INSTRUCTIONS.md`

### Phase 2: Implementation (IF TESTS PASS)

**Files to modify**:
1. `src/pipelines.py` (4 changes)
2. `src/mixer/core.py` (2 changes)
3. `config.yml` (5 changes)

**Changes prepared**: `h265_migration_changes.patch`

### Phase 3: Production Testing

1. Deploy to R58
2. Test with real cameras
3. Monitor for 24 hours
4. Verify recordings are valid

---

## Risk Assessment

### High Risk: mpph265enc Instability

**Probability**: Medium (30-40%)  
**Impact**: Critical (kernel panics, system crashes)  
**Evidence**: mpph264enc uses same MPP driver and crashes

**Mitigation**:
- Test thoroughly before deployment
- Have rollback plan ready
- Monitor system logs closely

### Medium Risk: RTSP Compatibility

**Probability**: Low (10-20%)  
**Impact**: Medium (streaming issues)  
**Evidence**: RTSP already used in macOS pipeline

**Mitigation**:
- Test RTSP push in isolation first
- Verify MediaMTX transcoding works
- Keep RTMP code as fallback

### Low Risk: H.265 Playback

**Probability**: Very Low (<5%)  
**Impact**: Low (browser compatibility)  
**Evidence**: MediaMTX transcodes to HLS/WebRTC

**Mitigation**:
- MediaMTX handles H.265 → H.264 transcoding
- Modern browsers support H.265 via HLS
- WebRTC fallback available

---

## Decision Tree

```
┌─────────────────────────────┐
│ Run mpph265enc stability    │
│ tests on R58                │
└──────────┬──────────────────┘
           │
           ├─── ✅ STABLE (no crashes)
           │    │
           │    ├─ Apply h265_migration_changes.patch
           │    ├─ Deploy to R58
           │    ├─ Test with real cameras
           │    ├─ Monitor for 24h
           │    └─ Enable all 4 cameras
           │
           └─── ❌ UNSTABLE (kernel panics)
                │
                ├─ Keep x264enc (software)
                ├─ Document MPP driver issues
                ├─ Limit to 2 cameras max
                └─ Investigate alternatives:
                   ├─ Firmware updates
                   ├─ Driver patches
                   └─ External encoding
```

---

## Rollback Plan

If mpph265enc causes issues after deployment:

```bash
# 1. SSH to R58
ssh linaro@r58.itagenten.no

# 2. Stop service
sudo systemctl stop preke-recorder

# 3. Revert to previous commit
cd /opt/preke-r58-recorder
git log --oneline -5  # Find commit before H.265 migration
git reset --hard <commit-hash>

# 4. Restart service
sudo systemctl restart preke-recorder

# 5. Verify system is stable
curl http://localhost:5000/api/health
```

---

## Expected Outcomes

### If mpph265enc is Stable

**Immediate**:
- ✅ CPU usage drops from ~80% to ~20% (2 cameras)
- ✅ Can enable all 4 cameras simultaneously
- ✅ Better video quality (H.265 compression)
- ✅ Lower power consumption
- ✅ System more responsive

**Long-term**:
- ✅ Scalable to more cameras if needed
- ✅ Lower storage costs (better compression)
- ✅ Professional-grade performance

### If mpph265enc is Unstable

**Immediate**:
- ❌ Keep current 2-camera limitation
- ❌ High CPU usage continues
- ❌ Cannot use hardware acceleration

**Long-term**:
- ❌ Need to investigate RK3588 firmware/drivers
- ❌ May need external encoding hardware
- ❌ Limited scalability

---

## Recommendations

### Critical Next Step

**DO NOT PROCEED** with implementation until stability tests pass.

The mpph264enc kernel panics are a serious warning. We must verify mpph265enc doesn't have the same issues.

### Testing Checklist

- [ ] Run Test 1: Simple 30-second encode
- [ ] Verify output file is valid
- [ ] Check `dmesg` for kernel errors
- [ ] Run Test 2: Sustained 5-minute encode
- [ ] Monitor CPU usage during test
- [ ] Run Test 3: RTSP push to MediaMTX
- [ ] Verify stream in browser
- [ ] Check system stability after tests

### If Tests Pass

- [ ] Apply changes from `h265_migration_changes.patch`
- [ ] Commit with message: "Migrate to H.265 hardware encoding"
- [ ] Deploy to R58
- [ ] Test with 2 cameras first
- [ ] Gradually enable cameras 3 and 4
- [ ] Monitor for 24 hours

### If Tests Fail

- [ ] Document failure in `docs/fix-log.md`
- [ ] Keep current x264enc configuration
- [ ] Research RK3588 MPP driver issues
- [ ] Consider firmware updates
- [ ] Evaluate external encoding options

---

## Files Created

1. **test_h265_vpu.sh** - Automated test script
2. **H265_VPU_TEST_INSTRUCTIONS.md** - Manual testing guide
3. **H265_MIGRATION_STATUS.md** - Current status summary
4. **h265_migration_changes.patch** - Implementation changes (ready to apply)
5. **ENCODER_INVESTIGATION_DEC19.md** - This document

---

## Conclusion

We have a clear path forward, but it depends entirely on mpph265enc stability. The hardware encoder could solve our CPU problems and enable 4-camera operation, but only if it doesn't crash like mpph264enc.

**Next Action**: Run stability tests manually on R58 device.

**Estimated Time**:
- Testing: 10-15 minutes
- Implementation (if stable): 30 minutes
- Total: ~45 minutes to production-ready system

**Risk**: Medium-High (MPP driver instability)  
**Reward**: High (4x capacity increase, 75% CPU reduction)
