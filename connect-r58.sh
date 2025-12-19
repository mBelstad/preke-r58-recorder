#!/bin/bash
# Helper script to connect to R58 device via Cloudflare Tunnel
# Usage: ./connect-r58.sh [command]
# 
# SECURITY: Uses SSH key authentication (no passwords)
# Setup: ssh-copy-id linaro@r58.itagenten.no

set -e

R58_HOST="${R58_HOST:-r58.itagenten.no}"
R58_USER="${R58_USER:-linaro}"

# Set up SSH command with password authentication
# Uses password-only to avoid SSH key passphrase prompts
R58_PASSWORD="${R58_PASSWORD:-linaro}"
if ! command -v sshpass >/dev/null 2>&1; then
    echo "Error: sshpass required for password auth."
    echo "Install: brew install sshpass"
    exit 1
fi
SSH_CMD=(sshpass -p "${R58_PASSWORD}" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no)

# If a command is provided, execute it remotely
if [ -n "$1" ]; then
    "${SSH_CMD[@]}" "${R58_USER}@${R58_HOST}" "$@"
else
    # Interactive SSH session
    echo "Connecting to ${R58_USER}@${R58_HOST}..."
    echo "Press Ctrl+D or type 'exit' to disconnect"
    "${SSH_CMD[@]}" "${R58_USER}@${R58_HOST}"
fi

