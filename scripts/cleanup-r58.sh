#!/bin/bash
# R58 System Cleanup Script
# Generated: December 29, 2025
# Purpose: Remove disabled services, backup files, and test files
#
# USAGE:
#   ./scripts/cleanup-r58.sh        - Run in dry-run mode (shows what would be deleted)
#   ./scripts/cleanup-r58.sh --run  - Actually perform the cleanup
#
# This script should be run on the R58 device as root or with sudo.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DRY_RUN=true
DELETED_COUNT=0
SPACE_FREED=0

if [[ "$1" == "--run" ]]; then
    DRY_RUN=false
    echo -e "${RED}=== RUNNING IN LIVE MODE ===${NC}"
    echo "Changes WILL be applied!"
    echo ""
    read -p "Are you sure you want to continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
else
    echo -e "${YELLOW}=== DRY RUN MODE ===${NC}"
    echo "This will show what would be deleted. Use --run to apply changes."
    echo ""
fi

# Function to delete a file/directory
delete_item() {
    local item="$1"
    local description="$2"
    
    if [[ -e "$item" ]]; then
        local size=$(du -sh "$item" 2>/dev/null | cut -f1)
        echo -e "  ${GREEN}[DELETE]${NC} $description"
        echo "           Path: $item"
        echo "           Size: $size"
        
        if [[ "$DRY_RUN" == false ]]; then
            rm -rf "$item"
        fi
        ((DELETED_COUNT++))
    else
        echo -e "  ${YELLOW}[SKIP]${NC} $description - not found"
    fi
}

# Function to delete a systemd service
delete_service() {
    local service="$1"
    local description="$2"
    local service_file="/etc/systemd/system/${service}"
    
    if [[ -e "$service_file" ]]; then
        echo -e "  ${GREEN}[DELETE]${NC} $description"
        echo "           Service: $service"
        
        if [[ "$DRY_RUN" == false ]]; then
            sudo systemctl stop "$service" 2>/dev/null || true
            sudo systemctl disable "$service" 2>/dev/null || true
            sudo rm -f "$service_file"
        fi
        ((DELETED_COUNT++))
    else
        echo -e "  ${YELLOW}[SKIP]${NC} $description - not installed"
    fi
}

echo "========================================="
echo "R58 System Cleanup"
echo "========================================="
echo ""

# 1. Remove disabled systemd services
echo "1. Removing disabled systemd services..."
echo ""

delete_service "cloudflared.service" "Cloudflare tunnel (replaced by FRP)"
delete_service "ninja-publish-cam0.service" "Ninja publisher for cam0 (unused)"
delete_service "ninja-receive-guest1.service" "Ninja guest receiver 1 (old approach)"
delete_service "ninja-receive-guest2.service" "Ninja guest receiver 2 (old approach)"
delete_service "ninja-rtmp-restream.service" "Ninja RTMP restream (test)"
delete_service "ninja-rtmp-test.service" "Ninja RTMP test (test)"
delete_service "ninja-rtsp-restream.service" "Ninja RTSP restream (test)"
delete_service "ninja-pipeline-test.service" "Ninja pipeline test (test)"
delete_service "r58-opencast-agent.service" "Opencast agent (unused)"

if [[ "$DRY_RUN" == false ]]; then
    echo ""
    echo "Reloading systemd daemon..."
    sudo systemctl daemon-reload
fi

echo ""

# 2. Remove backup files from preke-r58-recorder
echo "2. Removing backup files..."
echo ""

PREKE_DIR="/opt/preke-r58-recorder"
if [[ -d "$PREKE_DIR" ]]; then
    # Find and delete backup files
    for backup in $(find "$PREKE_DIR" -name "*.backup.*" -o -name "*.backup" 2>/dev/null); do
        delete_item "$backup" "Backup file"
    done
    
    # Delete src.backup directories
    for backup_dir in $(find "$PREKE_DIR" -type d -name "src.backup.*" 2>/dev/null); do
        delete_item "$backup_dir" "Backup directory"
    done
else
    echo -e "  ${YELLOW}[SKIP]${NC} $PREKE_DIR not found"
fi

echo ""

# 3. Remove test HTML files
echo "3. Removing test HTML files..."
echo ""

STATIC_DIR="/opt/preke-r58-recorder/src/static"
if [[ -d "$STATIC_DIR" ]]; then
    delete_item "$STATIC_DIR/camera_viewer.html" "Camera viewer test"
    delete_item "$STATIC_DIR/ninja_hls_viewer.html" "Ninja HLS viewer test"
    delete_item "$STATIC_DIR/ninja_join.html" "Ninja join test"
    delete_item "$STATIC_DIR/ninja_pipeline_test.html" "Ninja pipeline test"
    delete_item "$STATIC_DIR/ninja_view.html" "Ninja view test"
    delete_item "$STATIC_DIR/test_vdo_simple.html" "VDO simple test"
else
    echo -e "  ${YELLOW}[SKIP]${NC} $STATIC_DIR not found"
fi

echo ""

# 4. Clean up macOS metadata files
echo "4. Removing macOS metadata files..."
echo ""

if [[ -d "$PREKE_DIR" ]]; then
    for metadata in $(find "$PREKE_DIR" -name "._*" 2>/dev/null); do
        delete_item "$metadata" "macOS metadata file"
    done
    
    for dsstore in $(find "$PREKE_DIR" -name ".DS_Store" 2>/dev/null); do
        delete_item "$dsstore" ".DS_Store file"
    done
fi

echo ""

# 5. Clean up pip version marker files
echo "5. Removing pip version marker files..."
echo ""

for marker in $(find "$PREKE_DIR" -maxdepth 1 -name "=*" 2>/dev/null); do
    delete_item "$marker" "Pip version marker"
done

echo ""

# Summary
echo "========================================="
echo "Summary"
echo "========================================="
echo ""

if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}DRY RUN COMPLETE${NC}"
    echo "Would delete $DELETED_COUNT items"
    echo ""
    echo "To apply these changes, run:"
    echo "  $0 --run"
else
    echo -e "${GREEN}CLEANUP COMPLETE${NC}"
    echo "Deleted $DELETED_COUNT items"
fi

echo ""
echo "========================================="

