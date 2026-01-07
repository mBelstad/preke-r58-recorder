#!/bin/bash
# Check VDO.ninja status on R58
# Can be run remotely via SSH

set -e

echo "======================================"
echo "VDO.ninja Status Check"
echo "======================================"
echo ""

# Check installation
echo "1. Installation Check:"
if [[ -d "/opt/vdo.ninja" ]]; then
    echo "   ✓ VDO.ninja found at /opt/vdo.ninja"
    ls -la /opt/vdo.ninja | head -5
elif [[ -d "/opt/vdo-signaling" ]]; then
    echo "   ✓ VDO.ninja signaling found at /opt/vdo-signaling"
else
    echo "   ✗ VDO.ninja not found"
    echo "   Expected locations: /opt/vdo.ninja or /opt/vdo-signaling"
fi
echo ""

# Check services
echo "2. Service Status:"
if systemctl list-unit-files | grep -q "vdo-ninja.service"; then
    if systemctl is-active --quiet vdo-ninja 2>/dev/null; then
        echo "   ✓ vdo-ninja.service is running"
    else
        echo "   ✗ vdo-ninja.service is not running"
        systemctl status vdo-ninja --no-pager -l | head -10
    fi
else
    echo "   ✗ vdo-ninja.service not found"
fi

if systemctl list-unit-files | grep -q "vdo-webapp.service"; then
    if systemctl is-active --quiet vdo-webapp 2>/dev/null; then
        echo "   ✓ vdo-webapp.service is running"
    else
        echo "   ✗ vdo-webapp.service is not running"
        systemctl status vdo-webapp --no-pager -l | head -10
    fi
else
    echo "   ✗ vdo-webapp.service not found"
fi
echo ""

# Check FRP tunnel
echo "3. FRP Tunnel Configuration:"
if [[ -f "/opt/frp/frpc.toml" ]]; then
    if grep -q "vdoninja\|18443" /opt/frp/frpc.toml; then
        echo "   ✓ VDO.ninja FRP tunnel configured"
        grep -A 3 "vdoninja\|18443" /opt/frp/frpc.toml | head -10
    else
        echo "   ✗ VDO.ninja FRP tunnel NOT configured"
        echo "   Run: sudo bash /opt/preke-r58-recorder/scripts/setup-vdoninja.sh"
    fi
else
    echo "   ✗ FRP config not found at /opt/frp/frpc.toml"
fi
echo ""

# Check bridge service
echo "4. Bridge Service:"
if systemctl list-unit-files | grep -q "vdoninja-bridge.service"; then
    echo "   ✓ vdoninja-bridge.service installed"
    if systemctl is-active --quiet vdoninja-bridge 2>/dev/null; then
        echo "   ✓ vdoninja-bridge.service is running"
    else
        echo "   ⚠ vdoninja-bridge.service is not running (normal - controlled by mode_manager)"
    fi
else
    echo "   ✗ vdoninja-bridge.service not installed"
    echo "   Run: sudo bash /opt/preke-r58-recorder/scripts/setup-vdoninja.sh"
fi
echo ""

# Check ports
echo "5. Port Status:"
if netstat -tln 2>/dev/null | grep -q ":8443"; then
    echo "   ✓ Port 8443 is listening (VDO.ninja signaling)"
else
    echo "   ✗ Port 8443 is NOT listening"
fi

if netstat -tln 2>/dev/null | grep -q ":8444"; then
    echo "   ✓ Port 8444 is listening (VDO.ninja web app)"
else
    echo "   ✗ Port 8444 is NOT listening"
fi
echo ""

# Summary
echo "======================================"
echo "Summary"
echo "======================================"
echo ""
echo "If VDO.ninja is not installed:"
echo "  1. Download from: https://github.com/steveseguin/vdoninja"
echo "  2. Extract to: /opt/vdo.ninja"
echo "  3. Set up signaling server"
echo ""
echo "To set up services and FRP tunnel:"
echo "  sudo bash /opt/preke-r58-recorder/scripts/setup-vdoninja.sh"
echo ""

