#!/bin/bash
# Test script for dynamic resolution adaptation
# This script helps monitor resolution changes in real-time

set -e

R58_HOST="${1:-r58.itagenten.no}"
R58_USER="${2:-linaro}"
R58_PASSWORD="${R58_PASSWORD:-linaro}"

echo "=== Dynamic Resolution Adaptation Test ==="
echo "Target: ${R58_USER}@${R58_HOST}"
echo ""

# Function to get current resolutions
get_resolutions() {
    echo "=== Current Resolutions (via API) ==="
    local response=$(curl -s -k "https://${R58_HOST}/api/preview/status" 2>/dev/null)
    if [ -n "$response" ]; then
        echo "$response" | python3 -m json.tool 2>/dev/null | grep -A 1 "formatted" | grep -v "^--$" || echo "API data available (see hardware detection below)"
    else
        echo "Could not fetch API data"
    fi
    echo ""
}

# Function to monitor logs
monitor_logs() {
    echo "=== Monitoring Service Logs (Ctrl+C to stop) ==="
    echo "Watching for resolution changes..."
    echo ""
    sshpass -p "${R58_PASSWORD}" ssh -o StrictHostKeyChecking=no "${R58_USER}@${R58_HOST}" \
        "sudo journalctl -u preke-recorder.service -f --since '1 minute ago'" | \
        grep --line-buffered -i "resolution\|tracking\|changed\|restarting\|successfully"
}

# Function to check subdev resolutions
check_subdevs() {
    echo "=== Hardware-Level Resolution Detection ==="
    sshpass -p "${R58_PASSWORD}" ssh -o StrictHostKeyChecking=no "${R58_USER}@${R58_HOST}" << 'EOF'
        echo "cam0 (subdev2):"
        v4l2-ctl -d /dev/v4l-subdev2 --get-subdev-fmt pad=0 2>/dev/null | grep "Width/Height" || echo "  No signal"
        
        echo "cam2 (subdev3):"
        v4l2-ctl -d /dev/v4l-subdev3 --get-subdev-fmt pad=0 2>/dev/null | grep "Width/Height" || echo "  No signal"
        
        echo "cam3 (subdev4):"
        v4l2-ctl -d /dev/v4l-subdev4 --get-subdev-fmt pad=0 2>/dev/null | grep "Width/Height" || echo "  No signal"
        
        echo "cam1 (video60 - direct HDMI):"
        v4l2-ctl -d /dev/video60 --get-fmt-video 2>/dev/null | grep "Width/Height" || echo "  No signal"
EOF
    echo ""
}

# Main menu
case "${3:-status}" in
    status)
        echo "Current system status:"
        echo ""
        get_resolutions
        check_subdevs
        echo "=== Instructions ==="
        echo "To test resolution changes:"
        echo "1. Note the current resolutions above"
        echo "2. Run: $0 $R58_HOST $R58_USER monitor"
        echo "3. Change HDMI source resolution (switch device, change settings, etc.)"
        echo "4. Watch for automatic detection and restart (~10 seconds)"
        echo ""
        ;;
    
    monitor)
        echo "Starting continuous monitoring..."
        echo "Change an HDMI source resolution now and watch for automatic adaptation."
        echo ""
        get_resolutions
        monitor_logs
        ;;
    
    check)
        while true; do
            clear
            echo "=== Live Resolution Monitor (refreshing every 5s) ==="
            date
            echo ""
            get_resolutions
            check_subdevs
            echo "Press Ctrl+C to stop"
            sleep 5
        done
        ;;
    
    *)
        echo "Usage: $0 [host] [user] [command]"
        echo ""
        echo "Commands:"
        echo "  status  - Show current resolutions (default)"
        echo "  monitor - Monitor logs for resolution changes"
        echo "  check   - Continuously check resolutions every 5s"
        echo ""
        echo "Example:"
        echo "  $0 r58.itagenten.no linaro monitor"
        ;;
esac

