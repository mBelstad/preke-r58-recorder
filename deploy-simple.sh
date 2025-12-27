#!/bin/bash
# Simple, Reliable R58 Deployment Script
# Deploys code to R58 device via FRP tunnel
# Uses connect-r58-frp.sh for SSH (SSH key auth, reliable timeouts)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "======================================"
echo "R58 Simple Deployment Script"
echo "======================================"
echo -e "${NC}"
echo ""

# Check connect script exists
if [[ ! -x "$SCRIPT_DIR/connect-r58-frp.sh" ]]; then
    echo -e "${RED}Error: connect-r58-frp.sh not found or not executable${NC}"
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
"$SCRIPT_DIR/connect-r58-frp.sh" "cd /opt/preke-r58-recorder && git pull && sudo systemctl restart preke-recorder && echo 'Deployment complete!'"

echo ""
echo -e "${GREEN}======================================"
echo "Deployment Successful!"
echo "======================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Test: https://r58-api.itagenten.no/static/app.html"
echo "  2. Check logs: ./connect-r58-frp.sh 'sudo journalctl -u preke-recorder -f'"
echo ""

