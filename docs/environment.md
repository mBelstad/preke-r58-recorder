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

- HDMI receiver: `/dev/video60`, symlinked from `/dev/v4l/by-path/platform-fdee0000.hdmirx-controller-video-index0`. This is currently the only tested HDMI input (cam0).
- `/dev/video0-32`: `rkcif-mipi-lvds*` capture blocks (CSI/MIPI). They are unused until sensors are connected, so referencing them in config will not yield a signal.
- `/dev/video33-59`: ISP virtual paths; not required for HDMI ingest unless we later chain through rkisp processing.

## Deployment Considerations

- Password-based SSH is the default for the lab unit. Export `R58_PASSWORD` on your workstation and ensure `sshpass` is installed so `deploy.sh` can authenticate.
- System Python lives under `/opt/preke-r58-recorder/venv`. Keeping GI packages in the base OS avoids long pip/meson builds on this limited hardware.


