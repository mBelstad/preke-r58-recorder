#!/bin/bash
# Launch Electron Capture to view cam0
# Clean frameless window for OBS capture

APP_PATH="$HOME/Applications/elecap.app"
URL="https://192.168.1.25:8443/?view=r58-cam0&noaudio"

echo "Launching Electron Capture - Camera 0 View"
echo "URL: $URL"

# Kill any existing instance
killall elecap 2>/dev/null || true
sleep 0.5

# Launch app
open -a "$APP_PATH" --args --url="$URL"

echo "✓ App launched"
echo ""
echo "Add to OBS:"
echo "  1. Add Source → Window Capture"
echo "  2. Select window: elecap"
echo "  3. Enable: Window Capture (macOS 10.15+)"
echo ""
echo "To stop: killall elecap"
