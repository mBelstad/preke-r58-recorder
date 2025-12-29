#!/bin/bash
# Coolify Deployment Script for vdo.itagenten.no
# Run this script to deploy MediaMTX and VDO.ninja to your Coolify server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔══════════════════════════════════════════╗
║  vdo.itagenten.no Deployment             ║
║  Coolify + MediaMTX + VDO.ninja          ║
╚══════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Check if we're on Coolify server
if [ ! -f "/etc/coolify" ] && [ ! -d "/data/coolify" ]; then
    echo -e "${YELLOW}⚠️  Warning: This doesn't appear to be a Coolify server${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Configuration
PROJECT_NAME="vdo-itagenten"
DEPLOY_DIR="/data/coolify/services/${PROJECT_NAME}"

echo -e "${BLUE}📦 Deployment Configuration${NC}"
echo "  Project: ${PROJECT_NAME}"
echo "  Directory: ${DEPLOY_DIR}"
echo ""

# Create deployment directory
echo -e "${YELLOW}📁 Creating deployment directory...${NC}"
sudo mkdir -p "${DEPLOY_DIR}"/{ssl,data,vdo-signaling}
cd "${DEPLOY_DIR}"

# Copy configuration files
echo -e "${YELLOW}📋 Copying configuration files...${NC}"
sudo cp -v ./mediamtx-coolify.yml "${DEPLOY_DIR}/mediamtx.yml"
sudo cp -v ./docker-compose-coolify.yml "${DEPLOY_DIR}/docker-compose.yml"
sudo cp -v ./nginx.conf "${DEPLOY_DIR}/nginx.conf"

# Generate SSL certificates (self-signed for testing)
if [ ! -f "${DEPLOY_DIR}/ssl/cert.pem" ]; then
    echo -e "${YELLOW}🔐 Generating SSL certificates...${NC}"
    sudo openssl req -x509 -newkey rsa:4096 -nodes \
        -keyout "${DEPLOY_DIR}/ssl/server.key" \
        -out "${DEPLOY_DIR}/ssl/server.crt" \
        -days 365 -subj "/CN=vdo.itagenten.no" \
        -addext "subjectAltName=DNS:vdo.itagenten.no,DNS:mediamtx.vdo.itagenten.no"
    
    sudo ln -sf server.crt "${DEPLOY_DIR}/ssl/cert.pem"
    sudo ln -sf server.key "${DEPLOY_DIR}/ssl/key.pem"
    
    echo -e "${GREEN}✅ SSL certificates generated${NC}"
else
    echo -e "${GREEN}✅ SSL certificates already exist${NC}"
fi

# Create VDO.ninja signaling server
echo -e "${YELLOW}🔧 Setting up VDO.ninja signaling server...${NC}"
cat > "${DEPLOY_DIR}/vdo-signaling/server.js" << 'SIGNALING_EOF'
"use strict";
const fs = require("fs");
const https = require("https");
const WebSocket = require("ws");

const key = fs.readFileSync("/ssl/server.key");
const cert = fs.readFileSync("/ssl/server.crt");

const server = https.createServer({ key, cert });
const wss = new WebSocket.Server({ server });

console.log("VDO.ninja signaling server starting...");

wss.on('connection', (ws) => {
    console.log("New client connected");
    
    ws.on('message', (message) => {
        // Broadcast to all other clients
        wss.clients.forEach((client) => {
            if (client !== ws && client.readyState === WebSocket.OPEN) {
                client.send(message.toString());
            }
        });
    });
    
    ws.on('close', () => {
        console.log("Client disconnected");
    });
});

server.listen(8443, () => {
    console.log("VDO.ninja signaling server running on :8443");
});
SIGNALING_EOF

# Create package.json for signaling server
cat > "${DEPLOY_DIR}/vdo-signaling/package.json" << 'PACKAGE_EOF'
{
  "name": "vdo-ninja-signaling",
  "version": "1.0.0",
  "description": "VDO.ninja WebSocket signaling server",
  "main": "server.js",
  "dependencies": {
    "ws": "^8.14.0"
  }
}
PACKAGE_EOF

echo -e "${GREEN}✅ VDO.ninja signaling server configured${NC}"

# Start deployment
echo ""
echo -e "${BLUE}🚀 Starting deployment...${NC}"
echo ""

# Pull Docker images
echo -e "${YELLOW}📥 Pulling Docker images...${NC}"
sudo docker-compose pull

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
sudo docker-compose up -d

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""

# Wait for services to start
echo -e "${YELLOW}⏳ Waiting for services to start...${NC}"
sleep 10

# Check service status
echo -e "${BLUE}📊 Service Status:${NC}"
sudo docker-compose ps

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment Successful! 🎉             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Display access URLs
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo ""
echo -e "  ${GREEN}MediaMTX Web UI:${NC}"
echo -e "    https://vdo.itagenten.no"
echo ""
echo -e "  ${GREEN}Camera Streams (WHEP):${NC}"
echo -e "    https://vdo.itagenten.no/cam0/whep"
echo -e "    https://vdo.itagenten.no/cam2/whep"
echo -e "    https://vdo.itagenten.no/cam3/whep"
echo ""
echo -e "  ${GREEN}Camera Viewers:${NC}"
echo -e "    https://vdo.itagenten.no/cam0"
echo -e "    https://vdo.itagenten.no/cam2"
echo -e "    https://vdo.itagenten.no/cam3"
echo ""
echo -e "  ${GREEN}MediaMTX API:${NC}"
echo -e "    https://vdo.itagenten.no/api/v3/paths/list"
echo ""
echo -e "  ${GREEN}VDO.ninja Signaling:${NC}"
echo -e "    wss://vdo.itagenten.no/signal"
echo ""

# Next steps
echo -e "${YELLOW}📝 Next Steps:${NC}"
echo ""
echo "  1. Update DNS records:"
echo "     A     vdo.itagenten.no → [Your Coolify Server IP]"
echo "     CNAME mediamtx.vdo.itagenten.no → vdo.itagenten.no"
echo ""
echo "  2. Configure R58 to publish via WHIP:"
echo "     Run: ./r58-whip-publisher.sh start"
echo ""
echo "  3. Access VDO.ninja mixer:"
echo "     https://vdo.ninja/mixer?wss=vdo.itagenten.no/signal&room=r58studio"
echo ""
echo "  4. View logs:"
echo "     docker-compose logs -f"
echo ""

exit 0






