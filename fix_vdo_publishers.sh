#!/bin/bash
# Fix VDO.ninja publisher services - remove password hashing and salt

set -e

echo "🔧 Fixing VDO.ninja publisher services..."

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
ExecStart=/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py --server wss://localhost:8443 --room r58studio --password false --turn-server "turns://g043f56439a8c4bf3c483c737bf1ecb06c41c79fa6946193495d6a6ed4989a5b:86020d5428a1465a3cd1d8aded2dd3b47623ffccee03c8a96d39c68f6e0f2e10@turn.cloudflare.com:5349" --stun-server "stun://stun.cloudflare.com:3478" \
    --v4l2 /dev/video60 \
    --streamid r58-cam1 \
     \
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
ExecStart=/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py --server wss://localhost:8443 --room r58studio --password false --turn-server "turns://g043f56439a8c4bf3c483c737bf1ecb06c41c79fa6946193495d6a6ed4989a5b:86020d5428a1465a3cd1d8aded2dd3b47623ffccee03c8a96d39c68f6e0f2e10@turn.cloudflare.com:5349" --stun-server "stun://stun.cloudflare.com:3478" \
    --v4l2 /dev/video11 \
    --streamid r58-cam2 \
     \
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
ExecStart=/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py --server wss://localhost:8443 --room r58studio --password false --turn-server "turns://g043f56439a8c4bf3c483c737bf1ecb06c41c79fa6946193495d6a6ed4989a5b:86020d5428a1465a3cd1d8aded2dd3b47623ffccee03c8a96d39c68f6e0f2e10@turn.cloudflare.com:5349" --stun-server "stun://stun.cloudflare.com:3478" \
    --v4l2 /dev/video22 \
    --streamid r58-cam3 \
     \
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
echo "📊 Checking service status..."

# Check status
sudo systemctl status ninja-publish-cam1 --no-pager | head -10
sudo systemctl status ninja-publish-cam2 --no-pager | head -10
sudo systemctl status ninja-publish-cam3 --no-pager | head -10

echo ""
echo "🔍 Checking stream IDs in logs..."
sleep 2
sudo journalctl -u ninja-publish-cam1 --since "10 seconds ago" --no-pager | grep streamID | tail -3

echo ""
echo "✅ Done! Check the stream IDs above - they should be r58-cam1, r58-cam2, r58-cam3 (no hash suffix)"

