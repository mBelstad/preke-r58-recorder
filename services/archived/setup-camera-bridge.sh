#!/bin/bash
# Setup script for R58 Camera Bridge service
# Run this on the R58 device to install and enable the bridge service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/r58-camera-bridge.service"
SERVICE_NAME="r58-camera-bridge"

echo "=== R58 Camera Bridge Setup ==="
echo ""

# Check if running on R58
if [[ ! -d /opt/preke-r58-recorder ]]; then
    echo "WARNING: /opt/preke-r58-recorder not found. Are you running this on R58?"
    echo ""
fi

# Check for chromium
if ! command -v chromium-browser &> /dev/null; then
    echo "ERROR: chromium-browser not found. Install with:"
    echo "  sudo apt install chromium-browser"
    exit 1
fi

# Copy service file
echo "Installing systemd service..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start service
echo "Enabling $SERVICE_NAME service..."
sudo systemctl enable $SERVICE_NAME

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Commands:"
echo "  Start:   sudo systemctl start $SERVICE_NAME"
echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
echo "  Status:  sudo systemctl status $SERVICE_NAME"
echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "The bridge will start automatically on boot."
echo "To start now, run: sudo systemctl start $SERVICE_NAME"

