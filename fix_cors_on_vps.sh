#!/bin/bash
# Fix CORS duplicate headers on VPS nginx container
# Run this script ON the VPS directly

set -e

NGINX_CONTAINER="r58-proxy"

echo "🔧 Fixing CORS Duplicate Headers..."
echo ""

# Step 1: Backup current config
echo "Step 1: Backing up current nginx config..."
docker exec $NGINX_CONTAINER cat /etc/nginx/conf.d/r58.conf > /tmp/r58.conf.backup
echo "✅ Backup saved to /tmp/r58.conf.backup"
echo ""

# Step 2: Remove CORS headers from nginx (MediaMTX will handle them)
echo "Step 2: Removing duplicate CORS headers from nginx..."
docker exec $NGINX_CONTAINER sed -i '/add_header Access-Control-Allow-Origin/d' /etc/nginx/conf.d/r58.conf
docker exec $NGINX_CONTAINER sed -i '/add_header Access-Control-Allow-Methods/d' /etc/nginx/conf.d/r58.conf
docker exec $NGINX_CONTAINER sed -i '/add_header Access-Control-Allow-Headers/d' /etc/nginx/conf.d/r58.conf
echo "✅ CORS headers removed"
echo ""

# Step 3: Test nginx config
echo "Step 3: Testing nginx configuration..."
docker exec $NGINX_CONTAINER nginx -t
echo "✅ nginx config is valid"
echo ""

# Step 4: Reload nginx
echo "Step 4: Reloading nginx..."
docker exec $NGINX_CONTAINER nginx -s reload
echo "✅ nginx reloaded successfully"
echo ""

# Step 5: Verify
echo "Step 5: Verifying changes..."
echo "Current nginx config (relevant section):"
docker exec $NGINX_CONTAINER grep -A 20 "location / {" /etc/nginx/conf.d/r58.conf | head -25
echo ""

echo "✅ CORS fix complete!"
echo ""
echo "📝 What was changed:"
echo "   - Removed 'add_header Access-Control-Allow-Origin * always;'"
echo "   - Removed 'add_header Access-Control-Allow-Methods ...'"
echo "   - Removed 'add_header Access-Control-Allow-Headers ...'"
echo ""
echo "   MediaMTX will now handle CORS headers without duplication."
echo ""
echo "🧪 Test the fix:"
echo "   Open: https://vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=https://app.itagenten.no/cam0/whep&label=CAM0&whep=https://app.itagenten.no/cam2/whep&label=CAM2&whep=https://app.itagenten.no/cam3/whep&label=CAM3"

