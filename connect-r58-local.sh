#!/bin/bash
# Connect to R58 on local network
# Usage: ./connect-r58-local.sh [IP] [command]
# 
# Note: When prompted for passphrase, press ENTER
#       Then type password: linaro

set -e

# Try to find R58 IP if not provided
if [ -z "$1" ]; then
    echo "======================================"
    echo "R58 Local Connection Helper"
    echo "======================================"
    echo ""
    echo "Trying common IPs on your network..."
    echo ""
    
    # Try common IPs
    for ip in 192.168.68.50 192.168.68.51 192.168.68.55 192.168.68.58; do
        echo -n "Testing $ip... "
        if ping -c 1 -W 1 $ip &>/dev/null; then
            echo "reachable"
            echo ""
            echo "Found device at: $ip"
            echo "Connecting..."
            echo ""
            echo "When prompted:"
            echo "  1. Passphrase: Press ENTER"
            echo "  2. Password: Type 'linaro'"
            echo ""
            ssh linaro@$ip
            exit 0
        else
            echo "not reachable"
        fi
    done
    
    echo ""
    echo "Could not find R58 automatically."
    echo ""
    echo "Usage: $0 <IP> [command]"
    echo ""
    echo "Examples:"
    echo "  $0 192.168.68.55"
    echo "  $0 192.168.68.55 'hostname'"
    echo "  $0 192.168.68.55 'sudo systemctl status vdo-ninja'"
    echo ""
    exit 1
fi

R58_IP="$1"
COMMAND="${2:-}"

echo "======================================"
echo "Connecting to R58 at $R58_IP"
echo "======================================"
echo ""
echo "When prompted:"
echo "  1. Passphrase: Press ENTER"
echo "  2. Password: Type 'linaro'"
echo ""

if [ -z "$COMMAND" ]; then
    # Interactive session
    ssh linaro@$R58_IP
else
    # Run command
    ssh linaro@$R58_IP "$COMMAND"
fi







