#!/bin/bash
# Install VDO.ninja Bridge Service
# Run this script on R58 to install the auto-start service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/vdoninja-bridge.service"
BRIDGE_SCRIPT="$SCRIPT_DIR/start-vdoninja-bridge.sh"

echo "Installing VDO.ninja Bridge Service..."

# Make scripts executable
chmod +x "$BRIDGE_SCRIPT"

# Copy service file
sudo cp "$SERVICE_FILE" /etc/systemd/system/vdoninja-bridge.service

# Create log file
sudo touch /var/log/vdoninja-bridge.log
sudo chown linaro:linaro /var/log/vdoninja-bridge.log

# Reload systemd
sudo systemctl daemon-reload

# Enable the service
sudo systemctl enable vdoninja-bridge.service

echo ""
echo "=========================================="
echo "VDO.ninja Bridge Service Installed!"
echo "=========================================="
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start vdoninja-bridge"
echo "  Stop:    sudo systemctl stop vdoninja-bridge"
echo "  Status:  sudo systemctl status vdoninja-bridge"
echo "  Logs:    journalctl -u vdoninja-bridge -f"
echo "           tail -f /var/log/vdoninja-bridge.log"
echo ""
echo "The service will auto-start on boot after the graphical environment is ready."
echo ""
echo "Configuration (edit /etc/systemd/system/vdoninja-bridge.service):"
echo "  VDONINJA_ROOM=r58studio"
echo "  CAMERA_LABEL=HDMI-Camera"
echo "  CAMERA_PUSH_ID=hdmicam"
echo ""

