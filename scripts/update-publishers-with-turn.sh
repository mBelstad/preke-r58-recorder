#!/bin/bash

# Update raspberry.ninja publishers to use Cloudflare TURN
# This script updates the systemd service files to fetch and use TURN credentials

set -e

echo "=== Updating Camera Publishers with TURN ==="

# TURN API endpoint
TURN_API="https://api.r58.itagenten.no/turn-credentials"

# Backup existing service files
echo "Backing up existing service files..."
sudo cp /etc/systemd/system/ninja-publish-cam1.service /etc/systemd/system/ninja-publish-cam1.service.backup 2>/dev/null || true
sudo cp /etc/systemd/system/ninja-publish-cam2.service /etc/systemd/system/ninja-publish-cam2.service.backup 2>/dev/null || true
sudo cp /etc/systemd/system/ninja-publish-cam3.service /etc/systemd/system/ninja-publish-cam3.service.backup 2>/dev/null || true
sudo cp /etc/systemd/system/ninja-publish-cam4.service /etc/systemd/system/ninja-publish-cam4.service.backup 2>/dev/null || true

# Create a helper script to fetch TURN credentials and start publisher
cat > /opt/preke-r58-recorder/scripts/start-publisher-with-turn.sh << 'EOF'
#!/bin/bash

# Helper script to start raspberry.ninja publisher with TURN credentials
# Usage: start-publisher-with-turn.sh <cam-number> <video-device> <stream-id> <room>

CAM_NUM=$1
VIDEO_DEVICE=$2
STREAM_ID=$3
ROOM=$4
TURN_API="${TURN_API:-https://api.r58.itagenten.no/turn-credentials}"

echo "[Cam $CAM_NUM] Fetching TURN credentials..."

# Fetch TURN credentials
TURN_DATA=$(curl -s "$TURN_API" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$TURN_DATA" ]; then
    echo "[Cam $CAM_NUM] Warning: Failed to fetch TURN credentials, starting without TURN"
    TURN_SERVER=""
    STUN_SERVER="stun://stun.cloudflare.com:3478"
else
    # Extract credentials using basic text processing (no jq needed)
    # This is a simplified version - in production, use proper JSON parsing
    TURN_URL=$(echo "$TURN_DATA" | grep -o '"turns://[^"]*' | head -1 | sed 's/"//g')
    STUN_URL=$(echo "$TURN_DATA" | grep -o '"stun://[^"]*' | head -1 | sed 's/"//g')
    
    if [ -n "$TURN_URL" ]; then
        echo "[Cam $CAM_NUM] TURN credentials obtained"
        TURN_SERVER="--turn-server $TURN_URL"
        STUN_SERVER="--stun-server $STUN_URL"
    else
        echo "[Cam $CAM_NUM] Warning: Could not parse TURN credentials"
        TURN_SERVER=""
        STUN_SERVER="--stun-server stun://stun.cloudflare.com:3478"
    fi
fi

# Start publisher
echo "[Cam $CAM_NUM] Starting publisher: $STREAM_ID"
exec /opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --v4l2 "$VIDEO_DEVICE" \
    --streamid "$STREAM_ID" \
    --room "$ROOM" \
    --server wss://wss.vdo.ninja:443 \
    --h264 \
    --bitrate 4000 \
    --width 1920 \
    --height 1080 \
    --framerate 30 \
    --noaudio \
    $TURN_SERVER \
    $STUN_SERVER \
    --ice-transport-policy all
EOF

chmod +x /opt/preke-r58-recorder/scripts/start-publisher-with-turn.sh

# Update service files to use the helper script
for CAM in 1 2 3 4; do
    SERVICE_FILE="/etc/systemd/system/ninja-publish-cam${CAM}.service"
    
    if [ -f "$SERVICE_FILE" ]; then
        echo "Updating ninja-publish-cam${CAM}.service..."
        
        # Determine video device and stream ID
        case $CAM in
            1) VIDEO_DEV="/dev/video60"; STREAM_ID="r58-cam1" ;;
            2) VIDEO_DEV="/dev/video61"; STREAM_ID="r58-cam2" ;;
            3) VIDEO_DEV="/dev/video62"; STREAM_ID="r58-cam3" ;;
            4) VIDEO_DEV="/dev/video63"; STREAM_ID="r58-cam4" ;;
        esac
        
        # Create new service file
        sudo tee "$SERVICE_FILE" > /dev/null << SERVICEEOF
[Unit]
Description=VDO.Ninja Publisher - Camera $CAM
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/preke-r58-recorder
Environment="PATH=/opt/preke-r58-recorder/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="TURN_API=https://api.r58.itagenten.no/turn-credentials"
ExecStart=/opt/preke-r58-recorder/scripts/start-publisher-with-turn.sh $CAM $VIDEO_DEV $STREAM_ID r58-production
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICEEOF
    fi
done

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo ""
echo "=== Update Complete ==="
echo ""
echo "Services updated:"
echo "  - ninja-publish-cam1.service"
echo "  - ninja-publish-cam2.service"
echo "  - ninja-publish-cam3.service"
echo "  - ninja-publish-cam4.service"
echo ""
echo "To restart services:"
echo "  sudo systemctl restart ninja-publish-cam1"
echo "  sudo systemctl restart ninja-publish-cam2"
echo "  sudo systemctl restart ninja-publish-cam3"
echo "  sudo systemctl restart ninja-publish-cam4"
echo ""
echo "To check status:"
echo "  sudo systemctl status ninja-publish-cam1"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u ninja-publish-cam1 -f"

