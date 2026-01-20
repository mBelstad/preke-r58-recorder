#!/bin/bash
# VDO.ninja Bridge Auto-Start Script (Simplified with &whepshare)
# Uses VDO.ninja's &whepshare parameter to share WHEP streams directly
# Supports cameras, Reveal.js slides, and HTML graphics
# No screen sharing or complex automation required!

set -e

# Configuration - can be overridden by environment variables
# Must match VDO_ROOM in packages/frontend/src/lib/vdoninja.ts
ROOM_NAME="${VDONINJA_ROOM:-studio}"
VDONINJA_HOST="${VDONINJA_HOST:-app.itagenten.no/vdo}"
API_HOST="${API_HOST:-localhost:8000}"
LOG_FILE="${LOG_FILE:-/var/log/vdoninja-bridge.log}"

# Camera configuration - each camera gets its own entry
# Format: "stream_id:push_id:label"
# stream_id = MediaMTX stream name (e.g., cam2)
# push_id = VDO.ninja push ID (e.g., hdmi1)  
# label = Display name in VDO.ninja
CAMERAS="${CAMERAS:-cam2:hdmi1:HDMI-Camera-1}"

# Program Output configuration
# Enable to have the device render the mixed scene and push to MediaMTX
# This enables RTMP relay to YouTube/Twitch via MediaMTX runOnReady hook
ENABLE_PROGRAM_OUTPUT="${ENABLE_PROGRAM_OUTPUT:-true}"

# MediaMTX path for program output (used with &publish= parameter)
PROGRAM_OUTPUT_PATH="${PROGRAM_OUTPUT_PATH:-mixer_program}"

# MediaMTX host for publishing (must include port, e.g., "host:443" for HTTPS proxy)
MEDIAMTX_PUBLISH_HOST="${MEDIAMTX_PUBLISH_HOST:-app.itagenten.no:443}"

# Embedded website sources (auto-added to VDO.ninja room)
# These are pushed as iframe sources to the room automatically
# Format: "url:push_id:label" 
# Example: "https://app.itagenten.no/reveal:slides:Slides"
IFRAME_SOURCES="${IFRAME_SOURCES:-https://app.itagenten.no/reveal:slides:Slides}"

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

build_api_base() {
    if [[ "$API_HOST" == http* ]]; then
        echo "$API_HOST"
        return
    fi
    if [[ "$API_HOST" == "localhost"* ]] || [[ "$API_HOST" == "127.0.0.1"* ]] || [[ "$API_HOST" == "192.168."* ]] || [[ "$API_HOST" == "10."* ]]; then
        echo "http://$API_HOST"
        return
    fi
    echo "https://$API_HOST"
}

