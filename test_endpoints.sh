#!/bin/bash
# Comprehensive endpoint testing

echo "=== Testing R58 Endpoints ==="
echo ""

# Test 1: Check if remote mixer HTML loads
echo "1. Testing Remote Mixer HTML..."
curl -s https://app.itagenten.no/static/r58_remote_mixer.html | head -20
echo ""

# Test 2: Test WHEP endpoint with actual POST
echo "2. Testing WHEP endpoint (cam0)..."
curl -X POST https://app.itagenten.no/cam0/whep \
  -H "Content-Type: application/sdp" \
  -d "v=0" \
  -v 2>&1 | grep -E "HTTP|access-control|< "

echo ""
echo "=== Tests Complete ==="
