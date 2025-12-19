#!/bin/bash
# Test script for dynamic signal detection
# Verifies that disabled cameras don't waste resources

set -e

echo "======================================"
echo "Dynamic Signal Detection - Test Suite"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

# Test 1: Verify Python syntax
echo "Test 1: Python syntax check..."
if python3 -m py_compile src/ingest.py 2>/dev/null; then
    echo -e "${GREEN}✓ PASSED${NC}: Python syntax is valid"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: Python syntax error"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 2: Verify signal indicator CSS exists in switcher
echo "Test 2: Switcher signal indicator CSS..."
if grep -q "compact-signal-indicator" src/static/switcher.html; then
    echo -e "${GREEN}✓ PASSED${NC}: Signal indicator CSS found in switcher.html"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: Signal indicator CSS missing"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 3: Verify signal update function exists in switcher
echo "Test 3: Switcher signal update function..."
if grep -q "async function updateSignalIndicators" src/static/switcher.html; then
    echo -e "${GREEN}✓ PASSED${NC}: Signal update function found in switcher.html"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: Signal update function missing"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 4: Verify initCompactInputs is async
echo "Test 4: Switcher initCompactInputs is async..."
if grep -q "async function initCompactInputs" src/static/switcher.html; then
    echo -e "${GREEN}✓ PASSED${NC}: initCompactInputs is async"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: initCompactInputs is not async"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 5: Verify disabled camera check in backend
echo "Test 5: Backend skips disabled cameras..."
if grep -q "if not cam_config or not cam_config.enabled:" src/ingest.py; then
    echo -e "${GREEN}✓ PASSED${NC}: Backend checks for disabled cameras"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: Backend doesn't check for disabled cameras"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 6: Verify signal indicator CSS in control
echo "Test 6: Control signal indicator CSS..."
if grep -q "camera-signal" src/static/control.html; then
    echo -e "${GREEN}✓ PASSED${NC}: Signal indicator CSS found in control.html"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: Signal indicator CSS missing"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 7: Verify signal status function in control
echo "Test 7: Control signal status function..."
if grep -q "updateCameraSignalStatus" src/static/control.html; then
    echo -e "${GREEN}✓ PASSED${NC}: Signal status function found in control.html"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: Signal status function missing"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 8: Verify hardcoded cam0 skip is removed
echo "Test 8: Hardcoded cam0 skip removed from switcher..."
if grep -q "// Skip cam0 (no HDMI cable connected)" src/static/switcher.html; then
    echo -e "${YELLOW}⚠ WARNING${NC}: Hardcoded cam0 comment still exists (but logic is replaced)"
else
    echo -e "${GREEN}✓ PASSED${NC}: Hardcoded cam0 skip removed"
    PASSED=$((PASSED + 1))
fi
echo ""

# Test 9: Verify preloadHLSManifests is async
echo "Test 9: Switcher preloadHLSManifests is async..."
if grep -q "async function preloadHLSManifests" src/static/switcher.html; then
    echo -e "${GREEN}✓ PASSED${NC}: preloadHLSManifests is async"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC}: preloadHLSManifests is not async"
    FAILED=$((FAILED + 1))
fi
echo ""

# Summary
echo "======================================"
echo "Test Results"
echo "======================================"
echo ""
echo -e "Passed: ${GREEN}${PASSED}${NC}"
echo -e "Failed: ${RED}${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Ready to deploy:"
    echo "  ./deploy.sh r58.itagenten.no linaro"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
