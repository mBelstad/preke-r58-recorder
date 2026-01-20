#!/bin/bash
# Install Tailscale on server (192.168.1.77) from R58 device
# This script should be run on the R58 device to set up Tailscale on the server

set -e

# Server configuration
SERVER_IP="192.168.1.77"
SSH_USER="cursor"
SSH_PASSWORD="vibe1914"
SUDO_PASSWORD="${SUDO_PASSWORD:-vibe1914}"  # Assuming same password for sudo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Check if sshpass is installed on R58
check_sshpass() {
    if ! command -v sshpass &> /dev/null; then
        log_warn "sshpass not found. Installing..."
        sudo apt-get update && sudo apt-get install -y sshpass || {
            log_error "Failed to install sshpass. Please install manually:"
            log_error "  sudo apt-get update && sudo apt-get install -y sshpass"
            exit 1
        }
    fi
}

# Test SSH connection to server
test_connection() {
    log_info "Testing SSH connection to server..."
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" "echo 'Connection successful'" &>/dev/null; then
        log_info "SSH connection successful!"
        return 0
    else
        log_error "Cannot connect to server. Please check:"
        log_error "  - Server IP: $SERVER_IP"
        log_error "  - Server is online and SSH is running"
        log_error "  - Network connectivity from R58 to server"
        return 1
    fi
}

# Detect OS on server
detect_os() {
    log_info "Detecting server OS..."
    OS_INFO=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" "cat /etc/os-release 2>/dev/null || echo 'ID=unknown'")
    
    if echo "$OS_INFO" | grep -qi "ubuntu\|debian"; then
        echo "debian"
    elif echo "$OS_INFO" | grep -qi "fedora\|rhel\|centos"; then
        echo "rhel"
    elif echo "$OS_INFO" | grep -qi "arch"; then
        echo "arch"
    else
        echo "unknown"
    fi
}

# Install Tailscale on server
install_tailscale() {
    local os_type=$1
    log_info "Installing Tailscale on server (OS: $os_type)..."
    
    sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" bash -s << ENDSSH
        set -e
        
        # Check if Tailscale is already installed
        if command -v tailscale &>/dev/null; then
            echo "Tailscale is already installed"
            exit 0
        fi
        
        # Install Tailscale using official installer (with sudo password)
        echo "$SUDO_PASSWORD" | sudo -S bash -c "curl -fsSL https://tailscale.com/install.sh | sh"
        
        # Enable and start Tailscale service
        echo "$SUDO_PASSWORD" | sudo -S systemctl enable --now tailscaled
        
        echo "Tailscale installed successfully"
ENDSSH
    
    log_info "Tailscale installation complete"
}

# Check Tailscale status on server
check_tailscale_status() {
    log_info "Checking Tailscale status on server..."
    STATUS=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" "echo '$SUDO_PASSWORD' | sudo -S tailscale status 2>&1" || echo "not_authenticated")
    
    if echo "$STATUS" | grep -q "Logged in"; then
        log_info "Tailscale is already authenticated on server!"
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" "echo '$SUDO_PASSWORD' | sudo -S tailscale status"
        return 0
    else
        return 1
    fi
}

# Authenticate Tailscale on server
authenticate_tailscale() {
    log_info "Starting Tailscale authentication on server..."
    log_warn "You need to authenticate the server with your Tailscale account."
    
    # Get authentication URL
    AUTH_OUTPUT=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" "echo '$SUDO_PASSWORD' | sudo -S tailscale up 2>&1" || true)
    
    # Extract URL from output
    AUTH_URL=$(echo "$AUTH_OUTPUT" | grep -oP 'https://[^\s]+' | head -1 || echo "")
    
    if [ -n "$AUTH_URL" ]; then
        log_info ""
        log_info "=========================================="
        log_info "AUTHENTICATION REQUIRED"
        log_info "=========================================="
        log_info "Please open this URL in your browser:"
        log_info ""
        log_info "  $AUTH_URL"
        log_info ""
        log_info "Sign in with your Tailscale account to authenticate the server."
        log_info "After authenticating, press Enter to continue..."
        log_info ""
        read -r
        
        # Wait a moment for authentication to complete
        sleep 3
        
        # Check status again
        if check_tailscale_status; then
            log_info "Authentication successful!"
        else
            log_warn "Checking authentication status..."
            sleep 5
            if check_tailscale_status; then
                log_info "Authentication successful!"
            else
                log_error "Authentication may have failed. Please check manually:"
                log_info "  ssh $SSH_USER@$SERVER_IP"
                log_info "  sudo tailscale status"
            fi
        fi
    else
        log_warn "Could not get authentication URL automatically."
        log_info "Please run the following manually:"
        log_info "  ssh $SSH_USER@$SERVER_IP"
        log_info "  sudo tailscale up"
        log_info "Then copy the authentication URL and open it in your browser."
    fi
}

# Get Tailscale IP of server
get_tailscale_ip() {
    log_info "Getting Tailscale IP address of server..."
    TAILSCALE_IP=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" "echo '$SUDO_PASSWORD' | sudo -S tailscale ip -4 2>/dev/null" || echo "")
    
    if [ -n "$TAILSCALE_IP" ]; then
        log_info "Server Tailscale IP: $TAILSCALE_IP"
        echo "$TAILSCALE_IP"
    else
        log_warn "Could not get Tailscale IP. The server may not be fully connected yet."
        return 1
    fi
}

# Main function
main() {
    log_info "=========================================="
    log_info "Tailscale Setup on Server from R58"
    log_info "Server: $SSH_USER@$SERVER_IP"
    log_info "=========================================="
    log_info ""
    
    # Check prerequisites
    check_sshpass
    
    # Test connection
    if ! test_connection; then
        exit 1
    fi
    
    # Detect OS
    OS_TYPE=$(detect_os)
    log_info "Detected server OS: $OS_TYPE"
    log_info ""
    
    # Check if Tailscale is already installed
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no "$SSH_USER@$SERVER_IP" "command -v tailscale &>/dev/null"; then
        log_info "Tailscale is already installed on server"
    else
        # Install Tailscale
        install_tailscale "$OS_TYPE"
        log_info ""
    fi
    
    # Check authentication status
    if ! check_tailscale_status; then
        log_info ""
        # Authenticate
        authenticate_tailscale
        log_info ""
    fi
    
    # Get Tailscale IP
    TAILSCALE_IP=$(get_tailscale_ip || echo "")
    
    # Summary
    log_info ""
    log_info "=========================================="
    log_info "Setup Complete!"
    log_info "=========================================="
    if [ -n "$TAILSCALE_IP" ]; then
        log_info "Server Tailscale IP: $TAILSCALE_IP"
        log_info ""
        log_info "The server is now on your Tailscale network!"
        log_info "You can access it from your MacBook using:"
        log_info "  ssh $SSH_USER@$TAILSCALE_IP"
    fi
    log_info ""
    log_info "To check status: ssh $SSH_USER@$SERVER_IP 'sudo tailscale status'"
    log_info "To view IP: ssh $SSH_USER@$SERVER_IP 'sudo tailscale ip'"
    log_info ""
}

# Run main function
main "$@"
