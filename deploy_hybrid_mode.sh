#!/bin/bash
# Deploy Hybrid Mode implementation to R58

set -e

echo "🚀 Deploying Hybrid Mode to R58..."

# Deploy mode_manager.py
echo "📦 Deploying mode_manager.py..."
sshpass -p 'linaro' scp -o StrictHostKeyChecking=no src/mode_manager.py linaro@r58.itagenten.no:/opt/preke-r58-recorder/src/

# Deploy updated main.py
echo "📦 Deploying main.py..."
sshpass -p 'linaro' scp -o StrictHostKeyChecking=no src/main.py linaro@r58.itagenten.no:/opt/preke-r58-recorder/src/

# Deploy mode_control.html
echo "📦 Deploying mode_control.html..."
sshpass -p 'linaro' scp -o StrictHostKeyChecking=no src/static/mode_control.html linaro@r58.itagenten.no:/opt/preke-r58-recorder/src/static/

# Deploy updated config.yml
echo "📦 Deploying config.yml..."
sshpass -p 'linaro' scp -o StrictHostKeyChecking=no config.yml linaro@r58.itagenten.no:/opt/preke-r58-recorder/

# Restart preke-recorder service
echo "🔄 Restarting preke-recorder service..."
sshpass -p 'linaro' ssh -o StrictHostKeyChecking=no linaro@r58.itagenten.no 'sudo systemctl restart preke-recorder'

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 3

# Check service status
echo "✅ Checking service status..."
sshpass -p 'linaro' ssh -o StrictHostKeyChecking=no linaro@r58.itagenten.no 'systemctl is-active preke-recorder'

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access mode control at:"
echo "   Remote: https://r58-api.itagenten.no/static/mode_control.html"
echo "   Local:  http://192.168.1.24:8000/static/mode_control.html"
echo ""

