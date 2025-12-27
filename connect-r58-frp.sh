#!/bin/bash
# Connect to R58 via FRP tunnel on Coolify VPS
# This replaces the Cloudflare Tunnel SSH access

R58_VPS="65.109.32.111"
R58_PORT="10022"
R58_USER="linaro"
R58_PASSWORD="${R58_PASSWORD:-linaro}"
R58_KEY="$HOME/.ssh/r58_key"

echo "Connecting to R58 via FRP tunnel..."
echo "Server: $R58_VPS:$R58_PORT"
echo ""

# Common SSH options for reliability
SSH_OPTS=(
    -o StrictHostKeyChecking=no
    -o ConnectTimeout=15
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
    -o TCPKeepAlive=yes
    -p ${R58_PORT}
)

# Prefer SSH key if available, fall back to password
if [[ -f "$R58_KEY" ]]; then
    echo "Using SSH key authentication"
    ssh "${SSH_OPTS[@]}" \
        -i "$R58_KEY" \
        ${R58_USER}@${R58_VPS} \
        "$@"
else
    # Fall back to password authentication
    if ! command -v sshpass >/dev/null 2>&1; then
        echo "Error: sshpass is required for password authentication"
        echo "Install: brew install sshpass"
        echo "Or set up SSH key: ssh-keygen -t ed25519 -f ~/.ssh/r58_key -N \"\""
        exit 1
    fi
    
    sshpass -p "${R58_PASSWORD}" ssh \
        "${SSH_OPTS[@]}" \
        -o PreferredAuthentications=password \
        -o PubkeyAuthentication=no \
        ${R58_USER}@${R58_VPS} \
        "$@"
fi




