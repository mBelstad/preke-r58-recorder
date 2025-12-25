#!/bin/bash
# Fix duplicate CORS headers in nginx configuration
# The issue: nginx adds CORS headers AND MediaMTX adds them = duplicate headers

set -e

echo "🔧 Fixing Duplicate CORS Headers..."
echo ""

VPS_HOST="root@65.109.32.111"
NGINX_CONTAINER="r58-proxy"

echo "Step 1: Backing up current nginx config..."
ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER cat /etc/nginx/conf.d/r58.conf > /tmp/r58.conf.backup"

echo "Step 2: Creating fixed nginx config..."
ssh "$VPS_HOST" << 'EOF'
cat > /tmp/r58-mediamtx-fixed.conf << 'NGINX_CONFIG'
# r58-mediamtx.itagenten.no - MediaMTX WHEP/WebRTC
server {
    listen 80;
    server_name r58-mediamtx.itagenten.no;
    
    location / {
        proxy_pass http://host.docker.internal:18889;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # DO NOT add CORS headers here - MediaMTX already adds them
        # This prevents duplicate Access-Control-Allow-Origin headers
    }
}
NGINX_CONFIG
EOF

echo "Step 3: Copying fixed config to nginx container..."
ssh "$VPS_HOST" "docker cp /tmp/r58-mediamtx-fixed.conf $NGINX_CONTAINER:/etc/nginx/conf.d/r58-mediamtx.conf"

echo "Step 4: Testing nginx configuration..."
if ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -t"; then
    echo "✅ Nginx config is valid"
else
    echo "❌ Nginx config has errors - restoring backup"
    ssh "$VPS_HOST" "docker cp /tmp/r58.conf.backup $NGINX_CONTAINER:/etc/nginx/conf.d/r58.conf"
    exit 1
fi

echo "Step 5: Reloading nginx..."
ssh "$VPS_HOST" "docker exec $NGINX_CONTAINER nginx -s reload"

echo ""
echo "✅ CORS fix applied!"
echo ""
echo "Testing CORS headers..."
curl -s -I "https://r58-mediamtx.itagenten.no/cam0/whep" | grep -i "access-control"

echo ""
echo "🧪 Test VDO.ninja mixer now:"
echo "https://vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=https://r58-mediamtx.itagenten.no/cam0/whep&label=CAM0&whep=https://r58-mediamtx.itagenten.no/cam2/whep&label=CAM2&whep=https://r58-mediamtx.itagenten.no/cam3/whep&label=CAM3"
echo ""

