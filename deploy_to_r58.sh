#!/bin/bash
# Deploy script for R58 remote access updates
# Run this script on the R58 device after SSH'ing in

set -e  # Exit on error

echo "=========================================="
echo "R58 Remote Access Deployment Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/opt/preke-r58-recorder"

echo -e "${YELLOW}Step 1: Navigating to project directory${NC}"
cd "$PROJECT_DIR" || { echo -e "${RED}Failed to navigate to $PROJECT_DIR${NC}"; exit 1; }
echo -e "${GREEN}✓ In project directory${NC}"
echo ""

echo -e "${YELLOW}Step 2: Fetching latest code from GitHub${NC}"
sudo git fetch origin
echo -e "${GREEN}✓ Fetched latest code${NC}"
echo ""

echo -e "${YELLOW}Step 3: Checking out feature/remote-access-v2 branch${NC}"
sudo git checkout feature/remote-access-v2
echo -e "${GREEN}✓ Checked out branch${NC}"
echo ""

echo -e "${YELLOW}Step 4: Pulling latest changes${NC}"
sudo git pull origin feature/remote-access-v2
echo -e "${GREEN}✓ Pulled latest changes${NC}"
echo ""

echo -e "${YELLOW}Step 5: Fixing file permissions${NC}"
sudo chown -R linaro:linaro .
echo -e "${GREEN}✓ Fixed permissions${NC}"
echo ""

echo -e "${YELLOW}Step 6: Restarting preke-recorder service${NC}"
sudo systemctl restart preke-recorder
echo -e "${GREEN}✓ Service restart initiated${NC}"
echo ""

echo -e "${YELLOW}Step 7: Waiting for service to start (8 seconds)${NC}"
sleep 8
echo -e "${GREEN}✓ Wait complete${NC}"
echo ""

echo -e "${YELLOW}Step 8: Checking service status${NC}"
sudo systemctl status preke-recorder --no-pager | head -40
echo ""

echo -e "${YELLOW}Step 9: Verifying FRP tunnel configuration${NC}"
if grep -q "\[vdo-nginx\]" /etc/frp/frpc.ini; then
    echo -e "${GREEN}✓ FRP tunnel for VDO.ninja (port 8443) is configured${NC}"
else
    echo -e "${RED}⚠ FRP tunnel for VDO.ninja not found in /etc/frp/frpc.ini${NC}"
    echo "Expected configuration:"
    echo "[vdo-nginx]"
    echo "type = tcp"
    echo "local_ip = 127.0.0.1"
    echo "local_port = 8443"
    echo "remote_port = 18443"
    echo ""
    echo "Please add this manually and restart FRP: sudo systemctl restart frpc"
fi
echo ""

echo -e "${YELLOW}Step 10: Checking MediaMTX status${NC}"
sudo systemctl status mediamtx --no-pager | head -20
echo ""

echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify DNS record for r58-vdo.itagenten.no points to 65.109.32.111"
echo "2. Update nginx configuration on Coolify VPS"
echo "3. Test the following URLs:"
echo "   - https://r58-api.itagenten.no/ (main dashboard with WHEP)"
echo "   - https://r58-api.itagenten.no/static/r58_remote_mixer (remote mixer)"
echo "   - https://r58-vdo.itagenten.no/?director=r58studio (VDO.ninja director)"
echo ""

