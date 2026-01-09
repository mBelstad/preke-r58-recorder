#!/bin/bash
# Deploy PWA to Raspberry Pi as Kiosk
# Usage: ./deploy-raspberry-pi-kiosk.sh [PI_IP] [R58_IP]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
PI_USER="${PI_USER:-marius}"
PI_PASSWORD="${PI_PASSWORD:-Famalive94}"
PI_IP="${1:-${PI_IP:-100.107.248.29}}"
R58_IP="${2:-${R58_IP:-192.168.1.24}}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}"
echo "======================================"
echo "Raspberry Pi Kiosk PWA Deployment"
echo "======================================"
echo -e "${NC}"
echo -e "${BLUE}Configuration:${NC}"
echo "  Pi IP: $PI_IP"
echo "  R58 IP: $R58_IP"
echo "  Pi User: $PI_USER"
echo ""

# Check sshpass
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}sshpass not found. Installing...${NC}"
    if command -v brew &> /dev/null; then
        brew install hudochenkov/sshpass/sshpass
    else
        echo -e "${RED}Error: sshpass is required${NC}"
        exit 1
    fi
fi

# Test connection first
echo -e "${YELLOW}Testing SSH connection...${NC}"
if ! sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$PI_USER@$PI_IP" "echo 'Connection test successful'" &>/dev/null; then
    echo -e "${RED}Error: Cannot connect to Raspberry Pi at $PI_IP${NC}"
    echo ""
    echo "Please ensure:"
    echo "  1. SSH is enabled on the Pi: sudo systemctl enable ssh && sudo systemctl start ssh"
    echo "  2. The Pi is on the network"
    echo "  3. Firewall allows SSH (port 22)"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Connection successful${NC}"
echo ""

# Step 1: Build PWA
echo -e "${YELLOW}Step 1: Building PWA...${NC}"
cd "$SCRIPT_DIR/packages/frontend"

# Build with STATIC_BUILD for relative paths (works better for kiosk)
echo "Building with STATIC_BUILD=true..."
STATIC_BUILD=true npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}Error: Build failed - dist directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ PWA built successfully${NC}"
echo ""

# Step 2: Install packages on Pi
echo -e "${YELLOW}Step 2: Installing required packages on Pi...${NC}"

INSTALL_CMD="sudo apt-get update && \
sudo apt-get install -y nginx chromium unclutter x11-xserver-utils xdotool && \
echo 'Packages installed successfully'"

sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
    -o ServerAliveInterval=30 \
    -o TCPKeepAlive=yes \
    -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "$INSTALL_CMD"

echo -e "${GREEN}✓ Packages installed${NC}"
echo ""

# Step 3: Create directory structure on Pi
echo -e "${YELLOW}Step 3: Creating directory structure on Pi...${NC}"

SETUP_DIRS_CMD="mkdir -p /home/$PI_USER/preke-pwa && \
mkdir -p /home/$PI_USER/.config/autostart && \
echo 'Directories created'"

sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
    -o ServerAliveInterval=30 \
    -o TCPKeepAlive=yes \
    -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "$SETUP_DIRS_CMD"

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Step 4: Copy PWA files to Pi
echo -e "${YELLOW}Step 4: Copying PWA files to Pi...${NC}"

# Use rsync if available, otherwise scp
if command -v rsync &> /dev/null; then
    rsync -avz --delete \
        -e "sshpass -p '$PI_PASSWORD' ssh -o StrictHostKeyChecking=no" \
        "$SCRIPT_DIR/packages/frontend/dist/" \
        "$PI_USER@$PI_IP:/home/$PI_USER/preke-pwa/"
else
    # Fallback to scp
    sshpass -p "$PI_PASSWORD" scp -r \
        -o StrictHostKeyChecking=no \
        "$SCRIPT_DIR/packages/frontend/dist/"* \
        "$PI_USER@$PI_IP:/home/$PI_USER/preke-pwa/"
fi

echo -e "${GREEN}✓ PWA files copied${NC}"
echo ""

# Step 5: Create nginx configuration
echo -e "${YELLOW}Step 5: Configuring nginx...${NC}"

