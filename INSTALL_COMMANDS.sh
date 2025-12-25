#!/bin/bash
# Final installation commands for Cairo graphics
# Run these on the R58 after SSH'ing in

set -e

echo "======================================"
echo "Cairo Graphics - Final Installation"
echo "======================================"
echo ""

# 1. Install pycairo
echo "Step 1: Installing pycairo..."
sudo pip3 install --upgrade pycairo --break-system-packages

echo ""
echo "Step 2: Restarting service..."
sudo systemctl restart preke-recorder

echo ""
echo "Step 3: Waiting for service to start..."
sleep 8

echo ""
echo "Step 4: Checking service status..."
sudo systemctl status preke-recorder --no-pager -l | head -40

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""

# Verify Cairo
echo "Verifying Cairo installation..."
python3 -c "import cairo; print('✓ Cairo version:', cairo.version)" || echo "✗ Cairo import failed"

echo ""
echo "Testing Cairo API..."
curl -s http://localhost:8000/api/cairo/status | python3 -m json.tool || echo "✗ API test failed"

echo ""
echo "======================================"
echo "Next Steps"
echo "======================================"
echo ""
echo "1. Run automated tests:"
echo "   ./test_cairo_graphics.sh"
echo ""
echo "2. Test web UI:"
echo "   https://recorder.itagenten.no/cairo"
echo ""
echo "3. Create your first lower third:"
echo "   curl -X POST http://localhost:8000/api/cairo/lower_third \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"element_id\":\"test1\",\"name\":\"John Doe\",\"title\":\"CEO\"}'"
echo ""
echo "4. Show it:"
echo "   curl -X POST http://localhost:8000/api/cairo/lower_third/test1/show"
echo ""

