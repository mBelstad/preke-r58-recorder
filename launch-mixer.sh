#!/bin/bash
# Launch Electron Capture to view mixer output
# Clean frameless window for OBS capture

APP_PATH="$HOME/Applications/elecap.app"
URL="https://192.168.1.25:8443/?view=r58-mixer&noaudio"

echo "Launching Electron Capture - Mixer Output View"
echo "URL: $URL"

# Kill any existing instance
killall elecap 2>/dev/null || true
sleep 0.5

# Launch app
open -a "$APP_PATH" --args --url="$URL"

echo "✓ App launched"
echo ""
echo "This shows the mixed/switched output from the R58 mixer"
echo ""
echo "Add to OBS:"
echo "  1. Add Source → Window Capture"
echo "  2. Select window: elecap"
echo "  3. Enable: Window Capture (macOS 10.15+)"
echo ""
echo "To stop: killall elecap"
