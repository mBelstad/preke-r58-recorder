# Known Issues - To Fix After Stability Verified

**Created:** December 30, 2025  
**Status:** Noted for future fixing - do NOT fix during stability testing

---

## Pipeline Optimization Issues

### Issue 1: Unnecessary `videoconvert` for NV12 Sources

**Location:** `src/pipelines.py` - `build_r58_ingest_pipeline()`

**Problem:** The pipeline includes `videoconvert` even when the source device is already outputting NV12 format. This adds unnecessary CPU overhead.

**Current pipeline:**
```
v4l2src (NV12) → videorate → videoconvert → videoscale → NV12 → encoder
```

**Optimal pipeline:**
```
v4l2src (NV12) → videorate → videoscale → encoder
```

**Fix:** Conditionally skip `videoconvert` when source format matches target format (NV12).

**Impact:** ~5-10% CPU savings per camera

---

### Issue 2: RGA Hardware Scaling Not Fully Utilized

**Location:** `src/pipelines.py`

**Problem:** Even with `GST_VIDEO_CONVERT_USE_RGA=1` enabled, the `videoconvert` element may prevent optimal RGA usage. RGA works best with direct NV12→NV12 scaling without format conversion.

**Fix:** Remove `videoconvert` for NV12 sources to let RGA handle scaling directly.

---

### Issue 3: Bitrate Lower Than Expected

**Observed:** Recording file was ~3.3 Mbps instead of expected 18 Mbps

**Possible causes:**
1. QP-based rate control (qp-init=26, qp-min=10, qp-max=51) overriding CBR target
2. Encoder not receiving full 18Mbps parameter
3. Static/low-motion content being aggressively compressed

**Investigation needed:**
- Check actual encoder output bitrate with `gst-debug`
- Test with high-motion content
- Consider using VBR or adjusting QP range

**Location:** `src/pipelines.py` - `get_h264_hardware_encoder()`

```python
encoder_str = (
    f"mpph264enc "
    f"qp-init=26 qp-min=10 qp-max=51 "  # ← QP may override CBR
    f"gop=30 profile=baseline rc-mode=cbr bps={bps}"
)
```

---

## Configuration Notes

### External Camera Control (Deferred to Phase 2)

**Status:** Disabled (all `enabled: false`)

**Feature:** Triggers Blackmagic and Obsbot cameras to start/stop recording in sync with R58.

**Cameras supported:**
- Blackmagic Design Studio Cameras (REST API)
- Obsbot Tail 2 (VISCA over UDP)

**Will enable:** After core stability is verified

---

## Priority for Fixing

| Issue | Priority | When to Fix |
|-------|----------|-------------|
| Bitrate investigation | High | After stability test |
| Remove unnecessary videoconvert | Medium | After stability test |
| Optimize RGA usage | Medium | After stability test |
| Enable external cameras | Low | Phase 2 |

---

## Do NOT Fix During Stability Testing

These issues are **cosmetic/optimization** and should NOT be addressed until:
1. 4 cameras streaming stably for 1+ hour
2. Recording works for all cameras
3. Hot-plug tested without crashes

Fixing optimization issues now could introduce new instability.

---

## References

- [STABILITY_RESTORATION.md](./STABILITY_RESTORATION.md) - Current deployment
- [TESTING_CHECKLIST.md](./TESTING_CHECKLIST.md) - Testing procedures
- `src/pipelines.py` - Pipeline builders
- `src/camera_control/` - External camera control (Phase 2)