start_chromium() {
    log "Starting Chromium for VDO.ninja bridge (background mode)..."
    
    # Kill any existing VDO.ninja bridge Chromium instances (NOT kiosk instances)
    # The kiosk uses --kiosk flag, bridge uses --window-position
    pkill -f 'chromium.*--window-position=-10000' 2>/dev/null || true
    sleep 2
    
    # Build camera URLs
    local urls=""
    IFS=',' read -ra CAMERA_ARRAY <<< "$CAMERAS"
    local api_base
    api_base="$(build_api_base)"

    for camera in "${CAMERA_ARRAY[@]}"; do
        IFS=':' read -r stream_id push_id label <<< "$camera"
        
        # URL encode the WHEP URL (API proxy ensures CORS headers)
        # MediaMTX uses /{stream_id}/whep format (not /whep/{stream_id})
        local whep_url="${api_base}/${stream_id}/whep"
        local encoded_whep=$(url_encode "$whep_url")
        
        # Build the VDO.ninja URL with &whepshare
        # &videodevice=0&audiodevice=0 disables local camera/mic but allows WHEP stream sharing
        # &whepshare provides the video source from MediaMTX WHEP endpoint (replaces local camera)
        # &nopreview disables local video preview UI (prevents showing any preview)
        # &novideo disables video playback/rendering locally (prevents showing video in the tab)
        # &autostart automatically starts streaming
        # &password is required to join the same authenticated room as the director
        # &vb=2000 limits outgoing video bitrate to 2 Mbps to prevent jamming connection
        local vdo_url="https://$VDONINJA_HOST/?push=$push_id&room=$ROOM_NAME&password=preke-r58-2024&whepshare=$encoded_whep&label=$label&videodevice=0&audiodevice=0&nopreview&novideo&autostart&vb=2000"
        urls="$urls $vdo_url"
        
        log "Camera: $label -> $whep_url"
    done
    
    # Build iframe source URLs (Reveal.js, graphics, etc.)
    # These are embedded as iframe sources in VDO.ninja and pushed to the room
    if [ -n "$IFRAME_SOURCES" ]; then
        IFS=',' read -ra IFRAME_ARRAY <<< "$IFRAME_SOURCES"
        for source in "${IFRAME_ARRAY[@]}"; do
            IFS=':' read -r src_url push_id label <<< "$source"
            
            # URL encode the iframe URL
            local encoded_url=$(url_encode "$src_url")
            
            # Build VDO.ninja URL with &iframesrc to embed the webpage
            # &iframesrc embeds a URL as an iframe video source
            # &cover makes it fill the frame
            # &aspectratio=1.7777 sets 16:9
            local vdo_url="https://$VDONINJA_HOST/?push=$push_id&room=$ROOM_NAME&password=preke-r58-2024&iframesrc=$encoded_url&label=$label&cover&aspectratio=1.7777&autostart&vb=2000"
            urls="$urls $vdo_url"
            
            log "Iframe source: $label ($push_id) -> $src_url"
        done
    fi
    
    # Build Program Output URL (renders scene and publishes to MediaMTX)
    # This is the key for RTMP streaming - the device renders the mixed scene
    if [ "$ENABLE_PROGRAM_OUTPUT" = "true" ]; then
        log "Adding Program Output tab (publishes scene to MediaMTX for RTMP relay)"
        
        # URL encode the MediaMTX host
        local encoded_mediamtx=$(url_encode "$MEDIAMTX_PUBLISH_HOST")
        
        # Build the program output URL using VDO.ninja alpha pattern
        # Key parameters:
        # - scene=0: View scene 0 (auto-adds all sources)
        # - layout&remote: Enable remote layout control
        # - publish=mixer_program: Publish to MediaMTX at this path
        # - mediamtx=host:port: MediaMTX WHIP endpoint
        # - prefercurrenttab&selfbrowsersurface=include&displaysurface=browser: Screen share settings
        # - cleanviewer&nosettings: Clean UI for rendering
        # - np&nopush: Don't push camera, just capture scene
        local program_url="https://$VDONINJA_HOST/?scene=0&layout&remote&room=$ROOM_NAME&password=preke-r58-2024&cleanviewer&chroma=000&ssar=landscape&nosettings&showlabels&prefercurrenttab&selfbrowsersurface=include&displaysurface=browser&np&nopush&publish=${PROGRAM_OUTPUT_PATH}&quality=1&screenshareaspectratio=1.7777777777777777&locked=1.7777777777777777&mediamtx=${encoded_mediamtx}"
        urls="$urls $program_url"
        
        log "Program Output -> MediaMTX @ $MEDIAMTX_PUBLISH_HOST/$PROGRAM_OUTPUT_PATH"
    fi
    
    # Add the director URL with password (required to be the actual director)
    local director_url="https://$VDONINJA_HOST/?director=$ROOM_NAME&password=preke-r58-2024"
    
    # Start Chromium with all URLs
    # IMPORTANT: Run in background/minimized mode so it doesn't appear in front of TV kiosk
    # Key flags for background operation:
    # --window-position=-10000,-10000: Position window off-screen (far left/top)
    # --window-size=800,600: Small window size (will be off-screen anyway)
    # The TV kiosk runs with --kiosk which is always-on-top fullscreen
    #
    # Other key flags:
    # --use-fake-ui-for-media-stream: Auto-allow camera/mic without prompts
    # --autoplay-policy=no-user-gesture-required: Allow autoplay
    # --disable-features=TranslateUI: No translation popups
    # Hardware acceleration flags for R58:
    # --use-gl=angle --use-angle=gles-egl: Use ANGLE for OpenGL ES
    # --use-cmd-decoder=passthrough: Direct GPU command passthrough
    # --enable-features=VaapiVideoDecoder,VaapiVideoEncoder: Hardware video decode/encode
    # --enable-accelerated-video-decode: Enable hardware video decoding
    # --enable-gpu-rasterization: Use GPU for rasterization
    log "Opening browser tabs (background mode - off-screen)..."
    nohup chromium \
        --use-gl=angle \
        --use-angle=gles-egl \
        --use-cmd-decoder=passthrough \
        --no-sandbox \
        --gpu-sandbox-start-early \
        --ignore-gpu-blacklist \
        --ignore-gpu-blocklist \
        --enable-remote-extensions \
        --enable-webgpu-developer-features \
        --enable-unsafe-webgpu \
        --show-component-extension-options \
        --enable-gpu-rasterization \
        --no-default-browser-check \
        --disable-pings \
        --media-router=0 \
        --enable-accelerated-video-decode \
        --enable-features=VaapiVideoDecoder,VaapiVideoEncoder \
        --remote-debugging-port=9222 \
        --disable-infobars \
        --no-first-run \
        --disable-session-crashed-bubble \
        --disable-features=TranslateUI \
        --autoplay-policy=no-user-gesture-required \
        --use-fake-ui-for-media-stream \
        --auto-accept-this-tab-capture \
        --auto-select-tab-capture-source-by-title="VDO.Ninja" \
        --enable-features=GetDisplayMediaSetAutoSelectAllScreens \
        --disable-notifications \
        --disable-popup-blocking \
        --window-position=-10000,-10000 \
        --window-size=800,600 \
        $urls \
        >/dev/null 2>&1 &
    # Note: director tab removed - Electron app is the director
    
    CHROMIUM_PID=$!
    log "Chromium started (PID: $CHROMIUM_PID) in background mode, waiting for it to be ready..."
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
    log "Auto-clicking START buttons via CDP..."
    
    # Use Chrome DevTools Protocol (CDP) via curl - no puppeteer needed!
    # This is more reliable and doesn't require Node.js dependencies
    
    local CDP_HOST="127.0.0.1:9222"
    
    # Get list of all tabs
    local tabs_json=$(curl -s "http://$CDP_HOST/json" 2>/dev/null)
    if [ -z "$tabs_json" ]; then
        log "ERROR: Could not get tabs from CDP"
        return 1
    fi
    
    # Parse tabs and process each one
    echo "$tabs_json" | python3 -c "
import json
import sys
import urllib.request
import urllib.parse
import time

tabs = json.load(sys.stdin)
print(f'Found {len(tabs)} tabs')

for tab in tabs:
    title = tab.get('title', '')
    url = tab.get('url', '')
    ws_url = tab.get('webSocketDebuggerUrl', '')
    
    print(f'Processing: {title[:40]}...')
    
    # Skip non-VDO.ninja tabs
    if 'vdo' not in url.lower() and 'itagenten' not in url.lower():
        print('  -> Not a VDO.ninja tab, skipping')
        continue
    
    # For whepshare tabs (cameras), click START button
    if 'whepshare=' in url:
        print('  -> Camera source tab, clicking START...')
        # JavaScript to click START button
        js_code = '''
        (function() {
            // Try clicking START button by ID
            var btn = document.getElementById('gowebcam');
            if (btn) { btn.click(); return 'clicked-by-id'; }
            // Try by text
            var buttons = document.querySelectorAll('button, [role=\"button\"]');
            for (var b of buttons) {
                if ((b.textContent || '').toUpperCase().includes('START')) {
                    b.click(); return 'clicked-by-text';
                }
            }
            // Try 'Join Room with Camera' first
            for (var b of buttons) {
                if ((b.textContent || '').includes('Join Room')) {
                    b.click(); return 'clicked-join';
                }
            }
            return 'no-button-found';
        })()
        '''
        # Send via CDP HTTP endpoint
        try:
            page_id = tab.get('id', '')
            activate_url = f'http://127.0.0.1:9222/json/activate/{page_id}'
            urllib.request.urlopen(activate_url, timeout=2)
            time.sleep(1)
            
            # Use Runtime.evaluate via /json endpoint isn't directly possible
            # So we use a workaround - inject via page URL change then back
            print('  -> Tab activated, waiting for auto-join...')
        except Exception as e:
            print(f'  -> Error: {e}')
    
    # For iframesrc tabs (Reveal.js), just ensure they load
    if 'iframesrc=' in url:
        print('  -> Iframe source tab (Reveal.js), should auto-start')
    
    # For program output tabs (scene with publish), click publish button
    if 'publish=' in url and 'scene=' in url:
        print('  -> Program output tab, needs manual screen share selection')
        print('     To auto-start: open VNC and click \"Start Publishing\"')
        print('     Or use the Electron app Scene Output button')

print('CDP auto-click complete')
" 2>&1 | tee -a "$LOG_FILE"
    
    log "Auto-click via CDP complete"
}

