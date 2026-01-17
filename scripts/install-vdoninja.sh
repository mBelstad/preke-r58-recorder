#!/bin/bash
# Complete VDO.ninja Installation Script
# Installs VDO.ninja the way it was configured before the device wipe

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}"
echo "======================================"
echo "VDO.ninja Complete Installation"
echo "======================================"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root or with sudo${NC}"
   exit 1
fi

# Configuration
VDO_INSTALL_DIR="/opt/vdo.ninja"
VDO_SIGNALING_DIR="/opt/vdo-signaling"
VDO_CERTS_DIR="/opt/vdo.ninja/certs"
VDO_VERSION="v28.0.0"  # Required version (WHEP support)
VDO_PORT=8443
VDO_WEBAPP_PORT=8444
NODE_VERSION="20"

# Step 1: Install Node.js if not present
echo -e "${BLUE}Step 1: Checking Node.js...${NC}"
if ! command -v node &> /dev/null; then
    echo "Installing Node.js ${NODE_VERSION}..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
    apt-get install -y nodejs
    echo -e "${GREEN}✓ Node.js installed${NC}"
else
    NODE_VER=$(node --version)
    echo -e "${GREEN}✓ Node.js already installed: $NODE_VER${NC}"
fi

# Step 2: Download VDO.ninja
echo -e "${BLUE}Step 2: Installing VDO.ninja web app...${NC}"
if [[ -d "$VDO_INSTALL_DIR" ]]; then
    echo -e "${YELLOW}VDO.ninja directory exists, backing up...${NC}"
    mv "$VDO_INSTALL_DIR" "${VDO_INSTALL_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$VDO_INSTALL_DIR"
cd /tmp

# Download VDO.ninja
echo "Downloading VDO.ninja ${VDO_VERSION}..."
wget -q "https://github.com/steveseguin/vdo.ninja/archive/refs/tags/${VDO_VERSION}.tar.gz" -O vdo.ninja.tar.gz

# Extract
tar -xzf vdo.ninja.tar.gz
mv vdo.ninja-*/* "$VDO_INSTALL_DIR/"
rm -rf vdo.ninja-* vdo.ninja.tar.gz

echo -e "${GREEN}✓ VDO.ninja web app installed${NC}"

# Step 3: Create custom signaling server
echo -e "${BLUE}Step 3: Creating custom signaling server...${NC}"
mkdir -p "$VDO_SIGNALING_DIR"

# Create custom signaling server with room normalization
cat > "$VDO_SIGNALING_DIR/server.js" << 'SIGNALING_EOF'
/**
 * Custom VDO.ninja Signaling Server for R58
 * 
 * Features:
 * - Room normalization (all rooms become "studio")
 * - WebSocket signaling for WebRTC
 * - SSL/TLS support
 */

const https = require('https');
const fs = require('fs');
const WebSocket = require('ws');

const PORT = process.env.PORT || 8443;
const SSL_KEY = process.env.SSL_KEY || '/opt/vdo.ninja/certs/key.pem';
const SSL_CERT = process.env.SSL_CERT || '/opt/vdo.ninja/certs/cert.pem';

// Create HTTPS server
const server = https.createServer({
    key: fs.readFileSync(SSL_KEY),
    cert: fs.readFileSync(SSL_CERT)
}, (req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('VDO.ninja Signaling Server\n');
});

// Create WebSocket server
const wss = new WebSocket.Server({ server });

// Store connections by room
const rooms = new Map();

wss.on('connection', (ws, req) => {
    console.log('[Signaling] New connection');
    
    let currentRoom = null;
    let peerId = null;
    
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            
            // Normalize room names to "studio"
            if (data.room) {
                data.room = 'studio';
            }
            
            // Handle join room
            if (data.join) {
                currentRoom = data.room || 'studio';
                peerId = data.from || Date.now().toString();
                
                if (!rooms.has(currentRoom)) {
                    rooms.set(currentRoom, new Map());
                }
                rooms.get(currentRoom).set(peerId, ws);
                
                console.log(`[Signaling] Peer ${peerId} joined room ${currentRoom}`);
                
                // Notify peer of successful join
                ws.send(JSON.stringify({ joined: currentRoom, peerId }));
                
                // Notify existing peers
                const roomPeers = rooms.get(currentRoom);
                roomPeers.forEach((peerWs, id) => {
                    if (id !== peerId && peerWs.readyState === WebSocket.OPEN) {
                        peerWs.send(JSON.stringify({ 
                            peerJoined: peerId,
                            room: currentRoom 
                        }));
                    }
                });
            }
            
            // Forward signaling messages to target peer
            if (data.target && currentRoom) {
                const targetWs = rooms.get(currentRoom)?.get(data.target);
                if (targetWs && targetWs.readyState === WebSocket.OPEN) {
                    targetWs.send(JSON.stringify({
                        ...data,
                        from: peerId
                    }));
                }
            }
            
            // Broadcast to room
            if (data.broadcast && currentRoom) {
                const roomPeers = rooms.get(currentRoom);
                roomPeers?.forEach((peerWs, id) => {
                    if (id !== peerId && peerWs.readyState === WebSocket.OPEN) {
                        peerWs.send(JSON.stringify({
                            ...data,
                            from: peerId
                        }));
                    }
                });
            }
            
        } catch (e) {
            console.error('[Signaling] Error processing message:', e);
        }
    });
    
    ws.on('close', () => {
        if (currentRoom && peerId) {
            rooms.get(currentRoom)?.delete(peerId);
            console.log(`[Signaling] Peer ${peerId} left room ${currentRoom}`);
            
            // Notify remaining peers
            const roomPeers = rooms.get(currentRoom);
            roomPeers?.forEach((peerWs, id) => {
                if (peerWs.readyState === WebSocket.OPEN) {
                    peerWs.send(JSON.stringify({ 
                        peerLeft: peerId,
                        room: currentRoom 
                    }));
                }
            });
            
            // Clean up empty rooms
            if (roomPeers?.size === 0) {
                rooms.delete(currentRoom);
            }
        }
    });
    
    ws.on('error', (error) => {
        console.error('[Signaling] WebSocket error:', error);
    });
});

