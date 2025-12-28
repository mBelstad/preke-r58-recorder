#!/bin/bash

# Deploy R58 services with Traefik labels for SSL and routing
# Run this on the Coolify server

set -e

echo "=== R58 Services Deployment with Traefik ==="

# Configuration
CF_TURN_ID="${CF_TURN_ID:-79d61c83455a63d11a18c17bedb53d3f}"
CF_TURN_TOKEN="${CF_TURN_TOKEN:-9054653545421be55e42219295b74b1036d261e1c0259c2cf410fb9d8a372984}"

# Get Traefik network name
TRAEFIK_NETWORK=$(docker network ls --filter name=coolify --format "{{.Name}}" | head -1)
if [ -z "$TRAEFIK_NETWORK" ]; then
    echo "Error: Coolify/Traefik network not found"
    exit 1
fi
echo "Using Traefik network: $TRAEFIK_NETWORK"

# Stop and remove existing containers
echo "Stopping existing containers..."
docker stop r58-turn-api 2>/dev/null || true
docker rm r58-turn-api 2>/dev/null || true
docker stop r58-relay 2>/dev/null || true
docker rm r58-relay 2>/dev/null || true

# Deploy TURN API with Traefik labels
echo ""
echo "=== Deploying TURN API with Traefik ==="
docker run -d \
    --name r58-turn-api \
    --network "$TRAEFIK_NETWORK" \
    -e CF_TURN_ID="$CF_TURN_ID" \
    -e CF_TURN_TOKEN="$CF_TURN_TOKEN" \
    -e PORT=3000 \
    --label "traefik.enable=true" \
    --label "traefik.http.routers.r58-turn-api.rule=Host(\`api.r58.itagenten.no\`)" \
    --label "traefik.http.routers.r58-turn-api.entrypoints=websecure" \
    --label "traefik.http.routers.r58-turn-api.tls=true" \
    --label "traefik.http.routers.r58-turn-api.tls.certresolver=letsencrypt" \
    --label "traefik.http.services.r58-turn-api.loadbalancer.server.port=3000" \
    --restart unless-stopped \
    r58-turn-api:latest

echo "✓ TURN API deployed"

# Deploy Relay with Traefik labels
echo ""
echo "=== Deploying Relay with Traefik ==="
docker run -d \
    --name r58-relay \
    --network "$TRAEFIK_NETWORK" \
    -e PORT=8080 \
    --label "traefik.enable=true" \
    --label "traefik.http.routers.r58-relay.rule=Host(\`relay.r58.itagenten.no\`)" \
    --label "traefik.http.routers.r58-relay.entrypoints=websecure" \
    --label "traefik.http.routers.r58-relay.tls=true" \
    --label "traefik.http.routers.r58-relay.tls.certresolver=letsencrypt" \
    --label "traefik.http.services.r58-relay.loadbalancer.server.port=8080" \
    --restart unless-stopped \
    r58-relay:latest

echo "✓ Relay deployed"

# Wait for services to start
echo ""
echo "Waiting for services to start..."
sleep 5

# Test services
echo ""
echo "=== Testing Services ==="
docker exec r58-turn-api wget -q -O- http://localhost:3000/health && echo " ✓ TURN API OK" || echo " ✗ TURN API FAILED"
docker exec r58-relay wget -q -O- http://localhost:8080/health && echo " ✓ Relay OK" || echo " ✗ Relay FAILED"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Services are running with Traefik SSL:"
echo "  - TURN API: https://api.r58.itagenten.no"
echo "  - Relay: wss://relay.r58.itagenten.no"
echo ""
echo "Next steps:"
echo "  1. Configure DNS records in Cloudflare:"
echo "     - api.r58.itagenten.no -> 65.109.32.111"
echo "     - relay.r58.itagenten.no -> 65.109.32.111"
echo "  2. Wait for DNS propagation (1-5 minutes)"
echo "  3. Traefik will automatically request Let's Encrypt certificates"
echo ""
echo "Test externally:"
echo "  curl https://api.r58.itagenten.no/health"
echo "  curl https://relay.r58.itagenten.no/health"

