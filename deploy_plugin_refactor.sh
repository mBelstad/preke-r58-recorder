#!/bin/bash
# Deploy Plugin Refactor to R58
# This script safely deploys the plugin architecture changes

set -e  # Exit on error

echo "=== R58 Plugin Refactor Deployment ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if we're on the R58 or deploying to it
if [ "$1" == "--remote" ]; then
    echo -e "${YELLOW}Deploying to remote R58...${NC}"
    REMOTE_HOST="rock@192.168.1.58"
    REMOTE_PATH="/home/rock/preke-r58-recorder"
    
    echo "1. Stopping services on R58..."
    ssh "$REMOTE_HOST" "sudo systemctl stop preke-recorder || true"
    
    echo "2. Backing up current installation..."
    ssh "$REMOTE_HOST" "cd $REMOTE_PATH && cp -r src src.backup.$(date +%Y%m%d_%H%M%S) || true"
    
    echo "3. Syncing new code..."
    rsync -avz --exclude='*.pyc' --exclude='__pycache__' --exclude='.git' \
        src/ "$REMOTE_HOST:$REMOTE_PATH/src/"
    rsync -avz config.yml "$REMOTE_HOST:$REMOTE_PATH/"
    
    echo "4. Restarting services..."
    ssh "$REMOTE_HOST" "sudo systemctl start preke-recorder"
    
    echo "5. Checking service status..."
    ssh "$REMOTE_HOST" "sudo systemctl status preke-recorder --no-pager | head -20"
    
    echo ""
    echo -e "${GREEN}✓ Deployment complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Check logs: ssh rock@192.168.1.58 'sudo journalctl -u preke-recorder -f'"
    echo "  2. Test recording: curl -X POST http://192.168.1.58:5000/api/recording/start"
    echo "  3. Test mixer: curl -X POST http://192.168.1.58:5000/api/mixer/start"
    
else
    echo -e "${YELLOW}Local deployment check...${NC}"
    echo ""
    
    echo "1. Verifying file structure..."
    
    # Check shared infrastructure
    if [ -f "src/database.py" ] && [ -f "src/files.py" ]; then
        echo -e "  ${GREEN}✓${NC} Shared infrastructure (database.py, files.py)"
    else
        echo -e "  ${RED}✗${NC} Missing shared infrastructure files"
        exit 1
    fi
    
    # Check graphics plugin
    if [ -d "src/graphics" ] && [ -f "src/graphics/__init__.py" ]; then
        echo -e "  ${GREEN}✓${NC} Graphics plugin directory"
    else
        echo -e "  ${RED}✗${NC} Missing graphics plugin"
        exit 1
    fi
    
    # Check mixer plugin
    if [ -f "src/mixer/__init__.py" ]; then
        echo -e "  ${GREEN}✓${NC} Mixer plugin updated"
    else
        echo -e "  ${RED}✗${NC} Missing mixer plugin"
        exit 1
    fi
    
    # Check config
    if grep -q "graphics:" config.yml; then
        echo -e "  ${GREEN}✓${NC} Config updated with graphics section"
    else
        echo -e "  ${RED}✗${NC} Config missing graphics section"
        exit 1
    fi
    
    echo ""
    echo "2. Testing Python imports..."
    python3 -c "
from src.database import Database
from src.files import FileManager
from src.graphics import create_graphics_plugin
from src.mixer import create_mixer_plugin
print('  ✓ All imports successful')
" || exit 1
    
    echo ""
    echo -e "${GREEN}✓ Local verification complete!${NC}"
    echo ""
    echo "Ready to deploy to R58. Run:"
    echo "  ./deploy_plugin_refactor.sh --remote"
fi


