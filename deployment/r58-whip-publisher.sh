#!/bin/bash
# R58 WHIP Publisher to Coolify MediaMTX
# Publishes camera streams from R58 to central relay server

set -e

# Configuration
COOLIFY_URL="https://vdo.itagenten.no:8889"
CAMERAS=("cam0" "cam2" "cam3")  # cam1 not connected
LOCAL_RTSP="rtsp://localhost:8554"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 R58 → Coolify WHIP Publisher"
echo "================================"
echo ""

# Check if gstreamer is installed
if ! command -v gst-launch-1.0 &> /dev/null; then
    echo -e "${RED}❌ GStreamer not found${NC}"
    echo "Installing GStreamer with WHIP support..."
    sudo apt-get update
    sudo apt-get install -y \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav
    echo -e "${GREEN}✅ GStreamer installed${NC}"
fi

# Function to start WHIP publisher for a camera
start_whip_publisher() {
    local cam=$1
    local rtsp_url="${LOCAL_RTSP}/${cam}"
    local whip_url="${COOLIFY_URL}/${cam}/whip"
    
    echo -e "${YELLOW}📹 Starting publisher for ${cam}...${NC}"
    echo "   RTSP: ${rtsp_url}"
    echo "   WHIP: ${whip_url}"
    
    # Check if camera is available
    if ! curl -s "http://localhost:9997/v3/paths/get/${cam}" | grep -q "ready.*true"; then
        echo -e "${RED}   ❌ Camera ${cam} not ready${NC}"
        return 1
    fi
    
    # Start GStreamer WHIP publisher in background
    # Using rtspsrc → h264parse → webrtcbin for WHIP
    gst-launch-1.0 -v \
        rtspsrc location="${rtsp_url}" latency=0 ! \
        rtph264depay ! \
        h264parse ! \
        avdec_h264 ! \
        videoconvert ! \
        x264enc tune=zerolatency bitrate=6000 speed-preset=ultrafast ! \
        rtph264pay config-interval=1 pt=96 ! \
        webrtcbin name=sendonly bundle-policy=max-bundle \
            stun-server=stun://stun.l.google.com:19302 \
            signaller::whip-endpoint="${whip_url}" \
        > "/var/log/whip-${cam}.log" 2>&1 &
    
    local pid=$!
    echo "${pid}" > "/var/run/whip-${cam}.pid"
    echo -e "${GREEN}   ✅ Started (PID: ${pid})${NC}"
    
    return 0
}

# Function to stop WHIP publisher
stop_whip_publisher() {
    local cam=$1
    local pid_file="/var/run/whip-${cam}.pid"
    
    if [ -f "${pid_file}" ]; then
        local pid=$(cat "${pid_file}")
        if kill -0 "${pid}" 2>/dev/null; then
            echo -e "${YELLOW}⏹️  Stopping ${cam} publisher (PID: ${pid})...${NC}"
            kill "${pid}"
            rm "${pid_file}"
            echo -e "${GREEN}   ✅ Stopped${NC}"
        else
            echo -e "${YELLOW}   ℹ️  Process already stopped${NC}"
            rm "${pid_file}"
        fi
    else
        echo -e "${YELLOW}   ℹ️  No PID file found${NC}"
    fi
}

# Function to check status
check_status() {
    echo "📊 Publisher Status:"
    echo "==================="
    
    for cam in "${CAMERAS[@]}"; do
        local pid_file="/var/run/whip-${cam}.pid"
        if [ -f "${pid_file}" ]; then
            local pid=$(cat "${pid_file}")
            if kill -0 "${pid}" 2>/dev/null; then
                echo -e "${GREEN}✅ ${cam}: Running (PID: ${pid})${NC}"
                # Check if stream is active on Coolify
                if curl -s "${COOLIFY_URL}/${cam}" | grep -q "video"; then
                    echo -e "   ${GREEN}📡 Stream active on Coolify${NC}"
                else
                    echo -e "   ${YELLOW}⚠️  Stream may not be reaching Coolify${NC}"
                fi
            else
                echo -e "${RED}❌ ${cam}: Dead process${NC}"
            fi
        else
            echo -e "${RED}❌ ${cam}: Not running${NC}"
        fi
    done
}

# Main command handling
case "${1:-start}" in
    start)
        echo "🚀 Starting WHIP publishers..."
        for cam in "${CAMERAS[@]}"; do
            start_whip_publisher "${cam}" || echo -e "${YELLOW}⚠️  Failed to start ${cam}${NC}"
        done
        echo ""
        sleep 3
        check_status
        ;;
    
    stop)
        echo "⏹️  Stopping WHIP publishers..."
        for cam in "${CAMERAS[@]}"; do
            stop_whip_publisher "${cam}"
        done
        ;;
    
    restart)
        echo "🔄 Restarting WHIP publishers..."
        $0 stop
        sleep 2
        $0 start
        ;;
    
    status)
        check_status
        ;;
    
    logs)
        cam="${2:-cam0}"
        echo "📋 Logs for ${cam}:"
        tail -f "/var/log/whip-${cam}.log"
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [cam]}"
        exit 1
        ;;
esac

exit 0







