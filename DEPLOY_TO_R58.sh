#!/bin/bash
# Safe Deployment Script for R58 WebRTC Feature
# Run this ON THE R58 DEVICE

set -e  # Exit on error

echo "==================================="
echo "R58 WebRTC Deployment Script"
echo "==================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo "ℹ️  $1"
}

# Check if running on R58
echo "Step 1: Verifying environment..."
if [ ! -d "/home/linaro" ]; then
    print_warning "Not running as linaro user, continuing anyway..."
fi

# Find project directory
if [ -d "/home/linaro/preke-r58-recorder" ]; then
    PROJECT_DIR="/home/linaro/preke-r58-recorder"
elif [ -d "$(pwd)/preke-r58-recorder" ]; then
    PROJECT_DIR="$(pwd)/preke-r58-recorder"
elif [ -d "$(pwd)" ] && [ -f "$(pwd)/src/main.py" ]; then
    PROJECT_DIR="$(pwd)"
else
    print_error "Could not find project directory!"
    echo "Please run this script from the project directory or specify the path."
    exit 1
fi

print_success "Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Backup current state
echo ""
echo "Step 2: Creating backup..."
BACKUP_BRANCH=$(git branch --show-current)
BACKUP_COMMIT=$(git rev-parse HEAD)
print_info "Current branch: $BACKUP_BRANCH"
print_info "Current commit: $BACKUP_COMMIT"
echo "$BACKUP_BRANCH" > /tmp/r58_backup_branch.txt
echo "$BACKUP_COMMIT" > /tmp/r58_backup_commit.txt
print_success "Backup info saved to /tmp/r58_backup_*.txt"

# Check for uncommitted changes
echo ""
echo "Step 3: Checking for uncommitted changes..."
if ! git diff --quiet || ! git diff --cached --quiet; then
    print_warning "You have uncommitted changes!"
    git status --short
    echo ""
    read -p "Do you want to stash these changes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash push -m "Pre-WebRTC-deployment backup $(date +%Y%m%d_%H%M%S)"
        print_success "Changes stashed"
    else
        print_error "Deployment cancelled. Please commit or stash your changes first."
        exit 1
    fi
fi

# Fetch latest changes
echo ""
echo "Step 4: Fetching latest changes from GitHub..."
if git fetch origin; then
    print_success "Fetched latest changes"
else
    print_error "Failed to fetch from origin"
    exit 1
fi

# Checkout feature branch
echo ""
echo "Step 5: Checking out feature branch..."
print_info "Switching to: feature/webrtc-switcher-preview"
if git checkout feature/webrtc-switcher-preview; then
    print_success "Checked out feature branch"
else
    print_error "Failed to checkout feature branch"
    exit 1
fi

# Pull latest changes
echo ""
echo "Step 6: Pulling latest changes..."
if git pull origin feature/webrtc-switcher-preview; then
    print_success "Pulled latest changes"
else
    print_error "Failed to pull changes"
    exit 1
fi

# Verify WebRTC code is present
echo ""
echo "Step 7: Verifying WebRTC implementation..."
if grep -q "function getWebRTCUrl" src/static/switcher.html; then
    print_success "getWebRTCUrl() function found"
else
    print_error "getWebRTCUrl() function NOT found!"
    echo "The WebRTC code may not be in this branch."
    exit 1
fi

if grep -q "function startWebRTCPreview" src/static/switcher.html; then
    print_success "startWebRTCPreview() function found"
else
    print_error "startWebRTCPreview() function NOT found!"
    exit 1
fi

if grep -q "let webrtcConnections" src/static/switcher.html; then
    print_success "webrtcConnections storage found"
else
    print_error "webrtcConnections storage NOT found!"
    exit 1
fi

print_success "WebRTC code verified!"

# Check MediaMTX status
echo ""
echo "Step 8: Checking MediaMTX status..."
if systemctl is-active --quiet mediamtx 2>/dev/null; then
    print_success "MediaMTX service is running"
elif ps aux | grep -v grep | grep -q mediamtx; then
    print_success "MediaMTX process is running"
else
    print_warning "MediaMTX is NOT running!"
    echo "WebRTC requires MediaMTX. Please start it first:"
    echo "  sudo systemctl start mediamtx"
fi

# Check if service needs restart
echo ""
echo "Step 9: Checking R58 recorder service..."
if systemctl is-active --quiet r58-recorder 2>/dev/null; then
    print_info "R58 recorder service is running"
    echo ""
    read -p "Do you want to restart the service now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Restarting r58-recorder service..."
        if sudo systemctl restart r58-recorder; then
            print_success "Service restarted successfully"
            sleep 3
            if systemctl is-active --quiet r58-recorder; then
                print_success "Service is running"
            else
                print_error "Service failed to start!"
                echo "Check logs: sudo journalctl -u r58-recorder -n 50"
                exit 1
            fi
        else
            print_error "Failed to restart service"
            exit 1
        fi
    else
        print_warning "Service NOT restarted. Changes will take effect on next restart."
    fi
elif ps aux | grep -v grep | grep -q "python.*main.py"; then
    print_warning "R58 recorder is running but not as a service"
    print_info "You may need to manually restart the process"
else
    print_warning "R58 recorder is NOT running"
fi

# Final verification
echo ""
echo "Step 10: Running final verification..."
./verify_webrtc_deployment.sh

# Summary
echo ""
echo "==================================="
echo "Deployment Summary"
echo "==================================="
print_success "Deployment completed successfully!"
echo ""
echo "Current branch: $(git branch --show-current)"
echo "Current commit: $(git log --oneline -1)"
echo ""
echo "Next Steps:"
echo "1. Test WebRTC locally: http://recorder.itagenten.no/static/switcher.html"
echo "   (From a device on the SAME network as R58)"
echo "2. Check browser console for WebRTC messages"
echo "3. Verify latency is <200ms"
echo ""
echo "Rollback if needed:"
echo "  git checkout $BACKUP_BRANCH"
echo "  git reset --hard $BACKUP_COMMIT"
echo "  sudo systemctl restart r58-recorder"
echo ""
print_success "Deployment complete! 🚀"
