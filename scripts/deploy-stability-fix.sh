#!/bin/bash
# Deployment script for stability restoration
# Restores single-encoder architecture for stable 4-camera operation

set -e  # Exit on error

echo "=========================================="
echo "R58 Stability Restoration Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on R58
if [ ! -f /proc/device-tree/model ] || ! grep -q "Rockchip" /proc/device-tree/model 2>/dev/null; then
    echo -e "${RED}ERROR: This script must be run on the R58 device${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Running on R58 device"
echo ""

# Check current directory
if [ ! -f "preke-recorder.service" ]; then
    echo -e "${RED}ERROR: Must run from /opt/preke-r58-recorder${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} In correct directory: $(pwd)"
echo ""

# Verify service configuration
echo "Checking service configuration..."
if grep -q "src.main:app" preke-recorder.service; then
    echo -e "${GREEN}✓${NC} Service configured to use src/main.py (correct)"
else
    echo -e "${YELLOW}⚠${NC} Service may not be using src/main.py"
    grep "ExecStart" preke-recorder.service
fi
echo ""

# Pull latest changes
echo "Pulling latest changes from git..."
if git pull origin main; then
    echo -e "${GREEN}✓${NC} Git pull successful"
else
    echo -e "${YELLOW}⚠${NC} Git pull failed or no changes"
fi
echo ""

# Check disk space
echo "Checking disk space..."
df -h /mnt/sdcard | tail -1
FREE_GB=$(df -BG /mnt/sdcard | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$FREE_GB" -lt 10 ]; then
    echo -e "${YELLOW}⚠${NC} Warning: Less than 10GB free on /mnt/sdcard"
else
    echo -e "${GREEN}✓${NC} Sufficient disk space available"
fi
echo ""

# Restart service
echo "Restarting preke-r58-recorder service..."
if sudo systemctl restart preke-r58-recorder; then
    echo -e "${GREEN}✓${NC} Service restarted"
else
    echo -e "${RED}✗${NC} Service restart failed"
    exit 1
fi
echo ""

# Wait for service to start
echo "Waiting for service to start (10 seconds)..."
sleep 10

# Check service status
echo "Checking service status..."
if sudo systemctl is-active --quiet preke-r58-recorder; then
    echo -e "${GREEN}✓${NC} Service is active"
else
    echo -e "${RED}✗${NC} Service is not active"
    echo "Recent logs:"
    sudo journalctl -u preke-r58-recorder -n 20 --no-pager
    exit 1
fi
echo ""

# Check API health
echo "Checking API health..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓${NC} API is responding"
else
    echo -e "${RED}✗${NC} API is not responding"
    exit 1
fi
echo ""

# Check ingest status
echo "Checking ingest status..."
INGEST_STATUS=$(curl -s http://localhost:8000/api/ingest/status)
echo "$INGEST_STATUS" | jq '.'
echo ""

# Count streaming cameras
STREAMING_COUNT=$(echo "$INGEST_STATUS" | jq '[.[] | select(.status == "streaming")] | length')
echo "Cameras streaming: $STREAMING_COUNT"
echo ""

# Summary
echo "=========================================="
echo "Deployment Summary"
echo "=========================================="
echo -e "${GREEN}✓${NC} Service deployed and running"
echo -e "${GREEN}✓${NC} API responding on port 8000"
echo "  Cameras streaming: $STREAMING_COUNT"
echo ""
echo "Next steps:"
echo "1. Monitor logs: journalctl -u preke-r58-recorder -f"
echo "2. Test recording: curl -X POST http://localhost:8000/api/recording/start_all"
echo "3. Monitor stability for 1+ hour"
echo "4. Test hot-plug (disconnect/reconnect HDMI cables)"
echo ""
echo "See docs/STABILITY_RESTORATION.md for detailed testing procedures"
echo ""

