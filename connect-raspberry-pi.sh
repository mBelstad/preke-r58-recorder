#!/bin/bash
# Connect to Raspberry Pi via SSH
# Usage: ./connect-raspberry-pi.sh [IP_ADDRESS] [COMMAND]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
PI_USER="${PI_USER:-marius}"
PI_PASSWORD="${PI_PASSWORD:-Famalive94}"
PI_IP="${1:-${PI_IP:-100.107.248.29}}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Connecting to Raspberry Pi at $PI_IP...${NC}"
echo ""

# Check sshpass
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}sshpass not found. Installing...${NC}"
    if command -v brew &> /dev/null; then
        brew install hudochenkov/sshpass/sshpass
    else
        echo -e "${RED}Error: sshpass is required${NC}"
        exit 1
    fi
fi

# If command provided, execute it
if [ -n "$2" ]; then
    COMMAND="$2"
    echo -e "${YELLOW}Executing command on Raspberry Pi...${NC}"
    echo ""
    
    sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
        -o ServerAliveInterval=30 \
        -o TCPKeepAlive=yes \
        -o StrictHostKeyChecking=no \
        "$PI_USER@$PI_IP" "$COMMAND"
else
    # Interactive SSH session
    echo -e "${GREEN}Starting interactive session...${NC}"
    echo ""
    
    sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=15 \
        -o ServerAliveInterval=30 \
        -o TCPKeepAlive=yes \
        -o StrictHostKeyChecking=no \
        "$PI_USER@$PI_IP"
fi
