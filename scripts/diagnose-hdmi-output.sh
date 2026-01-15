#!/bin/bash
# R58 HDMI Output Diagnostic Script
# Captures display subsystem information to diagnose HDMI + USB-C freeze issue

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
section() { echo -e "\n${BLUE}=== $1 ===${NC}\n"; }

TIMESTAMP=$(date +%Y-%m-%d_%H%M%S)
OUTPUT_FILE="/tmp/r58-hdmi-diagnostics-${TIMESTAMP}.txt"

info "R58 HDMI Output Diagnostic Tool"
info "Output will be saved to: $OUTPUT_FILE"
echo ""

# Redirect all output to both console and file
exec > >(tee -a "$OUTPUT_FILE") 2>&1

section "System Information"
echo "Date: $(date)"
echo "Hostname: $(hostname)"
echo "Kernel: $(uname -r)"
echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
echo ""

section "Display Subsystem Summary"
if [ -f /sys/kernel/debug/dri/0/summary ]; then
    cat /sys/kernel/debug/dri/0/summary
else
    warn "DRM debug summary not available (requires debugfs)"
    warn "Try: sudo mount -t debugfs none /sys/kernel/debug"
fi

section "Connected Display Connectors"
if [ -d /sys/class/drm ]; then
    for conn in /sys/class/drm/card*-*; do
        if [ -d "$conn" ]; then
            connector=$(basename "$conn")
            status=$(cat "$conn/status" 2>/dev/null || echo "unknown")
            enabled=$(cat "$conn/enabled" 2>/dev/null || echo "unknown")
            dpms=$(cat "$conn/dpms" 2>/dev/null || echo "unknown")
            
            echo "Connector: $connector"
            echo "  Status: $status"
            echo "  Enabled: $enabled"
            echo "  DPMS: $dpms"
            
            if [ "$status" = "connected" ]; then
                echo "  Modes:"
                cat "$conn/modes" 2>/dev/null | head -5 | sed 's/^/    /'
            fi
            echo ""
        fi
    done
else
    error "DRM subsystem not found"
fi

section "Device Tree Display Nodes"
echo "HDMI nodes:"
ls -d /proc/device-tree/*hdmi* 2>/dev/null || echo "  None found"
echo ""

echo "DisplayPort nodes:"
ls -d /proc/device-tree/*dp* 2>/dev/null || echo "  None found"
echo ""

echo "DSI/MIPI nodes:"
ls -d /proc/device-tree/*dsi* 2>/dev/null || echo "  None found"
echo ""

echo "VOP nodes:"
ls -d /proc/device-tree/*vop* 2>/dev/null || echo "  None found"
echo ""

section "Video Port (VP) Endpoint Configuration"
for vp in /proc/device-tree/*vop*/port@* 2>/dev/null; do
    if [ -d "$vp" ]; then
        echo "VP: $(basename $(dirname $vp))/$(basename $vp)"
        ls "$vp/" 2>/dev/null | sed 's/^/  /'
        echo ""
    fi
done

section "USB-C / Type-C Status"
if [ -d /sys/kernel/debug/usb ]; then
    for typec in /sys/kernel/debug/usb/typec* 2>/dev/null; do
        if [ -f "$typec" ]; then
            echo "Type-C port: $(basename $typec)"
            cat "$typec" 2>/dev/null | head -20
            echo ""
        fi
    done
else
    warn "USB debug info not available"
fi

section "USB Devices (for DisplayLink detection)"
lsusb 2>/dev/null || warn "lsusb not available"
echo ""

echo "DisplayLink/EVDI kernel modules:"
lsmod | grep -E "udl|evdi|displaylink" || echo "  None loaded"
echo ""

section "Kernel Messages - Display Related (last 100 lines)"
dmesg | grep -iE "hdmi|dp|vop|drm|display" | tail -100

section "DRM Device Information"
if command -v modetest >/dev/null 2>&1; then
    modetest -M rockchip 2>/dev/null || warn "modetest failed"
else
    warn "modetest not installed (install libdrm-tests for detailed info)"
fi

section "Framebuffer Devices"
ls -la /dev/fb* 2>/dev/null || echo "No framebuffer devices found"

section "Diagnostic Complete"
info "Diagnostics saved to: $OUTPUT_FILE"
info ""
info "Next steps:"
info "1. Check Mekotronics website for firmware updates"
info "2. If issue persists, send this file to support@mekotronics.com"
info "3. Include description: 'Device freezes when HDMI output + USB-C display connected'"
