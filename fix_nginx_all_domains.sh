#!/bin/bash
# Fix nginx configuration to add missing server blocks for r58-vdo and r58-api
# 
# NOTE: This script is OBSOLETE as of Jan 2026.
# VDO.ninja was migrated from r58-vdo.itagenten.no to app.itagenten.no/vdo/
# The current nginx configuration serves VDO.ninja at /vdo/ path on app.itagenten.no
# The r58-vdo.itagenten.no domain now only redirects to app.itagenten.no/vdo/
# See deployment/nginx.conf for the current configuration.
#
# Run this script ON the Coolify VPS (65.109.32.111)

set -e

NGINX_CONTAINER="r58-proxy"
CONFIG_FILE="/etc/nginx/conf.d/r58.conf"

echo "🔧 Adding missing server blocks for r58-vdo and r58-api..."
echo ""

# Step 1: Backup current config
echo "Step 1: Backing up current nginx config..."
docker exec $NGINX_CONTAINER cat $CONFIG_FILE > /tmp/r58.conf.backup.$(date +%Y%m%d_%H%M%S)
echo "✅ Backup saved"
echo ""

# Step 2: Create complete new configuration
echo "Step 2: Creating updated nginx configuration..."
cat > /tmp/r58_complete.conf << 'EOF'
# MediaMTX server block
server {
    listen 80;
    server_name vdo.itagenten.no mediamtx.vdo.itagenten.no app.itagenten.no;

    # Security headers (Traefik adds HSTS)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    # MediaMTX WebRTC/WHIP/WHEP
    location / {
        # Handle OPTIONS preflight requests for CORS
        if ($request_method = OPTIONS) {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, OPTIONS, PUT, DELETE" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
            add_header Access-Control-Max-Age 1728000 always;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        proxy_pass http://65.109.32.111:18889;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # MediaMTX API
    location /v3/ {
        proxy_pass http://65.109.32.111:19997/v3/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # HLS streams
    location /hls/ {
        proxy_pass http://65.109.32.111:18889/;
        proxy_set_header Host $host;
        
        # HLS specific headers
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}

# VDO.ninja server block
# NOTE: As of Jan 2026, this server block is OBSOLETE.
# VDO.ninja is now served at app.itagenten.no/vdo/ (see deployment/nginx.conf)
# This block is kept only for legacy redirects. The actual VDO.ninja service
# is proxied through the app.itagenten.no server block with /vdo/ path prefix.
server {
    listen 80;
    server_name r58-vdo.itagenten.no;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://65.109.32.111:18443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for VDO.ninja signaling
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for WebSocket
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}

# FastAPI (R58 API) server block
server {
    listen 80;
    server_name app.itagenten.no;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://65.109.32.111:18000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Support for static files and API
        proxy_http_version 1.1;
        proxy_buffering off;
    }
}
EOF

echo "✅ New configuration created"
echo ""

# Step 3: Copy new config to container
echo "Step 3: Copying new configuration to nginx container..."
docker cp /tmp/r58_complete.conf $NGINX_CONTAINER:$CONFIG_FILE
echo "✅ Configuration copied"
echo ""

# Step 4: Test nginx config
echo "Step 4: Testing nginx configuration..."
if docker exec $NGINX_CONTAINER nginx -t; then
    echo "✅ nginx config is valid"
else
    echo "❌ nginx config test failed! Restoring backup..."
    docker cp /tmp/r58.conf.backup.* $NGINX_CONTAINER:$CONFIG_FILE
    docker exec $NGINX_CONTAINER nginx -s reload
    echo "❌ Backup restored. Please check the configuration."
    exit 1
fi
echo ""

# Step 5: Reload nginx
echo "Step 5: Reloading nginx..."
docker exec $NGINX_CONTAINER nginx -s reload
echo "✅ nginx reloaded successfully"
echo ""

# Step 6: Verify
echo "Step 6: Verifying all server blocks..."
echo ""
echo "=== MediaMTX Server Block ==="
docker exec $NGINX_CONTAINER grep -A 5 "server_name.*r58-mediamtx" $CONFIG_FILE | head -8
echo ""
echo "=== VDO.ninja Server Block ==="
docker exec $NGINX_CONTAINER grep -A 5 "server_name.*r58-vdo" $CONFIG_FILE | head -8
echo ""
echo "=== FastAPI Server Block ==="
docker exec $NGINX_CONTAINER grep -A 5 "server_name.*r58-api" $CONFIG_FILE | head -8
echo ""

echo "✅ All server blocks configured!"
echo ""
echo "📝 What was added:"
echo "   ✅ app.itagenten.no → port 18889 (MediaMTX)"
echo "   ✅ r58-vdo.itagenten.no → port 18443 (VDO.ninja) [OBSOLETE - now at app.itagenten.no/vdo/]"
echo "   ✅ app.itagenten.no → port 18000 (FastAPI) [NEW]"
echo ""
echo "⚠️  NOTE: This script creates an OBSOLETE configuration."
echo "   VDO.ninja is now served at https://app.itagenten.no/vdo/ (migrated Jan 2026)"
echo "   The r58-vdo.itagenten.no domain now only redirects to app.itagenten.no/vdo/"
echo ""
echo "🧪 Test the services:"
echo "   MediaMTX: curl -I https://app.itagenten.no/cam0"
echo "   VDO.ninja: curl -I https://app.itagenten.no/vdo/ (NEW location)"
echo "   VDO.ninja (legacy redirect): curl -I https://r58-vdo.itagenten.no/ (should redirect)"
echo "   API: curl -I https://app.itagenten.no/static/r58_control.html"
echo ""
echo "🎉 Configuration complete!"

