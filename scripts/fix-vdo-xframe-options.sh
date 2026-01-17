#!/bin/bash
# Fix X-Frame-Options for VDO.ninja to allow iframe embedding
# 
# NOTE: This script is OBSOLETE as of Jan 2026.
# VDO.ninja was migrated from r58-vdo.itagenten.no to app.itagenten.no/vdo/
# The X-Frame-Options header is now configured in the main app.itagenten.no server block
# in deployment/nginx.conf, not in a separate r58-vdo.itagenten.no server block.
#
# Run this script ON the Coolify VPS (65.109.32.111) as root

set -e

NGINX_CONTAINER="r58-proxy"
CONFIG_FILE="/etc/nginx/conf.d/r58.conf"

echo "🔧 Fixing X-Frame-Options for VDO.ninja..."
echo ""

# Step 1: Backup current config
echo "Step 1: Backing up current nginx config..."
docker exec $NGINX_CONTAINER cat $CONFIG_FILE > /tmp/r58.conf.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup saved to /tmp/"
echo ""

# Step 2: Update VDO.ninja server block to REMOVE X-Frame-Options
# This allows the iframe to be embedded from any origin
# NOTE: As of Jan 2026, VDO.ninja is served at app.itagenten.no/vdo/, not r58-vdo.itagenten.no
# The old r58-vdo.itagenten.no server block now only redirects to app.itagenten.no/vdo/
echo "Step 2: Removing X-Frame-Options from VDO.ninja server block..."
echo "⚠️  WARNING: This script targets the old r58-vdo.itagenten.no server block which now only redirects."

docker exec $NGINX_CONTAINER sed -i '/server_name r58-vdo.itagenten.no;/,/^server {/s/add_header X-Frame-Options.*always;//g' $CONFIG_FILE

echo "✅ X-Frame-Options removed from VDO.ninja block"
echo ""

# Step 3: Test nginx config
echo "Step 3: Testing nginx configuration..."
if docker exec $NGINX_CONTAINER nginx -t; then
    echo "✅ nginx config is valid"
else
    echo "❌ nginx config test failed! Restoring backup..."
    latest_backup=$(ls -t /tmp/r58.conf.backup.* | head -1)
    docker cp "$latest_backup" $NGINX_CONTAINER:$CONFIG_FILE
    docker exec $NGINX_CONTAINER nginx -s reload
    echo "❌ Backup restored. Please check the configuration manually."
    exit 1
fi
echo ""

# Step 4: Reload nginx
echo "Step 4: Reloading nginx..."
docker exec $NGINX_CONTAINER nginx -s reload
echo "✅ nginx reloaded successfully"
echo ""

# Step 5: Verify
echo "Step 5: Verifying X-Frame-Options is removed..."
echo ""
if docker exec $NGINX_CONTAINER grep -A 10 "server_name r58-vdo" $CONFIG_FILE | grep -q "X-Frame-Options"; then
    echo "⚠️  X-Frame-Options still present in config"
else
    echo "✅ X-Frame-Options successfully removed from VDO.ninja block"
fi
echo ""

# Step 6: Test with curl
echo "Step 6: Testing HTTP headers..."
# NOTE: r58-vdo.itagenten.no now redirects to app.itagenten.no/vdo/, so test the new URL
response=$(curl -sI https://app.itagenten.no/vdo/ 2>/dev/null | grep -i "x-frame-options" || echo "No X-Frame-Options header found")
echo "Response: $response"
echo ""

echo "🎉 Fix complete!"
echo ""
echo "The VDO.ninja iframe should now work in Preke Studio."
echo "Test at: https://app.itagenten.no/mixer"
echo ""
echo "⚠️  NOTE: VDO.ninja is now served at https://app.itagenten.no/vdo/ (migrated Jan 2026)"

