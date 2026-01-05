#!/bin/bash
#
# R58 Automated Smoke Test Script
# Run this on the R58 device before each release
#
# Usage: ./scripts/smoke-test.sh [--verbose]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VERBOSE=${1:-""}
API_URL="http://localhost:8000"
PASSED=0
FAILED=0
WARNINGS=0

# Helper functions
log_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

log_info() {
    if [ "$VERBOSE" == "--verbose" ]; then
        echo "  → $1"
    fi
}

# Test functions
test_service_running() {
    local service=$1
    if systemctl is-active --quiet "$service" 2>/dev/null; then
        log_pass "Service $service is running"
        return 0
    else
        log_fail "Service $service is not running"
        return 1
    fi
}

test_api_endpoint() {
    local endpoint=$1
    local expected=$2
    local response

    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL$endpoint" 2>/dev/null)
    
    if [ "$response" == "$expected" ]; then
        log_pass "GET $endpoint returns $expected"
        return 0
    else
        log_fail "GET $endpoint returned $response (expected $expected)"
        return 1
    fi
}

test_api_json() {
    local endpoint=$1
    local jq_query=$2
    local expected=$3
    local response

    response=$(curl -s "$API_URL$endpoint" 2>/dev/null | jq -r "$jq_query" 2>/dev/null)
    
    if [ "$response" == "$expected" ]; then
        log_pass "GET $endpoint.$jq_query == $expected"
        return 0
    else
        log_fail "GET $endpoint.$jq_query == $response (expected $expected)"
        return 1
    fi
}

test_disk_space() {
    local min_gb=$1
    local available_kb
    local available_gb

    # Check /opt/r58/recordings first, fall back to root
    available_kb=$(df /opt/r58/recordings 2>/dev/null | tail -1 | awk '{print $4}' || df / | tail -1 | awk '{print $4}')
    available_gb=$((available_kb / 1024 / 1024))
    
    if [ "$available_gb" -ge "$min_gb" ]; then
        log_pass "Disk space: ${available_gb}GB available (minimum ${min_gb}GB)"
        return 0
    elif [ "$available_gb" -ge 2 ]; then
        log_warn "Disk space: ${available_gb}GB available (recommended ${min_gb}GB)"
        return 0
    else
        log_fail "Disk space: ${available_gb}GB available (need at least 2GB)"
        return 1
    fi
}

test_recording_cycle() {
    local session_id
    local status

    echo ""
    echo "Testing recording cycle..."
    
    # Start recording
    response=$(curl -s -X POST "$API_URL/api/v1/recorder/start" \
        -H "Content-Type: application/json" \
        -d '{"name": "smoke-test", "inputs": ["cam2"]}' 2>/dev/null)
    
    session_id=$(echo "$response" | jq -r '.session_id' 2>/dev/null)
    status=$(echo "$response" | jq -r '.status' 2>/dev/null)
    
    if [ "$status" == "recording" ]; then
        log_pass "Recording started (session: $session_id)"
    else
        log_fail "Failed to start recording: $response"
        return 1
    fi
    
    # Wait for recording
    sleep 5
    
    # Check status
    status=$(curl -s "$API_URL/api/v1/recorder/status" 2>/dev/null | jq -r '.status' 2>/dev/null)
    if [ "$status" == "recording" ]; then
        log_pass "Recording status confirmed"
    else
        log_fail "Recording status check failed: $status"
    fi
    
    # Stop recording
    response=$(curl -s -X POST "$API_URL/api/v1/recorder/stop" 2>/dev/null)
    status=$(echo "$response" | jq -r '.status' 2>/dev/null)
    
    if [ "$status" == "stopped" ]; then
        log_pass "Recording stopped successfully"
    else
        log_fail "Failed to stop recording: $response"
        return 1
    fi
    
    # Check file exists
    sleep 2
    if ls /opt/r58/recordings/*smoke-test* 1>/dev/null 2>&1; then
        log_pass "Recording file created"
        # Cleanup
        rm -f /opt/r58/recordings/*smoke-test* 2>/dev/null
    else
        log_warn "Recording file not found (may be named differently)"
    fi
    
    return 0
}

# Main test sequence
echo "========================================"
echo "R58 Smoke Test"
echo "========================================"
echo "Date: $(date)"
echo "Host: $(hostname)"
echo ""

# 1. Service Health
echo "=== 1. Service Health ==="
test_service_running "preke-recorder" || true
test_service_running "mediamtx" || true
test_service_running "vdo-ninja" || true
test_service_running "frpc" || true
echo ""

# 2. API Endpoints
echo "=== 2. API Endpoints ==="
test_api_endpoint "/api/v1/health" "200" || true
test_api_json "/api/v1/health" ".status" "healthy" || true
test_api_endpoint "/api/v1/health/detailed" "200" || true
test_api_endpoint "/api/v1/capabilities" "200" || true
test_api_endpoint "/api/v1/recorder/status" "200" || true
echo ""

# 3. Device Capabilities
echo "=== 3. Device Capabilities ==="
test_api_json "/api/v1/capabilities" ".recorder_available" "true" || true
test_api_json "/api/v1/capabilities" ".api_version" "2.0.0" || true
echo ""

# 4. Storage
echo "=== 4. Storage ==="
test_disk_space 5 || true
echo ""

# 5. Recording Cycle (Optional - requires cam2 connected)
echo "=== 5. Recording Cycle ==="
if [ "$VERBOSE" == "--verbose" ] || [ "$1" == "--with-recording" ]; then
    test_recording_cycle || true
else
    echo "  Skipped (use --with-recording to enable)"
fi
echo ""

# Summary
echo "========================================"
echo "SUMMARY"
echo "========================================"
echo -e "Passed:   ${GREEN}$PASSED${NC}"
echo -e "Failed:   ${RED}$FAILED${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review.${NC}"
    exit 1
fi

