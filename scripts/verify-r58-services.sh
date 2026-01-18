#!/bin/bash
# Verify R58 services are running and configured correctly
# Run this script via: ./connect-r58-frp.sh "bash -s" < scripts/verify-r58-services.sh

set -e

echo "=== R58 Service Verification ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_service() {
    local service=$1
    local description=$2
    
    echo -n "Checking $description ($service)... "
    if systemctl is-active --quiet "$service"; then
        echo -e "${GREEN}✓ Running${NC}"
        systemctl status "$service" --no-pager -l | head -3
    else
        echo -e "${RED}✗ Not running${NC}"
        systemctl status "$service" --no-pager -l | head -5
        return 1
    fi
    echo ""
}

# Check if service is enabled
check_enabled() {
    local service=$1
    if systemctl is-enabled --quiet "$service"; then
        echo -e "  ${GREEN}✓ Enabled on boot${NC}"
    else
        echo -e "  ${YELLOW}⚠ Not enabled on boot${NC}"
    fi
}

echo "=== Core Services ==="
check_service "preke-recorder" "Main Recorder Service"
check_enabled "preke-recorder"

check_service "mediamtx" "MediaMTX Streaming Server"
check_enabled "mediamtx"

echo "=== Network Services ==="
check_service "frpc" "FRP Client"
check_enabled "frpc"

check_service "tailscale-userspace" "Tailscale P2P"
check_enabled "tailscale-userspace"

check_service "tailscale-funnel" "Tailscale Funnel"
check_enabled "tailscale-funnel"

echo "=== Service Ports ==="
echo "Checking if ports are listening..."
netstat -tlnp 2>/dev/null | grep -E ":(8000|8889|8888|8554|22)" || ss -tlnp | grep -E ":(8000|8889|8888|8554|22)"

echo ""
echo "=== FRP Configuration ==="
if [ -f "/etc/frp/frpc.toml" ]; then
    echo -e "${GREEN}✓ FRP config exists${NC}"
    echo "FRP config contents:"
    cat /etc/frp/frpc.toml
else
    echo -e "${RED}✗ FRP config missing: /etc/frp/frpc.toml${NC}"
fi

echo ""
echo "=== Tailscale Status ==="
if command -v tailscale >/dev/null 2>&1; then
    echo "Tailscale status:"
    tailscale status 2>/dev/null || echo "  (not logged in or error)"
    echo ""
    echo "Tailscale IP:"
    tailscale ip 2>/dev/null || echo "  (not available)"
    echo ""
    echo "Funnel status:"
    tailscale funnel status 2>/dev/null || echo "  (not configured)"
else
    echo -e "${RED}✗ Tailscale not installed${NC}"
fi

echo ""
echo "=== MediaMTX Status ==="
if curl -s http://localhost:9997/v3/paths/list > /dev/null 2>&1; then
    echo -e "${GREEN}✓ MediaMTX API responding${NC}"
    echo "Active paths:"
    curl -s http://localhost:9997/v3/paths/list | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f'  - {p[\"name\"]}: {\"ready\" if p.get(\"ready\") else \"not ready\"}') for p in d.get('items',[])]" 2>/dev/null || echo "  (could not parse)"
else
    echo -e "${RED}✗ MediaMTX API not responding${NC}"
fi

echo ""
echo "=== FastAPI Status ==="
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ FastAPI responding${NC}"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "  (could not parse)"
else
    echo -e "${RED}✗ FastAPI not responding${NC}"
fi

echo ""
echo "=== Verification Complete ==="
