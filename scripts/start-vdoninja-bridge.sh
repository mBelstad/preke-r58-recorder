#!/bin/bash
# VDO.ninja Bridge Auto-Start Script (Simplified with &whepshare)
# Uses VDO.ninja's &whepshare parameter to share WHEP streams directly
# No screen sharing or complex automation required!

set -e

# Configuration - can be overridden by environment variables
# Must match VDO_ROOM in packages/frontend/src/lib/vdoninja.ts
ROOM_NAME="${VDONINJA_ROOM:-studio}"
VDONINJA_HOST="${VDONINJA_HOST:-r58-vdo.itagenten.no}"
API_HOST="${API_HOST:-app.itagenten.no}"
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

url_encode() {
    python3 -c "import urllib.parse; print(urllib.parse.quote('$1', safe=''))"
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
        
        # URL encode the WHEP URL (format: /{stream_id}/whep)
        local whep_url="https://$API_HOST/$stream_id/whep"
        local encoded_whep=$(url_encode "$whep_url")
        
        # Build the VDO.ninja URL with &whepshare
        # &videodevice=0&audiodevice=0 disables local devices
        # &nopreview disables local video preview (saves CPU/memory on R58)
        # &cleanoutput removes UI clutter
        # &b64css hides video element completely to save GPU (CSS: video { display: none !important; })
        # &autostart automatically starts streaming
        # &password is required to join the same authenticated room as the director
        local hide_video_css="b64:dmlkZW8geyBkaXNwbGF5OiBub25lICFpbXBvcnRhbnQ7IH0="
        local vdo_url="https://$VDONINJA_HOST/?push=$push_id&room=$ROOM_NAME&password=preke-r58-2024&whepshare=$encoded_whep&label=$label&videodevice=0&audiodevice=0&nopreview&cleanoutput&css=$hide_video_css&autostart"
        urls="$urls $vdo_url"
        
        log "Camera: $label -> $whep_url"
    done
    
    # Add the director URL with password (required to be the actual director)
    local director_url="https://$VDONINJA_HOST/?director=$ROOM_NAME&password=preke-r58-2024"
    
    # Start Chromium with all URLs
    # Key flags:
    # --use-fake-ui-for-media-stream: Auto-allow camera/mic without prompts
    # --autoplay-policy=no-user-gesture-required: Allow autoplay
    # --disable-features=TranslateUI: No translation popups
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
        --disable-popup-blocking \
        --start-maximized \
        $urls \
        >/dev/null 2>&1 &
    # Note: director tab removed - Electron app is the director
    
    CHROMIUM_PID=$!
    log "Chromium started (PID: $CHROMIUM_PID), waiting for it to be ready..."
    sleep 3  # Reduced from 5s (conservative reduction)
    
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

auto_click_start() {
    log "Auto-clicking START buttons..."
    
    cd "$PROJECT_DIR"
    
    # Use Node.js/Puppeteer to click the START buttons
    # This handles the case where &autostart doesn't fully work
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
                await new Promise(r => setTimeout(r, 2000));
                
                // Check if already in room (has hang up button)
                const inRoom = await page.evaluate(() => {
                    return !!document.querySelector('[title*=\"Hang up\"]') || 
                           !!document.querySelector('[aria-label*=\"Hang up\"]');
                });
                
                if (inRoom) {
                    console.log('  -> Already in room');
                    continue;
                }
                
                // Click 'Join Room with Camera' button if visible
                const joinClicked = await page.evaluate(() => {
                    // Try clicking the button directly
                    const buttons = Array.from(document.querySelectorAll('button, [role=\"button\"]'));
                    for (const btn of buttons) {
                        const text = btn.textContent || btn.innerText || '';
                        if (text.includes('Join Room with Camera')) {
                            btn.click();
                            return true;
                        }
                    }
                    // Try heading click
                    const headings = Array.from(document.querySelectorAll('h2'));
                    for (const h of headings) {
                        if (h.textContent.includes('Join Room with Camera')) {
                            h.parentElement?.click();
                            return true;
                        }
                    }
                    return false;
                });
                
                if (joinClicked) {
                    console.log('  -> Clicked Join Room with Camera');
                    await new Promise(r => setTimeout(r, 3000));
                }
                
                // Now click START button
                const startClicked = await page.evaluate(() => {
                    // Try by ID first
                    const startBtn = document.getElementById('gowebcam');
                    if (startBtn) {
                        startBtn.click();
                        return 'by-id';
                    }
                    // Try by text content
                    const buttons = Array.from(document.querySelectorAll('button, [role=\"button\"]'));
                    for (const btn of buttons) {
                        const text = btn.textContent || btn.innerText || '';
                        if (text.toUpperCase().includes('START')) {
                            btn.click();
                            return 'by-text';
                        }
                    }
                    return false;
                });
                
                if (startClicked) {
                    console.log('  -> Clicked START (' + startClicked + ')');
                } else {
                    console.log('  -> Could not find START button (may already be streaming)');
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
    
    log "Auto-click complete"
}

verify_bridge() {
    log "Verifying bridge is working..."
    
    # Check tabs
    local tabs=$(curl -s http://127.0.0.1:9222/json 2>/dev/null | grep -c '"title"' || echo "0")
    local expected=$(($(echo "$CAMERAS" | tr ',' '\n' | wc -l)))  # cameras only - director in Electron
    
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
    log "Cameras: $CAMERAS"
    log "=========================================="
    
    wait_for_display
    wait_for_network
    wait_for_mediamtx
    start_chromium
    auto_click_start
    verify_bridge
    show_urls
    
    log "VDO.ninja bridge startup complete!"
}

main "$@"
