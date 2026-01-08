#!/bin/bash
# Simple, Reliable R58 Deployment Script
# Deploys code to R58 device via FRP tunnel
# Uses connect-r58-frp.sh for SSH (SSH key auth, reliable timeouts)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration - Set the branch to deploy
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}"
echo "======================================"
echo "R58 Simple Deployment Script"
echo "======================================"
echo -e "${NC}"
echo -e "${BLUE}Deploying branch: ${DEPLOY_BRANCH}${NC}"
echo ""

# Check connect script exists
if [[ ! -x "$SCRIPT_DIR/connect-r58-frp.sh" ]]; then
    echo -e "${RED}Error: connect-r58-frp.sh not found or not executable${NC}"
    exit 1
fi

# Check if we're on the correct branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" != "$DEPLOY_BRANCH" ]]; then
    echo -e "${YELLOW}Warning: Currently on branch '$CURRENT_BRANCH', but deploying '$DEPLOY_BRANCH'${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Deployment cancelled${NC}"
        exit 1
    fi
fi

# Step 1: Push to GitHub
echo -e "${YELLOW}Step 1: Pushing to GitHub...${NC}"
if [ -d ".git" ]; then
    # Ensure we're on the deploy branch
    git checkout "$DEPLOY_BRANCH" || {
        echo -e "${RED}Error: Could not checkout branch '$DEPLOY_BRANCH'${NC}"
        exit 1
    }
    
    git add . || true
    git commit -m "Deploy: $(date +%Y%m%d_%H%M%S)" || echo "Nothing to commit"
    git push origin "$DEPLOY_BRANCH" || {
        echo -e "${RED}Error: Failed to push to origin/$DEPLOY_BRANCH${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Pushed to GitHub (origin/$DEPLOY_BRANCH)${NC}"
else
    echo -e "${RED}✗ Not a git repository${NC}"
    exit 1
fi
echo ""

# Step 2: Deploy to R58
echo -e "${YELLOW}Step 2: Deploying to R58 via FRP tunnel...${NC}"
echo -e "${BLUE}This will:${NC}"
echo -e "  1. Check current branch on R58 device"
echo -e "  2. Switch to '$DEPLOY_BRANCH' branch if needed"
echo -e "  3. Pull latest code"
echo -e "  4. Restart preke-recorder service"
echo ""

DEPLOY_COMMANDS="cd /opt/preke-r58-recorder && \
    echo 'Current branch:' && git rev-parse --abbrev-ref HEAD && \
    echo 'Switching to $DEPLOY_BRANCH...' && \
    git fetch origin && \
    git checkout $DEPLOY_BRANCH && \
    echo 'Stashing local changes (build artifacts)...' && \
    git stash push -m 'Deploy: stashing local changes' || true && \
    echo 'Cleaning untracked build artifacts...' && \
    git clean -fd packages/frontend/dist/ || true && \
    git pull origin $DEPLOY_BRANCH && \
    echo 'Latest commit:' && git log -1 --oneline && \
    echo 'Setting up VDO.ninja if needed...' && \
    sudo bash scripts/setup-vdoninja.sh && \
    echo 'Setting up Reveal.js if needed...' && \
    NON_INTERACTIVE=true sudo bash setup_revealjs.sh && \
    sudo systemctl restart preke-recorder && \
    echo 'Deployment complete!'"

"$SCRIPT_DIR/connect-r58-frp.sh" "$DEPLOY_COMMANDS"

echo ""
echo -e "${GREEN}======================================"
echo "Deployment Successful!"
echo "======================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Test: https://app.itagenten.no/static/app.html"
echo "  2. Check logs: ./connect-r58-frp.sh 'sudo journalctl -u preke-recorder -f'"
echo ""

