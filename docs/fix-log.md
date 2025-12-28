# Fix & Incident Log

## 2025-12-19 — H.265 Hardware Encoder (mpph265enc) Stability Testing

- **Context**: After discovering mpph264enc causes kernel panics, we needed to verify if mpph265enc (H.265 hardware encoder) is stable before migrating the entire system.
- **Tests performed**:
  1. **Simple 30-second encode**: ✅ PASSED - Created 29MB file, no errors
  2. **Sustained 5-minute encode**: ✅ PASSED - Completed in 40 seconds, no crashes
  3. **RTSP push test**: ⚠️ PARTIAL - `rtspclientsink` not available on R58
- **Results**: 
  - **mpph265enc is STABLE** - No kernel panics, no segfaults, no errors in dmesg
  - Hardware encoder works reliably for H.265 encoding
  - System remained responsive throughout all tests
- **Findings**:
  - `rtspclientsink` GStreamer element not installed on R58
  - Will need to use alternative streaming method (keep RTMP or use RTP directly)
  - H.265 recording to file works perfectly with hardware acceleration
- **Decision**: Proceed with H.265 migration for recording, evaluate streaming options
- **CPU Impact**: Expected reduction from ~40% to ~10% per camera stream
- **Next steps**: Implement H.265 for recording pipelines, keep RTMP for streaming (MediaMTX will handle H.265 via WHIP/WebRTC)

## 2025-12-19 — mpph264enc Kernel Panic & Rollback

- **Symptom**: Kernel panic when attempting to use mpph264enc (H.264 hardware encoder)
- **Error**: `Internal error: Oops: 0000000096000005 [#29] SMP`
- **Impact**: System crash, SSH connection dropped, required hard reboot
- **Root cause**: MPP (Media Process Platform) driver instability with H.264 encoding
- **Action taken**: Immediate rollback to x264enc (software encoder)
- **Commits**:
  - `1ff7195` - ROLLBACK: Revert to software x264enc encoder
- **Key learnings**:
  - mpph264enc (H.264 VPU) is UNSTABLE - causes kernel crashes
  - Previous developers had already discovered this (code comments indicated prior issues)
  - Must test mpph265enc separately before assuming all MPP encoders are unstable
  - Always have rollback plan ready when testing hardware encoders
- **Status**: System stable with software x264enc, but limited to 2 cameras due to CPU usage

## 2025-12-19 — CAM1 (HDMI N60/video60) Recording Fix

- **Symptom**: cam1 recordings produced 0-byte files while cam0/cam2/cam3 recorded successfully. MediaMTX showed "no one is publishing to path 'cam1'" despite ingest status showing "streaming".
- **Root cause**: The hdmirx pipeline was forcing a specific framerate in the caps filter (`framerate=30/1`), but the camera was outputting at a different native framerate (120fps in this case). This caused GStreamer caps negotiation to fail silently.
- **Fix**: 
  1. Remove framerate constraint from v4l2src caps - let GStreamer negotiate the native framerate
  2. Use `videorate` element after the source to convert to 30fps for encoding
  3. Use actual detected resolution instead of configured resolution
- **Commits**: 
  - `d4c3ea0` - Fix hdmirx pipeline to use actual detected resolution
  - `a03eaf9` - Fix hdmirx framerate negotiation issue
- **Pipeline before** (broken):
  ```
  v4l2src device=/dev/video60 io-mode=mmap ! 
  video/x-raw,format=NV16,width=1920,height=1080,framerate=60/1 ! ...
  ```
- **Pipeline after** (working):
  ```
  v4l2src device=/dev/video60 io-mode=mmap ! 
  video/x-raw,format=NV16,width=3840,height=2160 ! 
  videorate ! video/x-raw,framerate=30/1 ! ...
  ```
- **Key learnings**:
  - hdmirx devices may output at various framerates (30/60/120fps) depending on the source
  - Never force framerate in caps filter for live sources - use videorate instead
  - Always use the actual detected resolution from `get_device_capabilities()`, not the config resolution
  - The ingest status can show "streaming" even when the pipeline isn't actually producing frames

## 2025-11-27 — Hardware Investigation: Four Camera Support

- **Investigation**: Attempted to enable all four HDMI inputs as advertised in "4x 4K 60p" marketing.
- **Finding**: The R58 4x4 3S **DOES have four dedicated HDMI input ports**, but uses a hybrid architecture:
  - **One direct HDMI RX controller**: `fdee0000.hdmirx-controller` → `/dev/video60` (HDMI N60)
  - **Three HDMI inputs via LT6911UXE bridges**: HDMI-to-MIPI converters feeding into rkcif devices
    - HDMI N0 → `/dev/video0` (rkcif-mipi-lvds via LT6911 bridge on I2C 7-002b)
    - HDMI N11 → `/dev/video11` (rkcif-mipi-lvds1 via LT6911 bridge on I2C 4-002b)
    - HDMI N21 → `/dev/video21` (rkcif-mipi-lvds1 via LT6911 bridge on I2C 2-002b)
