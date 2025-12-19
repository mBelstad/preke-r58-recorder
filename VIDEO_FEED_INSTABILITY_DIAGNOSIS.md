# Video Feed Instability - Diagnosis Report

**Date**: 2025-12-19 21:07 UTC  
**Issue**: Unstable video feeds on recorder.itagenten.no

---

## Symptoms

1. **HLS segment 404 errors** - Segments not found
2. **500 Internal Server Errors** on HLS requests
3. **Intermittent feed drops** reported by user

---

## Root Cause Analysis

### 1. **Critical: System Overload**

**CPU Usage**: 281% (uvicorn process)
```
PID   USER  %CPU  %MEM  COMMAND
35298 root  281.2  3.5  uvicorn
6773  root    6.2  3.2  mediamtx
```

**Load Average**: 4.20, 4.12, 4.34 (on 8-core system)
- This indicates the system is heavily overloaded
- Load > 4 on an 8-core ARM system is concerning

### 2. **HLS Segment Lifecycle Issues**

**Error Pattern**:
```
ERROR - HLS proxy error for cam0/ea2a1990f49f_seg184.mp4: 404: Stream not found
ERROR - HLS proxy error for cam3/dd2917337701_seg156.mp4: 404: Stream not found
```

**Analysis**:
- Segments are being deleted before clients can fetch them
- Current HLS settings: 7 segments @ 1 second = 7 second buffer
- High CPU load causes delayed segment generation
- Clients request segments that have already been purged

### 3. **Camera Resolution Mismatch**

**cam1 Issue**:
- Configured: 1920x1080
- Actual: 640x480 (VGA fallback)
- **This indicates signal quality issues or cable problems**

**Other cameras**:
- cam0: 3840x2160 (4K) ✓
- cam2: 1920x1080 (FHD) ✓
- cam3: 3840x2160 (4K) ✓

---

## Contributing Factors

### A. Too Many Concurrent Processes

**Running**:
- 4x camera ingest pipelines (H.265 encoding)
- 1x Reveal.js output (slides) - WPE WebKit
- MediaMTX server (RTSP/RTMP/HLS/WebRTC)
- HLS proxy in FastAPI
- Multiple client connections

**Resource Impact**:
- Each H.265 encode: ~50-70% CPU (even with VPU)
- WPE WebKit: ~20-30% CPU
- HLS segment generation: I/O intensive
- Total: Exceeds available CPU capacity

### B. HLS Configuration Too Aggressive

**Current Settings** (mediamtx.yml):
```yaml
hlsSegmentCount: 7
hlsSegmentDuration: 1s
hlsPartDuration: 200ms
```

**Problem**:
- 1-second segments require very fast generation
- 7-segment buffer = only 7 seconds of content
- Under high load, segment generation lags
- Segments expire before slow clients can fetch them

### C. Reveal.js Output Running

**Impact**:
- WPE WebKit process active (PID 35436)
- Adds ~20-30% CPU overhead
- Competes with camera encoding for VPU access
- May cause encoding delays

---

## Immediate Fixes

### Fix 1: Increase HLS Buffer (CRITICAL)

**Change mediamtx.yml**:
```yaml
# FROM:
hlsSegmentCount: 7
hlsSegmentDuration: 1s
hlsPartDuration: 200ms

# TO:
hlsSegmentCount: 15          # More segments = larger buffer
hlsSegmentDuration: 2s       # Longer segments = less frequent generation
hlsPartDuration: 400ms       # Less aggressive LL-HLS
```

**Impact**:
- Buffer increases from 7s to 30s
- Reduces segment generation frequency by 50%
- Gives slow clients more time to fetch segments
- Reduces I/O pressure

### Fix 2: Stop Unused Reveal.js Output

**Command**:
```bash
curl -X POST http://localhost:8000/api/reveal/stop
```

**Impact**:
- Frees ~20-30% CPU
- Reduces VPU contention
- Improves encoding stability

### Fix 3: Fix cam1 Signal

**Issue**: cam1 is at 640x480 (should be 1920x1080)

**Possible causes**:
- Bad HDMI cable
- Loose connection
- Source device outputting VGA signal
- HDMI input not properly initialized

