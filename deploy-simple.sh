#!/bin/bash
# Simple, Reliable R58 Deployment Script
# Deploys code to R58 device via FRP tunnel

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
R58_VPS="65.109.32.111"
R58_PORT="10022"
R58_USER="linaro"
R58_PASSWORD="${R58_PASSWORD:-linaro}"

echo -e "${GREEN}"
echo "======================================"
echo "R58 Simple Deployment Script"
echo "======================================"
echo -e "${NC}"
echo ""

# Check sshpass
if ! command -v sshpass >/dev/null 2>&1; then
    echo -e "${RED}Error: sshpass is required${NC}"
    echo "Install: brew install sshpass"
    exit 1
fi

# Step 1: Push to GitHub
echo -e "${YELLOW}Step 1: Pushing to GitHub...${NC}"
if [ -d ".git" ]; then
    git add . || true
    git commit -m "Deploy: $(date +%Y-%m-%d\ %H:%M:%S)" || echo "Nothing to commit"
    git push origin feature/remote-access-v2
    echo -e "${GREEN}✓ Pushed to GitHub${NC}"
else
    echo -e "${RED}✗ Not a git repository${NC}"
    exit 1
fi
echo ""

# Step 2: Deploy to R58
echo -e "${YELLOW}Step 2: Deploying to R58 via FRP tunnel...${NC}"
echo "Connecting to ${R58_VPS}:${R58_PORT}"
echo ""

sshpass -p "${R58_PASSWORD}" ssh \
    -o StrictHostKeyChecking=no \
    -o ConnectTimeout=30 \
    -p ${R58_PORT} \
    ${R58_USER}@${R58_VPS} \
    "cd /home/linaro/preke-r58-recorder && \
     git pull && \
     sudo systemctl restart preke-recorder && \
     echo 'Deployment complete!'"

echo ""
echo -e "${GREEN}======================================"
echo "Deployment Successful!"
echo "======================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Test: https://r58-api.itagenten.no/static/app.html"
echo "  2. Check logs: ssh r58-frp 'sudo journalctl -u preke-recorder -f'"
echo ""

