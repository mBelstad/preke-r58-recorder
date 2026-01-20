#!/bin/bash
# Tailscale Setup Script for Remote Server Access
# This script installs and configures Tailscale on a remote server

set -e

# Configuration
SERVER_IP="${SERVER_IP:-192.168.1.77}"
SSH_USER="${SSH_USER:-Cursor}"
SSH_PASSWORD="${SSH_PASSWORD:-vibe1914}"

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

# Check if sshpass is installed (needed for password-based SSH)
check_sshpass() {
    if ! command -v sshpass &> /dev/null; then
        log_warn "sshpass not found. Installing..."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &> /dev/null; then
                brew install hudochenkov/sshpass/sshpass
            else
                log_error "Please install Homebrew first: https://brew.sh"
                log_error "Or install sshpass manually"
                exit 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo apt-get update && sudo apt-get install -y sshpass || \
            sudo yum install -y sshpass || \
            log_error "Please install sshpass manually"
        fi
    fi
}

# Detect OS on remote server
detect_remote_os() {
    log_info "Detecting remote server OS..."
    OS_INFO=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "cat /etc/os-release 2>/dev/null || echo 'ID=unknown'")
    
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

# Install Tailscale on remote server
install_tailscale() {
    local os_type=$1
    log_info "Installing Tailscale on remote server (OS: $os_type)..."
    
    case $os_type in
        debian)
            sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" << 'ENDSSH'
                # Add Tailscale repository
                curl -fsSL https://tailscale.com/install.sh | sh
                
                # Enable and start Tailscale service
                sudo systemctl enable --now tailscaled
ENDSSH
            ;;
        rhel)
            sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" << 'ENDSSH'
                # Add Tailscale repository
                curl -fsSL https://tailscale.com/install.sh | sh
                
                # Enable and start Tailscale service
                sudo systemctl enable --now tailscaled
ENDSSH
            ;;
        arch)
            sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" << 'ENDSSH'
                # Install from AUR or use official method
                curl -fsSL https://tailscale.com/install.sh | sh
                sudo systemctl enable --now tailscaled
ENDSSH
            ;;
        *)
            log_error "Unknown OS type. Please install Tailscale manually."
            log_info "Visit: https://tailscale.com/download/linux"
            return 1
            ;;
    esac
    
    log_info "Tailscale installed successfully"
}

# Check if Tailscale is already authenticated
check_tailscale_status() {
    log_info "Checking Tailscale status..."
    STATUS=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "sudo tailscale status 2>&1" || echo "not_authenticated")
    
    if echo "$STATUS" | grep -q "Logged in"; then
        log_info "Tailscale is already authenticated!"
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "sudo tailscale status"
        return 0
    else
        return 1
    fi
}

# Authenticate Tailscale
authenticate_tailscale() {
    log_info "Starting Tailscale authentication..."
    log_warn "You need to authenticate this device with your Tailscale account."
    log_info "A URL will be displayed - open it in your browser to authenticate."
    
    # Start Tailscale with authentication URL
    AUTH_URL=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "sudo tailscale up 2>&1" | grep -oP 'https://[^\s]+' | head -1 || echo "")
    
    if [ -n "$AUTH_URL" ]; then
        log_info "Authentication URL: $AUTH_URL"
        log_info "Opening URL in browser..."
        
        # Try to open URL in default browser
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open "$AUTH_URL"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open "$AUTH_URL" 2>/dev/null || echo "Please open this URL manually: $AUTH_URL"
        else
            echo "Please open this URL in your browser: $AUTH_URL"
        fi
        
        log_info "Waiting for authentication..."
        log_warn "After authenticating in the browser, press Enter to continue..."
        read -r
        
        # Check status again
        if check_tailscale_status; then
            log_info "Authentication successful!"
        else
            log_warn "Authentication may still be in progress. Checking again..."
            sleep 5
            check_tailscale_status || log_error "Authentication failed. Please run 'sudo tailscale up' manually on the server."
        fi
    else
        log_warn "Could not get authentication URL automatically."
        log_info "Please run the following command manually on the server:"
        echo "  ssh $SSH_USER@$SERVER_IP"
        echo "  sudo tailscale up"
        log_info "Then copy the authentication URL and open it in your browser."
    fi
}

