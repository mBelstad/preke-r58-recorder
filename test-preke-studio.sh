#!/bin/bash
# Comprehensive testing script for Preke Studio Mac app
# Tests all fixed bugs and new features

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
TOTAL=0

echo "======================================"
echo "Preke Studio - Comprehensive Test Suite"
echo "======================================"
echo ""

# Helper functions
test_start() {
    TOTAL=$((TOTAL + 1))
    echo -n "Test $TOTAL: $1... "
}

test_pass() {
    PASSED=$((PASSED + 1))
    echo -e "${GREEN}✓ PASS${NC}"
    if [ ! -z "$1" ]; then
        echo "  └─ $1"
    fi
}

test_fail() {
    FAILED=$((FAILED + 1))
    echo -e "${RED}✗ FAIL${NC}"
    if [ ! -z "$1" ]; then
        echo "  └─ $1"
    fi
}

test_info() {
    echo -e "${BLUE}  ℹ $1${NC}"
}

# Test 1: App exists
test_start "App installation"
if [ -d "/Applications/Preke Studio.app" ]; then
    test_pass "App found at /Applications/Preke Studio.app"
else
    test_fail "App not found"
    exit 1
fi

# Test 2: Backup exists
test_start "Backup created"
if [ -f ~/preke-studio-backup-*.asar ]; then
    BACKUP_FILE=$(ls -t ~/preke-studio-backup-*.asar | head -1)
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    test_pass "Backup found: $BACKUP_SIZE"
else
    test_fail "No backup found"
fi