NGINX_CONFIG=$(cat <<EOF
server {
    listen 80;
    server_name _;
    root /home/$PI_USER/preke-pwa;
    index index.html;

    # PWA static files
    location / {
        try_files \$uri \$uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Service worker and manifest
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|webmanifest)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy API requests to R58
    location /api/ {
        proxy_pass http://$R58_IP:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Proxy health endpoint
    location /health {
        proxy_pass http://$R58_IP:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # Proxy status endpoint
    location /status {
        proxy_pass http://$R58_IP:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # Proxy MediaMTX WHEP endpoints
    location ~ ^/(cam[0-9]+)/whep$ {
        proxy_pass http://$R58_IP:8889;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # WebSocket support for API
    location /ws {
        proxy_pass http://$R58_IP:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
    }
}
EOF
)

# Write nginx config to temp file and copy to Pi
NGINX_TEMP=$(mktemp)
echo "$NGINX_CONFIG" > "$NGINX_TEMP"

sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    "$NGINX_TEMP" \
    "$PI_USER@$PI_IP:/tmp/preke-nginx.conf"

# Install nginx config on Pi
SETUP_NGINX_CMD="sudo mv /tmp/preke-nginx.conf /etc/nginx/sites-available/preke && \
sudo ln -sf /etc/nginx/sites-available/preke /etc/nginx/sites-enabled/ && \
sudo rm -f /etc/nginx/sites-enabled/default && \
sudo nginx -t && \
sudo systemctl enable nginx && \
sudo systemctl restart nginx && \
echo 'Nginx configured and started'"

sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
    -o ServerAliveInterval=30 \
    -o TCPKeepAlive=yes \
    -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "$SETUP_NGINX_CMD"

rm -f "$NGINX_TEMP"

echo -e "${GREEN}✓ Nginx configured${NC}"
echo ""

# Step 6: Create kiosk systemd service
echo -e "${YELLOW}Step 6: Creating kiosk service...${NC}"

KIOSK_SERVICE=$(cat <<EOF
[Unit]
Description=Preke Studio Kiosk
After=network.target graphical.target
Wants=graphical.target

[Service]
Type=simple
User=$PI_USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$PI_USER/.Xauthority
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/chromium \\
    --kiosk \\
    --noerrdialogs \\
    --disable-infobars \\
    --disable-session-crashed-bubble \\
    --disable-restore-session-state \\
    --disable-features=TranslateUI \\
    --autoplay-policy=no-user-gesture-required \\
    --check-for-update-interval=31536000 \\
    --disable-background-networking \\
    http://localhost
Restart=always
RestartSec=10

[Install]
WantedBy=graphical.target
EOF
)

# Write service file to temp and copy to Pi
SERVICE_TEMP=$(mktemp)
echo "$KIOSK_SERVICE" > "$SERVICE_TEMP"

sshpass -p "$PI_PASSWORD" scp -o StrictHostKeyChecking=no \
    "$SERVICE_TEMP" \
    "$PI_USER@$PI_IP:/tmp/preke-kiosk.service"

# Install service on Pi
SETUP_SERVICE_CMD="sudo mv /tmp/preke-kiosk.service /etc/systemd/system/preke-kiosk.service && \
sudo systemctl daemon-reload && \
sudo systemctl enable preke-kiosk.service && \
echo 'Kiosk service installed'"

sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
    -o ServerAliveInterval=30 \
    -o TCPKeepAlive=yes \
    -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "$SETUP_SERVICE_CMD"

rm -f "$SERVICE_TEMP"

echo -e "${GREEN}✓ Kiosk service created${NC}"
echo ""

# Step 7: Disable screen blanking
echo -e "${YELLOW}Step 7: Disabling screen blanking...${NC}"

DISABLE_BLANK_CMD="mkdir -p /home/$PI_USER/.config/lxsession/LXDE-pi && \
echo '@xset s off' > /home/$PI_USER/.config/lxsession/LXDE-pi/autostart && \
echo '@xset -dpms' >> /home/$PI_USER/.config/lxsession/LXDE-pi/autostart && \
echo '@xset s noblank' >> /home/$PI_USER/.config/lxsession/LXDE-pi/autostart && \
echo 'Screen blanking disabled'"

sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
    -o ServerAliveInterval=30 \
    -o TCPKeepAlive=yes \
    -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "$DISABLE_BLANK_CMD"

echo -e "${GREEN}✓ Screen blanking disabled${NC}"
echo ""

# Step 8: Set permissions
echo -e "${YELLOW}Step 8: Setting permissions...${NC}"

PERMISSIONS_CMD="sudo chown -R $PI_USER:$PI_USER /home/$PI_USER/preke-pwa && \
sudo chmod -R 755 /home/$PI_USER/preke-pwa && \
echo 'Permissions set'"

sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
    -o ServerAliveInterval=30 \
    -o TCPKeepAlive=yes \
    -o StrictHostKeyChecking=no \
    "$PI_USER@$PI_IP" "$PERMISSIONS_CMD"

echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

echo -e "${GREEN}======================================"
echo "Deployment Complete!"
echo "======================================"
echo -e "${NC}"
echo "Next steps:"
echo "  1. Reboot the Pi: ssh $PI_USER@$PI_IP 'sudo reboot'"
echo "  2. The kiosk will start automatically on boot"
echo "  3. To start manually: ssh $PI_USER@$PI_IP 'sudo systemctl start preke-kiosk'"
echo "  4. To stop: ssh $PI_USER@$PI_IP 'sudo systemctl stop preke-kiosk'"
echo "  5. View logs: ssh $PI_USER@$PI_IP 'journalctl -u preke-kiosk -f'"
echo ""
echo "Access the PWA:"
echo "  http://$PI_IP"
echo ""
