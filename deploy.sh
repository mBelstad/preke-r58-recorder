#!/bin/bash
# Deployment script for R58 recorder via FRP tunnel
# Usage: ./deploy.sh
# 
# ACCESS: R58 via FRP tunnel on Coolify VPS
# Setup SSH keys: ./ssh-setup.sh

set -e

# Configuration - R58 accessible via FRP tunnel on Coolify VPS
R58_VPS="65.109.32.111"
R58_PORT="10022"
R58_USER="linaro"
R58_PASSWORD="${R58_PASSWORD:-linaro}"
REMOTE_DIR="/home/linaro/preke-r58-recorder"
SERVICE_NAME="preke-recorder.service"

echo "======================================"
echo "Deploying to R58 via FRP Tunnel"
echo "======================================"
echo "VPS: ${R58_VPS}:${R58_PORT}"
echo "User: ${R58_USER}"
echo ""

# Check for sshpass
if ! command -v sshpass >/dev/null 2>&1; then
    echo "Error: sshpass required for password auth."
    echo "Install: brew install sshpass"
    exit 1
fi

# Set up SSH command
SSH_CMD=(sshpass -p "${R58_PASSWORD}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=30 -p ${R58_PORT})

# Push to git (if in a git repo)
if [ -d ".git" ]; then
    echo "Pushing to git..."
    git add .
    git commit -m "Deploy: $(date +%Y%m%d_%H%M%S)" || true
    git push || echo "Warning: Git push failed or not configured"
fi

# Deploy to R58
echo "Connecting to R58..."

"${SSH_CMD[@]}" "${R58_USER}@${R58_VPS}" << EOF
    set -e
    
    # Create directory if it doesn't exist
    mkdir -p ${REMOTE_DIR}
    cd ${REMOTE_DIR}
    
    # Pull or clone
    if [ -d ".git" ]; then
        echo "Pulling latest changes..."
        git pull
    else
        echo "Warning: Not a git repository. Please clone manually first."
        exit 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate venv and install dependencies
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create recordings directory
    echo "Creating recordings directory..."
    mkdir -p /var/recordings/{cam0,cam1,cam2,cam3}
    chmod 755 /var/recordings
    
    # Install systemd service if not already installed
    if [ ! -f "/etc/systemd/system/${SERVICE_NAME}" ]; then
        echo "Installing systemd service..."
        cp ${REMOTE_DIR}/preke-recorder.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable ${SERVICE_NAME}
    fi
    
    # Restart service
    echo "Restarting service..."
    systemctl restart ${SERVICE_NAME}
    
    # Show status
    echo "Service status:"
    systemctl status ${SERVICE_NAME} --no-pager -l
    
    echo "Deployment complete!"
EOF

echo "Deployment finished successfully!"

