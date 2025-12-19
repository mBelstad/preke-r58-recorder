#!/bin/bash
# Preke R58 Headless Deployment Script
# This script sets up the R58 for headless operation with Preke Studio

set -e

echo "================================================"
echo "Preke R58 Headless Setup"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}Please do not run as root${NC}"
   exit 1
fi

# Function to print status
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

# Check if we're on R58
if [ ! -f /proc/device-tree/model ] || ! grep -q "RK3588" /proc/device-tree/model 2>/dev/null; then
    print_error "This script should be run on an R58 device (RK3588)"
    print_info "Detected system: $(uname -a)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
print_info "This script will install and configure:"
print_info "  1. R58 Recorder (HTTP API on port 5000)"
print_info "  2. VDO.Ninja (Self-hosted on port 8443)"
print_info "  3. MediaMTX (RTSP/RTMP/SRT streaming)"
print_info "  4. Cloudflared (Optional - for remote access)"
echo ""

read -p "Continue with installation? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Update system
print_info "Updating system packages..."
sudo apt-get update

# Install system dependencies
print_status "Installing system dependencies..."
sudo apt-get install -y \
    python3-pip python3-venv \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    python3-gi python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    git curl wget

# Install Node.js
print_status "Installing Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Setup R58 Recorder
print_status "Setting up R58 Recorder..."
RECORDER_DIR="/opt/preke-r58-recorder"
if [ ! -d "$RECORDER_DIR" ]; then
    sudo mkdir -p "$RECORDER_DIR"
    sudo chown $USER:$USER "$RECORDER_DIR"
fi

# If we're in the repo, copy files
if [ -f "$(pwd)/requirements.txt" ]; then
    print_info "Copying files to $RECORDER_DIR..."
    rsync -av --exclude='.git' --exclude='venv' --exclude='__pycache__' . "$RECORDER_DIR/"
fi

cd "$RECORDER_DIR"

# Setup Python environment
print_status "Setting up Python environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install R58 Recorder service
print_status "Installing R58 Recorder systemd service..."
sudo cp preke-recorder.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable preke-recorder.service

# Setup VDO.Ninja
print_status "Setting up VDO.Ninja..."
VDO_DIR="/opt/vdo.ninja"
if [ ! -d "$VDO_DIR" ]; then
    cd /opt
    sudo git clone https://github.com/steveseguin/vdo.ninja.git
    sudo chown -R $USER:$USER vdo.ninja
    cd vdo.ninja
    npm install
fi

cd "$VDO_DIR"

# Create SSL certificates
print_status "Creating SSL certificates for VDO.Ninja..."
mkdir -p ssl
if [ ! -f "ssl/cert.pem" ]; then
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes \
        -subj "/C=NO/ST=Oslo/L=Oslo/O=Preke/CN=r58.local"
fi

# Create VDO.Ninja systemd service
print_status "Installing VDO.Ninja systemd service..."
sudo tee /etc/systemd/system/vdo-ninja.service > /dev/null <<EOF
[Unit]
Description=VDO.Ninja Self-hosted
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$VDO_DIR
Environment="NODE_ENV=production"
ExecStart=/usr/bin/node server.js --port 8443 --ssl-cert ssl/cert.pem --ssl-key ssl/key.pem
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vdo-ninja.service

# Setup MediaMTX
print_status "Setting up MediaMTX..."
MEDIAMTX_DIR="/opt/mediamtx"
if [ ! -d "$MEDIAMTX_DIR" ]; then
    cd /opt
    
    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ]; then
        MEDIAMTX_ARCH="arm64v8"
    elif [ "$ARCH" = "armv7l" ]; then
        MEDIAMTX_ARCH="armv7"
    else
        MEDIAMTX_ARCH="amd64"
    fi
    
    print_info "Downloading MediaMTX for $MEDIAMTX_ARCH..."
    sudo wget -q https://github.com/bluenviron/mediamtx/releases/download/v1.5.0/mediamtx_v1.5.0_linux_${MEDIAMTX_ARCH}.tar.gz
    sudo tar -xzf mediamtx_v1.5.0_linux_${MEDIAMTX_ARCH}.tar.gz
    sudo mkdir -p "$MEDIAMTX_DIR"
    sudo mv mediamtx "$MEDIAMTX_DIR/"
    sudo mv mediamtx.yml "$MEDIAMTX_DIR/"
    sudo rm mediamtx_v1.5.0_linux_${MEDIAMTX_ARCH}.tar.gz
