#!/bin/bash
# Test script for Cairo graphics implementation
# Tests API endpoints and functionality

set -e

API_BASE="${API_BASE:-http://localhost:8000}"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================"
echo "Cairo Graphics Test Suite"
echo "======================================"
echo "API Base: $API_BASE"
echo ""

PASSED=0
FAILED=0

test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"
    
    echo -n "Testing: $name... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$API_BASE$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
        echo "  Response: $body"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Test 1: Check Cairo status
test_endpoint "Cairo status" "GET" "/api/cairo/status" ""

# Test 2: Create lower third
test_endpoint "Create lower third" "POST" "/api/cairo/lower_third" \
    '{"element_id":"test_lt","name":"Test User","title":"Test Title"}'

# Test 3: Show lower third
test_endpoint "Show lower third" "POST" "/api/cairo/lower_third/test_lt/show" ""

# Test 4: Update lower third
test_endpoint "Update lower third" "POST" "/api/cairo/lower_third/test_lt/update" \
    '{"name":"Updated Name","title":"Updated Title"}'

# Test 5: Hide lower third
test_endpoint "Hide lower third" "POST" "/api/cairo/lower_third/test_lt/hide" ""

# Test 6: Create scoreboard
test_endpoint "Create scoreboard" "POST" "/api/cairo/scoreboard" \
    '{"element_id":"test_sb","team1_name":"Home","team2_name":"Away","team1_score":0,"team2_score":0}'

# Test 7: Update scoreboard
test_endpoint "Update scoreboard" "POST" "/api/cairo/scoreboard/test_sb/score" \
    '{"team1_score":3,"team2_score":2}'

# Test 8: Create ticker
test_endpoint "Create ticker" "POST" "/api/cairo/ticker" \
    '{"element_id":"test_ticker","text":"Breaking News: Cairo graphics are working!"}'

# Test 9: Update ticker text
test_endpoint "Update ticker" "POST" "/api/cairo/ticker/test_ticker/text" \
    '{"text":"Updated ticker text"}'

# Test 10: Create timer
test_endpoint "Create timer" "POST" "/api/cairo/timer" \
    '{"element_id":"test_timer","duration":60,"mode":"countdown"}'

# Test 11: Start timer
test_endpoint "Start timer" "POST" "/api/cairo/timer/test_timer/start" ""

# Test 12: Pause timer
test_endpoint "Pause timer" "POST" "/api/cairo/timer/test_timer/pause" ""

# Test 13: Resume timer
test_endpoint "Resume timer" "POST" "/api/cairo/timer/test_timer/resume" ""

# Test 14: Reset timer
test_endpoint "Reset timer" "POST" "/api/cairo/timer/test_timer/reset" ""

# Test 15: List elements
test_endpoint "List elements" "GET" "/api/cairo/elements" ""

# Test 16: Delete element
test_endpoint "Delete element" "DELETE" "/api/cairo/element/test_lt" ""

# Test 17: Clear all
test_endpoint "Clear all elements" "POST" "/api/cairo/clear" ""

echo ""
echo "======================================"
echo "Test Results"
echo "======================================"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Open web UI: $API_BASE/cairo"
    echo "  2. Start mixer: curl -X POST $API_BASE/api/mixer/start"
    echo "  3. Create graphics and test live updates"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check that:"
    echo "  1. Service is running"
    echo "  2. Cairo is available (pycairo installed)"
    echo "  3. Mixer is initialized"
    exit 1
fi







