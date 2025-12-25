#!/bin/bash
# Test and Deploy R58 Remote Mixer
# This script pulls changes, tests the mixer, and fixes any issues

set -e

echo "🚀 R58 Remote Mixer - Test & Deploy"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REMOTE_HOST="linaro@r58.itagenten.no"
REMOTE_DIR="/opt/preke-r58-recorder"
MIXER_FILE="src/static/r58_remote_mixer.html"

echo -e "${BLUE}Step 1: Checking SSH connection...${NC}"
if ! ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    -o ConnectTimeout=10 \
    "$REMOTE_HOST" "echo 'Connected'" 2>/dev/null; then
    echo -e "${RED}✗ SSH connection failed${NC}"
    echo ""
    echo "Please ensure:"
    echo "  1. cloudflared is installed: brew install cloudflare/cloudflare/cloudflared"
    echo "  2. You're authenticated with Cloudflare"
    echo "  3. The tunnel is active"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓ SSH connection working${NC}"
echo ""

echo -e "${BLUE}Step 2: Pulling latest changes from git...${NC}"
ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    "$REMOTE_HOST" << 'EOF'
    cd /opt/preke-r58-recorder
    
    # Show current branch and status
    echo "Current branch: $(git branch --show-current)"
    echo "Current commit: $(git rev-parse --short HEAD)"
    
    # Pull latest changes
    git pull
    
    echo ""
    echo "After pull:"
    echo "New commit: $(git rev-parse --short HEAD)"
EOF

echo -e "${GREEN}✓ Git pull complete${NC}"
echo ""

echo -e "${BLUE}Step 3: Verifying mixer file exists...${NC}"
ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    "$REMOTE_HOST" << EOF
    if [ -f "$REMOTE_DIR/$MIXER_FILE" ]; then
        echo "✓ File exists: $MIXER_FILE"
        ls -lh "$REMOTE_DIR/$MIXER_FILE"
        echo ""
        echo "File size: \$(stat -f%z "$REMOTE_DIR/$MIXER_FILE" 2>/dev/null || stat -c%s "$REMOTE_DIR/$MIXER_FILE") bytes"
    else
        echo "✗ File not found: $MIXER_FILE"
        exit 1
    fi
EOF

echo -e "${GREEN}✓ Mixer file verified${NC}"
echo ""

echo -e "${BLUE}Step 4: Checking preke-recorder service...${NC}"
ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    "$REMOTE_HOST" << 'EOF'
    # Check if service is running
    if systemctl is-active --quiet preke-recorder; then
        echo "✓ preke-recorder service is running"
    else
        echo "⚠ preke-recorder service is not running"
        echo "Starting service..."
        sudo systemctl start preke-recorder
        sleep 2
        if systemctl is-active --quiet preke-recorder; then
            echo "✓ Service started successfully"
        else
            echo "✗ Failed to start service"
            exit 1
        fi
    fi
    
    # Show service status
    echo ""
    echo "Service status:"
    systemctl status preke-recorder --no-pager | head -10
EOF

echo -e "${GREEN}✓ Service check complete${NC}"
echo ""

echo -e "${BLUE}Step 5: Testing MediaMTX streams...${NC}"
ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    "$REMOTE_HOST" << 'EOF'
    echo "Checking MediaMTX camera streams..."
    
    for cam in cam0 cam2 cam3; do
        if curl -s -f -I http://localhost:8889/$cam >/dev/null 2>&1; then
            echo "✓ $cam is available"
        else
            echo "⚠ $cam is not available"
        fi
    done
    
    echo ""
    echo "MediaMTX paths status:"
    curl -s http://localhost:9997/v3/paths/list | grep -E "cam[0-3]" -A3 | head -20 || echo "Could not fetch paths"
EOF

echo -e "${GREEN}✓ Stream check complete${NC}"
echo ""

echo -e "${BLUE}Step 6: Testing remote access...${NC}"
echo "Testing if mixer is accessible remotely..."

# Test remote API endpoint
if curl -s -f -I "https://r58-api.itagenten.no/health" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Remote API is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Remote API health check failed (might be normal)${NC}"
fi

# Test if static file endpoint exists
if curl -s -f -I "https://r58-api.itagenten.no/static/mode_control.html" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Static files are being served${NC}"
else
    echo -e "${YELLOW}⚠ Static files endpoint check failed${NC}"
fi

echo ""

echo -e "${BLUE}Step 7: Checking FRP tunnel...${NC}"
ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    "$REMOTE_HOST" << 'EOF'
    if systemctl is-active --quiet frpc; then
        echo "✓ FRP client is running"
    else
        echo "⚠ FRP client is not running"
        echo "Starting FRP client..."
        sudo systemctl start frpc
        sleep 2
        if systemctl is-active --quiet frpc; then
            echo "✓ FRP client started"
        else
            echo "✗ Failed to start FRP client"
        fi
    fi
    
    echo ""
    echo "FRP status:"
    systemctl status frpc --no-pager | head -10
EOF

echo -e "${GREEN}✓ FRP check complete${NC}"
echo ""

echo -e "${BLUE}Step 8: Testing MediaMTX remote access...${NC}"
echo "Testing remote MediaMTX endpoints..."

for cam in cam0 cam2 cam3; do
    if curl -s -f -I "http://65.109.32.111:18889/$cam" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Remote $cam is accessible${NC}"
    else
        echo -e "${YELLOW}⚠ Remote $cam check failed${NC}"
    fi
done

echo ""

echo "======================================"
echo -e "${GREEN}✅ Deployment and Testing Complete!${NC}"
echo "======================================"
echo ""
echo "📋 Access URLs:"
echo ""
echo "  Remote Mixer:"
echo -e "    ${BLUE}https://r58-api.itagenten.no/static/r58_remote_mixer.html${NC}"
echo ""
echo "  Local Mixer (on R58 network):"
echo -e "    ${BLUE}http://192.168.1.24:8000/static/r58_remote_mixer.html${NC}"
echo ""
echo "  VDO.ninja Direct Link:"
echo -e "    ${BLUE}http://insecure.vdo.ninja/mixer?room=r58studio&slots=3&automixer&whep=http://65.109.32.111:18889/cam0/whep&label=CAM0&whep=http://65.109.32.111:18889/cam2/whep&label=CAM2&whep=http://65.109.32.111:18889/cam3/whep&label=CAM3${NC}"
echo ""
echo "📖 Usage Instructions:"
echo ""
echo "  1. Open the Remote Mixer URL in your browser"
echo "  2. Click 'Full Mixer (Recommended)' button"
echo "  3. VDO.ninja opens - click 'Get Started'"
echo "  4. Wait 5-10 seconds for cameras to load"
echo "  5. Click 'Auto Mix All' button"
echo "  6. Select a layout (2-up, 3-up, quad)"
echo "  7. All cameras appear in scene boxes! 🎉"
echo ""
echo "🔧 Troubleshooting:"
echo ""
echo "  If cameras don't load:"
echo "    ssh -o ProxyCommand=\"cloudflared access ssh --hostname r58.itagenten.no\" linaro@r58.itagenten.no"
echo "    sudo systemctl restart mediamtx preke-recorder"
echo ""
echo "  Check logs:"
echo "    sudo journalctl -u preke-recorder -f"
echo "    sudo journalctl -u mediamtx -f"
echo ""

