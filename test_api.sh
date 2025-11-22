#!/bin/bash
# Quick API test script

BASE_URL="${1:-http://localhost:8000}"

echo "=== Testing R58 Recorder API ==="
echo "Base URL: $BASE_URL"
echo ""

echo "1. Health check..."
curl -s $BASE_URL/health | python3 -m json.tool
echo ""

echo "2. Initial status..."
curl -s $BASE_URL/status | python3 -m json.tool
echo ""

echo "3. Starting recording for cam0..."
curl -s -X POST $BASE_URL/record/start/cam0 | python3 -m json.tool
echo ""

echo "4. Waiting 5 seconds..."
sleep 5
echo ""

echo "5. Status during recording..."
curl -s $BASE_URL/status/cam0 | python3 -m json.tool
echo ""

echo "6. Stopping recording for cam0..."
curl -s -X POST $BASE_URL/record/stop/cam0 | python3 -m json.tool
echo ""

echo "7. Final status..."
curl -s $BASE_URL/status | python3 -m json.tool
echo ""

echo "=== Test Complete ==="

