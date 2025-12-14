#!/bin/bash
# Deployment script for R58 recorder
# Usage: ./deploy.sh [r58_host] [r58_user]
# Optional: export R58_PASSWORD='your-password' to force sshpass-based auth
# 
# Remote access via Cloudflare Tunnel:
#   ./deploy.sh r58.itagenten.no linaro
#   Or use: ./connect-r58.sh

set -e

# Configuration
R58_HOST="${1:-r58.itagenten.no}"
R58_USER="${2:-linaro}"
R58_PASSWORD="${R58_PASSWORD:-linaro}"
REMOTE_DIR="/opt/preke-r58-recorder"
SERVICE_NAME="preke-recorder.service"

echo "Deploying to ${R58_USER}@${R58_HOST}..."

# Push to git (if in a git repo)
if [ -d ".git" ]; then
    echo "Pushing to git..."
    git add .
    git commit -m "Deploy: $(date +%Y%m%d_%H%M%S)" || true
    git push || echo "Warning: Git push failed or not configured"
fi

# Deploy to R58
echo "Connecting to ${R58_USER}@${R58_HOST}..."
SSH_CMD=(ssh)
if [ -n "${R58_PASSWORD}" ]; then
    if ! command -v sshpass >/dev/null 2>&1; then
        echo "Error: sshpass is required for password deployments. Install it or set up SSH keys."
        exit 1
    fi
    SSH_CMD=(sshpass -p "${R58_PASSWORD}" ssh -o StrictHostKeyChecking=no)
fi

"${SSH_CMD[@]}" "${R58_USER}@${R58_HOST}" << EOF
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

