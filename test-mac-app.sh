#!/bin/bash
# Mac App Testing Script for Preke R58 Recorder
# Tests the Electron Capture app with various configurations

set -e

APP_PATH="$HOME/Applications/elecap.app"
R58_IP="192.168.1.25"
R58_PORT="8443"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "Preke R58 - Mac App Testing Script"
echo "======================================"
echo ""

# Check if app exists
echo -n "Checking if Electron Capture app is installed... "
if [ -d "$APP_PATH" ]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "App not found at $APP_PATH"
    echo "Please install from: https://github.com/steveseguin/electroncapture/releases"
    exit 1
fi

# Check for quarantine
echo -n "Checking for quarantine attributes... "
if xattr -l "$APP_PATH" | grep -q "com.apple.quarantine"; then
    echo -e "${YELLOW}⚠${NC}"
    echo "Removing quarantine..."
    xattr -d com.apple.quarantine "$APP_PATH" 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Quarantine removed"
else
    echo -e "${GREEN}✓${NC}"
fi

# Kill any existing instances
echo -n "Stopping any existing instances... "
killall elecap 2>/dev/null || true
sleep 1
echo -e "${GREEN}✓${NC}"

# Test 1: Director Mode
echo ""
echo "Test 1: Director Mode"
echo "----------------------"
echo "Launching app in director mode..."
open -a "$APP_PATH" --args --url="https://${R58_IP}:${R58_PORT}/?director=r58studio"
sleep 3

if ps aux | grep -i "elecap.*director" | grep -v grep > /dev/null; then
    echo -e "${GREEN}✓${NC} App launched successfully in director mode"
    echo "  URL: https://${R58_IP}:${R58_PORT}/?director=r58studio"
else
    echo -e "${RED}✗${NC} Failed to launch app"
    exit 1
fi

echo ""
echo "Press Enter to continue to next test (will close current window)..."
read

# Test 2: Camera View Mode
killall elecap 2>/dev/null || true
sleep 1

echo ""
echo "Test 2: Camera View Mode (cam0)"
echo "--------------------------------"
echo "Launching app to view cam0..."
open -a "$APP_PATH" --args --url="https://${R58_IP}:${R58_PORT}/?view=r58-cam0"
sleep 3

if ps aux | grep -i elecap | grep -v grep > /dev/null; then
    echo -e "${GREEN}✓${NC} App launched successfully in camera view mode"
    echo "  URL: https://${R58_IP}:${R58_PORT}/?view=r58-cam0"
else
    echo -e "${RED}✗${NC} Failed to launch app"
    exit 1
fi

echo ""
echo "Press Enter to continue to next test (will close current window)..."
read

# Test 3: Camera View with Options
killall elecap 2>/dev/null || true
sleep 1

echo ""
echo "Test 3: Camera View with Options (cam2 + noaudio)"
echo "--------------------------------------------------"
echo "Launching app to view cam2 with no audio..."
open -a "$APP_PATH" --args --url="https://${R58_IP}:${R58_PORT}/?view=r58-cam2&noaudio"
sleep 3

if ps aux | grep -i elecap | grep -v grep > /dev/null; then
    echo -e "${GREEN}✓${NC} App launched successfully with options"
    echo "  URL: https://${R58_IP}:${R58_PORT}/?view=r58-cam2&noaudio"
else
    echo -e "${RED}✗${NC} Failed to launch app"
    exit 1
fi

echo ""
echo "Press Enter to continue to OBS integration test..."
read

# Test 4: OBS Integration
echo ""
echo "Test 4: OBS Integration"
echo "-----------------------"

if [ -d "/Applications/OBS.app" ]; then
    echo "OBS is installed at /Applications/OBS.app"
    
    if ps aux | grep -i "OBS.app" | grep -v grep > /dev/null; then
        echo -e "${GREEN}✓${NC} OBS is running"
    else
        echo -e "${YELLOW}⚠${NC} OBS is not running"
        echo ""
        echo "To test OBS integration:"
        echo "1. Open OBS"
        echo "2. Add Source → Window Capture"
        echo "3. Select window: 'elecap'"
        echo "4. Enable: Capture Method → Window Capture (macOS 10.15+)"
        echo "5. Verify clean video feed appears"
    fi
else
    echo -e "${YELLOW}⚠${NC} OBS not found at /Applications/OBS.app"
    echo "Install OBS from: https://obsproject.com/"
fi

echo ""
echo "======================================"
echo "Testing Complete!"
echo "======================================"
echo ""
echo "Summary:"
echo "  ✓ App installation verified"
echo "  ✓ Director mode tested"
echo "  ✓ Camera view mode tested"
echo "  ✓ Options (noaudio) tested"
echo "  ✓ OBS integration checked"
echo ""
echo "The Electron Capture app is running and ready for use."
echo ""
echo "To stop the app: killall elecap"
echo ""
