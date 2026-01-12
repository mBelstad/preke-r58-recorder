#!/bin/bash
# Quick update script for Raspberry Pi PWA
# Usage: ./update-raspberry-pi-pwa.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
PI_USER="${PI_USER:-marius}"
PI_PASSWORD="${PI_PASSWORD:-Famalive94}"
PI_IP="${PI_IP:-192.168.1.81}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Updating PWA on Raspberry Pi...${NC}"
echo ""

# Step 1: Build PWA
echo -e "${YELLOW}Step 1: Building PWA...${NC}"
cd "$SCRIPT_DIR/packages/frontend"
STATIC_BUILD=true npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}Error: Build failed - dist directory not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ PWA built${NC}"
echo ""

# Step 2: Deploy to Pi
echo -e "${YELLOW}Step 2: Deploying to Raspberry Pi...${NC}"

if command -v rsync &> /dev/null; then
    rsync -avz --delete \
        -e "sshpass -p '$PI_PASSWORD' ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no -o PreferredAuthentications=password" \
        "$SCRIPT_DIR/packages/frontend/dist/" \
        "$PI_USER@$PI_IP:/home/$PI_USER/preke-pwa/"
else
    sshpass -p "$PI_PASSWORD" scp -r \
        -o StrictHostKeyChecking=no \
        -o PubkeyAuthentication=no \
        -o PreferredAuthentications=password \
        "$SCRIPT_DIR/packages/frontend/dist/"* \
        "$PI_USER@$PI_IP:/home/$PI_USER/preke-pwa/"
fi

echo -e "${GREEN}✓ Files deployed${NC}"
echo ""

# Step 3: Restart nginx
echo -e "${YELLOW}Step 3: Restarting nginx...${NC}"
sshpass -p "$PI_PASSWORD" ssh \
    -o StrictHostKeyChecking=no \
    -o PubkeyAuthentication=no \
    -o PreferredAuthentications=password \
    "$PI_USER@$PI_IP" "sudo systemctl restart nginx"

echo -e "${GREEN}✓ Nginx restarted${NC}"
echo ""

echo -e "${GREEN}======================================"
echo "Update Complete!"
echo "======================================"
echo -e "${NC}"
echo "The PWA has been updated on the Raspberry Pi."
echo ""
echo "To see changes:"
echo "  - Restart kiosk: ssh $PI_USER@$PI_IP 'sudo systemctl restart preke-kiosk'"
echo "  - Or hard refresh in browser: Ctrl+Shift+R"
echo ""