**Actions**:
1. Check physical HDMI connection to IN60
2. Verify source device output resolution
3. Try different HDMI cable
4. Restart ingest: `curl -X POST http://localhost:8000/api/ingest/restart/cam1`

---

## Long-Term Solutions

### Solution 1: Optimize HLS Settings

**Balanced Configuration**:
```yaml
hlsSegmentCount: 10          # 20-second buffer
hlsSegmentDuration: 2s       # Reasonable generation frequency
hlsPartDuration: 400ms       # Balanced LL-HLS
```

**Benefits**:
- 20-second buffer for reliability
- 2-second segments reduce CPU load
- Still fast startup (~2-4 seconds)

### Solution 2: Reduce Concurrent Encoding

**Options**:
A. **Disable unused cameras**
   - If only 2-3 cameras needed, disable others in config.yml
   - Saves ~70% CPU per camera

B. **Use lower resolution for preview**
   - Keep 4K for recording
   - Use 1080p for streaming
   - Reduces encoding load

C. **Limit concurrent Reveal.js outputs**
   - Only run when actively presenting
   - Stop when not in use

### Solution 3: Hardware Upgrade Considerations

**Current System**: RK3588 (8-core ARM)
- **At capacity** with 4x 4K/1080p encodes + HLS + WebRTC
- Load average 4+ indicates oversubscription

**Options**:
A. **Reduce load** (preferred)
   - Optimize as above
   - Disable unused features

B. **Add dedicated streaming server** (if budget allows)
   - R58 does encoding only
   - Separate server handles HLS/WebRTC distribution
   - Reduces load on R58

### Solution 4: Monitor and Alert

**Add monitoring**:
```bash
# Check load average
uptime

# Check segment errors
journalctl -u preke-recorder -f | grep "404.*seg"

# Check CPU per process
top -bn1 | head -20
```

**Alert thresholds**:
- Load average > 6.0 = Critical
- HLS 404 errors > 10/min = Warning
- CPU > 300% = Critical

---

## Implementation Priority

### Immediate (Do Now)
1. ✅ **Stop Reveal.js output** - Frees 20-30% CPU
2. ✅ **Increase HLS buffer** - Fixes 404 errors
3. ✅ **Check cam1 cable** - Fix resolution issue

### Short-term (This Week)
4. **Optimize HLS settings** - Balance speed vs stability
5. **Add load monitoring** - Prevent future issues
6. **Document optimal configuration** - For reference

### Long-term (Future)
7. **Consider workload reduction** - Disable unused cameras
8. **Evaluate hardware upgrade** - If growth needed
9. **Implement auto-scaling** - Stop/start features based on load

---

## Testing After Fixes

### Test 1: HLS Stability
```bash
# Watch for 404 errors (should be zero)
ssh linaro@r58.itagenten.no "sudo journalctl -u preke-recorder -f | grep '404.*seg'"
```

### Test 2: Load Average
```bash
# Should drop below 3.0
ssh linaro@r58.itagenten.no "uptime"
```

### Test 3: Video Feed Quality
- Open: http://recorder.itagenten.no/
- Check all camera feeds load smoothly
- No buffering or stuttering
- Segments load without 500 errors

---

## Recommended Configuration

**mediamtx.yml** (optimized):
```yaml
hlsAddress: :8888
hlsAlwaysRemux: yes
hlsSegmentCount: 10          # 20-second buffer (balanced)
hlsSegmentDuration: 2s       # Reduce generation frequency
hlsPartDuration: 400ms       # Less aggressive LL-HLS
hlsAllowOrigin: "*"
```

**config.yml** (reduce load):
```yaml
# Disable cam0 if not needed (saves 70% CPU)
cameras:
  cam0:
    enabled: false  # 4K camera - high CPU cost

# Stop Reveal.js when not presenting
reveal:
  enabled: true  # But stop outputs when not in use
```

---

## Conclusion

**Root Cause**: System overload (281% CPU, load 4.2) causing HLS segment generation delays

**Primary Fix**: 
1. Stop Reveal.js output (immediate)
2. Increase HLS buffer to 10 segments @ 2s (immediate)
3. Fix cam1 signal issue (check cable)

**Expected Result**: 
- CPU drops to ~200%
- Load average drops to ~3.0
- HLS 404 errors eliminated
- Stable video feeds

**Status**: Ready to implement fixes
