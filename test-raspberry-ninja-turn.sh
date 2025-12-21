#!/bin/bash
# Test raspberry.ninja with Cloudflare TURN
# This script will run on R58

set -e

echo "=== Raspberry.Ninja TURN Test ==="
echo ""

# Get TURN credentials
echo "Fetching TURN credentials..."
TURN_DATA=$(curl -s https://recorder.itagenten.no/api/turn-credentials)
USERNAME=$(echo "$TURN_DATA" | jq -r '.iceServers[1].username')
CREDENTIAL=$(echo "$TURN_DATA" | jq -r '.iceServers[1].credential')

echo "Username: $USERNAME"
echo "Credential: ${CREDENTIAL:0:20}..."
echo ""

# Stop existing service if running
echo "Stopping existing ninja-publish-cam1 service..."
sudo systemctl stop ninja-publish-cam1 || true
sleep 2

# Run raspberry.ninja with TURN
echo "Starting raspberry.ninja with TURN..."
echo "Stream ID: r58-cam1-turn-test"
echo "Room: turn-test-room"
echo "Server: wss://wss.vdo.ninja:443"
echo ""

cd /opt/raspberry_ninja
/opt/preke-r58-recorder/venv/bin/python3 publish.py \
    --v4l2 /dev/video60 \
    --streamid r58-cam1-turn-test \
    --room turn-test-room \
    --server wss://wss.vdo.ninja:443 \
    --h264 --bitrate 4000 \
    --width 1920 --height 1080 \
    --framerate 30 \
    --noaudio \
    --turn-server "turns://${USERNAME}:${CREDENTIAL}@turn.cloudflare.com:5349" \
    --stun-server "stun://stun.cloudflare.com:3478" \
    --ice-transport-policy all

