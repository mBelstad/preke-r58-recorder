# Fix & Incident Log

## 2025-11-27 — HDMI “No Signal” on Preview

- **Symptom**: UI showed “No signal” for all four HDMI previews. MediaMTX logs reported `no one is publishing to path 'cam*_preview'` even though FastAPI/status said `preview`.
- **Root cause**: The HDMI source pipelines in `src/pipelines.py` forced `NV24` caps for `/dev/video60` (rk_hdmirx). Current R58 firmware only exposes `NV16` at 1080p, so every `TRY_FMT` failed before frames were produced.
- **Fix**: Changed both the recording and preview builders to request `NV16` before converting to `NV12`. Validated by manually pushing the HDMI feed with `gst-launch-1.0 … format=NV16 … rtmpsink location=rtmp://127.0.0.1:1935/cam0_preview`, which succeeded and populated the HLS playlist.
- **Operational notes**:
  - If you run manual `gst-launch` tests, stop them afterwards so `/dev/video60` isn’t held by a stray process.
  - When encountering “No signal,” check `sudo lsof /dev/video60`, `journalctl -u preke-recorder.service`, and MediaMTX logs for `TRY_FMT` or “no one is publishing” hints.
  - Cameras under test: 3× Blackmagic Design Studio Camera 4K Plus G2/Pro over HDMI (HD format). Ensure they output supported modes (1080p59.94/60).
- **Current device map** (Debian 12 / kernel 6.1.99 on Mekotronics R58 4x4 3S):
  - `/dev/video60` (`/dev/v4l/by-path/platform-fdee0000.hdmirx-controller-video-index0`) is the only active HDMI input (rk_hdmirx). This feeds `cam0`.
  - `/dev/video0-32` belong to three `rkcif-mipi-lvds*` capture blocks. Nothing is presently wired there, so our `cam1-3` previews stay idle until hardware is connected.
  - Additional ISP virtual nodes `/dev/video33-59` exist but are not required unless we use the MIPI sensors.
- **Verification**:
  - `curl http://192.168.1.25:8000/preview/start-all` — API reports every camera in `preview`; only HDMI `/dev/video60` (cam0) currently has an active signal because the other inputs aren’t populated yet.
  - `curl http://192.168.1.25:8888/cam0_preview/index.m3u8` returns HTTP 200 and a multi-variant playlist.
  - Manual `gst-launch-1.0 … format=NV16 … rtmpsink … cam0_preview` confirmed MediaMTX logging `is publishing to path 'cam0_preview'`.

### Hard stops to watch

- **Single HDMI receiver exposed as `/dev/video60`**: Without external switching, only one HDMI program feed is available. Additional `/dev/video*` nodes are MIPI CSI interfaces that currently lack connected sensors; requesting them in config will hang pipelines.
- **PyGObject via pip fails**: `pip install PyGObject` errors because `girepository-2.0.pc` isn’t shipped in the vendor image. Use Debian packages instead (`sudo apt install python3-gi gobject-introspection libgirepository1.0-dev`) and skip PyPI installs on-device.
- **Manual gst-launch leftovers**: Any foreground `gst-launch-1.0 v4l2src device=/dev/video60 …` holds the device and causes `TRY_FMT` failures for the recorder. Always Ctrl+C such tests.
- **Passworded SSH deploys**: `deploy.sh` now respects `R58_PASSWORD`, but deployments will still fail unless `sshpass` is available locally or SSH keys are configured.

## 2025-11-27 — Hardware Investigation: Four Camera Support

- **Investigation**: Attempted to enable all four HDMI inputs as advertised in "4x 4K 60p" marketing.
- **Finding**: The RK3588 SoC has only **ONE** HDMI RX controller in hardware (`fdee0000.hdmirx-controller` → `/dev/video60`). The "4x 4K 60p" claim does NOT mean 4 separate HDMI inputs.
- **Hardware Reality**:
  - Single HDMI RX: `/dev/video60` (rk_hdmirx) - only built-in HDMI input
  - HDMI TX: `fde80000.hdmi` (display output, not capture)
  - MIPI/CSI: `/dev/video0-32` (require camera modules, not HDMI)
  - ISP virtual: `/dev/video33-59` (image processing, not capture)
- **Solution Implemented**:
  - Created `src/device_detection.py` to identify device types (hdmirx, usb, mipi, isp)
  - Updated `src/pipelines.py` to handle USB capture devices differently from hdmirx
  - USB devices use format negotiation (let v4l2src auto-detect) vs. hdmirx which requires NV16
  - Added device detection utilities for automatic camera mapping
- **Recommendations for 4-Camera Setup**:
  - **Option 1 (Recommended)**: Use USB 3.0 HDMI capture devices for cam1-3
    - Connect 3 additional USB capture devices
    - They will appear as `/dev/video*` devices
    - Code automatically detects and handles USB devices
    - Limitations: USB 3.0 may limit to 4K 30p or 1080p 60p per device
  - **Option 2**: Use PCIe HDMI capture cards (if slots available)
    - Higher bandwidth than USB
    - Requires kernel drivers for specific cards
  - **Option 3**: Use MIPI camera modules (if HDMI not required)
    - Connect to CSI interfaces
    - Use `/dev/video0-32` for MIPI cameras
- **Documentation**:
  - Created `docs/hardware-investigation.md` with detailed findings
  - Updated `docs/environment.md` with hardware limitations
  - Device detection utilities ready for USB device testing


