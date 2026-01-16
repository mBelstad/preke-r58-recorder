#!/bin/bash
# Update nginx configuration to support WebSocket for /api/v1/ws
# Run this script ON the Coolify VPS (65.109.32.111) or via SSH

set -e

VPS_HOST="${VPS_HOST:-root@65.109.32.111}"
NGINX_CONTAINER="${NGINX_CONTAINER:-r58-proxy}"
CONFIG_FILE="/etc/nginx/conf.d/r58.conf"

echo "🔧 Updating nginx configuration for WebSocket support..."
echo ""

# Step 1: Backup current config
echo "Step 1: Backing up current nginx config..."
ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER cat $CONFIG_FILE > /tmp/r58.conf.backup.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo 'Config file may not exist yet'"
echo "✅ Backup saved"
echo ""

# Step 2: Read current config and update
echo "Step 2: Reading current nginx config..."
CURRENT_CONFIG=$(ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER cat $CONFIG_FILE 2>/dev/null || echo ''")

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
ssh "$VPS_HOST" "cat > /tmp/r58_websocket.conf << 'EOF'
$UPDATED_CONFIG
EOF"

echo "✅ Updated config created"
echo ""

# Step 4: Copy to container
echo "Step 4: Copying updated config to nginx container..."
ssh "$VPS_HOST" "docker cp /tmp/r58_websocket.conf $NGINX_CONTAINER:$CONFIG_FILE"
echo "✅ Configuration copied"
echo ""

# Step 5: Test nginx config
echo "Step 5: Testing nginx configuration..."
if ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -t"; then
    echo "✅ nginx config is valid"
else
    echo "❌ nginx config test failed! Restoring backup..."
    ssh "$VPS_HOST" "docker cp /tmp/r58.conf.backup.* $NGINX_CONTAINER:$CONFIG_FILE 2>/dev/null || true"
    ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -s reload"
    echo "❌ Backup restored. Please check the configuration manually."
    exit 1
fi
echo ""

# Step 6: Reload nginx
echo "Step 6: Reloading nginx..."
ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -s reload"
echo "✅ nginx reloaded successfully"
echo ""

echo "🎉 WebSocket support added to nginx!"
echo ""
echo "🧪 Test the WebSocket connection:"
echo "   wscat -c wss://app.itagenten.no/api/v1/ws"
echo ""
