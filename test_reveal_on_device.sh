#!/bin/bash
# Test reveal.js on R58 device via Tailscale

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

DEVICE_URL="${1:-http://100.65.219.117:8000}"

echo -e "${GREEN}Testing reveal.js on R58 device${NC}"
echo -e "Device URL: ${YELLOW}${DEVICE_URL}${NC}"
echo ""

# Test health endpoint
echo -e "${YELLOW}1. Testing device connection...${NC}"
if curl -s --connect-timeout 5 "${DEVICE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Device is reachable${NC}"
else
    echo -e "${RED}✗ Cannot reach device at ${DEVICE_URL}${NC}"
    echo "  Make sure Tailscale is connected and device is online"
    exit 1
fi

# Test reveal.js files
echo ""
echo -e "${YELLOW}2. Testing reveal.js files...${NC}"

files=(
    "/reveal.js/reveal.js"
    "/reveal.js/reveal.css"
    "/reveal.js/theme/black.css"
)

all_ok=true
for file in "${files[@]}"; do
    url="${DEVICE_URL}${file}"
    if response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "${url}" 2>/dev/null); then
        if [ "$response" = "200" ]; then
            size=$(curl -s --connect-timeout 5 "${url}" 2>/dev/null | wc -c | tr -d ' ')
            echo -e "${GREEN}✓ ${file} - ${size} bytes${NC}"
        else
            echo -e "${RED}✗ ${file} - HTTP ${response}${NC}"
            all_ok=false
        fi
    else
        echo -e "${RED}✗ ${file} - Connection failed${NC}"
        all_ok=false
    fi
done

echo ""
if [ "$all_ok" = true ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ All reveal.js files are accessible!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Test URLs:"
    echo "  - reveal.js: ${DEVICE_URL}/reveal.js/reveal.js"
    echo "  - reveal.css: ${DEVICE_URL}/reveal.js/reveal.css"
    echo "  - theme: ${DEVICE_URL}/reveal.js/theme/black.css"
    echo ""
    echo "Open test_reveal_device.html in your browser for interactive testing"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ Some files failed to load${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
