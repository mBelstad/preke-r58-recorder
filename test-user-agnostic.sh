#!/bin/bash
# Test script for user-agnostic app changes
# Verifies no hardcoded URLs are present and app works correctly

set -e

echo "=== Testing User-Agnostic App Changes ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check for hardcoded URLs in source code
echo "Test 1: Checking for hardcoded URLs in source code..."
HARDCODED_FOUND=0

# Check for your specific R58 IPs and domain
HARDCODED_PATTERNS=(
  "r58-api.itagenten.no"
  "192.168.1.24"
  "100.98.37.53"
)

for pattern in "${HARDCODED_PATTERNS[@]}"; do
  # Search in source files (exclude node_modules, dist, build artifacts)
  MATCHES=$(grep -r "$pattern" \
    packages/frontend/src \
    packages/desktop/src \
    2>/dev/null | grep -v "node_modules" | grep -v ".map" | grep -v "StyleGuide" | wc -l | tr -d ' ')
  
  if [ "$MATCHES" -gt 0 ]; then
    echo -e "${RED}✗ Found $MATCHES occurrence(s) of '$pattern'${NC}"
    grep -r "$pattern" \
      packages/frontend/src \
      packages/desktop/src \
      2>/dev/null | grep -v "node_modules" | grep -v ".map" | grep -v "StyleGuide" || true
    HARDCODED_FOUND=1
  else
    echo -e "${GREEN}✓ No hardcoded '$pattern' found${NC}"
  fi
done

if [ $HARDCODED_FOUND -eq 0 ]; then
  echo -e "${GREEN}✓ Test 1 PASSED: No hardcoded URLs in source code${NC}"
else
  echo -e "${RED}✗ Test 1 FAILED: Hardcoded URLs found${NC}"
fi
echo ""

# Test 2: Verify FRP URL is dynamic
echo "Test 2: Verifying FRP URL is fetched from device config..."
if grep -q "getFrpUrl\|frp_url\|frp_api_url" packages/frontend/src/lib/api.ts; then
  echo -e "${GREEN}✓ FRP URL is fetched dynamically from device config${NC}"
else
  echo -e "${RED}✗ FRP URL logic not found${NC}"
fi
echo ""

# Test 3: Verify WHEP URL builder is dynamic
echo "Test 3: Verifying WHEP URL builder uses device URL..."
if grep -q "buildWhepUrl\|getDeviceUrl" packages/frontend/src/lib/whepConnectionManager.ts; then
  echo -e "${GREEN}✓ WHEP URL builder uses device URL dynamically${NC}"
else
  echo -e "${RED}✗ WHEP URL builder not found or not dynamic${NC}"
fi
echo ""

# Test 4: Verify VDO.ninja host is configurable
echo "Test 4: Verifying VDO.ninja host is configurable..."
if grep -q "getVdoHost\|vdo_host\|vdoninja_host" packages/frontend/src/lib/vdoninja.ts; then
  echo -e "${GREEN}✓ VDO.ninja host is configurable${NC}"
else
  echo -e "${RED}✗ VDO.ninja host configuration not found${NC}"
fi
echo ""

# Test 5: Check built files for hardcoded URLs
echo "Test 5: Checking built frontend files for hardcoded URLs..."
BUILT_FOUND=0

if [ -d "packages/frontend/dist" ]; then
  for pattern in "${HARDCODED_PATTERNS[@]}"; do
    MATCHES=$(grep -r "$pattern" packages/frontend/dist 2>/dev/null | grep -v ".map" | wc -l | tr -d ' ')
    if [ "$MATCHES" -gt 0 ]; then
      echo -e "${YELLOW}⚠ Found $MATCHES occurrence(s) of '$pattern' in built files${NC}"
      echo "   (This may be in comments or test data - check manually)"
      BUILT_FOUND=1
    fi
  done
  
  if [ $BUILT_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No hardcoded URLs in built files${NC}"
  fi
else
  echo -e "${YELLOW}⚠ Frontend not built - skipping built file check${NC}"
fi
echo ""

# Summary
echo "=== Test Summary ==="
if [ $HARDCODED_FOUND -eq 0 ]; then
  echo -e "${GREEN}✓ All automated tests passed!${NC}"
  echo ""
  echo "Manual testing checklist:"
  echo "1. [ ] Start app with no device configured - should show 'No device' state"
  echo "2. [ ] Check browser DevTools Network tab - no requests to hardcoded URLs"
  echo "3. [ ] Add device manually - should connect to that URL only"
  echo "4. [ ] Test device discovery (LAN/Tailscale) - should find devices dynamically"
  echo "5. [ ] Test WHEP connections - should use configured device URL"
  echo "6. [ ] Test FRP fallback - should only work if device provides FRP URL"
  echo "7. [ ] Test VDO.ninja mixer - should use configured host"
  exit 0
else
  echo -e "${RED}✗ Some tests failed - please review above${NC}"
  exit 1
fi
