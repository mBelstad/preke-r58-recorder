#!/bin/bash
# VDO.ninja Bridge Auto-Start Script (Simplified with &whepshare)
# This script opens browser tabs that share WHEP streams to VDO.ninja rooms
# No screen sharing required - uses VDO.ninja's &whepshare parameter

set -e

# Configuration - can be overridden by environment variables
ROOM_NAME="${VDONINJA_ROOM:-r58studio}"
VDONINJA_HOST="${VDONINJA_HOST:-r58-vdo.itagenten.no}"
API_HOST="${API_HOST:-r58-api.itagenten.no}"
LOG_FILE="${LOG_FILE:-/var/log/vdoninja-bridge.log}"

# Camera configuration - each camera gets its own entry
# Format: "stream_id:push_id:label"
# stream_id = MediaMTX stream name (e.g., cam2)
# push_id = VDO.ninja push ID (e.g., hdmi1)  
# label = Display name in VDO.ninja
CAMERAS="${CAMERAS:-cam2:hdmi1:HDMI-Camera-1}"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

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

wait_for_mediamtx() {
    log "Waiting for MediaMTX streams..."
    local max_attempts=30
    local attempt=0
    while ! curl -s --connect-timeout 2 "https://$API_HOST/api/status" >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            log "WARNING: API not responding, continuing anyway..."
            return 0
        fi
        sleep 2
    done
    log "MediaMTX is available"
}

start_chromium() {
    log "Starting Chromium..."
    
    # Kill any existing Chromium instances
    pkill -f chromium 2>/dev/null || true
    sleep 2
    
    # Build camera URLs
    local urls=""
    IFS=',' read -ra CAMERA_ARRAY <<< "$CAMERAS"
    for camera in "${CAMERA_ARRAY[@]}"; do
        IFS=':' read -r stream_id push_id label <<< "$camera"
        
        # URL encode the WHEP URL
        local whep_url="https://$API_HOST/whep/$stream_id"
        local encoded_whep=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$whep_url', safe=''))")
        
        # Build the VDO.ninja URL with &whepshare
        local vdo_url="https://$VDONINJA_HOST/?push=$push_id&room=$ROOM_NAME&whepshare=$encoded_whep&label=$label&webcam"
        urls="$urls $vdo_url"
        
        log "Camera: $label -> $whep_url"
    done
    
    # Also add the director URL
    local director_url="https://$VDONINJA_HOST/?director=$ROOM_NAME"
    
    # Start Chromium with all URLs
    log "Opening browser tabs..."
    nohup chromium \
        --remote-debugging-port=9222 \
        --disable-infobars \
        --no-first-run \
        --disable-session-crashed-bubble \
        --disable-features=TranslateUI \
        --autoplay-policy=no-user-gesture-required \
        --use-fake-ui-for-media-stream \
        --disable-notifications \
        $director_url $urls \
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

auto_join_rooms() {
    log "Auto-joining camera streams to room..."
    
    cd "$PROJECT_DIR"
    
    # Use Node.js/Puppeteer to click the START buttons
    node -e "
const http = require('http');
const puppeteer = require('puppeteer-core');

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
    console.log('Connecting to Chromium...');
    const version = await getDebuggerEndpoint();
    const browser = await puppeteer.connect({ browserWSEndpoint: version.webSocketDebuggerUrl });
    const pages = await browser.pages();
    
    console.log('Found ' + pages.length + ' tabs');
    
    for (const page of pages) {
        const url = page.url();
        console.log('Checking: ' + url);
        
        // Skip director page
        if (url.includes('director=')) {
            console.log('  -> Director page, skipping');
            continue;
        }
        
        // For whepshare pages, click 'Join Room with Camera' then START
        if (url.includes('whepshare=')) {
            console.log('  -> WHEP share page, auto-joining...');
            
            try {
                await page.bringToFront();
                await new Promise(r => setTimeout(r, 1000));
                
                // Click 'Join Room with Camera' button if visible
                const joinClicked = await page.evaluate(() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        if (btn.textContent.includes('Join Room with Camera')) {
                            btn.click();
                            return true;
                        }
                    }
                    // Also try heading click
                    const headings = Array.from(document.querySelectorAll('h2'));
                    for (const h of headings) {
                        if (h.textContent.includes('Join Room with Camera')) {
                            h.parentElement.click();
                            return true;
                        }
                    }
                    return false;
                });
                
                if (joinClicked) {
                    console.log('  -> Clicked Join Room with Camera');
                    await new Promise(r => setTimeout(r, 2000));
                }
                
                // Now click START button
                const startClicked = await page.evaluate(() => {
                    // Try by ID first
                    const startBtn = document.getElementById('gowebcam');
                    if (startBtn) {
                        startBtn.click();
                        return true;
                    }
                    // Try by text
                    const buttons = Array.from(document.querySelectorAll('button'));
                    for (const btn of buttons) {
                        if (btn.textContent.includes('START') || btn.textContent.includes('Start')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                });
                
                if (startClicked) {
                    console.log('  -> Clicked START');
                } else {
                    console.log('  -> Could not find START button');
                }
                
                await new Promise(r => setTimeout(r, 2000));
            } catch (err) {
                console.error('  -> Error:', err.message);
            }
        }
    }
    
    console.log('Done setting up all cameras');
    browser.disconnect();
}

main().catch(err => {
    console.error('Error:', err.message);
    process.exit(1);
});
" 2>&1 | tee -a "$LOG_FILE"
    
    log "Auto-join complete"
}

verify_bridge() {
    log "Verifying bridge is working..."
    
    # Check tabs
    local tabs=$(curl -s http://127.0.0.1:9222/json 2>/dev/null | grep -c '"title"' || echo "0")
    local expected=$(($(echo "$CAMERAS" | tr ',' '\n' | wc -l) + 1))  # cameras + director
    
    if [ "$tabs" -ge "$expected" ]; then
        log "SUCCESS: Bridge is running ($tabs tabs open, expected $expected)"
        return 0
    else
        log "WARNING: Expected $expected tabs, found $tabs"
        return 1
    fi
}

show_urls() {
    log ""
    log "=========================================="
    log "VDO.ninja URLs:"
    log "=========================================="
    log "Director: https://$VDONINJA_HOST/?director=$ROOM_NAME"
    log "Scene:    https://$VDONINJA_HOST/?scene&room=$ROOM_NAME"
    log ""
    
    IFS=',' read -ra CAMERA_ARRAY <<< "$CAMERAS"
    for camera in "${CAMERA_ARRAY[@]}"; do
        IFS=':' read -r stream_id push_id label <<< "$camera"
        log "View $label: https://$VDONINJA_HOST/?view=$push_id&room=$ROOM_NAME"
    done
    log "=========================================="
}

main() {
    log ""
    log "=========================================="
    log "VDO.ninja WHEP Bridge Starting"
    log "Room: $ROOM_NAME"
    log "=========================================="
    
    wait_for_display
    wait_for_network
    wait_for_mediamtx
    start_chromium
    auto_join_rooms
    verify_bridge
    show_urls
    
    log "VDO.ninja bridge startup complete!"
}

main "$@"
