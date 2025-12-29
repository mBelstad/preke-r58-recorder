#!/bin/bash
# Install the r58-pipeline systemd service
# Run on the R58 device

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Installing R58 Pipeline Manager Service ==="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# IMPORTANT: Service now uses /opt/preke-r58-recorder directly
# This avoids the symlink confusion that caused stale code issues
echo "Creating directories..."
mkdir -p /opt/preke-r58-recorder/recordings
mkdir -p /run/r58
chown -R linaro:linaro /opt/preke-r58-recorder/recordings
chown -R linaro:linaro /run/r58

# Update symlink for backwards compatibility
echo "Updating symlink for backwards compatibility..."
rm -f /opt/r58-app/current 2>/dev/null || true
mkdir -p /opt/r58-app
ln -sf /opt/preke-r58-recorder /opt/r58-app/current

# Copy service file
echo "Installing systemd service..."
cp "$PROJECT_ROOT/systemd/r58-pipeline.service" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start the service
echo "Enabling and starting service..."
systemctl enable r58-pipeline.service
systemctl restart r58-pipeline.service

# Wait for it to start
sleep 2

# Check status
echo ""
echo "=== Service Status ==="
systemctl status r58-pipeline.service --no-pager || true

echo ""
echo "Pipeline manager installed!"
echo "Socket available at: /run/r58/pipeline.sock"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status r58-pipeline"
echo "  sudo journalctl -u r58-pipeline -f"
