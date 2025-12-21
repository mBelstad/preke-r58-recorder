#!/bin/bash

# Deploy R58 services to Coolify
# This script should be run on the Coolify server

set -e

echo "=== R58 Services Deployment to Coolify ==="
echo ""
echo "This script will deploy:"
echo "  1. r58-turn-api (api.r58.itagenten.no)"
echo "  2. r58-relay (relay.r58.itagenten.no)"
echo ""

# Check if we're on the Coolify server
if [ ! -f "/data/coolify/source/.env" ]; then
    echo "Error: This doesn't appear to be a Coolify server"
    echo "Please run this script on the Coolify server (65.109.32.111)"
    exit 1
fi

# Create deployment directory
DEPLOY_DIR="/tmp/r58-deploy-$(date +%s)"
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

echo "Cloning repository..."
git clone --branch feature/remote-access-v2 https://github.com/mBelstad/preke-r58-recorder.git
cd preke-r58-recorder

echo ""
echo "=== Deployment Instructions ==="
echo ""
echo "Services are ready to deploy. You have two options:"
echo ""
echo "Option 1: Deploy via Coolify Web UI"
echo "  1. Open Coolify dashboard"
echo "  2. Create new service -> Dockerfile"
echo "  3. For r58-turn-api:"
echo "     - Name: r58-turn-api"
echo "     - Repository: https://github.com/mBelstad/preke-r58-recorder.git"
echo "     - Branch: feature/remote-access-v2"
echo "     - Dockerfile path: coolify/r58-turn-api/Dockerfile"
echo "     - Build context: coolify/r58-turn-api"
echo "     - Domain: api.r58.itagenten.no"
echo "     - Port: 3000"
echo "     - Environment variables:"
echo "       CF_TURN_ID=<your_cloudflare_turn_id>"
echo "       CF_TURN_TOKEN=<your_cloudflare_turn_token>"
echo ""
echo "  4. For r58-relay:"
echo "     - Name: r58-relay"
echo "     - Repository: https://github.com/mBelstad/preke-r58-recorder.git"
echo "     - Branch: feature/remote-access-v2"
echo "     - Dockerfile path: coolify/r58-relay/Dockerfile"
echo "     - Build context: coolify/r58-relay"
echo "     - Domain: relay.r58.itagenten.no"
echo "     - Port: 8080"
echo "     - Enable WebSocket: Yes"
echo ""
echo "Option 2: Manual Docker deployment (for testing)"
echo "  Run the following commands:"
echo ""
echo "  # Build and run TURN API"
echo "  cd $DEPLOY_DIR/preke-r58-recorder/coolify/r58-turn-api"
echo "  docker build -t r58-turn-api ."
echo "  docker run -d --name r58-turn-api \\"
echo "    -p 3000:3000 \\"
echo "    -e CF_TURN_ID=your_turn_id \\"
echo "    -e CF_TURN_TOKEN=your_turn_token \\"
echo "    --restart unless-stopped \\"
echo "    r58-turn-api"
echo ""
echo "  # Build and run relay"
echo "  cd $DEPLOY_DIR/preke-r58-recorder/coolify/r58-relay"
echo "  docker build -t r58-relay ."
echo "  docker run -d --name r58-relay \\"
echo "    -p 8080:8080 \\"
echo "    --restart unless-stopped \\"
echo "    r58-relay"
echo ""
echo "After deployment, test with:"
echo "  curl http://localhost:3000/health"
echo "  curl http://localhost:8080/health"
echo ""
echo "Then configure DNS and SSL via Coolify or Cloudflare."

