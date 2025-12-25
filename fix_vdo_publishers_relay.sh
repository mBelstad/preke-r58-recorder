#!/bin/bash
# Fix VDO.ninja publisher services - Force TURN relay mode for FRP compatibility
# This forces all WebRTC traffic through the TURN server (TCP), bypassing UDP issues

set -e

echo "🔧 Configuring VDO.ninja publishers for TURN relay mode..."

# Update ninja-publish-cam1.service
cat > /tmp/ninja-publish-cam1.service << 'EOF'
[Unit]
Description=Raspberry Ninja Publisher - Camera 1 (HDMI N60) to VDO.Ninja
After=network.target vdo-ninja.service
Wants=vdo-ninja.service

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/raspberry_ninja
Environment="PATH=/opt/preke-r58-recorder/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --server wss://localhost:8443 \
    --room r58studio \
    --password false \
    --turn-server "turns://g043f56439a8c4bf3c483c737bf1ecb06c41c79fa6946193495d6a6ed4989a5b:86020d5428a1465a3cd1d8aded2dd3b47623ffccee03c8a96d39c68f6e0f2e10@turn.cloudflare.com:5349" \
    --stun-server "stun://stun.cloudflare.com:3478" \
    --ice-transport-policy relay \
    --v4l2 /dev/video60 \
    --streamid r58-cam1 \
    --noaudio \
    --h264 \
    --bitrate 8000 \
    --width 1920 \
    --height 1080 \
    --framerate 30 \
    --nored
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Update ninja-publish-cam2.service
cat > /tmp/ninja-publish-cam2.service << 'EOF'
[Unit]
Description=Raspberry Ninja Publisher - Camera 2 (HDMI N11) to VDO.Ninja
After=network.target vdo-ninja.service
Wants=vdo-ninja.service

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/raspberry_ninja
Environment="PATH=/opt/preke-r58-recorder/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --server wss://localhost:8443 \
    --room r58studio \
    --password false \
    --turn-server "turns://g043f56439a8c4bf3c483c737bf1ecb06c41c79fa6946193495d6a6ed4989a5b:86020d5428a1465a3cd1d8aded2dd3b47623ffccee03c8a96d39c68f6e0f2e10@turn.cloudflare.com:5349" \
    --stun-server "stun://stun.cloudflare.com:3478" \
    --ice-transport-policy relay \
    --v4l2 /dev/video11 \
    --streamid r58-cam2 \
    --noaudio \
    --h264 \
    --bitrate 8000 \
    --width 1920 \
    --height 1080 \
    --framerate 30 \
    --nored
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Update ninja-publish-cam3.service
cat > /tmp/ninja-publish-cam3.service << 'EOF'
[Unit]
Description=Raspberry Ninja Publisher - Camera 3 (HDMI N21) to VDO.Ninja
After=network.target vdo-ninja.service
Wants=vdo-ninja.service

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/raspberry_ninja
Environment="PATH=/opt/preke-r58-recorder/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --server wss://localhost:8443 \
    --room r58studio \
    --password false \
    --turn-server "turns://g043f56439a8c4bf3c483c737bf1ecb06c41c79fa6946193495d6a6ed4989a5b:86020d5428a1465a3cd1d8aded2dd3b47623ffccee03c8a96d39c68f6e0f2e10@turn.cloudflare.com:5349" \
    --stun-server "stun://stun.cloudflare.com:3478" \
    --ice-transport-policy relay \
    --v4l2 /dev/video22 \
    --streamid r58-cam3 \
    --noaudio \
    --h264 \
    --bitrate 8000 \
    --width 1920 \
    --height 1080 \
    --framerate 30 \
    --nored
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service files created in /tmp/"
echo ""
echo "📦 Deploying to R58..."

# Copy files to R58
sudo cp /tmp/ninja-publish-cam1.service /etc/systemd/system/
sudo cp /tmp/ninja-publish-cam2.service /etc/systemd/system/
sudo cp /tmp/ninja-publish-cam3.service /etc/systemd/system/

echo "✅ Service files deployed"
echo ""
echo "🔄 Reloading systemd and restarting services..."

# Reload systemd
sudo systemctl daemon-reload

# Restart services
sudo systemctl restart ninja-publish-cam1
sudo systemctl restart ninja-publish-cam2
sudo systemctl restart ninja-publish-cam3

echo "✅ Services restarted"
echo ""
echo "⏳ Waiting 5 seconds for services to initialize..."
sleep 5

echo ""
echo "📊 Checking service status..."
sudo systemctl is-active ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3

echo ""
echo "🔍 Checking for TURN relay configuration in logs..."
sudo journalctl -u ninja-publish-cam1 --since "10 seconds ago" --no-pager | grep -iE "turn|relay|ice|transport" | tail -10

echo ""
echo "✅ Done! Publishers configured with --ice-transport-policy relay"
echo ""
echo "📝 This forces all WebRTC traffic through the Cloudflare TURN server (TCP)"
echo "   which should work through FRP since it only uses TCP/TLS connections."

