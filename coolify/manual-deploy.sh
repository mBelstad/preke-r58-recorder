#!/bin/bash

# Manual deployment script for R58 services
# Run this on the Coolify server to deploy services directly with Docker

set -e

echo "=== R58 Services Manual Deployment ==="

# Configuration
REPO_URL="https://github.com/mBelstad/preke-r58-recorder.git"
BRANCH="feature/remote-access-v2"
DEPLOY_DIR="/opt/r58-services"

# Cloudflare TURN credentials (replace with actual values)
CF_TURN_ID="${CF_TURN_ID:-your_turn_id_here}"
CF_TURN_TOKEN="${CF_TURN_TOKEN:-your_turn_token_here}"

echo "Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v git >/dev/null 2>&1 || { echo "Git is required but not installed."; exit 1; }

# Clone or update repository
if [ -d "$DEPLOY_DIR" ]; then
    echo "Updating existing repository..."
    cd "$DEPLOY_DIR"
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    echo "Cloning repository..."
    git clone --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
fi

# Stop and remove existing containers
echo "Stopping existing containers..."
docker stop r58-turn-api 2>/dev/null || true
docker rm r58-turn-api 2>/dev/null || true
docker stop r58-relay 2>/dev/null || true
docker rm r58-relay 2>/dev/null || true

# Build and deploy TURN API
echo ""
echo "=== Deploying TURN API ==="
cd "$DEPLOY_DIR/coolify/r58-turn-api"
docker build -t r58-turn-api:latest .
docker run -d \
    --name r58-turn-api \
    -p 3000:3000 \
    -e CF_TURN_ID="$CF_TURN_ID" \
    -e CF_TURN_TOKEN="$CF_TURN_TOKEN" \
    -e PORT=3000 \
    --restart unless-stopped \
    r58-turn-api:latest

echo "✓ TURN API deployed on port 3000"

# Build and deploy relay
echo ""
echo "=== Deploying Relay ==="
cd "$DEPLOY_DIR/coolify/r58-relay"
docker build -t r58-relay:latest .
docker run -d \
    --name r58-relay \
    -p 8080:8080 \
    -e PORT=8080 \
    --restart unless-stopped \
    r58-relay:latest

echo "✓ Relay deployed on port 8080"

# Test services
echo ""
echo "=== Testing Services ==="
sleep 3

echo -n "TURN API health check: "
curl -s http://localhost:3000/health | grep -q "ok" && echo "✓ OK" || echo "✗ FAILED"

echo -n "Relay health check: "
curl -s http://localhost:8080/health | grep -q "ok" && echo "✓ OK" || echo "✗ FAILED"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services are running:"
echo "  - TURN API: http://localhost:3000"
echo "  - Relay: http://localhost:8080"
echo ""
echo "Next steps:"
echo "  1. Configure reverse proxy (Coolify/nginx) for SSL"
echo "  2. Set up DNS records:"
echo "     - api.r58.itagenten.no -> 65.109.32.111:3000"
echo "     - relay.r58.itagenten.no -> 65.109.32.111:8080"
echo ""
echo "View logs:"
echo "  docker logs -f r58-turn-api"
echo "  docker logs -f r58-relay"