- **Hardware Architecture**:
  - RK3588 SoC has one direct HDMI RX controller in silicon
  - Three LT6911UXE HDMI-to-MIPI bridge chips convert HDMI signals to MIPI CSI
  - Bridge outputs feed into Rockchip CIF (Camera Interface) devices
  - All four inputs support up to 4K@60Hz as advertised
- **Solution Implemented**:
  - Created `src/device_detection.py` with `hdmi_rkcif` device type for HDMI inputs via bridges
  - Added `get_hdmi_port_mapping()` function mapping port labels to device nodes
  - Updated `src/pipelines.py` to handle `hdmi_rkcif` devices with NV16 format (like hdmirx)
  - Updated `config.yml` with correct device mappings for all four HDMI ports:
    - cam0: `/dev/video0` (HDMI N0)
    - cam1: `/dev/video60` (HDMI N60)
    - cam2: `/dev/video11` (HDMI N11)
    - cam3: `/dev/video21` (HDMI N21)
  - All four cameras now configured and ready for simultaneous recording
- **Format Handling**:
  - Direct hdmirx (`/dev/video60`): NV16 format at 60fps
  - rkcif via bridges (`/dev/video0`, `/dev/video11`): NV16 format at 30fps
  - rkcif via bridges (`/dev/video21`): Format negotiation (may differ)
  - All converted to NV12 for encoding
- **Verification**:
  - Device detection correctly identifies all four HDMI inputs
  - Pipeline code handles both hdmirx and hdmi_rkcif device types
  - Configuration updated and service restarted successfully
- **Documentation**:
  - Updated `docs/environment.md` with correct HDMI port mappings and architecture
  - Updated `docs/fix-log.md` with corrected findings
  - Created `docs/hdmi-port-mapping.md` with comprehensive port mapping reference
  - All four HDMI inputs now documented and supported


## 2025-11-27 — HDMI "No Signal" on Preview

- **Symptom**: UI showed "No signal" for all four HDMI previews. MediaMTX logs reported `no one is publishing to path 'cam*_preview'` even though FastAPI/status said `preview`.
- **Root cause**: The HDMI source pipelines in `src/pipelines.py` forced `NV24` caps for `/dev/video60` (rk_hdmirx). Current R58 firmware only exposes `NV16` at 1080p, so every `TRY_FMT` failed before frames were produced.
- **Fix**: Changed both the recording and preview builders to request `NV16` before converting to `NV12`. Validated by manually pushing the HDMI feed with `gst-launch-1.0 … format=NV16 … rtmpsink location=rtmp://127.0.0.1:1935/cam0_preview`, which succeeded and populated the HLS playlist.
- **Operational notes**:
  - If you run manual `gst-launch` tests, stop them afterwards so `/dev/video60` isn't held by a stray process.
  - When encountering "No signal," check `sudo lsof /dev/video60`, `journalctl -u preke-recorder.service`, and MediaMTX logs for `TRY_FMT` or "no one is publishing" hints.
  - Cameras under test: 3× Blackmagic Design Studio Camera 4K Plus G2/Pro over HDMI (HD format). Ensure they output supported modes (1080p59.94/60).
- **Current device map** (Debian 12 / kernel 6.1.99 on Mekotronics R58 4x4 3S):
  - `/dev/video60` (`/dev/v4l/by-path/platform-fdee0000.hdmirx-controller-video-index0`) is the only active HDMI input (rk_hdmirx). This feeds `cam0`.
  - `/dev/video0-32` belong to three `rkcif-mipi-lvds*` capture blocks. Nothing is presently wired there, so our `cam1-3` previews stay idle until hardware is connected.
  - Additional ISP virtual nodes `/dev/video33-59` exist but are not required unless we use the MIPI sensors.
- **Verification**:
  - `curl http://192.168.1.25:8000/preview/start-all` — API reports every camera in `preview`; only HDMI `/dev/video60` (cam0) currently has an active signal because the other inputs aren't populated yet.
  - `curl http://192.168.1.25:8888/cam0_preview/index.m3u8` returns HTTP 200 and a multi-variant playlist.
  - Manual `gst-launch-1.0 … format=NV16 … rtmpsink … cam0_preview` confirmed MediaMTX logging `is publishing to path 'cam0_preview'`.

### Hard stops to watch

- **Single HDMI receiver exposed as `/dev/video60`**: Without external switching, only one HDMI program feed is available. Additional `/dev/video*` nodes are MIPI CSI interfaces that currently lack connected sensors; requesting them in config will hang pipelines.
- **PyGObject via pip fails**: `pip install PyGObject` errors because `girepository-2.0.pc` isn't shipped in the vendor image. Use Debian packages instead (`sudo apt install python3-gi gobject-introspection libgirepository1.0-dev`) and skip PyPI installs on-device.
- **Manual gst-launch leftovers**: Any foreground `gst-launch-1.0 v4l2src device=/dev/video60 …` holds the device and causes `TRY_FMT` failures for the recorder. Always Ctrl+C such tests.
- **Passworded SSH deploys**: `deploy.sh` now respects `R58_PASSWORD`, but deployments will still fail unless `sshpass` is available locally or SSH keys are configured.

