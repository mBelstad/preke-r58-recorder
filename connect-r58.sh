#!/bin/bash
# Helper script to connect to R58 device via Cloudflare Tunnel
# Usage: ./connect-r58.sh [command]

set -e

R58_HOST="r58.itagenten.no"
R58_USER="linaro"
R58_PASSWORD="linaro"

# Check if cloudflared is available
if ! command -v cloudflared >/dev/null 2>&1; then
    echo "Error: cloudflared is not installed."
    echo "Install it with: brew install cloudflared"
    exit 1
fi

# Check if SSH config is set up
if ! grep -q "r58.itagenten.no" ~/.ssh/config 2>/dev/null; then
    echo "Setting up SSH config for Cloudflare Tunnel..."
    cloudflared access ssh-config --hostname r58.itagenten.no
    echo "SSH config updated. Please run the script again."
    exit 0
fi

# If a command is provided, execute it remotely
if [ -n "$1" ]; then
    sshpass -p "$R58_PASSWORD" ssh -o StrictHostKeyChecking=no "${R58_USER}@${R58_HOST}" "$@"
else
    # Interactive SSH session
    echo "Connecting to ${R58_USER}@${R58_HOST} via Cloudflare Tunnel..."
    echo "Press Ctrl+D or type 'exit' to disconnect"
    sshpass -p "$R58_PASSWORD" ssh -o StrictHostKeyChecking=no "${R58_USER}@${R58_HOST}"
fi

