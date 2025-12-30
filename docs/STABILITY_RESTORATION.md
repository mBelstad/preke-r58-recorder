# Stability Restoration - Single-Encoder Architecture

**Date:** December 30, 2025  
**Status:** Ready for Deployment

---

## Summary

Restored the proven single-encoder architecture that ran 4 cameras stably for a week. The TEE dual-encoder approach was causing crashes due to VPU overload (8 encoders for 4 cameras vs. safe limit of 4).

---

## Changes Made

### 1. Increased Ingest Bitrate (18Mbps)
**File:** `src/ingest.py` (line 105)

Changed from 8Mbps to 18Mbps to ensure high-quality recording via subscriber pattern:

```python
bitrate=18000,  # 18Mbps for high-quality recording via subscriber
```

**Rationale:** Single encoder at 18Mbps provides sufficient quality for both preview and recording. Subscriber recorder re-muxes without encoding (zero VPU load).

### 2. Switched to MKV Container
**File:** `src/pipelines.py` (line 476)

Changed from `mp4mux` to `matroskamux streamable=true`:

```python
mux_str = "matroskamux streamable=true"
```

**Rationale:** MKV files can be opened in DaVinci Resolve while recording is in progress (edit-while-record capability).

### 3. Verified Read-Only Signal Detection
**Files:** `src/ingest.py`, `src/device_detection.py`

Confirmed that:
- `get_subdev_resolution()` is read-only (doesn't modify device state)
- Device reinitialization only happens AFTER pipeline is stopped
- Signal recovery only reinitializes when no active pipeline exists

**Rationale:** Prevents "queue busy" kernel errors and crashes from interfering with running pipelines.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PER-CAMERA PIPELINE                      │
│                                                             │
│  v4l2src → RGA videoscale → mpph264enc (18Mbps) → RTSP    │
│                                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   MediaMTX   │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌─────────┐     ┌──────────┐    ┌──────────┐
    │  WHEP   │     │ Recorder │    │   VDO    │
    │ Preview │     │ (re-mux) │    │  Mixer   │
    └─────────┘     └────┬─────┘    └──────────┘
                         │
                         ▼
                    ┌─────────┐
                    │ MKV File│
                    └─────────┘
```

**Key Points:**
- 1 hardware encoder per camera = 4 encoders for 4 cameras (within VPU limits)
- Recording subscribes to MediaMTX and re-muxes (zero VPU load)
- Preview streams directly from MediaMTX (zero additional encoding)
- 18Mbps provides high quality for both preview and recording

---

## Resource Usage (Expected)

| Component | CPU | VPU | Notes |
|-----------|-----|-----|-------|
| 4× v4l2src + RGA scale | ~2% | - | DMA transfer + hardware scaling |
| 4× mpph264enc (18Mbps) | ~8% | ~50% | Hardware encoding |
| 4× Subscriber recording | ~2% | - | Re-mux only (no encoding) |
| **Total** | **~12%** | **~50%** | Plenty of headroom |

---

## Deployment Instructions

### Prerequisites
- R58 device accessible at `192.168.1.24`
- SSH key at `~/.ssh/r58_key`
- 4 HDMI sources connected to test

### Step 1: Deploy Changes

```bash
# Connect to R58
ssh -i ~/.ssh/r58_key linaro@192.168.1.24

# Navigate to deployment directory
cd /opt/preke-r58-recorder

# Pull latest changes
git pull origin main

# Verify service configuration (should use src/main.py)
cat preke-recorder.service | grep ExecStart

# Restart service
sudo systemctl restart preke-r58-recorder

# Monitor startup
journalctl -u preke-r58-recorder -f
```

### Step 2: Verify Ingest (5 minutes)

```bash
# Check service status
sudo systemctl status preke-r58-recorder

# Check if all 4 cameras are streaming
curl http://localhost:8000/api/ingest/status | jq

# Expected output: All enabled cameras should show "streaming"
```

### Step 3: Test Recording (10 minutes)

```bash
# Start recording on all cameras
curl -X POST http://localhost:8000/api/recording/start_all

# Wait 2 minutes, then check recording status
curl http://localhost:8000/api/recording/status | jq

# Verify MKV files are growing
ls -lh /mnt/sdcard/recordings/*/

# Stop recording
curl -X POST http://localhost:8000/api/recording/stop_all

# Verify files are playable (copy one to your machine and test in DaVinci Resolve)
```

### Step 4: Monitor Stability (1 hour)

```bash
# Monitor logs for errors
journalctl -u preke-r58-recorder -f

# Check CPU/VPU usage
htop

# Check VPU frequency (should be stable)
watch -n 1 'cat /sys/class/devfreq/fdab0000.rkvenc-core/cur_freq'
```

### Step 5: Test Hot-Plug

```bash
# Disconnect one HDMI cable
# Wait 30 seconds - system should NOT crash
# Check logs: journalctl -u preke-r58-recorder -n 50

# Reconnect cable
# Wait 30 seconds - stream should resume
# Verify: curl http://localhost:8000/api/ingest/status | jq
```

---

## Success Criteria

- [x] Code changes completed
- [ ] Service restarts without errors
- [ ] 4 cameras streaming simultaneously
- [ ] Recording produces growing MKV files
- [ ] MKV files playable in DaVinci Resolve
- [ ] System stable for 1+ hour
- [ ] Hot-plug doesn't crash system
- [ ] CPU usage < 20%
- [ ] No kernel panics or VPU errors

---

## Rollback Plan

If issues occur, the TEE pipeline code is still available in `packages/backend/`. To rollback:

```bash
# Edit preke-recorder.service
sudo nano /opt/preke-r58-recorder/preke-recorder.service

# Change ExecStart to use packages/backend
ExecStart=/opt/preke-r58-recorder/venv/bin/uvicorn packages.backend.pipeline_manager.main:app --host 0.0.0.0 --port 8000

# Restart service
sudo systemctl daemon-reload
sudo systemctl restart preke-r58-recorder
```

---

## Next Steps (After Validation)

1. **Document the architecture** - Update main docs to reflect single-encoder pattern
2. **Remove TEE code** - Clean up `packages/backend/` if not needed
3. **Add monitoring** - Set up alerts for pipeline failures
4. **Test mixer integration** - Verify VDO.ninja mixer works with 18Mbps streams

---

## Technical Notes

### Why Single-Encoder Works Better

1. **VPU Limits:** RK3588 safely handles 3-4 concurrent hardware encoders
2. **Zero-Copy Re-Mux:** Subscriber recording adds no VPU load
3. **Simplicity:** Fewer moving parts = easier to debug
4. **Proven Stable:** Ran for 1 week without crashes

### Why TEE Failed

1. **VPU Overload:** 8 encoders (2 per camera × 4 cameras) exceeds limits
2. **RGA Conflicts:** Multiple encoders competing for RGA resources
3. **Complexity:** More failure modes and race conditions

---

## References

- [INVESTIGATION_SUMMARY.md](./INVESTIGATION_SUMMARY.md) - Full test results
- [TEE_RECORDING_PIPELINE_SPEC.md](./TEE_RECORDING_PIPELINE_SPEC.md) - TEE architecture (not used)
- [lessons-learned.md](./lessons-learned.md) - Device initialization details

