#!/bin/bash
# Prepare extra sources (Reveal.js, graphics) for VDO.ninja bridge
# This script starts any configured extra sources before the bridge runs

set -e

API_HOST="${API_HOST:-localhost:8000}"
EXTRA_SOURCES="${EXTRA_SOURCES:-}"
LOG_FILE="${LOG_FILE:-/var/log/vdoninja-bridge.log}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [prepare] $*" | tee -a "$LOG_FILE"
}

build_api_base() {
    if [[ "$API_HOST" == http* ]]; then
        echo "$API_HOST"
        return
    fi
    if [[ "$API_HOST" == "localhost"* ]] || [[ "$API_HOST" == "127.0.0.1"* ]]; then
        echo "http://$API_HOST"
        return
    fi
    echo "https://$API_HOST"
}

start_reveal_source() {
    local stream_id="$1"
    local label="$2"
    local api_base
    api_base="$(build_api_base)"
    
    log "Starting Reveal.js source: $stream_id ($label)"
    
    # Check if the source is a known Reveal.js output
    case "$stream_id" in
        slides|slides_overlay)
            # Start the Reveal.js source via API
            # Use a default presentation URL - can be customized
            local presentation_url="http://localhost:8000/reveal/graphics"
            
            # Try to start the Reveal.js output
            local response
            response=$(curl -s -X POST \
                "${api_base}/api/reveal/${stream_id}/start?presentation_id=${stream_id}&url=${presentation_url}" \
                -H "Content-Type: application/json" \
                --connect-timeout 5 \
                --max-time 10 \
                2>/dev/null || echo '{"error": "request failed"}')
            
            if echo "$response" | grep -q '"success".*true\|"output_id"'; then
                log "  Started Reveal.js output: $stream_id"
                return 0
            elif echo "$response" | grep -q "already running"; then
                log "  Reveal.js output already running: $stream_id"
                return 0
            else
                log "  Warning: Could not start Reveal.js output $stream_id: $response"
                return 1
            fi
            ;;
        *)
            # Unknown source type - check if MediaMTX stream exists
            log "  Note: $stream_id is not a Reveal.js source, assuming external"
            return 0
            ;;
    esac
}

wait_for_api() {
    local api_base
    api_base="$(build_api_base)"
    
    log "Waiting for API at $api_base..."
    local max_attempts=30
    local attempt=0
    
    while ! curl -s --connect-timeout 2 "${api_base}/api/status" >/dev/null 2>&1; do
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            log "Warning: API not responding after $max_attempts attempts"
            return 1
        fi
        sleep 1
    done
    log "API is available"
    return 0
}

main() {
    log "Preparing extra sources for VDO.ninja bridge..."
    
    if [ -z "$EXTRA_SOURCES" ]; then
        log "No extra sources configured, skipping"
        exit 0
    fi
    
    log "Extra sources to prepare: $EXTRA_SOURCES"
    
    # Wait for API to be ready
    if ! wait_for_api; then
        log "Warning: API not available, extra sources may not start"
        exit 0  # Don't fail - let the bridge try anyway
    fi
    
    # Parse and start each extra source
    IFS=',' read -ra EXTRA_ARRAY <<< "$EXTRA_SOURCES"
    local started=0
    local failed=0
    
    for source in "${EXTRA_ARRAY[@]}"; do
        IFS=':' read -r stream_id push_id label <<< "$source"
        if start_reveal_source "$stream_id" "$label"; then
            started=$((started + 1))
        else
            failed=$((failed + 1))
        fi
    done
    
    # Give sources a moment to initialize
    if [ $started -gt 0 ]; then
        log "Waiting for sources to initialize..."
        sleep 3
    fi
    
    log "Preparation complete: $started started, $failed failed"
    exit 0
}

main "$@"
