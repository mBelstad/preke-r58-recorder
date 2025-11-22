#!/bin/bash
# Quick R58 test script
# Usage: ./test_r58.sh [r58_host]

R58_HOST="${1:-r58.local}"
BASE_URL="http://${R58_HOST}:8000"

echo "=== Testing R58 Recorder ==="
echo "Host: $R58_HOST"
echo "Base URL: $BASE_URL"
echo ""

echo "1. Health check..."
curl -s $BASE_URL/health | python3 -m json.tool
echo ""

echo "2. Initial status..."
curl -s $BASE_URL/status | python3 -m json.tool
echo ""

echo "3. Starting cam0..."
curl -s -X POST $BASE_URL/record/start/cam0 | python3 -m json.tool
echo ""

echo "4. Waiting 10 seconds..."
sleep 10
echo ""

echo "5. Status during recording..."
curl -s $BASE_URL/status/cam0 | python3 -m json.tool
echo ""

echo "6. Checking recording file on R58..."
ssh root@${R58_HOST} "ls -lh /var/recordings/cam0/ 2>/dev/null || echo 'No files yet'"
echo ""

echo "7. Stopping cam0..."
curl -s -X POST $BASE_URL/record/stop/cam0 | python3 -m json.tool
echo ""

echo "8. Final file check..."
ssh root@${R58_HOST} "ls -lh /var/recordings/cam0/"
echo ""

echo "9. Final status..."
curl -s $BASE_URL/status | python3 -m json.tool
echo ""

echo "=== Test Complete ==="

