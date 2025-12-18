#!/bin/bash
# WebRTC Deployment Verification Script
# Run this on the R58 device after deployment

echo "=== WebRTC Deployment Verification ==="
echo ""

# Check current branch
echo "1. Checking Git Branch:"
git branch --show-current
echo ""

# Check latest commit
echo "2. Latest Commit:"
git log --oneline -1
echo "   Expected: 8068d77 Add WebRTC support to switcher for ultra-low latency previews"
echo ""

# Check if WebRTC code exists in switcher.html
echo "3. Checking WebRTC Code in switcher.html:"
if grep -q "function getWebRTCUrl" src/static/switcher.html; then
    echo "   ✅ getWebRTCUrl() function found"
else
    echo "   ❌ getWebRTCUrl() function NOT found"
fi

if grep -q "function startWebRTCPreview" src/static/switcher.html; then
    echo "   ✅ startWebRTCPreview() function found"
else
    echo "   ❌ startWebRTCPreview() function NOT found"
fi

if grep -q "let webrtcConnections" src/static/switcher.html; then
    echo "   ✅ webrtcConnections storage found"
else
    echo "   ❌ webrtcConnections storage NOT found"
fi
echo ""

# Check MediaMTX status
echo "4. Checking MediaMTX:"
if systemctl is-active --quiet mediamtx 2>/dev/null; then
    echo "   ✅ MediaMTX service is running"
elif ps aux | grep -v grep | grep -q mediamtx; then
    echo "   ✅ MediaMTX process is running"
else
    echo "   ❌ MediaMTX is NOT running"
fi
echo ""

# Check WebRTC port
echo "5. Checking WebRTC Port (8889):"
if lsof -i :8889 2>/dev/null | grep -q LISTEN; then
    echo "   ✅ Port 8889 is listening"
    lsof -i :8889 | grep LISTEN
else
    echo "   ❌ Port 8889 is NOT listening"
fi
echo ""

# Check HLS port
echo "6. Checking HLS Port (8888):"
if lsof -i :8888 2>/dev/null | grep -q LISTEN; then
    echo "   ✅ Port 8888 is listening"
else
    echo "   ❌ Port 8888 is NOT listening"
fi
echo ""

# Check R58 service
echo "7. Checking R58 Recorder Service:"
if systemctl is-active --quiet r58-recorder 2>/dev/null; then
    echo "   ✅ r58-recorder service is running"
    systemctl status r58-recorder --no-pager | head -5
elif ps aux | grep -v grep | grep -q "python.*main.py"; then
    echo "   ✅ R58 recorder process is running"
else
    echo "   ❌ R58 recorder is NOT running"
fi
echo ""

# Test WebRTC endpoint
echo "8. Testing WebRTC Endpoint:"
response=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8889/cam1/whep -H "Content-Type: application/sdp" -d "test" 2>/dev/null)
if [ "$response" = "400" ]; then
    echo "   ✅ WebRTC endpoint responding (400 = bad SDP, expected)"
elif [ "$response" = "404" ]; then
    echo "   ❌ WebRTC endpoint not found (404)"
else
    echo "   ⚠️  WebRTC endpoint returned: $response"
fi
echo ""

# Check camera status
echo "9. Checking Camera Status:"
curl -s http://localhost:8000/status 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for cam, info in data.get('cameras', {}).items():
        status = info.get('status', 'unknown')
        icon = '✅' if status in ['preview', 'recording'] else '⚠️' if status == 'idle' else '❌'
        print(f'   {icon} {cam}: {status}')
except:
    print('   ❌ Could not fetch camera status')
"
echo ""

echo "=== Deployment Verification Complete ==="
echo ""
echo "Next Steps:"
echo "1. If WebRTC code is NOT found, run: git checkout feature/webrtc-switcher-preview"
echo "2. If service is not running, run: sudo systemctl restart r58-recorder"
echo "3. Test in browser: http://recorder.itagenten.no/static/switcher.html"
echo "   - Local access should use WebRTC"
echo "   - Remote access should use HLS"
