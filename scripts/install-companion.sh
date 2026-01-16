#!/bin/bash
# Install Bitfocus Companion on R58 device
# This allows Stream Deck to connect directly to the device

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Installing Bitfocus Companion on R58 Device ==="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed. Please install Node.js 20+ first."
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 20 ]; then
    echo "ERROR: Node.js 20+ is required. Found version: $(node --version)"
    exit 1
fi

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# Create Companion directory
COMPANION_DIR="/opt/companion"
echo "Creating Companion directory at $COMPANION_DIR..."
mkdir -p "$COMPANION_DIR"
chown -R linaro:linaro "$COMPANION_DIR"

# Clone or update Companion
cd "$COMPANION_DIR"
if [ -d "companion" ]; then
    echo "Companion directory exists, updating..."
    cd companion
    sudo -u linaro git pull origin main || echo "Warning: Could not update, continuing..."
else
    echo "Cloning Companion repository..."
    sudo -u linaro git clone https://github.com/bitfocus/companion.git
    cd companion
fi

# Install dependencies
echo "Installing Companion dependencies (this may take a while)..."
sudo -u linaro npm install

# Build Companion
echo "Building Companion..."
sudo -u linaro npm run build

# Create systemd service
echo "Creating systemd service..."
# Note: Companion uses port 8000 by default, but R58 API also uses 8000
# We'll configure Companion to use port 8080 instead
cat > /etc/systemd/system/companion.service << 'EOF'
[Unit]
Description=Bitfocus Companion
After=network.target preke-recorder.service

[Service]
Type=simple
User=linaro
Group=linaro
WorkingDirectory=/opt/companion/companion
Environment=NODE_ENV=production
Environment=COMPANION_CONFIG_DIR=/opt/companion/config
Environment=HTTP_PORT=8080
Environment=HTTP_LISTEN_ADDRESS=0.0.0.0
ExecStart=/usr/bin/node dist/companion.js
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create config directory
mkdir -p /opt/companion/config
chown -R linaro:linaro /opt/companion/config

# Reload systemd
systemctl daemon-reload

# Enable and start Companion
echo "Enabling and starting Companion service..."
systemctl enable companion.service
systemctl restart companion.service

# Wait for it to start
sleep 3

# Check status
echo ""
echo "=== Companion Service Status ==="
systemctl status companion.service --no-pager || true

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Companion is now running on:"
echo "  - Web UI: http://localhost:8080 (on device)"
echo "  - Web UI: https://app.itagenten.no:8080 (via FRP tunnel)"
echo ""
echo "To access Companion from a PC:"
echo "  1. Open browser to: https://app.itagenten.no:8080"
echo "  2. Or use the device's local IP: http://<device-ip>:8080"
echo ""
echo "Note: Companion uses port 8080 to avoid conflict with R58 API (port 8000)"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status companion"
echo "  sudo journalctl -u companion -f"
echo "  sudo systemctl restart companion"
echo ""
echo "Next steps:"
echo "  1. Open Companion web UI"
echo "  2. Add HTTP instance pointing to: https://app.itagenten.no"
echo "  3. Configure camera control buttons (see docs/COMPANION_PROFESSIONAL_SETUP.md)"
echo "  4. Connect Stream Deck to Companion"
