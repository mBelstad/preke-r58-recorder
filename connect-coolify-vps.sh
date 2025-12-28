#!/bin/bash
# Connect to Coolify VPS (65.109.32.111)
# Reliable SSH with key auth, proper timeouts, and keepalives

VPS_HOST="65.109.32.111"
VPS_PORT="22"
VPS_USER="root"
VPS_KEY="$HOME/.ssh/coolify_vps_key"

echo "Connecting to Coolify VPS..."
echo "Server: $VPS_HOST:$VPS_PORT"
echo ""

# Common SSH options for reliability
SSH_OPTS=(
    -o StrictHostKeyChecking=no
    -o ConnectTimeout=15
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
    -o TCPKeepAlive=yes
    -p ${VPS_PORT}
)

# Check for --password flag to force password auth
USE_PASSWORD=false
ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--password" ]]; then
        USE_PASSWORD=true
    else
        ARGS+=("$arg")
    fi
done

# Prefer SSH key if available (unless --password flag), fall back to password
if [[ -f "$VPS_KEY" ]] && [[ "$USE_PASSWORD" == "false" ]]; then
    echo "Using SSH key authentication"
    ssh "${SSH_OPTS[@]}" \
        -i "$VPS_KEY" \
        ${VPS_USER}@${VPS_HOST} \
        "${ARGS[@]}"
else
    # Interactive password auth
    echo "Using password authentication (set up SSH key for easier access)"
    ssh "${SSH_OPTS[@]}" \
        ${VPS_USER}@${VPS_HOST} \
        "${ARGS[@]}"
fi

