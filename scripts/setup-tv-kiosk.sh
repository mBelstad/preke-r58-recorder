#!/bin/bash
# Setup TV Kiosk and VDO.ninja Bridge Services
# This script installs and enables the services that:
# 1. Show the QR page on the TV in fullscreen kiosk mode
# 2. Run VDO.ninja bridge in the background (off-screen)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "Preke TV Kiosk Setup"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x "$PROJECT_DIR/scripts/preke-tv-kiosk.sh"
chmod +x "$PROJECT_DIR/scripts/start-vdoninja-bridge.sh"

# Copy service files
echo "Installing systemd service files..."
cp "$PROJECT_DIR/services/preke-tv-kiosk.service" /etc/systemd/system/
cp "$PROJECT_DIR/scripts/vdoninja-bridge.service" /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable TV kiosk service (starts on boot)
echo "Enabling preke-tv-kiosk service..."
systemctl enable preke-tv-kiosk.service

# Enable VDO.ninja bridge service (starts on boot, runs in background)
echo "Enabling vdoninja-bridge service..."
systemctl enable vdoninja-bridge.service

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Services installed:"
echo "  - preke-tv-kiosk.service: Shows QR page on TV in fullscreen"
echo "  - vdoninja-bridge.service: Runs VDO.ninja bridge in background"
echo ""
echo "On next boot, the TV will show the QR page."
echo "VDO.ninja bridge runs in the background (off-screen)."
echo ""
echo "To start now (without reboot):"
echo "  sudo systemctl start vdoninja-bridge"
echo "  sudo systemctl start preke-tv-kiosk"
echo ""
echo "To check status:"
echo "  sudo systemctl status preke-tv-kiosk"
echo "  sudo systemctl status vdoninja-bridge"
echo ""
echo "To view logs:"
echo "  journalctl -u preke-tv-kiosk -f"
echo "  journalctl -u vdoninja-bridge -f"
echo "  cat /var/log/preke-tv-kiosk.log"
echo "  cat /var/log/vdoninja-bridge.log"
