#!/bin/bash
# Verify VPS services are running and configured correctly
# Run this on the VPS: ssh root@65.109.32.111 "bash -s" < scripts/verify-vps-services.sh

set -e

echo "=== VPS Service Verification ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== FRP Server ==="
if docker ps | grep -q frp; then
    echo -e "${GREEN}✓ FRP container running${NC}"
    docker ps | grep frp
    echo ""
    echo "Recent FRP logs:"
    docker logs frps --tail 20 2>/dev/null || docker logs $(docker ps | grep frp | awk '{print $1}') --tail 20
else
    echo -e "${RED}✗ FRP container not running${NC}"
fi

echo ""
echo "=== Nginx Proxy ==="
if docker ps | grep -q nginx; then
    echo -e "${GREEN}✓ Nginx container running${NC}"
    docker ps | grep nginx
    echo ""
    echo "Checking nginx config for R58 routes..."
    if docker exec $(docker ps | grep nginx | awk '{print $1}') cat /etc/nginx/conf.d/r58-proxy.conf 2>/dev/null; then
        echo -e "${GREEN}✓ R58 proxy config found${NC}"
    else
        echo -e "${YELLOW}⚠ R58 proxy config not found${NC}"
    fi
else
    echo -e "${RED}✗ Nginx container not running${NC}"
fi

echo ""
echo "=== Relay Service ==="
if docker ps | grep -q relay; then
    echo -e "${GREEN}✓ Relay container running${NC}"
    docker ps | grep relay
    echo ""
    echo "Testing relay health:"
    curl -s https://relay.r58.itagenten.no/health | python3 -m json.tool 2>/dev/null || echo "  (could not reach)"
else
    echo -e "${YELLOW}⚠ Relay container not running (optional)${NC}"
fi

echo ""
echo "=== Port Status ==="
echo "Checking if FRP ports are listening..."
netstat -tlnp 2>/dev/null | grep -E ":(7000|10022|18889|18888|18000)" || ss -tlnp | grep -E ":(7000|10022|18889|18888|18000)"

echo ""
echo "=== Traefik (Coolify) ==="
if docker ps | grep -q traefik; then
    echo -e "${GREEN}✓ Traefik running${NC}"
else
    echo -e "${YELLOW}⚠ Traefik not found (may be managed by Coolify)${NC}"
fi

echo ""
echo "=== Verification Complete ==="
