#!/bin/bash
# SSH Key Setup for R58 Device
# Run once to configure passwordless SSH access

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
R58_HOST="${R58_HOST:-r58.itagenten.no}"
R58_USER="${R58_USER:-linaro}"
SSH_KEY="$HOME/.ssh/id_ed25519"

echo "======================================"
echo "SSH Key Setup for R58 Device"
echo "======================================"
echo ""
echo "Host: ${R58_HOST}"
echo "User: ${R58_USER}"
echo ""

# Step 1: Check/generate SSH key
echo "Step 1: Checking SSH key..."
if [ -f "$SSH_KEY" ]; then
    echo -e "${GREEN}✓${NC} SSH key already exists: $SSH_KEY"
else
    echo "Generating new SSH key..."
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N "" -C "r58-deployment-key"
    echo -e "${GREEN}✓${NC} SSH key generated: $SSH_KEY"
fi
echo ""

# Step 2: Copy key to R58
echo "Step 2: Copying SSH key to R58..."
echo -e "${YELLOW}You will be prompted for the R58 password${NC}"
echo ""

if ssh-copy-id -i "$SSH_KEY.pub" "${R58_USER}@${R58_HOST}"; then
    echo ""
    echo -e "${GREEN}✓${NC} SSH key copied successfully"
else
    echo ""
    echo -e "${RED}✗${NC} Failed to copy SSH key"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check network connection to R58"
    echo "  2. Verify hostname: ${R58_HOST}"
    echo "  3. Verify username: ${R58_USER}"
    echo "  4. Check password is correct"
    exit 1
fi
echo ""

# Step 3: Test connection
echo "Step 3: Testing SSH connection..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 "${R58_USER}@${R58_HOST}" "echo 'SSH key setup successful!'" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} SSH key authentication working!"
else
    echo -e "${RED}✗${NC} SSH key authentication failed"
    echo ""
    echo "The key was copied but authentication is not working."
    echo "This might be a server configuration issue."
    exit 1
fi
echo ""

# Step 4: Update SSH config for Cloudflare Tunnel (optional)
echo "Step 4: Checking SSH config..."
SSH_CONFIG="$HOME/.ssh/config"

if [ -f "$SSH_CONFIG" ] && grep -q "Host ${R58_HOST}" "$SSH_CONFIG"; then
    echo -e "${GREEN}✓${NC} SSH config already contains entry for ${R58_HOST}"
else
    echo "Adding entry to SSH config..."
    mkdir -p "$HOME/.ssh"
    cat >> "$SSH_CONFIG" << EOF

# R58 Device via Cloudflare Tunnel
Host ${R58_HOST}
    User ${R58_USER}
    IdentityFile ${SSH_KEY}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF
    chmod 600 "$SSH_CONFIG"
    echo -e "${GREEN}✓${NC} SSH config updated"
fi
echo ""

echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "You can now use SSH without passwords:"
echo "  ssh ${R58_USER}@${R58_HOST}"
echo "  ./deploy.sh"
echo "  ./connect-r58.sh"
echo ""
echo -e "${GREEN}✓ SSH key authentication is ready!${NC}"
