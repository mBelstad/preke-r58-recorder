#!/bin/bash
# Helper script to connect to R58 device via Cloudflare Tunnel
# Usage: ./connect-r58.sh [command]
# 
# SECURITY: Uses SSH key authentication (no passwords)
# Setup: ssh-copy-id linaro@r58.itagenten.no

set -e

R58_HOST="${R58_HOST:-r58.itagenten.no}"
R58_USER="${R58_USER:-linaro}"

# Check if SSH key is set up
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "${R58_USER}@${R58_HOST}" exit 2>/dev/null; then
    echo "Error: SSH key authentication not set up."
    echo ""
    echo "To set up SSH keys:"
    echo "  1. Generate key (if needed): ssh-keygen -t ed25519"
    echo "  2. Copy to R58: ssh-copy-id ${R58_USER}@${R58_HOST}"
    echo "  3. Test: ssh ${R58_USER}@${R58_HOST}"
    echo ""
    exit 1
fi

# If a command is provided, execute it remotely
if [ -n "$1" ]; then
    ssh "${R58_USER}@${R58_HOST}" "$@"
else
    # Interactive SSH session
    echo "Connecting to ${R58_USER}@${R58_HOST}..."
    echo "Press Ctrl+D or type 'exit' to disconnect"
    ssh "${R58_USER}@${R58_HOST}"
fi

