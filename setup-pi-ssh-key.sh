#!/bin/bash
# Setup SSH key for passwordless authentication to Raspberry Pi
# Usage: ./setup-pi-ssh-key.sh

set -e

# Configuration
PI_USER="${PI_USER:-marius}"
PI_PASSWORD="${PI_PASSWORD:-Famalive94}"
PI_IP="${PI_IP:-192.168.1.81}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Setting up SSH key for Raspberry Pi...${NC}"
echo ""

# Check if SSH key exists
if [ ! -f ~/.ssh/id_ed25519.pub ]; then
    echo -e "${RED}Error: SSH public key not found at ~/.ssh/id_ed25519.pub${NC}"
    echo "Generating new SSH key..."
    ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "marius@macbook-pro"
fi

echo -e "${YELLOW}Step 1: Reading public key...${NC}"
PUBLIC_KEY=$(cat ~/.ssh/id_ed25519.pub)
echo "Public key: ${PUBLIC_KEY:0:50}..."
echo ""

echo -e "${YELLOW}Step 2: Copying public key to Pi...${NC}"
echo "You will be prompted for the password: ${PI_PASSWORD}"

# Use sshpass to copy the key
if command -v sshpass &> /dev/null; then
    sshpass -p "$PI_PASSWORD" ssh-copy-id -o StrictHostKeyChecking=no \
        -i ~/.ssh/id_ed25519.pub \
        "$PI_USER@$PI_IP"
else
    echo -e "${YELLOW}sshpass not found. Please run manually:${NC}"
    echo "ssh-copy-id -i ~/.ssh/id_ed25519.pub $PI_USER@$PI_IP"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 3: Testing passwordless SSH...${NC}"
if ssh -o BatchMode=yes -o ConnectTimeout=5 "$PI_USER@$PI_IP" "echo 'SSH key works!'" 2>/dev/null; then
    echo -e "${GREEN}✓ SSH key setup successful!${NC}"
    echo ""
    echo "You can now connect without password:"
    echo "  ssh $PI_USER@$PI_IP"
    echo ""
else
    echo -e "${RED}✗ SSH key test failed${NC}"
    echo "You may need to manually copy the key or check Pi's SSH configuration"
    exit 1
fi
