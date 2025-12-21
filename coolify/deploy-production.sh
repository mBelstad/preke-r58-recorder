#!/bin/bash

# Production deployment script for R58 services on Coolify
# This script deploys services using Docker Compose with Traefik integration

set -e

echo "=== R58 Services Production Deployment ==="
echo ""

# Configuration
DEPLOY_DIR="/opt/r58-services"
REPO_URL="https://github.com/mBelstad/preke-r58-recorder.git"
BRANCH="feature/remote-access-v2"

# Check if running on Coolify server
if [ ! -d "/data/coolify" ]; then
    echo "⚠️  Warning: This doesn't appear to be a Coolify server"
    echo "Continuing anyway..."
fi

# Create deployment directory
echo "📁 Creating deployment directory..."
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# Clone or update repository
if [ -d "$DEPLOY_DIR/.git" ]; then
    echo "📥 Updating repository..."
    git fetch origin
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
else
    echo "📥 Cloning repository..."
    git clone -b "$BRANCH" "$REPO_URL" .
fi

# Navigate to coolify directory
cd coolify

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production not found"
    echo "Please create .env.production with CF_TURN_ID and CF_TURN_TOKEN"
    exit 1
fi

# Stop existing containers if any
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Build and start services
echo "🏗️  Building services..."
docker-compose -f docker-compose.production.yml build --no-cache

echo "🚀 Starting services..."
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "=== Service Status ==="
docker-compose -f docker-compose.production.yml ps

# Test services locally
echo ""
echo "=== Testing Services ==="

# Test TURN API
echo -n "Testing TURN API... "
if curl -s http://localhost:3000/health | grep -q "ok"; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

# Test Relay
echo -n "Testing Relay... "
if curl -s http://localhost:8080/health | grep -q "ok"; then
    echo "✅ OK"
else
    echo "❌ FAILED"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services are running with Traefik SSL:"
echo "  - TURN API: https://api.r58.itagenten.no"
echo "  - Relay: https://relay.r58.itagenten.no"
echo ""
echo "Wait 1-2 minutes for SSL certificates to be issued."
echo ""
echo "Test externally:"
echo "  curl https://api.r58.itagenten.no/health"
echo "  curl https://relay.r58.itagenten.no/health"
echo ""
echo "View logs:"
echo "  docker-compose -f $DEPLOY_DIR/coolify/docker-compose.production.yml logs -f"

