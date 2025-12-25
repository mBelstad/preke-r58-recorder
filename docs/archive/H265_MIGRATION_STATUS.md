# H.265 VPU Migration - Current Status

**Date**: 2025-12-19  
**Status**: ⏸️ PAUSED - Awaiting Manual Testing  
**Reason**: SSH commands being aborted, requires manual device access

---

## What We Discovered

### Critical Findings

1. **mpph264enc (H.264 VPU) is UNSTABLE**
   - Causes kernel panics: `Internal error: Oops: 0000000096000005 [#29] SMP`
   - Cannot be used in production
   - Rolled back to x264enc (software encoder)

2. **mpph265enc (H.265 VPU) is UNTESTED**
   - Code exists in `src/pipelines.py` (line 191) and `src/mixer/core.py` (line 1071)
   - Never verified for stability
   - Same MPP driver as mpph264enc (potential risk)

3. **Current Architecture Blocks H.265**
   - Using RTMP + flvmux for streaming to MediaMTX
   - flvmux does NOT support H.265
   - Must switch to RTSP push for H.265 support

### Why H.265 Matters

- **CPU Usage**: x264enc (software) uses ~30-40% CPU per stream
- **Hardware VPU**: mpph265enc would use ~5-10% CPU per stream
- **Scalability**: Can't run 4 cameras simultaneously with software encoding
- **Quality**: H.265 provides better compression than H.264

---

## Testing Plan Created

### Phase 1: Stability Testing (CURRENT PHASE)

Three tests to verify mpph265enc stability:

1. **Test 1**: Simple 30-second encode to file
2. **Test 2**: Sustained 5-minute encode (stress test)
3. **Test 3**: RTSP push to MediaMTX

**Test Script**: `test_h265_vpu.sh` (created)  
**Instructions**: `H265_VPU_TEST_INSTRUCTIONS.md` (created)

### Phase 2: Implementation (IF TESTS PASS)

Files to modify:
- `src/pipelines.py`: Switch to mpph265enc, RTSP push
- `src/mixer/core.py`: Use H.265 for mixer output
- `config.yml`: Change defaults to h265
- `src/pipelines.py`: Update recording subscriber for H.265

### Phase 3: Documentation

- Update `docs/fix-log.md` with findings
- Create `ENCODER_SELECTION.md` with decision rationale

---

## Current Blocker

**Issue**: SSH commands to R58 are being aborted by the system  
**Impact**: Cannot run automated tests remotely  
**Workaround**: Manual testing required

### Manual Testing Required

User needs to:
1. SSH to R58: `ssh linaro@r58.itagenten.no`
2. Stop service: `sudo systemctl stop preke-recorder`
3. Run test commands from `H265_VPU_TEST_INSTRUCTIONS.md`
4. Report results

---

## Decision Tree

```
mpph265enc stability test
├─ ✅ STABLE
│  ├─ Implement H.265 migration
│  ├─ Switch to RTSP push
│  ├─ Update all pipelines
│  └─ Enable 4-camera support
│
└─ ❌ UNSTABLE (kernel panics)
   ├─ Keep x264enc (software)
   ├─ Keep RTMP streaming
   ├─ Document MPP driver issues
   └─ Limit to 2 cameras max
```

---

## What Happens Next

### If mpph265enc is Stable

1. **Immediate Benefits**:
   - CPU usage drops from ~40% to ~10% per stream
   - Can run all 4 cameras simultaneously
   - Better video quality with H.265 compression

2. **Implementation** (automated):
   - Create `get_h265_encoder()` helper function
   - Replace all `rtmpsink` with `rtspclientsink`
   - Update encoder strings to use `mpph265enc`
   - Change default codec to h265 in config

3. **Testing**:
   - Deploy to R58
   - Test with real cameras
   - Monitor for stability issues

### If mpph265enc is Unstable

1. **Current State Maintained**:
   - Keep x264enc (software encoder)
   - Keep RTMP streaming
   - Limit to 2 cameras to avoid CPU overload

2. **Documentation**:
   - Record MPP driver instability
   - Document why hardware encoding can't be used
   - Recommend firmware/driver investigation

3. **Alternative Solutions**:
   - Investigate RK3588 firmware updates
   - Check for MPP driver patches
   - Consider external encoding hardware

---

## Files Created

1. `test_h265_vpu.sh` - Automated test script
2. `H265_VPU_TEST_INSTRUCTIONS.md` - Manual testing guide
3. `H265_MIGRATION_STATUS.md` - This file

---

## Recommendation

**CRITICAL**: Test mpph265enc stability BEFORE any code changes.

The mpph264enc kernel panics show that the MPP driver has serious issues. We must verify mpph265enc doesn't have the same problems before committing to a full migration.

**Estimated Time**:
- Testing: 10-15 minutes
- Implementation (if stable): 30 minutes
- Deployment & verification: 15 minutes

**Total**: ~1 hour if tests pass, 15 minutes if tests fail