# Get Tailscale IP address
get_tailscale_ip() {
    log_info "Getting Tailscale IP address..."
    TAILSCALE_IP=$(sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "sudo tailscale ip -4 2>/dev/null" || echo "")
    
    if [ -n "$TAILSCALE_IP" ]; then
        log_info "Tailscale IP: $TAILSCALE_IP"
        echo "$TAILSCALE_IP"
    else
        log_warn "Could not get Tailscale IP. The device may not be fully connected yet."
        return 1
    fi
}

# Configure Tailscale as subnet router (optional, for accessing local network)
configure_subnet_router() {
    log_info "Do you want to configure this server as a subnet router?"
    log_info "This allows you to access other devices on the 192.168.1.0/24 network via Tailscale."
    read -p "Configure as subnet router? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Configuring as subnet router..."
        sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" << 'ENDSSH'
            # Enable IP forwarding
            echo 'net.ipv4.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
            echo 'net.ipv6.ip_forward = 1' | sudo tee -a /etc/sysctl.conf
            sudo sysctl -p
            
            # Advertise routes
            sudo tailscale up --advertise-routes=192.168.1.0/24 --accept-routes
ENDSSH
        
        log_warn "You need to approve the subnet routes in your Tailscale admin console:"
        log_info "1. Go to https://login.tailscale.com/admin/machines"
        log_info "2. Find this device"
        log_info "3. Click '...' -> 'Edit route settings'"
        log_info "4. Enable the 192.168.1.0/24 route"
    fi
}

# Main setup function
main() {
    log_info "=========================================="
    log_info "Tailscale Setup for Remote Server"
    log_info "Server: $SSH_USER@$SERVER_IP"
    log_info "=========================================="
    
    # Check prerequisites
    check_sshpass
    
    # Test SSH connection
    log_info "Testing SSH connection..."
    if ! sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$SSH_USER@$SERVER_IP" "echo 'Connection successful'" &>/dev/null; then
        log_error "Cannot connect to server. Please check:"
        log_error "  - Server IP: $SERVER_IP"
        log_error "  - SSH user: $SSH_USER"
        log_error "  - Password: (check if correct)"
        log_error "  - Server is online and SSH is running"
        exit 1
    fi
    log_info "SSH connection successful!"
    
    # Detect OS
    OS_TYPE=$(detect_remote_os)
    log_info "Detected OS type: $OS_TYPE"
    
    # Check if Tailscale is already installed
    if sshpass -p "$SSH_PASSWORD" ssh -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "command -v tailscale &>/dev/null"; then
        log_info "Tailscale is already installed"
    else
        # Install Tailscale
        install_tailscale "$OS_TYPE"
    fi
    
    # Check authentication status
    if ! check_tailscale_status; then
        # Authenticate
        authenticate_tailscale
    fi
    
    # Get Tailscale IP
    TAILSCALE_IP=$(get_tailscale_ip || echo "")
    
    # Optional: Configure as subnet router
    configure_subnet_router
    
    # Summary
    log_info ""
    log_info "=========================================="
    log_info "Setup Complete!"
    log_info "=========================================="
    if [ -n "$TAILSCALE_IP" ]; then
        log_info "Tailscale IP: $TAILSCALE_IP"
        log_info "You can now access the server via:"
        log_info "  ssh $SSH_USER@$TAILSCALE_IP"
    fi
    log_info ""
    log_info "To check status: ssh $SSH_USER@$SERVER_IP 'sudo tailscale status'"
    log_info "To view IP: ssh $SSH_USER@$SERVER_IP 'sudo tailscale ip'"
    log_info ""
}

# Run main function
main "$@"
