#!/bin/bash
# Test Companion and Stream Deck setup
# Run this script to verify everything is configured correctly

set -e

echo "=== Testing Companion and Stream Deck Setup ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check R58 API is accessible
echo "Test 1: R58 API Accessibility"
echo "----------------------------"
API_URL="https://app.itagenten.no/api/v1/cameras/"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$API_URL" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓${NC} R58 API is accessible (HTTP $HTTP_CODE)"
    CAMERAS=$(curl -s "$API_URL" | python3 -c "import sys, json; print(', '.join(json.load(sys.stdin)))" 2>/dev/null || echo "[]")
    echo "  Available cameras: $CAMERAS"
else
    echo -e "${RED}✗${NC} R58 API is not accessible (HTTP $HTTP_CODE)"
    echo "  Check: Is the R58 device online? Is the API URL correct?"
fi
echo ""

# Test 2: Check Companion service (if on R58)
echo "Test 2: Companion Service Status (R58 Device)"
echo "----------------------------------------------"
if command -v systemctl &> /dev/null && systemctl is-active --quiet companion 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Companion service is running"
    COMPANION_PORT=$(systemctl show companion -p Environment | grep -oP 'HTTP_PORT=\K[0-9]+' || echo "8080")
    echo "  Companion port: $COMPANION_PORT"
    
    # Test Companion web UI
    if curl -s -o /dev/null -w '%{http_code}' "http://localhost:$COMPANION_PORT" | grep -q "200\|302"; then
        echo -e "${GREEN}✓${NC} Companion web UI is accessible"
    else
        echo -e "${YELLOW}⚠${NC} Companion web UI may not be accessible"
    fi
else
    echo -e "${YELLOW}⚠${NC} Companion service not found or not running"
    echo "  This is OK if Companion is running on a PC instead"
fi
echo ""

# Test 3: Test camera control endpoint
echo "Test 3: Camera Control Endpoint"
echo "--------------------------------"
if [ -n "$CAMERAS" ] && [ "$CAMERAS" != "[]" ]; then
    # Get first camera name
    FIRST_CAMERA=$(echo "$CAMERAS" | cut -d',' -f1 | tr -d ' "' | head -1)
    if [ -n "$FIRST_CAMERA" ]; then
        STATUS_URL="https://app.itagenten.no/api/v1/cameras/$FIRST_CAMERA/status"
        STATUS_CODE=$(curl -s -o /dev/null -w '%{http_code}' "$STATUS_URL" || echo "000")
        
        if [ "$STATUS_CODE" = "200" ]; then
            echo -e "${GREEN}✓${NC} Camera status endpoint works for: $FIRST_CAMERA"
            # Get connection status
            CONNECTED=$(curl -s "$STATUS_URL" | python3 -c "import sys, json; print('connected' if json.load(sys.stdin).get('connected') else 'disconnected')" 2>/dev/null || echo "unknown")
            echo "  Connection status: $CONNECTED"
        else
            echo -e "${RED}✗${NC} Camera status endpoint failed (HTTP $STATUS_CODE)"
        fi
    fi
else
    echo -e "${YELLOW}⚠${NC} No cameras configured - cannot test camera endpoints"
    echo "  Add cameras to config.yml and restart service"
fi
echo ""

# Test 4: Check Stream Deck connection (if Companion is running)
echo "Test 4: Stream Deck Connection"
echo "-------------------------------"
if command -v systemctl &> /dev/null && systemctl is-active --quiet companion 2>/dev/null; then
    # Check if Stream Deck is connected via USB
    if lsusb 2>/dev/null | grep -qi "stream\|elgato"; then
        echo -e "${GREEN}✓${NC} Stream Deck detected via USB"
    else
        echo -e "${YELLOW}⚠${NC} No Stream Deck detected via USB"
        echo "  Make sure Stream Deck is connected via USB"
        echo "  Or configure network connection in Companion"
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot check Stream Deck - Companion not running on device"
    echo "  If Companion is on PC, check Stream Deck connection there"
fi
echo ""

# Summary
echo "=== Summary ==="
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓${NC} R58 API is ready for Companion integration"
    echo ""
    echo "Next steps:"
    echo "  1. Open Companion web UI"
    echo "  2. Add HTTP instance with base URL: https://app.itagenten.no"
    echo "  3. Configure camera control buttons"
    echo "  4. Connect Stream Deck"
    echo ""
    echo "See docs/STREAM_DECK_SETUP_COMPLETE.md for detailed instructions"
else
    echo -e "${RED}✗${NC} Setup incomplete - fix issues above"
    echo ""
    echo "Troubleshooting:"
    echo "  - Check R58 device is online"
    echo "  - Verify API URL is correct"
    echo "  - Check firewall settings"
fi