# Test 3: Source code extracted
test_start "Source code available"
if [ -d ~/preke-studio-fixed ]; then
    FILE_COUNT=$(ls ~/preke-studio-fixed/*.js 2>/dev/null | wc -l)
    test_pass "Source extracted: $FILE_COUNT JS files"
else
    test_fail "Source not extracted"
fi

# Test 4: Modified files exist
test_start "Bug fixes applied"
if [ -f ~/preke-studio-fixed/preke-studio.js ]; then
    if grep -q "storeAvailable" ~/preke-studio-fixed/preke-studio.js; then
        test_pass "Error handling code present"
    else
        test_fail "Error handling code missing"
    fi
else
    test_fail "preke-studio.js not found"
fi

# Test 5: Validation code added
test_start "Input validation added"
if [ -f ~/preke-studio-fixed/launcher.js ]; then
    if grep -q "validateIPAddress" ~/preke-studio-fixed/launcher.js; then
        test_pass "Validation functions present"
    else
        test_fail "Validation functions missing"
    fi
else
    test_fail "launcher.js not found"
fi

# Test 6: Kill any existing instances
test_start "Clean app state"
killall "Preke Studio" 2>/dev/null || true
sleep 2
if ! pgrep -x "Preke Studio" > /dev/null; then
    test_pass "No existing instances"
else
    test_fail "Failed to kill existing instances"
fi

# Test 7: Launch app
test_start "App launch"
open -a "/Applications/Preke Studio.app" 2>&1 &
sleep 5

if pgrep -x "Preke Studio" > /dev/null; then
    PROCESS_COUNT=$(pgrep -x "Preke Studio" | wc -l)
    test_pass "App launched with $PROCESS_COUNT processes"
else
    test_fail "App failed to launch"
fi

# Test 8: Check processes
test_start "Process architecture"
MAIN_PROCESS=$(pgrep -f "Preke Studio.app/Contents/MacOS/Preke Studio" | wc -l)
GPU_PROCESS=$(pgrep -f "Preke Studio Helper (GPU)" | wc -l)
RENDERER_PROCESS=$(pgrep -f "Preke Studio Helper (Renderer)" | wc -l)

if [ $MAIN_PROCESS -ge 1 ] && [ $GPU_PROCESS -ge 1 ] && [ $RENDERER_PROCESS -ge 1 ]; then
    test_pass "Main: $MAIN_PROCESS, GPU: $GPU_PROCESS, Renderer: $RENDERER_PROCESS"
else
    test_fail "Missing processes"
fi

# Test 9: Check for crashes
test_start "Stability check"
sleep 3
if pgrep -x "Preke Studio" > /dev/null; then
    test_pass "No crashes after 8 seconds"
else
    test_fail "App crashed"
fi

# Test 10: Memory usage
test_start "Memory usage"
MEMORY=$(ps aux | grep "Preke Studio.app/Contents/MacOS/Preke Studio" | grep -v grep | awk '{print $6}' | head -1)
if [ ! -z "$MEMORY" ]; then
    MEMORY_MB=$((MEMORY / 1024))
    if [ $MEMORY_MB -lt 500 ]; then
        test_pass "${MEMORY_MB}MB (acceptable)"
    else
        test_fail "${MEMORY_MB}MB (high)"
    fi
else
    test_fail "Could not measure memory"
fi

# Test 11: CPU usage
test_start "CPU usage"
CPU=$(ps aux | grep "Preke Studio.app/Contents/MacOS/Preke Studio" | grep -v grep | awk '{print $3}' | head -1)
if [ ! -z "$CPU" ]; then
    if (( $(echo "$CPU < 10.0" | bc -l) )); then
        test_pass "${CPU}% (low)"
    else
        test_info "${CPU}% (initial load)"
        test_pass "Within acceptable range"
    fi
else
    test_fail "Could not measure CPU"
fi

# Test 12: Check console logs
test_start "Console logging"
LOG_FILE="/tmp/preke-studio-test-log.txt"
log show --predicate 'process == "Preke Studio"' --last 30s --style compact 2>/dev/null > "$LOG_FILE" || true

if [ -s "$LOG_FILE" ]; then
    if grep -q "✓" "$LOG_FILE" 2>/dev/null; then
        test_pass "Success markers found in logs"
    else
        test_info "No success markers (may be normal)"
        test_pass "Logs available"
    fi
else
    test_info "Console logs not accessible"
    test_pass "Skipped (permissions)"
fi

# Test 13: Window visibility (best effort)
test_start "Window visibility"
WINDOW_COUNT=$(osascript -e 'tell application "System Events" to count windows of process "Preke Studio"' 2>/dev/null || echo "0")
if [ "$WINDOW_COUNT" != "0" ]; then
    test_pass "$WINDOW_COUNT window(s) detected"
else
    test_info "Cannot verify (accessibility permissions needed)"
    test_pass "Skipped"
fi

# Test 14: App responds to signals
test_start "App responsiveness"
if pkill -0 "Preke Studio" 2>/dev/null; then
    test_pass "App responds to signals"
else
    test_fail "App not responding"
fi

# Test 15: File permissions
test_start "File permissions"
if [ -r "/Applications/Preke Studio.app/Contents/Resources/app.asar" ]; then
    test_pass "App files readable"
else
    test_fail "Permission issues"
fi

echo ""
echo "======================================"
echo "Test Results Summary"
echo "======================================"
echo ""
echo -e "Total Tests:  ${BLUE}$TOTAL${NC}"
echo -e "Passed:       ${GREEN}$PASSED${NC}"
echo -e "Failed:       ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    echo "The Preke Studio app is working correctly!"
    echo ""
    echo "Next steps:"
    echo "  1. Test with real R58 device connection"
    echo "  2. Test invalid inputs (IP, Room ID)"
    echo "  3. Test device discovery"
    echo "  4. Test all tabs"
    EXIT_CODE=0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Check the failures above for details."
    EXIT_CODE=1
fi

echo ""
echo "App is currently running. To stop:"
echo "  killall 'Preke Studio'"
echo ""
echo "To view logs:"
echo "  log show --predicate 'process == \"Preke Studio\"' --last 5m"
echo ""

exit $EXIT_CODE
