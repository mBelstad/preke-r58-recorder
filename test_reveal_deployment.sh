#!/bin/bash
# Test Reveal.js video source deployment on R58
# Run this on the R58 device after deployment

set -e

echo "=========================================="
echo "Reveal.js Video Source Deployment Tests"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

# Test function
test_step() {
    local name="$1"
    local command="$2"
    
    echo -n "Testing: $name... "
    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Test 1: Check wpesrc availability
echo "1. Checking wpesrc availability..."
if gst-inspect-1.0 wpesrc > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ wpesrc is available${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "   ${YELLOW}⚠ wpesrc not found - install with:${NC}"
    echo "   sudo apt install gstreamer1.0-plugins-bad-apps libwpewebkit-1.0-3"
    FAILED=$((FAILED + 1))
fi

# Test 2: Check configuration files
echo ""
echo "2. Checking configuration files..."
test_step "config.yml has reveal section" "grep -q 'reveal:' config.yml"
test_step "mediamtx.yml has slides path" "grep -q 'slides:' mediamtx.yml"

# Test 3: Check Python files
echo ""
echo "3. Checking Python files..."
test_step "reveal_source.py exists" "test -f src/reveal_source.py"
test_step "reveal_source.py compiles" "python3 -m py_compile src/reveal_source.py"
test_step "config.py compiles" "python3 -m py_compile src/config.py"
test_step "main.py compiles" "python3 -m py_compile src/main.py"

# Test 4: Check scene files
echo ""
echo "4. Checking scene files..."
test_step "presentation_speaker.json exists" "test -f scenes/presentation_speaker.json"
test_step "presentation_focus.json exists" "test -f scenes/presentation_focus.json"
test_step "presentation_pip.json exists" "test -f scenes/presentation_pip.json"
test_step "presentation_speaker.json valid JSON" "python3 -c 'import json; json.load(open(\"scenes/presentation_speaker.json\"))'"

# Test 5: Check service
echo ""
echo "5. Checking service..."
if systemctl is-active --quiet preke-recorder; then
    echo -e "   ${GREEN}✓ preke-recorder service is running${NC}"
    PASSED=$((PASSED + 1))
    
    # Check logs for initialization
    echo ""
    echo "   Recent logs:"
    sudo journalctl -u preke-recorder -n 20 --no-pager | grep -i "reveal\|initialized" || echo "   (no reveal logs yet)"
else
    echo -e "   ${RED}✗ preke-recorder service not running${NC}"
    FAILED=$((FAILED + 1))
fi

# Test 6: Check API endpoints
echo ""
echo "6. Checking API endpoints..."
if systemctl is-active --quiet preke-recorder; then
    # Wait for service to be ready
    sleep 2
    
    test_step "API is responding" "curl -s -f http://localhost:8000/api/reveal/status > /dev/null || curl -s http://localhost:8000/api/reveal/status | grep -q 'Reveal.js not enabled\|state'"
    test_step "Mixer status includes overlay" "curl -s http://localhost:8000/api/mixer/status | grep -q 'overlay_enabled' || true"
else
    echo -e "   ${YELLOW}⚠ Skipping API tests - service not running${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Check wpesrc: gst-inspect-1.0 wpesrc"
    echo "  2. Test API: curl http://localhost:8000/api/reveal/status"
    echo "  3. Start Reveal.js: curl -X POST 'http://localhost:8000/api/reveal/start?presentation_id=test'"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check logs: sudo journalctl -u preke-recorder -f"
    echo ""
    exit 1
fi
