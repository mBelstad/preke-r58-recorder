#!/bin/bash
# Connect to R58 via FRP tunnel on Coolify VPS
# This replaces the Cloudflare Tunnel SSH access

R58_VPS="65.109.32.111"
R58_PORT="10022"
R58_USER="linaro"
R58_PASSWORD="${R58_PASSWORD:-linaro}"

echo "Connecting to R58 via FRP tunnel..."
echo "Server: $R58_VPS:$R58_PORT"
echo ""

if ! command -v sshpass >/dev/null 2>&1; then
    echo "Error: sshpass is required for password authentication"
    echo "Install: brew install sshpass"
    exit 1
fi

# Use sshpass for password authentication
sshpass -p "${R58_PASSWORD}" ssh \
    -o StrictHostKeyChecking=no \
    -o PreferredAuthentications=password \
    -o PubkeyAuthentication=no \
    -p ${R58_PORT} \
    ${R58_USER}@${R58_VPS} \
    "$@"



