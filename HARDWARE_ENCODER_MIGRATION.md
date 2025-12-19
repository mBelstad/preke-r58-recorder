# Hardware Encoder Migration Complete

**Date**: December 19, 2025  
**Status**: Code deployed, awaiting service restart

## Changes Implemented

### 1. Created Helper Function
Added `get_h264_encoder()` in `src/pipelines.py` with:
- Platform detection (macOS vs R58)
- Automatic selection of x264enc (software) or mpph264enc (hardware)
- 4K source detection for potential optimizations

### 2. Updated All Pipeline Builders

| Function | File | Status |
|----------|------|--------|
| `build_r58_pipeline()` | src/pipelines.py | ✅ Updated |
| `build_r58_preview_pipeline()` | src/pipelines.py | ✅ Updated |
| `build_ingest_pipeline_r58()` | src/pipelines.py | ✅ Updated |
| Mixer encoder | src/mixer/core.py | ✅ Updated |

### 3. Hardware Encoder Parameters

```python
# mpph264enc configuration
bps = bitrate * 1000  # Convert kbps to bps
encoder_str = f"mpph264enc rc-mode=cbr bps={bps} gop=30 qp-init=26"
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `rc-mode` | cbr | Constant bitrate for streaming |
| `bps` | bitrate * 1000 | Bits per second (not kbps) |
| `gop` | 30 | Keyframe every 1 second at 30fps |
| `qp-init` | 26 | Initial quality parameter |

## Expected Benefits

| Metric | Before (x264) | After (mpph264enc) |
|--------|--------------|-------------------|
| CPU per 4K stream | ~100-200% | ~5-10% |
| Max stable cameras | 2 | 4 |
| Encoding latency | ~50-100ms | ~10-20ms |
| Power consumption | High | Low |

## Deployment Status

✅ Code committed and pushed to GitHub  
✅ Code pulled to R58 device  
⏳ Service restart pending (SSH connection unstable)

## Next Steps

1. **Manual service restart required**:
   ```bash
   ssh linaro@r58.itagenten.no
   sudo systemctl restart preke-recorder
   ```

2. **Verify hardware encoder is active**:
   ```bash
   sudo journalctl -u preke-recorder --since '1 minute ago' | grep mpph264enc
   ```

3. **Test with 2 cameras** (cam1 + cam2 currently enabled):
   - Start recording
   - Monitor CPU usage (should be ~10-20% total)
   - Verify video quality

4. **Re-enable all 4 cameras** in `config.yml`:
   ```yaml
   cam0:
     enabled: true  # Change from false
   cam3:
     enabled: true  # Change from false
   ```

5. **Test 4-camera operation**:
   - Should now be stable with hardware encoding
   - CPU usage should remain under 50%

## Troubleshooting

### If mpph264enc not found:
```bash
gst-inspect-1.0 mpph264enc
```

If not available, the encoder will need to be installed or the system may need a firmware update.

### Rollback Plan

If hardware encoder causes issues, revert to software encoder:
```python
# In src/pipelines.py, change get_h264_encoder() to always use x264enc
encoder_str = f"x264enc tune=zerolatency bitrate={bitrate} speed-preset=superfast"
```

## Commit

```
commit 554b276
Migrate to hardware H.264 encoder (mpph264enc)

Replace software x264enc with Rockchip's hardware mpph264enc encoder
to dramatically reduce CPU usage and enable stable 4-camera operation.
```

## References

- [CAM2_4K_FIX.md](CAM2_4K_FIX.md) - Previous CPU optimization attempts
- [docs/improvement-ideas.md](docs/improvement-ideas.md) - Hardware encoder recommendation
- Raspberry.Ninja tests confirmed mpph264enc works on R58 hardware
