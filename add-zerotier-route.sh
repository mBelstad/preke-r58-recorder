#!/bin/bash
# Add route to R58 network via Windows PC ZeroTier gateway
# Windows PC ZeroTier IP: 10.76.254.72
# R58 network: 192.168.1.0/24

echo "Adding route to R58 network via Windows PC..."
echo ""
echo "Windows PC ZeroTier IP: 10.76.254.72"
echo "R58 network: 192.168.1.0/24"
echo ""

# Add the route
sudo route add -net 192.168.1.0/24 10.76.254.72

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Route added successfully!"
    echo ""
    echo "Testing connection to R58..."
    ping -c 3 192.168.1.24
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "🎉 SUCCESS! You can now access R58!"
        echo ""
        echo "Access VDO.ninja:"
        echo "  Director: https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443"
        echo "  Camera 1: https://192.168.1.24:8443/?view=r58-cam1&room=r58studio&wss=192.168.1.24:8443"
        echo "  Mixer: https://192.168.1.24:8443/mixer?push=MIXOUT&room=r58studio&wss=192.168.1.24:8443"
        echo ""
    else
        echo ""
        echo "⚠️  Route added but cannot reach R58 yet."
        echo ""
        echo "Troubleshooting:"
        echo "1. Make sure Windows PC can reach R58: ping 192.168.1.24 (from Windows)"
        echo "2. Enable IP forwarding on Windows (see ZEROTIER_GATEWAY_SETUP.md)"
        echo "3. Check Windows firewall settings"
    fi
else
    echo ""
    echo "❌ Failed to add route"
    echo "Try running manually: sudo route add -net 192.168.1.0/24 10.76.254.72"
fi




