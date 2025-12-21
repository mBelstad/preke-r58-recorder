#!/bin/bash
# Test raspberry.ninja with Cloudflare TURN - Final version

set -e

echo "=== Raspberry.Ninja TURN Test (Final) ==="
echo ""

# TURN credentials (valid for 24 hours)
USERNAME="g0257db38282e4d658dbe95077c3e86805de650dd48e3511e54bc2519bf96d06"
CREDENTIAL="1252a64dff3bce66c396efef9cf4cfd2dc40a8f8702acb12b4fc3543fa546af6"

echo "Using Cloudflare TURN credentials"
echo "Stream ID: r58cam1test"
echo "Room: turntestroom (alphanumeric only)"
echo ""

# Stop existing service if running
sudo systemctl stop ninja-publish-cam1 || true
sleep 2

# Run raspberry.ninja with TURN
cd /opt/raspberry_ninja
exec /opt/preke-r58-recorder/venv/bin/python3 publish.py \
    --v4l2 /dev/video60 \
    --streamid r58cam1test \
    --room turntestroom \
    --server wss://wss.vdo.ninja:443 \
    --h264 --bitrate 4000 \
    --width 1920 --height 1080 \
    --framerate 30 \
    --noaudio \
    --turn-server "turns://${USERNAME}:${CREDENTIAL}@turn.cloudflare.com:5349" \
    --stun-server "stun://stun.cloudflare.com:3478" \
    --ice-transport-policy all

