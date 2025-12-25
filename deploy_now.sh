#!/bin/bash
# One-command deployment to R58
# Cleans blocking files and deploys Cairo + MSE

set -e

echo "======================================"
echo "R58 Deployment - Cairo + MSE"
echo "======================================"
echo ""

# Deploy via SSH
sshpass -p "linaro" ssh -o StrictHostKeyChecking=no linaro@r58.itagenten.no << 'ENDSSH'
set -e

cd /opt/preke-r58-recorder

echo "1. Cleaning blocking files..."
sudo rm -f SIGNAL_DETECTION_VERIFICATION.md SYSTEM_LOAD_ANALYSIS_DEC19.md

echo "2. Resetting git state..."
sudo git reset --hard HEAD

echo "3. Pulling latest code..."
sudo git pull origin feature/webrtc-switcher-preview

echo "4. Fixing permissions..."
sudo chown -R linaro:linaro .

echo "5. Installing pycairo..."
sudo pip3 install --upgrade pycairo 2>&1 | tail -5

echo "6. Restarting service..."
sudo systemctl restart preke-recorder

echo "7. Waiting for service to start..."
sleep 8

echo "8. Checking service status..."
sudo systemctl status preke-recorder --no-pager -l | head -40

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Test Cairo graphics:"
echo "  curl http://localhost:8000/api/cairo/status"
echo ""
echo "Test MSE streaming:"
echo "  curl http://localhost:8000/mse/cam0"
echo ""
echo "Web UIs:"
echo "  https://recorder.itagenten.no/cairo"
echo "  https://recorder.itagenten.no/mse_test"
echo ""

ENDSSH

echo ""
echo "✓ Deployment script completed"
echo ""
echo "Next steps:"
echo "  1. Run tests: ssh linaro@r58.itagenten.no 'cd /opt/preke-r58-recorder && ./test_cairo_graphics.sh'"
echo "  2. Open web UI: open https://recorder.itagenten.no/cairo"
echo "  3. Test graphics: Create a lower third and click Show"
echo ""


