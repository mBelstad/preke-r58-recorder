#!/bin/bash
# Find R58 device on local network
# Scans for SSH services and tests for R58 characteristics

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================"
echo "R58 Device Finder"
echo "======================================"
echo ""

# Get current network
CURRENT_IP=$(ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print $2}' | head -1)
NETWORK=$(echo $CURRENT_IP | cut -d. -f1-3)

echo "Your IP: $CURRENT_IP"
echo "Scanning network: ${NETWORK}.0/24"
echo ""

# Try common hostnames first
echo "Trying common hostnames..."
for hostname in r58.local rock64.local orangepi.local rk3588.local; do
    echo -n "  Testing $hostname... "
    if ping -c 1 -W 1 $hostname &>/dev/null; then
        IP=$(ping -c 1 $hostname | grep "PING" | awk '{print $3}' | tr -d '()')
        echo -e "${GREEN}FOUND${NC} at $IP"
        echo ""
        echo "Testing SSH..."
        if ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no linaro@$IP "hostname" 2>/dev/null; then
            echo -e "${GREEN}✓ R58 device found!${NC}"
            echo ""
            echo "IP Address: $IP"
            echo "Hostname: $hostname"
            echo ""
            echo "Update your configuration:"
            echo "  export R58_IP=\"$IP\""
            echo ""
            exit 0
        fi
    else
        echo "not found"
    fi
done

echo ""
echo "Scanning for SSH services on network..."
echo "(This may take 1-2 minutes)"
echo ""

# Scan common IP range
FOUND_HOSTS=()
for i in {1..254}; do
    IP="${NETWORK}.$i"
    # Skip your own IP
    if [ "$IP" == "$CURRENT_IP" ]; then
        continue
    fi
    
    # Quick ping test
    if ping -c 1 -W 1 $IP &>/dev/null; then
        # Test SSH port
        if nc -z -w 1 $IP 22 2>/dev/null; then
            echo -e "${YELLOW}Found SSH service:${NC} $IP"
            FOUND_HOSTS+=("$IP")
        fi
    fi
done

if [ ${#FOUND_HOSTS[@]} -eq 0 ]; then
    echo -e "${RED}No SSH services found on network${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify R58 is powered on"
    echo "  2. Verify R58 is connected to network"
    echo "  3. Check router DHCP client list"
    echo "  4. Try connecting R58 via Ethernet"
    exit 1
fi

echo ""
echo "Testing SSH services for R58..."
echo ""

for IP in "${FOUND_HOSTS[@]}"; do
    echo -n "Testing $IP... "
    
    # Try SSH with linaro user
    HOSTNAME=$(ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no linaro@$IP "hostname" 2>/dev/null || echo "")
    
    if [ -n "$HOSTNAME" ]; then
        echo -e "${GREEN}FOUND${NC}"
        echo "  Hostname: $HOSTNAME"
        
        # Check for VDO.Ninja
        HAS_VDO=$(ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no linaro@$IP "systemctl list-units --all | grep vdo-ninja" 2>/dev/null || echo "")
        
        if [ -n "$HAS_VDO" ]; then
            echo -e "  ${GREEN}✓ VDO.Ninja service found!${NC}"
            echo ""
            echo -e "${GREEN}R58 device found!${NC}"
            echo ""
            echo "IP Address: $IP"
            echo "Hostname: $HOSTNAME"
            echo ""
            echo "Update your configuration:"
            echo "  export R58_IP=\"$IP\""
            echo ""
            echo "Test VDO.Ninja:"
            echo "  open \"https://$IP:8443/?director=r58studio\""
            echo ""
            exit 0
        else
            echo "  (not R58 - no VDO.Ninja service)"
        fi
    else
        echo "no access"
    fi
done

echo ""
echo -e "${YELLOW}R58 not found automatically${NC}"
echo ""
echo "Manual steps:"
echo "  1. Check router DHCP client list"
echo "  2. Look for device named 'r58' or 'rock64'"
echo "  3. Test IP manually:"
echo "     ssh linaro@IP_ADDRESS"
echo ""







