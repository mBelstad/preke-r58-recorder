#!/bin/bash
# Preke Studio TV Kiosk Mode Launcher
# Launches the QR page in fullscreen kiosk mode on the R58 device TV output
# This is the first thing customers see when entering the studio

set -e

LOG_FILE="/var/log/preke-tv-kiosk.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Wait for display to be available
export DISPLAY=:0

log "Starting Preke TV Kiosk..."

# Wait for X server to be ready
while ! xdpyinfo >/dev/null 2>&1; do
    log "Waiting for X server..."
    sleep 2
done
log "X server is ready"

# Wait for network and API to be ready
log "Waiting for Preke API to be ready..."
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        log "API is ready!"
        break
    fi
    log "Waiting for API... ($RETRY/$MAX_RETRIES)"
    sleep 2
    RETRY=$((RETRY + 1))
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    log "Warning: API not responding, launching anyway..."
fi

# Kill any existing kiosk Chromium instances (but not VDO.ninja bridge instances)
pkill -f 'chromium.*--kiosk' 2>/dev/null || true
sleep 1

# Disable screen saver and power management
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

log "Launching QR page in kiosk mode..."

# Launch Chromium in kiosk mode for the QR page
# - --kiosk: Fullscreen, no UI chrome, always on top
# - --app: PWA mode (minimal UI)
# - --noerrdialogs: Suppress error dialogs
# - --disable-infobars: No "Chrome is being controlled" bar
# Key: --kiosk creates an always-on-top fullscreen window that will cover
# any VDO.ninja bridge windows running in the background

# Note: Using port 9223 for kiosk CDP (9222 is used by VDO.ninja bridge)
# CRITICAL: Use separate user-data-dir to prevent attaching to VDO.ninja bridge session
# Add cache-busting timestamp to force fresh load
TIMESTAMP=$(date +%s)
exec /usr/bin/chromium \
    --user-data-dir=/home/linaro/.config/chromium-kiosk \
    --kiosk \
    --app="http://localhost:8000/#/qr?t=${TIMESTAMP}" \
    --disable-background-networking \
    --disable-background-timer-throttling \
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
    --no-first-run \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    --remote-debugging-port=9223 \
    --window-position=0,0 \
    --window-size=1920,1080
