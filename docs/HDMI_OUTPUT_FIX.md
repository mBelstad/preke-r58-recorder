# HDMI Output & Display Configuration - R58 4x4 3S

**Date**: January 15, 2026  
**Device**: Mekotronics R58-4x4 3S (RK3588)  
**Status**: **FIXED**

---

## Working Configuration

The R58 now supports simultaneous operation of:

| Display | Connector | Resolution | Notes |
|---------|-----------|------------|-------|
| USB-C Touchscreen | DP-1 | 1920x1080 | Primary, touch enabled |
| HDMI TV Output | HDMI-1 | 1920x1080 | Mirrored with DP-1 |
| 3-inch Front Panel | DSI-1 | 480x640 | Separate display |
| DSI-2 | - | Disabled | Conflicts with USB-C DP |

---

## Problem Solved

1. **HDMI output wasn't enabled** - X wasn't configured to use it
2. **USB-C touchscreen uses DisplayPort** - Appears as DP-1, not DSI-2
3. **Touch mapping was wrong** - Had to map ELAN Touchscreen to DP-1
4. **DSI-2 caused conflicts** - Disabled to allow DP-1 to work properly

---

## Solution Applied

### Startup Script

The script `/opt/preke-r58-recorder/scripts/enable-hdmi.sh` runs at X session start and configures all displays:

```bash
# Disable DSI-2 (conflicts with USB-C DisplayPort)
xrandr --output DSI-2 --off

# Configure HDMI output
xrandr --output HDMI-1 --set 'output_hdmi_dvi' 'force_hdmi'
xrandr --output HDMI-1 --set 'Colorspace' 'Default'
xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0

# Configure USB-C touchscreen (DP-1) - mirror with HDMI
xrandr --output DP-1 --mode 1920x1080 --same-as HDMI-1

# Map touchscreen to DP-1
xinput map-to-output 'ELAN Touchscreen' DP-1

# Configure front panel (DSI-1)
xrandr --output DSI-1 --auto --rotate left --pos 1920x0
```

### Files Installed

- `/opt/preke-r58-recorder/scripts/enable-hdmi.sh` - Display configuration script
- `/etc/xdg/autostart/enable-hdmi.desktop` - Autostart at X session
- `/etc/X11/xorg.conf.d/10-displays.conf` - X11 display config

---

## Manual Configuration

If displays need to be reconfigured manually:

```bash
export DISPLAY=:0

# Disable conflicting DSI-2
xrandr --output DSI-2 --off

# Set up HDMI + USB-C mirrored at 1080p
xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0
xrandr --output DP-1 --mode 1920x1080 --same-as HDMI-1

# Map touch to correct display
xinput map-to-output 'ELAN Touchscreen' DP-1

# Enable front panel
xrandr --output DSI-1 --auto --rotate left --pos 1920x0
```

Or run the script:

```bash
/opt/preke-r58-recorder/scripts/enable-hdmi.sh
```

---

## Key Findings

### USB-C Touchscreen

The USB-C touchscreen connects via **DisplayPort Alt Mode**, appearing as `DP-1` in xrandr. It does NOT use DSI-2. The touch input device is `ELAN Touchscreen`.

### DSI-2 Conflict

When the USB-C touchscreen is connected, DSI-2 must be disabled. Otherwise:
- Both DP-1 and DSI-2 appear at position 0,0
- Touch coordinates are mapped to the wrong display
- Visual overlap causes confusion

### HDMI Settings

The HDMI output requires:
- `output_hdmi_dvi: force_hdmi` - Forces HDMI mode (not DVI auto-detect)
- `Colorspace: Default` - For TV compatibility
- Resolution: 1920x1080 works reliably

---

## Display Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     R58 4x4 3S                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  DSI-1   │    │   DP-1   │    │  HDMI-1  │              │
│  │  (Front  │    │  (USB-C  │    │   (TV    │              │
│  │  Panel)  │    │  Touch)  │    │  Output) │              │
│  │ 480x640  │    │1920x1080 │    │1920x1080 │              │
│  └──────────┘    └────┬─────┘    └────┬─────┘              │
│       │               │               │                     │
│       │               └───── MIRRORED ┘                     │
│       │                                                     │
│  Separate display              Same content                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Touch not working correctly

```bash
# Check which display touch is mapped to
xinput list-props 'ELAN Touchscreen' | grep 'Coordinate Transformation'

# Remap to DP-1
xinput map-to-output 'ELAN Touchscreen' DP-1
```

### HDMI not showing anything

```bash
# Check if HDMI is connected
xrandr | grep HDMI-1

# Force enable
xrandr --output HDMI-1 --set 'output_hdmi_dvi' 'force_hdmi'
xrandr --output HDMI-1 --mode 1920x1080
```

### Displays overlapping incorrectly

```bash
# Check current layout
xrandr --listmonitors

# Reset to known good configuration
/opt/preke-r58-recorder/scripts/enable-hdmi.sh
```

---

## References

- [Mekotronics R58-4x4 3S Product Page](https://www.mekotronics.com/h-pd-89.html)
- [RK3588 Display Documentation](https://wiki.t-firefly.com/en/ROC-RK3588-PC/usage_display.html)
