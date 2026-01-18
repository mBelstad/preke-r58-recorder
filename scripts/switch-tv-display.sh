#!/bin/bash
# Switch TV Display URL
# Uses Chrome DevTools Protocol to navigate the kiosk to a different page
# 
# Usage: switch-tv-display.sh <path>
#   Examples:
#     switch-tv-display.sh /qr              # Show QR page
#     switch-tv-display.sh /podcast         # Show podcast display
#     switch-tv-display.sh /talking-head    # Show talking head display
#     switch-tv-display.sh /course          # Show course display
#     switch-tv-display.sh /webinar         # Show webinar display
#     switch-tv-display.sh /customer/TOKEN  # Show customer session

set -e

TARGET_PATH="${1:-/qr}"
BASE_URL="http://localhost:8000/#"
FULL_URL="${BASE_URL}${TARGET_PATH}"

# Chrome DevTools Protocol endpoint (from kiosk Chromium)
CDP_PORT=9223  # Different port from VDO.ninja bridge (9222)

echo "Switching TV display to: $TARGET_PATH"

# Check if CDP is available
if ! curl -s "http://127.0.0.1:${CDP_PORT}/json" >/dev/null 2>&1; then
    echo "Error: TV kiosk not running or CDP not available on port $CDP_PORT"
    exit 1
fi

# Get the page target
PAGE_ID=$(curl -s "http://127.0.0.1:${CDP_PORT}/json" | python3 -c "
import sys, json
pages = json.load(sys.stdin)
for p in pages:
    if p.get('type') == 'page':
        print(p['id'])
        break
")

if [ -z "$PAGE_ID" ]; then
    echo "Error: No page found in kiosk"
    exit 1
fi

# Navigate to new URL using CDP
echo "Navigating to: $FULL_URL"
curl -s "http://127.0.0.1:${CDP_PORT}/json/version" >/dev/null

# Use websocket to send navigation command
python3 << EOF
import asyncio
import websockets
import json

async def navigate():
    # Get WebSocket URL for the page
    import urllib.request
    targets = json.loads(urllib.request.urlopen('http://127.0.0.1:${CDP_PORT}/json').read())
    ws_url = None
    for t in targets:
        if t.get('type') == 'page':
            ws_url = t.get('webSocketDebuggerUrl')
            break
    
    if not ws_url:
        print("Error: No WebSocket URL found")
        return
    
    async with websockets.connect(ws_url) as ws:
        # Send navigation command
        await ws.send(json.dumps({
            "id": 1,
            "method": "Page.navigate",
            "params": {"url": "$FULL_URL"}
        }))
        response = await ws.recv()
        result = json.loads(response)
        if result.get('id') == 1:
            print("Navigation successful")
        else:
            print(f"Navigation result: {result}")

asyncio.run(navigate())
EOF

echo "Done"
