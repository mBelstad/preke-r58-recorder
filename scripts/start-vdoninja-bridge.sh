#!/bin/bash
# VDO.ninja Bridge Auto-Start Script
# This script starts Chromium with the WHEP viewer and sets up the screen share to VDO.ninja

set -e

# Configuration
ROOM_NAME="${VDONINJA_ROOM:-r58studio}"
WHEP_URL="${WHEP_URL:-https://r58-api.itagenten.no/whep/cam2}"
VDONINJA_HOST="${VDONINJA_HOST:-r58-vdo.itagenten.no}"
CAMERA_LABEL="${CAMERA_LABEL:-HDMI-Camera}"
CAMERA_PUSH_ID="${CAMERA_PUSH_ID:-hdmicam}"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/vdoninja-bridge.log"

# Ensure we have a display
export DISPLAY="${DISPLAY:-:0}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

wait_for_display() {
    log "Waiting for X display..."
    local max_attempts=60
    local attempt=0
    while ! xdpyinfo >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            log "ERROR: X display not available after $max_attempts attempts"
            exit 1
        fi
        sleep 2
    done
    log "X display is available"
}

wait_for_network() {
    log "Waiting for network..."
    local max_attempts=30
    local attempt=0
    while ! curl -s --connect-timeout 2 "https://$VDONINJA_HOST" >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            log "ERROR: Network not available after $max_attempts attempts"
            exit 1
        fi
        sleep 2
    done
    log "Network is available"
}

start_chromium() {
    log "Starting Chromium with WHEP viewer..."
    
    # Kill any existing Chromium instances
    pkill -f chromium 2>/dev/null || true
    sleep 2
    
    # Start Chromium with remote debugging
    nohup chromium \
        --remote-debugging-port=9222 \
        --disable-infobars \
        --no-first-run \
        --disable-session-crashed-bubble \
        --disable-features=TranslateUI \
        --autoplay-policy=no-user-gesture-required \
        "https://$VDONINJA_HOST/?whepplay=$WHEP_URL" \
        >/dev/null 2>&1 &
    
    log "Chromium started, waiting for it to be ready..."
    sleep 5
    
    # Wait for debugger to be available
    local max_attempts=30
    local attempt=0
    while ! curl -s http://127.0.0.1:9222/json >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            log "ERROR: Chromium debugger not available"
            exit 1
        fi
        sleep 1
    done
    log "Chromium debugger is ready"
}

setup_bridge() {
    log "Setting up VDO.ninja bridge..."
    
    cd "$PROJECT_DIR"
    
    # Run the setup script via Node.js
    node -e "
const http = require('http');
const puppeteer = require('puppeteer-core');

const ROOM = '$ROOM_NAME';
const HOST = '$VDONINJA_HOST';
const LABEL = '$CAMERA_LABEL';
const PUSH_ID = '$CAMERA_PUSH_ID';

async function getDebuggerEndpoint() {
    return new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9222/json/version', (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
    });
}

async function main() {
    const version = await getDebuggerEndpoint();
    const browser = await puppeteer.connect({ browserWSEndpoint: version.webSocketDebuggerUrl });
    const pages = await browser.pages();
    const whepPage = pages[0];
    
    // 1. Play the video
    console.log('Playing WHEP video...');
    await whepPage.evaluate(() => {
        const video = document.querySelector('video');
        if (video) video.click();
    });
    await new Promise(r => setTimeout(r, 2000));
    
    // 2. Dismiss any dialogs
    await whepPage.keyboard.press('Escape').catch(() => {});
    
    // 3. Open Director tab
    console.log('Opening Director...');
    const dirPage = await browser.newPage();
    await dirPage.goto('https://' + HOST + '/?director=' + ROOM, { 
        waitUntil: 'networkidle2', 
        timeout: 30000 
    });
    await new Promise(r => setTimeout(r, 2000));
    
    // 4. Open screen share page
    console.log('Opening screen share page...');
    const sharePage = await browser.newPage();
    await sharePage.goto('https://' + HOST + '/?push=' + PUSH_ID + '&room=' + ROOM + '&screenshare&label=' + LABEL, { 
        waitUntil: 'networkidle2', 
        timeout: 30000 
    });
    await new Promise(r => setTimeout(r, 2000));
    
    // 5. Click the SELECT SCREEN TO SHARE button
    console.log('Clicking SELECT SCREEN button...');
    await sharePage.evaluate(() => {
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {
            if (btn.textContent.includes('SELECT') || btn.textContent.includes('SCREEN')) {
                btn.click();
                return true;
            }
        }
        // Try the green button by ID
        const selectBtn = document.getElementById('getScreenShareButton');
        if (selectBtn) selectBtn.click();
    });
    
    // Wait for picker to appear
    await new Promise(r => setTimeout(r, 2000));
    
    console.log('Bridge setup complete. Screen picker should be open.');
    console.log('Use xdotool to complete the selection.');
    
    browser.disconnect();
}

main().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
});
"
    
    log "Puppeteer setup complete, using xdotool for picker..."
    
    # Wait for picker dialog to appear
    sleep 3
    
    # The Chrome tab picker dialog appears in the center of the screen
    # Screen is 1920x1080, dialog is approximately centered
    # Tab list items are around x=620, first item at y=230, second at y=258
    # Share button is around x=877, y=549
    
    log "Clicking on WHEP tab in picker (second item)..."
    xdotool mousemove 620 258
    sleep 0.2
    xdotool click 1
    sleep 0.5
    
    log "Clicking Share button..."
    xdotool mousemove 877 549
    sleep 0.2
    xdotool click 1
    sleep 1
    
    log "Screen share selection complete"
}

verify_bridge() {
    log "Verifying bridge is working..."
    
    # Check if screen sharing is active by looking at Chromium tabs
    local tabs=$(curl -s http://127.0.0.1:9222/json 2>/dev/null | grep -c '"title"' || echo "0")
    
    if [ "$tabs" -ge 3 ]; then
        log "SUCCESS: Bridge appears to be running ($tabs tabs open)"
        return 0
    else
        log "WARNING: Expected 3+ tabs, found $tabs"
        return 1
    fi
}

main() {
    log "=========================================="
    log "Starting VDO.ninja Bridge for room: $ROOM_NAME"
    log "=========================================="
    
    wait_for_display
    wait_for_network
    start_chromium
    setup_bridge
    verify_bridge
    
    log "VDO.ninja bridge startup complete!"
    log "Director URL: https://$VDONINJA_HOST/?director=$ROOM_NAME"
    log "Scene URL: https://$VDONINJA_HOST/?scene&room=$ROOM_NAME"
}

main "$@"

