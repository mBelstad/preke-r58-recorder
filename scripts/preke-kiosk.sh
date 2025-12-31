#!/bin/bash
# Preke Studio Kiosk Mode Launcher
# Launches the PWA in fullscreen kiosk mode on the R58 device

# Wait for display to be available
export DISPLAY=:0

# Wait for X server to be ready
while ! xdpyinfo >/dev/null 2>&1; do
    echo "Waiting for X server..."
    sleep 2
done

# Wait for network and API to be ready
echo "Waiting for Preke API to be ready..."
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo "API is ready!"
        break
    fi
    echo "Waiting for API... ($RETRY/$MAX_RETRIES)"
    sleep 2
    RETRY=$((RETRY + 1))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "Warning: API not responding, launching anyway..."
fi

# Kill any existing Preke Chromium instances
pkill -f 'chromium.*localhost:8000' 2>/dev/null || true
sleep 1

# Disable screen saver and power management
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# Launch Chromium in kiosk mode
# - --kiosk: Fullscreen, no UI chrome
# - --app: PWA mode (minimal UI)
# - --noerrdialogs: Suppress error dialogs
# - --disable-infobars: No "Chrome is being controlled" bar
# - --disable-session-crashed-bubble: No crash recovery dialogs
# - --check-for-update-interval=31536000: Disable update checks (1 year)
# - --disable-gpu-sandbox: Required for R58 Mali GPU
# - --enable-features=VaapiVideoDecoder: Hardware video decode

echo "Launching Preke Studio in kiosk mode..."

exec /usr/bin/chromium \
    --kiosk \
    --app="http://localhost:8000/#/recorder" \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --check-for-update-interval=31536000 \
    --disable-gpu-sandbox \
    --no-sandbox \
    --enable-features=VaapiVideoDecoder,VaapiVideoEncoder \
    --use-gl=angle \
    --use-angle=gles-egl \
    --disable-breakpad \
    --disable-component-update \
    --disable-background-networking \
    --disable-sync \
    --metrics-recording-only \
    --disable-default-apps \
    --mute-audio \
    --no-first-run \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding

