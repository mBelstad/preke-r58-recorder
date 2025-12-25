#!/bin/bash
# VDO.ninja Service Fix Script
# Paste this entire script into your remote PC terminal

set -e

echo "=================================================="
echo "R58 VDO.ninja Service Recovery Script"
echo "=================================================="
echo ""

# Try to find R58 on network
echo "Step 1: Finding R58 device..."
R58_IP=""
for ip in "192.168.1.24" "192.168.1.25" "192.168.68.55" "10.58.0.1"; do
    echo -n "  Testing $ip... "
    if ping -c 1 -W 2 $ip &>/dev/null; then
        echo "✅ FOUND!"
        R58_IP=$ip
        break
    else
        echo "❌"
    fi
done

if [ -z "$R58_IP" ]; then
    echo ""
    echo "❌ ERROR: Could not find R58 device"
    echo "Please check:"
    echo "  1. R58 is powered on"
    echo "  2. Network cable is connected"
    echo "  3. This PC is on the same network"
    echo ""
    exit 1
fi

echo ""
echo "✅ R58 found at: $R58_IP"
echo ""

# SSH into R58 and fix services
echo "Step 2: Connecting to R58 and fixing services..."
echo ""

ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 linaro@$R58_IP << 'ENDSSH'
echo "=================================================="
echo "Connected to R58!"
echo "=================================================="
echo ""

# Check current status
echo "Step 3: Checking service status..."
echo ""
echo "VDO.ninja signaling server:"
systemctl is-active vdo-ninja && echo "  ✅ Active" || echo "  ❌ Inactive"

echo ""
echo "Camera publishers:"
systemctl is-active ninja-publish-cam1 && echo "  CAM1: ✅" || echo "  CAM1: ❌"
systemctl is-active ninja-publish-cam2 && echo "  CAM2: ✅" || echo "  CAM2: ❌"
systemctl is-active ninja-publish-cam3 && echo "  CAM3: ✅" || echo "  CAM3: ❌"

echo ""
echo "Preke-recorder:"
systemctl is-active preke-recorder && echo "  ✅ Active (conflicts with publishers)" || echo "  ✅ Inactive (good for VDO.ninja)"

echo ""
echo "=================================================="
echo "Step 4: Restarting VDO.ninja services..."
echo "=================================================="
echo ""

# Stop preke-recorder to free video devices
echo "→ Stopping preke-recorder (to free video devices)..."
sudo systemctl stop preke-recorder 2>/dev/null || true
sleep 2

# Restart VDO.ninja signaling server
echo "→ Restarting VDO.ninja signaling server..."
sudo systemctl restart vdo-ninja
sleep 3

# Restart camera publishers
echo "→ Restarting camera publishers..."
sudo systemctl restart ninja-publish-cam1
sudo systemctl restart ninja-publish-cam2
sudo systemctl restart ninja-publish-cam3
sleep 5

echo ""
echo "=================================================="
echo "Step 5: Verifying services..."
echo "=================================================="
echo ""

# Check if services are running
VDO_STATUS=$(systemctl is-active vdo-ninja)
CAM1_STATUS=$(systemctl is-active ninja-publish-cam1)
CAM2_STATUS=$(systemctl is-active ninja-publish-cam2)
CAM3_STATUS=$(systemctl is-active ninja-publish-cam3)

echo "VDO.ninja server: $VDO_STATUS"
echo "Camera 1 publisher: $CAM1_STATUS"
echo "Camera 2 publisher: $CAM2_STATUS"
echo "Camera 3 publisher: $CAM3_STATUS"

echo ""
echo "Recent publisher logs (checking for errors):"
echo "--- CAM1 (last 5 lines) ---"
sudo journalctl -u ninja-publish-cam1 -n 5 --no-pager | tail -5

echo ""
echo "--- CAM2 (last 5 lines) ---"
sudo journalctl -u ninja-publish-cam2 -n 5 --no-pager | tail -5

echo ""
echo "--- CAM3 (last 5 lines) ---"
sudo journalctl -u ninja-publish-cam3 -n 5 --no-pager | tail -5

echo ""
echo "=================================================="
echo "Step 6: Checking port 8443..."
echo "=================================================="
netstat -tln | grep 8443 && echo "✅ Port 8443 is listening" || echo "❌ Port 8443 not available"

echo ""
echo "=================================================="
echo "✅ SERVICE RESTART COMPLETE!"
echo "=================================================="
echo ""
echo "Access URLs (use R58's IP address):"
echo ""
echo "Test Page:"
echo "  https://$R58_IP:8443/test_r58.html"
echo ""
echo "Director View:"
echo "  https://$R58_IP:8443/?director=r58studio&wss=$R58_IP:8443"
echo ""
echo "Mixer:"
echo "  https://$R58_IP:8443/mixer?push=MIXOUT&room=r58studio&wss=$R58_IP:8443"
echo ""
echo "Individual Cameras:"
echo "  https://$R58_IP:8443/?view=r58-cam1&room=r58studio&wss=$R58_IP:8443"
echo "  https://$R58_IP:8443/?view=r58-cam2&room=r58studio&wss=$R58_IP:8443"
echo "  https://$R58_IP:8443/?view=r58-cam3&room=r58studio&wss=$R58_IP:8443"
echo ""
echo "NOTE: You'll need to accept the self-signed certificate"
echo "      Click 'Advanced' → 'Proceed to ...' in your browser"
echo ""

ENDSSH

echo ""
echo "=================================================="
echo "DONE! Services restarted on R58"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Open a browser on this PC"
echo "2. Go to: https://$R58_IP:8443/test_r58.html"
echo "3. Accept the security warning (self-signed certificate)"
echo "4. You should see the camera test page"
echo ""