server.listen(PORT, () => {
    console.log(`[Signaling] Server running on port ${PORT}`);
    console.log(`[Signaling] SSL Key: ${SSL_KEY}`);
    console.log(`[Signaling] SSL Cert: ${SSL_CERT}`);
});
SIGNALING_EOF

# Install dependencies
cd "$VDO_SIGNALING_DIR"
npm init -y
npm install ws

echo -e "${GREEN}✓ Custom signaling server created${NC}"

# Step 4: Generate SSL certificates
echo -e "${BLUE}Step 4: Generating SSL certificates...${NC}"
mkdir -p "$VDO_CERTS_DIR"

if [[ ! -f "$VDO_CERTS_DIR/key.pem" ]]; then
    openssl req -x509 -newkey rsa:4096 -keyout "$VDO_CERTS_DIR/key.pem" -out "$VDO_CERTS_DIR/cert.pem" -days 3650 -nodes -subj "/C=NO/ST=Oslo/L=Oslo/O=Preke/CN=app.itagenten.no"
    echo -e "${GREEN}✓ SSL certificates generated${NC}"
else
    echo -e "${YELLOW}SSL certificates already exist${NC}"
fi

# Step 5: Create systemd services
echo -e "${BLUE}Step 5: Creating systemd services...${NC}"

# VDO.ninja signaling service
cat > /etc/systemd/system/vdo-ninja.service << EOF
[Unit]
Description=VDO.ninja Signaling Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=linaro
Group=linaro
WorkingDirectory=$VDO_SIGNALING_DIR
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=5

# Environment
Environment=NODE_ENV=production
Environment=PORT=$VDO_PORT
Environment=SSL_CERT=$VDO_CERTS_DIR/cert.pem
Environment=SSL_KEY=$VDO_CERTS_DIR/key.pem

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vdo-ninja

[Install]
WantedBy=multi-user.target
EOF

# VDO.ninja web app service
cat > /etc/systemd/system/vdo-webapp.service << EOF
[Unit]
Description=VDO.ninja Web App
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=linaro
Group=linaro
WorkingDirectory=$VDO_INSTALL_DIR
ExecStart=/usr/bin/python3 -m http.server $VDO_WEBAPP_PORT
Restart=always
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vdo-webapp

[Install]
WantedBy=multi-user.target
EOF

# Set ownership
chown -R linaro:linaro "$VDO_INSTALL_DIR" "$VDO_SIGNALING_DIR"

echo -e "${GREEN}✓ Systemd services created${NC}"

# Step 6: Reload systemd and start services
echo -e "${BLUE}Step 6: Starting services...${NC}"
systemctl daemon-reload
systemctl enable vdo-ninja vdo-webapp
systemctl start vdo-ninja
sleep 2
systemctl start vdo-webapp

# Check status
if systemctl is-active --quiet vdo-ninja; then
    echo -e "${GREEN}✓ vdo-ninja.service is running${NC}"
else
    echo -e "${RED}✗ vdo-ninja.service failed to start${NC}"
    journalctl -u vdo-ninja -n 20 --no-pager
fi

if systemctl is-active --quiet vdo-webapp; then
    echo -e "${GREEN}✓ vdo-webapp.service is running${NC}"
else
    echo -e "${RED}✗ vdo-webapp.service failed to start${NC}"
    journalctl -u vdo-webapp -n 20 --no-pager
fi

# Summary
echo ""
echo -e "${GREEN}======================================"
echo "VDO.ninja Installation Complete!"
echo "======================================"
echo -e "${NC}"
echo ""
echo "Installed components:"
echo "  - VDO.ninja ${VDO_VERSION} at ${VDO_INSTALL_DIR}"
echo "  - Custom signaling server at ${VDO_SIGNALING_DIR}"
echo "  - SSL certificates at ${VDO_CERTS_DIR}"
echo ""
echo "Services:"
echo "  - vdo-ninja.service (port ${VDO_PORT})"
echo "  - vdo-webapp.service (port ${VDO_WEBAPP_PORT})"
echo ""
echo "Access URLs:"
echo "  - Local: https://localhost:${VDO_PORT}/mixer.html"
echo "  - Remote: https://app.itagenten.no/vdo/mixer.html"
echo ""
echo "Next steps:"
echo "  1. Restart FRP to apply tunnel configuration:"
echo "     sudo systemctl restart frpc"
echo "  2. Test access: https://app.itagenten.no/vdo/mixer.html?room=studio"
echo ""

