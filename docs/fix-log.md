# Fix & Incident Log

## 2025-11-27 — HDMI “No Signal” on Preview

- **Symptom**: UI showed “No signal” for all four HDMI previews. MediaMTX logs reported `no one is publishing to path 'cam*_preview'` even though FastAPI/status said `preview`.
- **Root cause**: The HDMI source pipelines in `src/pipelines.py` forced `NV24` caps for `/dev/video60` (rk_hdmirx). Current R58 firmware only exposes `NV16` at 1080p, so every `TRY_FMT` failed before frames were produced.
- **Fix**: Changed both the recording and preview builders to request `NV16` before converting to `NV12`. Validated by manually pushing the HDMI feed with `gst-launch-1.0 … format=NV16 … rtmpsink location=rtmp://127.0.0.1:1935/cam0_preview`, which succeeded and populated the HLS playlist.
- **Operational notes**:
  - If you run manual `gst-launch` tests, stop them afterwards so `/dev/video60` isn’t held by a stray process.
  - When encountering “No signal,” check `sudo lsof /dev/video60`, `journalctl -u preke-recorder.service`, and MediaMTX logs for `TRY_FMT` or “no one is publishing” hints.
  - Cameras under test: 3× Blackmagic Design Studio Camera 4K Plus G2/Pro over HDMI (HD format). Ensure they output supported modes (1080p59.94/60).
- **Verification**:
  - `curl http://192.168.1.25:8000/preview/start-all` — all cameras report `preview`.
  - `curl http://192.168.1.25:8888/cam0_preview/index.m3u8` (and cam1–3) — manifests now served.
  - Manual gst-launch NV16 test confirmed MediaMTX logging `is publishing to path 'cam0_preview'`.