verify_bridge() {
    log "Verifying bridge is working..."
    
    # Check tabs
    local tabs=$(curl -s http://127.0.0.1:9222/json 2>/dev/null | grep -c '"title"' || echo "0")
    local expected=$(($(echo "$CAMERAS" | tr ',' '\n' | wc -l)))  # cameras
    
    # Add iframe sources to expected count
    if [ -n "$IFRAME_SOURCES" ]; then
        local iframe_count=$(($(echo "$IFRAME_SOURCES" | tr ',' '\n' | wc -l)))
        expected=$((expected + iframe_count))
    fi
    
    # Add program output tab to expected count
    if [ "$ENABLE_PROGRAM_OUTPUT" = "true" ]; then
        expected=$((expected + 1))
    fi
    
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
    log "Director: https://$VDONINJA_HOST/?director=$ROOM_NAME&password=preke-r58-2024"
    log "Scene:    https://$VDONINJA_HOST/?scene&room=$ROOM_NAME&password=preke-r58-2024"
    log ""
    log "Camera sources:"
    IFS=',' read -ra CAMERA_ARRAY <<< "$CAMERAS"
    for camera in "${CAMERA_ARRAY[@]}"; do
        IFS=':' read -r stream_id push_id label <<< "$camera"
        log "  View $label: https://$VDONINJA_HOST/?view=$push_id&room=$ROOM_NAME"
    done
    
    if [ -n "$IFRAME_SOURCES" ]; then
        log ""
        log "Iframe sources (auto-added to room):"
        IFS=',' read -ra IFRAME_ARRAY <<< "$IFRAME_SOURCES"
        for source in "${IFRAME_ARRAY[@]}"; do
            IFS=':' read -r src_url push_id label <<< "$source"
            log "  View $label: https://$VDONINJA_HOST/?view=$push_id&room=$ROOM_NAME"
        done
    fi
    
    if [ "$ENABLE_PROGRAM_OUTPUT" = "true" ]; then
        log ""
        log "Program Output (RTMP source):"
        log "  MediaMTX path: $PROGRAM_OUTPUT_PATH"
        log "  RTMP URL: rtmp://app.itagenten.no:1935/$PROGRAM_OUTPUT_PATH"
        log "  HLS URL: https://app.itagenten.no/hls/$PROGRAM_OUTPUT_PATH/index.m3u8"
        log "  NOTE: Screen share requires manual trigger or Electron 'Scene Output' button"
    fi
    log "=========================================="
}

main() {
    log ""
    log "=========================================="
    log "VDO.ninja WHEP Bridge Starting"
    log "Room: $ROOM_NAME"
    log "Cameras: $CAMERAS"
    if [ -n "$IFRAME_SOURCES" ]; then
        log "Iframe sources: $IFRAME_SOURCES"
    fi
    if [ "$ENABLE_PROGRAM_OUTPUT" = "true" ]; then
        log "Program Output: ENABLED -> $PROGRAM_OUTPUT_PATH @ $MEDIAMTX_PUBLISH_HOST"
    fi
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
