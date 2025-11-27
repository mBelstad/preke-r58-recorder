# Mekotronics R58 4x4 3S Environment Notes

## Base OS

- `PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"` with a vendor kernel `6.1.99 #1 SMP Thu Oct 23 14:54:47 CST 2025 aarch64 GNU/Linux`.
- Build metadata shows `RK_BUILD_INFO="root@blueberry Fri Oct 24 18:38:55 CST 2025"`, indicating Mekotronics’ customized Debian image.

## GObject Introspection / PyGObject

The vendor image already ships the Debian packages we need for GI bindings:

```bash
sudo apt-get update
sudo apt-get install -y python3-gi gobject-introspection libgirepository1.0-dev
```

- `python3-gi` 3.42.2 provides the Python bindings. Importers should prefer this over pip wheels.
- `gobject-introspection` / `libgirepository1.0-dev` install the GI scanner and headers, but they still **do not** provide a `girepository-2.0.pc` file. Pip’s `PyGObject` build therefore fails; rely on the distro packages instead of compiling from source on-device.
- Update `requirements.txt` or deployment docs to avoid invoking `pip install PyGObject` on the R58; treat GI as a system dependency handled via apt.

## Video Device Overview

### HDMI Inputs

**CRITICAL FINDING**: The RK3588 SoC has only **ONE** HDMI RX controller in hardware.

- **Single HDMI RX Controller**: `/dev/video60`
  - Device name: `stream_hdmirx`
  - Controller: `fdee0000.hdmirx-controller`
  - Format: NV16 (4:2:2) at 1080p 60fps
  - Symlink: `/dev/v4l/by-path/platform-fdee0000.hdmirx-controller-video-index0`
  - **This is the ONLY built-in HDMI input available**

**Important**: The "4x 4K 60p" marketing claim does NOT mean 4 separate HDMI inputs. It likely refers to:
- 4K 60p recording capability (not 4 inputs)
- 4 simultaneous recording streams (requires external capture devices)
- 4K resolution support (not 4 inputs)

### Other Video Devices

- `/dev/video0-32`: `rkcif-mipi-lvds*` capture blocks (CSI/MIPI). They are unused until sensors are connected, so referencing them in config will not yield a signal.
- `/dev/video33-59`: ISP virtual paths; not required for HDMI ingest unless we later chain through rkisp processing.

### USB Capture Devices (For Additional HDMI Inputs)

To achieve 4 simultaneous HDMI inputs, you need **USB 3.0 HDMI capture devices**:
- Connect USB capture devices (e.g., Elgato Cam Link, Magewell USB Capture)
- They will appear as additional `/dev/video*` devices
- Use `src/device_detection.py` to identify USB capture devices
- The pipeline code automatically handles USB devices differently from hdmirx

**Limitations**:
- USB 3.0 bandwidth may limit to 4K 30p or 1080p 60p per device
- For true 4K 60p, consider PCIe capture cards (if PCIe slots available)

## Deployment Considerations

- Password-based SSH is the default for the lab unit. Export `R58_PASSWORD` on your workstation and ensure `sshpass` is installed so `deploy.sh` can authenticate.
- System Python lives under `/opt/preke-r58-recorder/venv`. Keeping GI packages in the base OS avoids long pip/meson builds on this limited hardware.


