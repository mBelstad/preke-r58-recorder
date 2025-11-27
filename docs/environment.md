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

**R58 4x4 3S has FOUR dedicated HDMI input ports**, each labeled on the device:
- **HDMI N0** → `/dev/video0` (rkcif-mipi-lvds via LT6911 bridge)
- **HDMI N60** → `/dev/video60` (hdmirx direct controller)
- **HDMI N11** → `/dev/video11` (rkcif-mipi-lvds1 via LT6911 bridge)
- **HDMI N21** → `/dev/video21` (rkcif-mipi-lvds1 via LT6911 bridge)

**Hardware Architecture**:
- The RK3588 SoC has **ONE** direct HDMI RX controller (`fdee0000.hdmirx-controller` → `/dev/video60`)
- **Three additional HDMI inputs** use **LT6911UXE HDMI-to-MIPI bridge chips** that convert HDMI signals to MIPI CSI and feed into `rkcif` capture devices
- LT6911 bridges are on I2C buses: `2-002b`, `4-002b`, `7-002b`
- All four HDMI inputs support up to 4K@60Hz as advertised

**Device Details**:
- **HDMI N60** (`/dev/video60`):
  - Direct hdmirx controller
  - Format: NV16 (4:2:2) at 1080p 60fps
  - Device name: `stream_hdmirx`
  - Symlink: `/dev/v4l/by-path/platform-fdee0000.hdmirx-controller-video-index0`

- **HDMI N0, N11, N21** (`/dev/video0`, `/dev/video11`, `/dev/video21`):
  - rkcif devices receiving HDMI via LT6911 bridges
  - Format: NV16 (4:2:2) for video0 and video11, format negotiation for video21
  - Device names: `stream_cif_mipi_id0` (video0), `rkcif` (video11/video21)
  - Support same resolutions as direct hdmirx

**Configuration**:
- All four HDMI inputs are configured in `config.yml`:
  - `cam0`: `/dev/video0` (HDMI N0)
  - `cam1`: `/dev/video60` (HDMI N60)
  - `cam2`: `/dev/video11` (HDMI N11)
  - `cam3`: `/dev/video21` (HDMI N21)

### Other Video Devices

- `/dev/video1-10, video12-20, video22-32`: Additional `rkcif-mipi-lvds*` capture blocks (CSI/MIPI). Available for MIPI camera modules if needed.
- `/dev/video33-59`: ISP virtual paths; not required for HDMI ingest unless we later chain through rkisp processing.

## Deployment Considerations

- Password-based SSH is the default for the lab unit. Export `R58_PASSWORD` on your workstation and ensure `sshpass` is installed so `deploy.sh` can authenticate.
- System Python lives under `/opt/preke-r58-recorder/venv`. Keeping GI packages in the base OS avoids long pip/meson builds on this limited hardware.


