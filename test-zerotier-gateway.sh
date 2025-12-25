#!/bin/bash
# Test ZeroTier Gateway to R58
# Verifies that you can reach R58 through ZeroTier on Windows PC

set -e

R58_IP="192.168.1.24"

echo "=================================================="
echo "  ZeroTier Gateway Test"
echo "=================================================="
echo ""

# Test 1: Check if ZeroTier is installed
echo "Step 1: Checking ZeroTier installation..."
if command -v zerotier-cli >/dev/null 2>&1; then
    echo "✅ ZeroTier CLI found"
else
    echo "❌ ZeroTier not installed"
    echo ""
    echo "To install ZeroTier on Mac:"
    echo "  brew install zerotier-one"
    echo ""
    echo "Then join your network:"
    echo "  sudo zerotier-cli join <network-id>"
    exit 1
fi

# Test 2: Check ZeroTier status
echo ""
echo "Step 2: Checking ZeroTier connection..."
if sudo zerotier-cli listnetworks 2>/dev/null | grep -q "OK"; then
    echo "✅ ZeroTier connected"
    echo ""
    sudo zerotier-cli listnetworks | grep -v "^$"
else
    echo "⚠️  ZeroTier not connected or no networks joined"
    echo ""
    echo "To join a network:"
    echo "  sudo zerotier-cli join <network-id>"
    echo ""
    echo "Then authorize your Mac in ZeroTier Central:"
    echo "  https://my.zerotier.com"
    exit 1
fi

# Test 3: Ping R58
echo ""
echo "Step 3: Testing connection to R58 ($R58_IP)..."
if ping -c 2 -W 2 "$R58_IP" >/dev/null 2>&1; then
    echo "✅ Can reach R58 at $R58_IP"
    
    # Show ping stats
    ping -c 3 "$R58_IP" | tail -2
else
    echo "❌ Cannot reach R58 at $R58_IP"
    echo ""
    echo "Troubleshooting:"
    echo "1. Make sure Windows PC is on and connected to ZeroTier"
    echo "2. Configure route in ZeroTier Central:"
    echo "   - Go to: https://my.zerotier.com"
    echo "   - Select your network"
    echo "   - Add route: 192.168.1.0/24 via <windows-zerotier-ip>"
    echo "3. Enable IP forwarding on Windows PC"
    echo ""
    echo "See ZEROTIER_GATEWAY_SETUP.md for detailed instructions"
    exit 1
fi

# Test 4: Test HTTPS access
echo ""
echo "Step 4: Testing VDO.ninja web server..."
if curl -k -s --connect-timeout 5 "https://$R58_IP:8443" >/dev/null 2>&1; then
    echo "✅ VDO.ninja web server accessible"
else
    echo "⚠️  VDO.ninja web server not responding"
    echo "   (This might be OK if the service is stopped)"
fi

# Test 5: Show ZeroTier info
echo ""
echo "Step 5: ZeroTier network information..."
echo ""
sudo zerotier-cli listnetworks

echo ""
echo "=================================================="
echo "  ✅ Gateway Test Complete!"
echo "=================================================="
echo ""
echo "Your Mac can access R58 through ZeroTier!"
echo ""
echo "Next steps:"
echo ""
echo "1. Access VDO.ninja Director view:"
echo "   open \"https://$R58_IP:8443/?director=r58studio&wss=$R58_IP:8443\""
echo ""
echo "2. Test individual cameras:"
echo "   open \"https://$R58_IP:8443/?view=r58-cam1&room=r58studio&wss=$R58_IP:8443\""
echo ""
echo "3. Open Mixer:"
echo "   open \"https://$R58_IP:8443/mixer?push=MIXOUT&room=r58studio&wss=$R58_IP:8443\""
echo ""
echo "4. Check browser console (F12) for WebRTC stats:"
echo "   - Look for ICE candidates"
echo "   - Should see 'type: host' (not 'relay')"
echo "   - Latency should be <50ms"
echo ""
echo "For detailed setup guide, see: ZEROTIER_GATEWAY_SETUP.md"
echo ""

