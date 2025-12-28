#!/bin/bash
# Launch Electron Capture in Director Mode
# Quick access to VDO.Ninja mixer/director interface

APP_PATH="$HOME/Applications/elecap.app"
URL="https://192.168.1.25:8443/?director=r58studio"

echo "Launching Electron Capture - Director Mode"
echo "URL: $URL"

# Kill any existing instance
killall elecap 2>/dev/null || true
sleep 0.5

# Launch app
open -a "$APP_PATH" --args --url="$URL"

echo "✓ App launched"
echo ""
echo "To stop: killall elecap"
