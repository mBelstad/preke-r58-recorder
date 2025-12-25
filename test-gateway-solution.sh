#!/bin/bash
# Test Gateway Solution - Quick Test with Your Mac
# This script helps you test using your Mac as a VPN gateway to access R58

set -e

echo "=================================================="
echo "  WebRTC Gateway Solution - Quick Test"
echo "=================================================="
echo ""

# Check if on same network as R58
echo "Step 1: Checking network connectivity to R58..."
R58_IP="192.168.1.24"

if ping -c 2 "$R58_IP" >/dev/null 2>&1; then
    echo "✅ R58 is reachable at $R58_IP"
else
    echo "❌ Cannot reach R58 at $R58_IP"
    echo ""
    echo "Make sure:"
    echo "  1. Your Mac is on the same network as R58"
    echo "  2. R58 is powered on"
    echo "  3. R58 IP is correct (check router or use: ./find-r58.sh)"
    exit 1
fi

echo ""
echo "Step 2: Checking if Tailscale is installed..."

if command -v tailscale >/dev/null 2>&1; then
    echo "✅ Tailscale is installed"
    
    # Check if Tailscale is running
    if tailscale status >/dev/null 2>&1; then
        echo "✅ Tailscale is running"
        
        # Check if subnet routing is enabled
        if tailscale status --json 2>/dev/null | grep -q "192.168.1.0/24"; then
            echo "✅ Subnet routing already enabled"
        else
            echo "⚠️  Subnet routing not enabled"
            echo ""
            echo "To enable subnet routing:"
            echo "  sudo tailscale up --advertise-routes=192.168.1.0/24 --accept-routes"
        fi
    else
        echo "⚠️  Tailscale not running"
        echo ""
        echo "To start Tailscale:"
        echo "  sudo tailscale up --advertise-routes=192.168.1.0/24"
    fi
else
    echo "❌ Tailscale not installed"
    echo ""
    echo "To install Tailscale:"
    echo "  brew install tailscale"
    echo ""
    echo "Then start it with subnet routing:"
    echo "  sudo tailscale up --advertise-routes=192.168.1.0/24"
    exit 1
fi

echo ""
echo "Step 3: Testing VDO.ninja access..."

if curl -k -s "https://$R58_IP:8443" >/dev/null 2>&1; then
    echo "✅ VDO.ninja web server is accessible"
else
    echo "⚠️  VDO.ninja web server not responding"
    echo "   Check if vdo-ninja service is running on R58"
fi

echo ""
echo "=================================================="
echo "  Test Results Summary"
echo "=================================================="
echo ""
echo "Your Mac can act as a VPN gateway for R58!"
echo ""
echo "Next steps:"
echo ""
echo "1. On your Mac (this computer):"
echo "   - Make sure Tailscale is running with subnet routing"
echo "   - Command: sudo tailscale up --advertise-routes=192.168.1.0/24"
echo ""
echo "2. On another device (phone, tablet, laptop):"
echo "   - Install Tailscale app"
echo "   - Sign in with same account"
echo "   - Enable 'Accept routes' in settings"
echo ""
echo "3. Access VDO.ninja from the remote device:"
echo "   - Open: https://$R58_IP:8443/?director=r58studio"
echo "   - Accept self-signed certificate"
echo "   - Enjoy low-latency WebRTC!"
echo ""
echo "URLs to test:"
echo "  Director: https://$R58_IP:8443/?director=r58studio"
echo "  Camera 1: https://$R58_IP:8443/?view=r58-cam1&room=r58studio"
echo "  Test page: https://$R58_IP:8443/static/test_vdo_simple.html"
echo ""
echo "For permanent setup, see: WEBRTC_GATEWAY_SOLUTION.md"
echo ""

