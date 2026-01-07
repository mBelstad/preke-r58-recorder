#!/bin/bash
# Setup VDO.ninja on R58 device
# Installs VDO.ninja, configures services, and sets up FRP tunnel

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}"
echo "======================================"
echo "VDO.ninja Setup Script"
echo "======================================"
echo -e "${NC}"

# Check if running as root or with sudo
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}This script must be run as root or with sudo${NC}"
   exit 1
fi

# Configuration
VDO_INSTALL_DIR="/opt/vdo.ninja"
VDO_SIGNALING_DIR="/opt/vdo-signaling"
VDO_VERSION="v28.0.0"  # Minimum version with WHEP support
VDO_PORT=8443
VDO_WEBAPP_PORT=8444
FRP_CONFIG="/opt/frp/frpc.toml"

# Check if VDO.ninja is already installed
if [[ -d "$VDO_INSTALL_DIR" ]] || [[ -d "$VDO_SIGNALING_DIR" ]]; then
    echo -e "${YELLOW}VDO.ninja appears to be installed${NC}"
    echo "Checking services..."
    
    if systemctl is-active --quiet vdo-ninja 2>/dev/null; then
        echo -e "${GREEN}✓ vdo-ninja.service is running${NC}"
    else
        echo -e "${YELLOW}⚠ vdo-ninja.service is not running${NC}"
    fi
    
    if systemctl is-active --quiet vdo-webapp 2>/dev/null; then
        echo -e "${GREEN}✓ vdo-webapp.service is running${NC}"
    else
        echo -e "${YELLOW}⚠ vdo-webapp.service is not running${NC}"
    fi
else
    echo -e "${YELLOW}VDO.ninja not found. Installation requires manual setup.${NC}"
    echo ""
    echo "VDO.ninja installation steps:"
    echo "1. Download VDO.ninja from: https://github.com/steveseguin/vdoninja"
    echo "2. Extract to: $VDO_INSTALL_DIR"
    echo "3. Set up signaling server at: $VDO_SIGNALING_DIR"
    echo "4. Configure SSL certificates"
    echo ""
    echo "For now, we'll set up the services and FRP tunnel configuration."
    echo "You can install VDO.ninja later and the services will work."
fi

# Check and configure FRP tunnel
echo ""
echo -e "${BLUE}Checking FRP tunnel configuration...${NC}"

if [[ ! -f "$FRP_CONFIG" ]]; then
    echo -e "${RED}FRP config not found at $FRP_CONFIG${NC}"
    exit 1
fi

# Check if VDO.ninja tunnel exists in FRP config
if grep -q "vdoninja\|18443" "$FRP_CONFIG"; then
    echo -e "${GREEN}✓ VDO.ninja FRP tunnel already configured${NC}"
else
    echo -e "${YELLOW}Adding VDO.ninja FRP tunnel...${NC}"
    
    # Backup config
    cp "$FRP_CONFIG" "${FRP_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Add VDO.ninja tunnel (append to file)
    cat >> "$FRP_CONFIG" << 'EOF'

# VDO.ninja signaling server (WebSocket/HTTPS)
[[proxies]]
name = "vdoninja-wss"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8443
remotePort = 18443

# VDO.ninja web app (HTTP)
[[proxies]]
name = "vdoninja-webapp"
type = "tcp"
localIP = "127.0.0.1"
localPort = 8444
remotePort = 18444
EOF
    
    echo -e "${GREEN}✓ VDO.ninja FRP tunnels added${NC}"
    echo "Restart FRP client to apply: sudo systemctl restart frpc"
fi

# Install bridge service
echo ""
echo -e "${BLUE}Installing VDO.ninja bridge service...${NC}"

BRIDGE_SERVICE="$SCRIPT_DIR/vdoninja-bridge.service"
BRIDGE_SCRIPT="$SCRIPT_DIR/start-vdoninja-bridge.sh"

# Check if service file exists in scripts, otherwise check archived
if [[ ! -f "$BRIDGE_SERVICE" ]]; then
    ARCHIVED_SERVICE="$PROJECT_DIR/services/archived/vdoninja-bridge.service"
    if [[ -f "$ARCHIVED_SERVICE" ]]; then
        echo -e "${YELLOW}Using archived service file${NC}"
        BRIDGE_SERVICE="$ARCHIVED_SERVICE"
    else
        echo -e "${RED}Bridge service file not found${NC}"
        exit 1
    fi
fi

if [[ ! -f "$BRIDGE_SCRIPT" ]]; then
    echo -e "${RED}Bridge script not found: $BRIDGE_SCRIPT${NC}"
    exit 1
fi

# Make bridge script executable
chmod +x "$BRIDGE_SCRIPT"

# Copy service file
cp "$BRIDGE_SERVICE" /etc/systemd/system/vdoninja-bridge.service

# Create log file
touch /var/log/vdoninja-bridge.log
chown linaro:linaro /var/log/vdoninja-bridge.log

# Reload systemd
systemctl daemon-reload

echo -e "${GREEN}✓ VDO.ninja bridge service installed${NC}"
echo ""
echo -e "${YELLOW}Note: The bridge service is NOT enabled by default.${NC}"
echo "It's controlled by mode_manager.py (starts in mixer mode, stops in recorder/idle mode)."

# Summary
echo ""
echo -e "${GREEN}======================================"
echo "VDO.ninja Setup Complete"
echo "======================================"
echo -e "${NC}"
echo ""
echo "Next steps:"
echo "1. If VDO.ninja is not installed, install it manually:"
echo "   - Download from: https://github.com/steveseguin/vdoninja"
echo "   - Extract to: $VDO_INSTALL_DIR"
echo ""
echo "2. If FRP config was updated, restart FRP:"
echo "   sudo systemctl restart frpc"
echo ""
echo "3. Check service status:"
echo "   systemctl status vdo-ninja vdo-webapp"
echo ""
echo "4. Test VDO.ninja access:"
echo "   https://r58-vdo.itagenten.no/mixer.html?room=studio"
echo ""

