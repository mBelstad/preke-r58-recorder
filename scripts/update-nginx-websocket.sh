#!/bin/bash
# Update nginx configuration to support WebSocket for /api/v1/ws
# Can be run locally - will SSH to VPS automatically

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VPS_HOST="${VPS_HOST:-root@65.109.32.111}"
NGINX_CONTAINER="${NGINX_CONTAINER:-r58-proxy}"
CONFIG_FILE="/etc/nginx/conf.d/r58.conf"

# Try to use connect script if available
if [[ -f "$SCRIPT_DIR/../connect-coolify-vps.sh" ]]; then
    CONNECT_SCRIPT="$SCRIPT_DIR/../connect-coolify-vps.sh"
else
    CONNECT_SCRIPT="ssh"
fi

echo "🔧 Updating nginx configuration for WebSocket support..."
echo ""

# Step 1: Backup current config
echo "Step 1: Backing up current nginx config..."
if [[ "$CONNECT_SCRIPT" == "ssh" ]]; then
    ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER cat $CONFIG_FILE > /tmp/r58.conf.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'Config file may not exist yet'"
else
    bash "$CONNECT_SCRIPT" "docker exec $NGINX_CONTAINER cat $CONFIG_FILE > /tmp/r58.conf.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'Config file may not exist yet'"
fi
echo "✅ Backup saved"
echo ""

# Step 2: Read current config and update
echo "Step 2: Reading current nginx config..."
if [[ "$CONNECT_SCRIPT" == "ssh" ]]; then
    CURRENT_CONFIG=$(ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER cat $CONFIG_FILE 2>/dev/null || echo ''")
else
    CURRENT_CONFIG=$(bash "$CONNECT_SCRIPT" "docker exec $NGINX_CONTAINER cat $CONFIG_FILE 2>/dev/null || echo ''")
fi

if [[ -z "$CURRENT_CONFIG" ]]; then
    echo "⚠️  No existing config found. You may need to create the initial config first."
    echo "   See: deployment/nginx.conf for the full configuration"
    exit 1
fi

# Check if WebSocket support already exists
if echo "$CURRENT_CONFIG" | grep -q "proxy_set_header Upgrade.*http_upgrade"; then
    echo "✅ WebSocket support already configured in /api/ location"
    exit 0
fi

# Step 3: Add WebSocket support to /api/ location
echo "Step 3: Adding WebSocket support to /api/ location..."

# Create updated config with WebSocket support
UPDATED_CONFIG=$(echo "$CURRENT_CONFIG" | sed '/location \/api\/ {/,/}/ {
    /proxy_buffering off;/a\
        \
        # WebSocket support (for /api/v1/ws and other WebSocket endpoints)\
        proxy_set_header Upgrade $http_upgrade;\
        proxy_set_header Connection $connection_upgrade;\
        \
        # Longer timeouts for WebSocket\
        proxy_read_timeout 86400s;\
        proxy_send_timeout 86400s;
}')

# Add map directive at the top if not present
if ! echo "$UPDATED_CONFIG" | grep -q "map \$http_upgrade"; then
    UPDATED_CONFIG="# Map for WebSocket upgrade detection (must be before server blocks)
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

$UPDATED_CONFIG"
fi

# Write to temp file
if [[ "$CONNECT_SCRIPT" == "ssh" ]]; then
    ssh "$VPS_HOST" "cat > /tmp/r58_websocket.conf << 'EOF'
$UPDATED_CONFIG
EOF"
else
    bash "$CONNECT_SCRIPT" "cat > /tmp/r58_websocket.conf << 'EOF'
$UPDATED_CONFIG
EOF"
fi

echo "✅ Updated config created"
echo ""

# Step 4: Copy to container
echo "Step 4: Copying updated config to nginx container..."
if [[ "$CONNECT_SCRIPT" == "ssh" ]]; then
    ssh "$VPS_HOST" "docker cp /tmp/r58_websocket.conf $NGINX_CONTAINER:$CONFIG_FILE"
else
    bash "$CONNECT_SCRIPT" "docker cp /tmp/r58_websocket.conf $NGINX_CONTAINER:$CONFIG_FILE"
fi
echo "✅ Configuration copied"
echo ""

# Step 5: Test nginx config
echo "Step 5: Testing nginx configuration..."
if [[ "$CONNECT_SCRIPT" == "ssh" ]]; then
    TEST_RESULT=$(ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -t 2>&1")
else
    TEST_RESULT=$(bash "$CONNECT_SCRIPT" "docker exec $NGINX_CONTAINER nginx -t 2>&1")
fi

if echo "$TEST_RESULT" | grep -q "syntax is ok"; then
    echo "✅ nginx config is valid"
else
    echo "❌ nginx config test failed!"
    echo "$TEST_RESULT"
    echo ""
    echo "Restoring backup..."
    if [[ "$CONNECT_SCRIPT" == "ssh" ]]; then
        ssh "$VPS_HOST" "docker cp /tmp/r58.conf.backup.* $NGINX_CONTAINER:$CONFIG_FILE 2>/dev/null || true"
        ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -s reload"
    else
        bash "$CONNECT_SCRIPT" "docker cp /tmp/r58.conf.backup.* $NGINX_CONTAINER:$CONFIG_FILE 2>/dev/null || true"
        bash "$CONNECT_SCRIPT" "docker exec $NGINX_CONTAINER nginx -s reload"
    fi
    echo "❌ Backup restored. Please check the configuration manually."
    exit 1
fi
echo ""

# Step 6: Reload nginx
echo "Step 6: Reloading nginx..."
if [[ "$CONNECT_SCRIPT" == "ssh" ]]; then
    ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -s reload"
else
    bash "$CONNECT_SCRIPT" "docker exec $NGINX_CONTAINER nginx -s reload"
fi
echo "✅ nginx reloaded successfully"
echo ""

echo "🎉 WebSocket support added to nginx!"
echo ""
echo "🧪 Test the WebSocket connection:"
echo "   wscat -c wss://app.itagenten.no/api/v1/ws"
echo ""
