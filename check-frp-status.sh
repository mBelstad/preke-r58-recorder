#!/bin/bash
# Check FRP Tunnel Status on Coolify VPS

set -e

VPS="65.109.32.111"
echo "======================================"
echo "Checking FRP Tunnel Status"
echo "======================================"
echo ""

echo "Checking if FRP port 10022 is open on VPS..."
nc -zv $VPS 10022 2>&1 | grep -q "succeeded" && echo "✓ Port 10022 is OPEN" || echo "✗ Port 10022 is CLOSED"
echo ""

echo "Checking if FRP server is running..."
echo "SSH into Coolify VPS to check:"
echo "  ssh root@${VPS}"
echo "  sudo docker ps | grep frp"
echo "  sudo docker logs frps"
echo ""

echo "On R58 device, check if FRP client is running:"
echo "  ssh r58-frp (if SSH works)"
echo "  sudo systemctl status frpc"
echo "  sudo journalctl -u frpc -n 50"
echo ""

echo "FRP Configuration Files:"
echo "  VPS: /etc/frp/frps.ini"
echo "  R58: /etc/frp/frpc.ini"
echo ""

