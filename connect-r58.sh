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
    # SSH keys not set up - try password if provided
    if [ -n "${R58_PASSWORD}" ]; then
        if ! command -v sshpass >/dev/null 2>&1; then
            echo "Error: sshpass required for password auth."
            echo "Install: brew install sshpass"
            echo ""
            echo "Or set up SSH keys: ./ssh-setup.sh"
            exit 1
        fi
        echo "Using password authentication (set up SSH keys for better security)"
        SSH_CMD="sshpass -p '${R58_PASSWORD}' ssh -o StrictHostKeyChecking=no"
    else
        echo "Error: SSH key authentication not set up."
        echo ""
        echo "Options:"
        echo "  1. Run ./ssh-setup.sh to configure SSH keys (recommended)"
        echo "  2. Set R58_PASSWORD environment variable (temporary)"
        echo ""
        echo "Example: R58_PASSWORD=yourpassword ./connect-r58.sh"
        exit 1
    fi
else
    SSH_CMD="ssh"
fi

# If a command is provided, execute it remotely
if [ -n "$1" ]; then
    ${SSH_CMD} "${R58_USER}@${R58_HOST}" "$@"
else
    # Interactive SSH session
    echo "Connecting to ${R58_USER}@${R58_HOST}..."
    echo "Press Ctrl+D or type 'exit' to disconnect"
    ${SSH_CMD} "${R58_USER}@${R58_HOST}"
fi

