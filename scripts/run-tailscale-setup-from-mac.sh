#!/bin/bash
# Run Tailscale setup on server via R58 device
# This script connects to R58 and runs the Tailscale installation script on the server

set -e

# R58 connection details (using Tailscale if available, otherwise local)
R58_USER="linaro"
R58_TAILSCALE_IP="${R58_TAILSCALE_IP:-}"
R58_LOCAL_IP="${R58_LOCAL_IP:-192.168.1.25}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

# Determine R58 IP (prefer Tailscale if available)
determine_r58_ip() {
    if [ -n "$R58_TAILSCALE_IP" ]; then
        echo "$R58_TAILSCALE_IP"
        return
    fi
    
    # Try to get R58 Tailscale IP if connected
    if command -v tailscale &>/dev/null; then
        R58_TS_IP=$(tailscale status --json 2>/dev/null | grep -oP '"([^"]+)"\s*:\s*{\s*"[^"]*":\s*"[^"]*r58[^"]*"' | head -1 | cut -d'"' -f2 || echo "")
        if [ -n "$R58_TS_IP" ]; then
            echo "$R58_TS_IP"
            return
        fi
    fi
    
    # Fall back to local IP
    echo "$R58_LOCAL_IP"
}

# Upload and run the script on R58
main() {
    log_info "=========================================="
    log_info "Tailscale Setup via R58 Device"
    log_info "=========================================="
    log_info ""
    
    # Determine R58 IP
    R58_IP=$(determine_r58_ip)
    log_info "Connecting to R58 at: $R58_IP"
    log_info ""
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SETUP_SCRIPT="$SCRIPT_DIR/install-tailscale-on-server.sh"
    
    if [ ! -f "$SETUP_SCRIPT" ]; then
        log_warn "Setup script not found: $SETUP_SCRIPT"
        exit 1
    fi
    
    # Upload script to R58
    log_info "Uploading setup script to R58..."
    scp -o StrictHostKeyChecking=no "$SETUP_SCRIPT" "$R58_USER@$R58_IP:/tmp/install-tailscale-on-server.sh" || {
        log_warn "Failed to upload script. Trying with password authentication..."
        if command -v sshpass &>/dev/null; then
            sshpass -p "linaro" scp -o StrictHostKeyChecking=no "$SETUP_SCRIPT" "$R58_USER@$R58_IP:/tmp/install-tailscale-on-server.sh"
        else
            log_warn "Please upload the script manually or set up SSH keys"
            exit 1
        fi
    }
    
    # Make script executable and run it
    log_info "Running setup script on R58..."
    log_info ""
    
    ssh -o StrictHostKeyChecking=no "$R58_USER@$R58_IP" << 'ENDSSH'
        chmod +x /tmp/install-tailscale-on-server.sh
        /tmp/install-tailscale-on-server.sh
ENDSSH || {
    log_warn "SSH failed. Trying with password authentication..."
    if command -v sshpass &>/dev/null; then
        sshpass -p "linaro" ssh -o StrictHostKeyChecking=no "$R58_USER@$R58_IP" << 'ENDSSH'
            chmod +x /tmp/install-tailscale-on-server.sh
            /tmp/install-tailscale-on-server.sh
ENDSSH
    else
        log_warn "Please run the script manually on R58:"
        log_info "  ssh $R58_USER@$R58_IP"
        log_info "  /tmp/install-tailscale-on-server.sh"
    fi
    }
    
    log_info ""
    log_info "Setup complete!"
}

main "$@"
