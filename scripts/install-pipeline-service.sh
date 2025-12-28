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

# Create r58 user if it doesn't exist
if ! id "r58" &>/dev/null; then
    echo "Creating r58 user..."
    useradd -r -s /bin/false -d /opt/r58 r58
fi

# Create required directories
echo "Creating directories..."
mkdir -p /opt/r58/recordings
mkdir -p /var/lib/r58
chown -R r58:r58 /opt/r58/recordings /var/lib/r58

# Copy service file
echo "Installing systemd service..."
cp "$PROJECT_ROOT/systemd/r58-pipeline.service" /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start the service
echo "Enabling and starting service..."
systemctl enable r58-pipeline.service
systemctl start r58-pipeline.service

# Check status
echo ""
echo "=== Service Status ==="
systemctl status r58-pipeline.service --no-pager

echo ""
echo "Pipeline manager installed successfully!"
echo "Socket available at: /run/r58/pipeline.sock"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status r58-pipeline"
echo "  sudo journalctl -u r58-pipeline -f"

