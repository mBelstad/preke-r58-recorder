#!/bin/bash
#
# R58 Software Update Script
# Updates VDO.ninja, raspberry.ninja, MediaMTX and signaling server
#

set -e

echo "==========================================="
echo "R58 Software Update Script"
echo "==========================================="
echo ""

# 1. Update MediaMTX from v1.5.1 to latest
echo "📦 Updating MediaMTX..."
MEDIAMTX_CURRENT=$(/usr/local/bin/mediamtx --version 2>&1 || echo "unknown")
echo "   Current version: $MEDIAMTX_CURRENT"

# Detect architecture
ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ]; then
    MEDIAMTX_ARCH="arm64v8"
elif [ "$ARCH" = "armv7l" ]; then
    MEDIAMTX_ARCH="armv7"
else
    MEDIAMTX_ARCH="amd64"
fi

# Get latest release tag
LATEST=$(curl -s https://api.github.com/repos/bluenviron/mediamtx/releases/latest | grep tag_name | cut -d'"' -f4)
echo "   Latest version: $LATEST"

if [ "$MEDIAMTX_CURRENT" != "$LATEST" ]; then
    echo "   Downloading MediaMTX $LATEST for $MEDIAMTX_ARCH..."
    cd /tmp
    wget -q "https://github.com/bluenviron/mediamtx/releases/download/${LATEST}/mediamtx_${LATEST}_linux_${MEDIAMTX_ARCH}.tar.gz" -O mediamtx.tar.gz
    tar -xzf mediamtx.tar.gz
    sudo systemctl stop mediamtx 2>/dev/null || true
    sudo cp mediamtx /usr/local/bin/mediamtx
    sudo chmod +x /usr/local/bin/mediamtx
    sudo systemctl start mediamtx 2>/dev/null || true
    echo "   ✅ MediaMTX updated to $LATEST"
    rm -f mediamtx.tar.gz mediamtx
else
    echo "   ✅ MediaMTX is already up to date"
fi

echo ""

# 2. Update raspberry.ninja
echo "📦 Updating raspberry.ninja..."
cd /opt/raspberry_ninja
git fetch --tags 2>/dev/null || true
CURRENT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "none")
LATEST_TAG=$(git describe --tags $(git rev-list --tags --max-count=1) 2>/dev/null || echo "main")
echo "   Current: $CURRENT_TAG"
echo "   Latest: $LATEST_TAG"

if [ "$CURRENT_TAG" != "$LATEST_TAG" ]; then
    echo "   Pulling latest changes..."
    git stash 2>/dev/null || true
    git checkout main
    git pull origin main
    git checkout "$LATEST_TAG" 2>/dev/null || git checkout main
    echo "   ✅ raspberry.ninja updated"
else
    echo "   ✅ raspberry.ninja is already up to date"
fi

echo ""

# 3. Update VDO.ninja
echo "📦 Updating VDO.ninja..."
cd /opt/vdo.ninja
git fetch --tags 2>/dev/null || true
CURRENT_VDO=$(grep 'ver=' index.html | head -1 | grep -oP 'ver=\K[0-9]+' || echo "unknown")
echo "   Current: ver=$CURRENT_VDO"

git stash 2>/dev/null || true
git pull origin main 2>/dev/null || git pull origin master
NEW_VDO=$(grep 'ver=' index.html | head -1 | grep -oP 'ver=\K[0-9]+' || echo "unknown")
echo "   Updated: ver=$NEW_VDO"
echo "   ✅ VDO.ninja updated"

echo ""

# 4. Replace signaling server with simple broadcast version
echo "📦 Updating VDO.ninja signaling server..."
cat > /opt/vdo-signaling/vdo-server-simple.js << 'SERVEREOF'
//
// Official VDO.Ninja Websocket Server (simplified broadcast-all)
// Based on https://github.com/steveseguin/websocket_server
//

"use strict";
const fs = require("fs");
const https = require("https");
const express = require("express");
const path = require("path");
const WebSocket = require("ws");

const app = express();

// SSL certificates
const SSL_KEY = "/opt/vdo-signaling/ssl/key.pem";
const SSL_CERT = "/opt/vdo-signaling/ssl/cert.pem";

let key, cert;
try {
    key = fs.readFileSync(SSL_KEY);
    cert = fs.readFileSync(SSL_CERT);
} catch (err) {
    console.error("Failed to load SSL certificates:", err.message);
    process.exit(1);
}

// Serve static VDO.ninja files
app.use(express.static('/opt/vdo.ninja'));

const server = https.createServer({ key, cert }, app);
const wss = new WebSocket.Server({ server });

function log(msg) {
    console.log(`[${new Date().toISOString()}] ${msg}`);
}

wss.on('connection', (ws, req) => {
    const clientIP = req.socket.remoteAddress;
    log(`New connection from ${clientIP} (total: ${wss.clients.size})`);

    ws.on('message', (message) => {
        // Simple broadcast to ALL other connected clients
        // This is how the official VDO.ninja websocket server works
        wss.clients.forEach(client => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(message.toString());
            }
        });
    });

    ws.on('close', () => {
        log(`Connection closed (remaining: ${wss.clients.size})`);
    });

    ws.on('error', (err) => {
        log(`WebSocket error: ${err.message}`);
    });
});

const PORT = 8443;
server.listen(PORT, () => {
    log(`VDO.Ninja Simple Websocket Server running on port ${PORT}`);
    log(`Static files served from /opt/vdo.ninja`);
    log(`This server broadcasts ALL messages to ALL clients (official behavior)`);
});
SERVEREOF

# Backup old server and switch to simple version
cp /opt/vdo-signaling/vdo-server.js /opt/vdo-signaling/vdo-server-complex-backup.js 2>/dev/null || true
cp /opt/vdo-signaling/vdo-server-simple.js /opt/vdo-signaling/vdo-server.js

# Restart signaling service
sudo systemctl restart vdo-ninja 2>/dev/null || true
echo "   ✅ Signaling server updated to simple broadcast version"

echo ""
echo "==========================================="
echo "✅ All updates complete!"
echo "==========================================="
echo ""
echo "Restarting services..."
sudo systemctl restart mediamtx 2>/dev/null || true
sudo systemctl restart vdo-ninja 2>/dev/null || true
echo ""
echo "Current versions:"
echo "  MediaMTX: $(/usr/local/bin/mediamtx --version 2>&1)"
echo "  VDO.ninja: ver=$(grep 'ver=' /opt/vdo.ninja/index.html | head -1 | grep -oP 'ver=\K[0-9]+' || echo 'unknown')"
echo "  raspberry.ninja: $(cd /opt/raspberry_ninja && git describe --tags --abbrev=0 2>/dev/null || echo 'main')"

