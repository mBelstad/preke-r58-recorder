#!/bin/bash
# Recording Monitor Script
# Monitors active recording session and displays real-time stats

API_URL="http://recorder.itagenten.no/api/trigger/status"
INTERVAL=5  # seconds between checks

echo "=========================================="
echo "R58 Recording Monitor"
echo "=========================================="
echo ""

# Function to format bytes to human readable
format_bytes() {
    local bytes=$1
    if [ $bytes -gt 1073741824 ]; then
        echo "$(echo "scale=2; $bytes/1073741824" | bc) GB"
    elif [ $bytes -gt 1048576 ]; then
        echo "$(echo "scale=2; $bytes/1048576" | bc) MB"
    else
        echo "$(echo "scale=2; $bytes/1024" | bc) KB"
    fi
}

# Function to format seconds to HH:MM:SS
format_duration() {
    local seconds=$1
    printf "%02d:%02d:%02d" $((seconds/3600)) $((seconds%3600/60)) $((seconds%60))
}

while true; do
    # Get status
    STATUS=$(curl -s "$API_URL")
    
    # Parse JSON
    ACTIVE=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['active'])" 2>/dev/null)
    
    if [ "$ACTIVE" = "True" ]; then
        SESSION_ID=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)
        DURATION=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['duration'])" 2>/dev/null)
        FREE_GB=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['disk']['free_gb'])" 2>/dev/null)
        
        # Get camera statuses
        CAM1=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['cameras'].get('cam1', {}).get('status', 'N/A'))" 2>/dev/null)
        CAM2=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['cameras'].get('cam2', {}).get('status', 'N/A'))" 2>/dev/null)
        CAM3=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['cameras'].get('cam3', {}).get('status', 'N/A'))" 2>/dev/null)
        
        # Clear screen and display
        clear
        echo "=========================================="
        echo "🔴 RECORDING IN PROGRESS"
        echo "=========================================="
        echo ""
        echo "Session ID:    $SESSION_ID"
        echo "Duration:      $(format_duration $DURATION)"
        echo "Disk Free:     ${FREE_GB} GB"
        echo ""
        echo "Camera Status:"
        echo "  cam1: $CAM1"
        echo "  cam2: $CAM2"
        echo "  cam3: $CAM3"
        echo ""
        echo "Press Ctrl+C to stop monitoring"
        echo "=========================================="
        
        # Estimate file sizes (rough calculation: ~1 MB/sec per camera at 8 Mbps)
        ESTIMATED_SIZE=$(echo "scale=2; $DURATION * 3 / 1024" | bc)
        echo "Est. Size:     ~${ESTIMATED_SIZE} GB (3 cameras)"
        
    else
        clear
        echo "=========================================="
        echo "⚪ NO ACTIVE RECORDING"
        echo "=========================================="
        echo ""
        echo "Disk Free:     $(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['disk']['free_gb'])" 2>/dev/null) GB"
        echo ""
        echo "Press Ctrl+C to exit"
    fi
    
    sleep $INTERVAL
done

