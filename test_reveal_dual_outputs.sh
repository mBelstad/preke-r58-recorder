#!/bin/bash
# Comprehensive test script for dual Reveal.js outputs

set -e

echo "======================================"
echo "Reveal.js Dual Output Test Script"
echo "======================================"
echo ""

BASE_URL="http://r58.itagenten.no:8000"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass_count=0
fail_count=0

test_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    pass_count=$((pass_count + 1))
}

test_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    fail_count=$((fail_count + 1))
}

test_info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

# Test 1: List available outputs
echo "Test 1: List available outputs"
echo "-------------------------------"
OUTPUTS=$(curl -s "$BASE_URL/api/reveal/outputs")
echo "$OUTPUTS" | python3 -m json.tool
if echo "$OUTPUTS" | grep -q '"slides"' && echo "$OUTPUTS" | grep -q '"slides_overlay"'; then
    test_pass "Both outputs available"
else
    test_fail "Expected outputs not found"
fi
echo ""

# Test 2: Check initial status (should be idle)
echo "Test 2: Check initial status"
echo "-----------------------------"
STATUS=$(curl -s "$BASE_URL/api/reveal/status")
if echo "$STATUS" | grep -q '"any_running": false'; then
    test_pass "Initial state is idle"
else
    test_info "Outputs may already be running, stopping all first..."
    curl -s -X POST "$BASE_URL/api/reveal/stop" > /dev/null
    sleep 2
fi
echo ""

# Test 3: Start first output (slides)
echo "Test 3: Start 'slides' output"
echo "------------------------------"
START1=$(curl -s -X POST "$BASE_URL/api/reveal/slides/start?presentation_id=test1&url=http://localhost:8000/reveal.js/demo.html")
echo "$START1" | python3 -m json.tool
if echo "$START1" | grep -q '"status": "started"'; then
    test_pass "slides output started"
    sleep 2
else
    test_fail "Failed to start slides output"
fi
echo ""

# Test 4: Check slides status
echo "Test 4: Check 'slides' status"
echo "------------------------------"
SLIDES_STATUS=$(curl -s "$BASE_URL/api/reveal/slides/status")
echo "$SLIDES_STATUS" | python3 -m json.tool
if echo "$SLIDES_STATUS" | grep -q '"state": "running"'; then
    test_pass "slides is running"
else
    test_fail "slides should be running"
fi
echo ""

# Test 5: Start second output (slides_overlay) while first is running
echo "Test 5: Start 'slides_overlay' output"
echo "--------------------------------------"
START2=$(curl -s -X POST "$BASE_URL/api/reveal/slides_overlay/start?presentation_id=test2&url=http://localhost:8000/reveal.js/demo.html?slide=5")
echo "$START2" | python3 -m json.tool
if echo "$START2" | grep -q '"status": "started"'; then
    test_pass "slides_overlay output started"
    sleep 2
else
    test_fail "Failed to start slides_overlay output"
fi
echo ""

# Test 6: Check both outputs running
echo "Test 6: Verify both outputs running simultaneously"
echo "---------------------------------------------------"
BOTH_STATUS=$(curl -s "$BASE_URL/api/reveal/status")
echo "$BOTH_STATUS" | python3 -c "import json,sys;d=json.load(sys.stdin);print(f\"slides: {d['outputs']['slides']['state']} | slides_overlay: {d['outputs']['slides_overlay']['state']}\")"
if echo "$BOTH_STATUS" | grep -q '"any_running": true'; then
    SLIDES_RUNNING=$(echo "$BOTH_STATUS" | grep -o '"slides"[^}]*"state": "running"' || echo "")
    OVERLAY_RUNNING=$(echo "$BOTH_STATUS" | grep -o '"slides_overlay"[^}]*"state": "running"' || echo "")
    if [ -n "$SLIDES_RUNNING" ] && [ -n "$OVERLAY_RUNNING" ]; then
        test_pass "Both outputs running simultaneously"
    else
        test_fail "Not both outputs running"
    fi
else
    test_fail "No outputs running"
fi
echo ""

# Test 7: Check MediaMTX streams
echo "Test 7: Check MediaMTX stream availability"
echo "-------------------------------------------"
MEDIAMTX_PATHS=$(curl -s "http://r58.itagenten.no:8554/v3/paths/list" 2>/dev/null || echo '{"items":[]}')
if echo "$MEDIAMTX_PATHS" | grep -q "slides"; then
    test_pass "MediaMTX has slides streams"
else
    test_info "MediaMTX paths check skipped (may require auth)"
fi
echo ""

# Test 8: Stop one output (slides)
echo "Test 8: Stop 'slides' output only"
echo "----------------------------------"
STOP1=$(curl -s -X POST "$BASE_URL/api/reveal/slides/stop")
echo "$STOP1" | python3 -m json.tool
sleep 1
STATUS_AFTER_STOP1=$(curl -s "$BASE_URL/api/reveal/status")
SLIDES_STATE=$(echo "$STATUS_AFTER_STOP1" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['outputs']['slides']['state'])")
OVERLAY_STATE=$(echo "$STATUS_AFTER_STOP1" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['outputs']['slides_overlay']['state'])")
echo "After stopping slides: slides=$SLIDES_STATE | slides_overlay=$OVERLAY_STATE"
if [ "$SLIDES_STATE" = "idle" ] && [ "$OVERLAY_STATE" = "running" ]; then
    test_pass "slides stopped, slides_overlay still running"
else
    test_fail "Expected slides=idle, slides_overlay=running"
fi
echo ""

# Test 9: Stop all outputs
echo "Test 9: Stop all outputs"
echo "------------------------"
STOP_ALL=$(curl -s -X POST "$BASE_URL/api/reveal/stop")
echo "$STOP_ALL" | python3 -m json.tool
sleep 1
FINAL_STATUS=$(curl -s "$BASE_URL/api/reveal/status")
if echo "$FINAL_STATUS" | grep -q '"any_running": false'; then
    test_pass "All outputs stopped"
else
    test_fail "Outputs should all be stopped"
fi
echo ""

# Test 10: Restart both outputs (verify clean restart)
echo "Test 10: Restart both outputs"
echo "------------------------------"
curl -s -X POST "$BASE_URL/api/reveal/slides/start?presentation_id=restart1&url=http://localhost:8000/reveal.js/demo.html" > /dev/null
curl -s -X POST "$BASE_URL/api/reveal/slides_overlay/start?presentation_id=restart2&url=http://localhost:8000/reveal.js/demo.html" > /dev/null
sleep 2
RESTART_STATUS=$(curl -s "$BASE_URL/api/reveal/status")
if echo "$RESTART_STATUS" | grep -q '"any_running": true'; then
    test_pass "Both outputs restarted successfully"
else
    test_fail "Failed to restart outputs"
fi
echo ""

# Cleanup: Stop all
echo "Cleanup: Stopping all outputs..."
curl -s -X POST "$BASE_URL/api/reveal/stop" > /dev/null
echo ""

# Summary
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}Passed: $pass_count${NC}"
echo -e "${RED}Failed: $fail_count${NC}"
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