fi

# Configure MediaMTX
print_status "Configuring MediaMTX..."
sudo tee "$MEDIAMTX_DIR/mediamtx.yml" > /dev/null <<'EOF'
# MediaMTX Configuration for R58

api: yes
apiAddress: 127.0.0.1:9997

rtspAddress: :8554
protocols: [tcp]
encryption: no

rtmp: yes
rtmpAddress: :1935

hls: yes
hlsAddress: :8888

webrtc: yes
webrtcAddress: :8889

srt: yes
srtAddress: :8890

paths:
  all:
    source: publisher
  cam0:
    source: publisher
  cam1:
    source: publisher
  cam2:
    source: publisher
  cam3:
    source: publisher
  mixer:
    source: publisher
EOF

# Install MediaMTX service
print_status "Installing MediaMTX systemd service..."
sudo cp "$RECORDER_DIR/mediamtx.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mediamtx.service

# Start all services
print_status "Starting services..."
sudo systemctl start preke-recorder.service
sudo systemctl start vdo-ninja.service
sudo systemctl start mediamtx.service

# Wait a moment for services to start
sleep 3

# Check service status
echo ""
echo "================================================"
echo "Service Status"
echo "================================================"
echo ""

check_service() {
    SERVICE=$1
    if systemctl is-active --quiet $SERVICE; then
        print_status "$SERVICE is running"
    else
        print_error "$SERVICE failed to start"
        sudo journalctl -u $SERVICE -n 20 --no-pager
    fi
}

check_service "preke-recorder.service"
check_service "vdo-ninja.service"
check_service "mediamtx.service"

# Get IP address
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "================================================"
echo "Installation Complete!"
echo "================================================"
echo ""
print_status "R58 Recorder: http://$IP:5000"
print_status "VDO.Ninja: https://$IP:8443"
print_status "MediaMTX RTSP: rtsp://$IP:8554"
print_status "MediaMTX RTMP: rtmp://$IP:1935"
print_status "MediaMTX HLS: http://$IP:8888"
echo ""

# Test endpoints
print_info "Testing endpoints..."
echo ""

if curl -s http://localhost:5000/api/status > /dev/null; then
    print_status "R58 Recorder API is responding"
else
    print_error "R58 Recorder API is not responding"
fi

if curl -k -s https://localhost:8443 > /dev/null; then
    print_status "VDO.Ninja is responding"
else
    print_error "VDO.Ninja is not responding"
fi

if curl -s http://localhost:9997/v3/config/get > /dev/null; then
    print_status "MediaMTX API is responding"
else
    print_error "MediaMTX API is not responding"
fi

echo ""
print_info "Next steps:"
echo "  1. Configure Cloudflare tunnel for remote access (optional)"
echo "  2. Edit $RECORDER_DIR/config.yml for camera settings"
echo "  3. Open Preke Studio app and connect to: $IP"
echo ""
print_info "View logs:"
echo "  sudo journalctl -u preke-recorder.service -f"
echo "  sudo journalctl -u vdo-ninja.service -f"
echo "  sudo journalctl -u mediamtx.service -f"
echo ""
print_info "Restart services:"
echo "  sudo systemctl restart preke-recorder.service"
echo "  sudo systemctl restart vdo-ninja.service"
echo "  sudo systemctl restart mediamtx.service"
echo ""

print_status "Headless setup complete!"

