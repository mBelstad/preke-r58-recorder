#!/bin/bash
# Configure all displays on R58 device
# This script runs at X session start via /etc/xdg/autostart/enable-hdmi.desktop
#
# Display configuration:
#   - DP-1 (USB-C touchscreen): Primary display at 1920x1080
#   - HDMI-1 (TV output): Mirrored with DP-1 at 1920x1080
#   - DSI-1 (3-inch front panel): Separate display
#   - DSI-2: Disabled (conflicts with DP-1 USB-C connection)

export DISPLAY=:0

# Wait for X to be ready
for i in {1..30}; do
    if xrandr &>/dev/null; then
        break
    fi
    sleep 1
done

echo "Configuring R58 displays..."

# Disable DSI-2 (conflicts with USB-C DisplayPort)
xrandr --output DSI-2 --off 2>/dev/null

# Configure HDMI output
if xrandr | grep -q 'HDMI-1 connected'; then
    xrandr --output HDMI-1 --set 'output_hdmi_dvi' 'force_hdmi' 2>/dev/null
    xrandr --output HDMI-1 --set 'Colorspace' 'Default' 2>/dev/null
    xrandr --output HDMI-1 --mode 1920x1080 --pos 0x0
    echo "HDMI-1 enabled at 1920x1080"
fi

# Configure USB-C touchscreen (DP-1) - mirror with HDMI
if xrandr | grep -q 'DP-1 connected'; then
    xrandr --output DP-1 --mode 1920x1080 --same-as HDMI-1
    echo "DP-1 mirrored with HDMI-1"
    
    # Map touchscreen to DP-1
    if xinput list | grep -q 'ELAN Touchscreen'; then
        xinput map-to-output 'ELAN Touchscreen' DP-1
        echo "Touch mapped to DP-1"
    fi
fi

# Configure front panel (DSI-1)
if xrandr | grep -q 'DSI-1 connected'; then
    xrandr --output DSI-1 --auto --rotate left --pos 1920x0
    echo "DSI-1 (front panel) enabled"
fi

echo "Display configuration complete"
