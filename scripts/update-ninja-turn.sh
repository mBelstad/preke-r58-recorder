#!/bin/bash

# Update raspberry.ninja Publishers with TURN Configuration
# Fetches TURN credentials from Coolify API and updates systemd services

set -e

echo "=== Updating Raspberry.Ninja Publishers with TURN ==="
echo ""

# Configuration
COOLIFY_TURN_API="https://api.r58.itagenten.no/turn-credentials"
LOCAL_VDO_SERVER="wss://localhost:8443"
ROOM_NAME="r58studio"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Step 1: Fetch TURN credentials
echo "Step 1: Fetching TURN credentials from Coolify API..."

TURN_DATA=$(curl -s "$COOLIFY_TURN_API")

if [ $? -ne 0 ] || [ -z "$TURN_DATA" ]; then
    echo "✗ Failed to fetch TURN credentials from $COOLIFY_TURN_API"
    echo "  Make sure the Coolify TURN API is accessible"
    exit 1
fi

# Parse TURN credentials
# Expected format: {"iceServers":{"urls":[...],"username":"...","credential":"..."}}
USERNAME=$(echo "$TURN_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['iceServers']['username'])" 2>/dev/null)
CREDENTIAL=$(echo "$TURN_DATA" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['iceServers']['credential'])" 2>/dev/null)

if [ -z "$USERNAME" ] || [ -z "$CREDENTIAL" ]; then
    echo "✗ Failed to parse TURN credentials"
    echo "  Response: $TURN_DATA"
    exit 1
fi

echo "✓ TURN credentials obtained"
echo "  Username: ${USERNAME:0:20}..."
echo "  Credential: ${CREDENTIAL:0:20}..."

# Construct TURN server URL
TURN_SERVER="turns://${USERNAME}:${CREDENTIAL}@turn.cloudflare.com:5349"
STUN_SERVER="stun://stun.cloudflare.com:3478"

# Step 2: Update publisher services
echo ""
echo "Step 2: Updating publisher services..."

for CAM in 1 2 3; do
    SERVICE_FILE="/etc/systemd/system/ninja-publish-cam${CAM}.service"
    
    if [ ! -f "$SERVICE_FILE" ]; then
        echo "  Skipping cam${CAM} (service not found)"
        continue
    fi
    
    echo "  Updating ninja-publish-cam${CAM}.service..."
    
    # Backup original
    cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update ExecStart line
    # Remove old TURN/STUN parameters if they exist
    sed -i '/ExecStart=/s/--turn-server "[^"]*"//g' "$SERVICE_FILE"
    sed -i '/ExecStart=/s/--stun-server "[^"]*"//g' "$SERVICE_FILE"
    sed -i '/ExecStart=/s/--server wss:\/\/[^ ]*//g' "$SERVICE_FILE"
    sed -i '/ExecStart=/s/--room [^ ]*//g' "$SERVICE_FILE"
    
    # Add new parameters
    sed -i "/ExecStart=/ s|publish.py|publish.py --server $LOCAL_VDO_SERVER --room $ROOM_NAME --turn-server \"$TURN_SERVER\" --stun-server \"$STUN_SERVER\"|" "$SERVICE_FILE"
    
    echo "  ✓ Updated cam${CAM}"
done

# Step 3: Reload systemd
echo ""
echo "Step 3: Reloading systemd..."
systemctl daemon-reload

# Step 4: Restart services
echo ""
echo "Step 4: Restarting publisher services..."

for CAM in 1 2 3; do
    SERVICE_NAME="ninja-publish-cam${CAM}.service"
    
    if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
        echo "  Restarting $SERVICE_NAME..."
        systemctl restart "$SERVICE_NAME"
        
        sleep 2
        
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            echo "  ✓ $SERVICE_NAME is running"
        else
            echo "  ✗ $SERVICE_NAME failed to start"
            systemctl status "$SERVICE_NAME" --no-pager -l | head -20
        fi
    fi
done

echo ""
echo "=== Update Complete ==="
echo ""
echo "Configuration:"
echo "  VDO.ninja Server: $LOCAL_VDO_SERVER"
echo "  Room: $ROOM_NAME"
echo "  TURN Server: turns://[user]:[pass]@turn.cloudflare.com:5349"
echo "  STUN Server: $STUN_SERVER"
echo ""
echo "To verify:"
echo "  - Check service status: systemctl status ninja-publish-cam1"
echo "  - Check logs: journalctl -u ninja-publish-cam1 -f"
echo "  - Open VDO.ninja director: https://localhost:8443/?director=$ROOM_NAME"
echo ""
echo "Note: TURN credentials expire in 24 hours"
echo "Set up a cron job to run this script every 12 hours:"
echo "  0 */12 * * * /opt/preke-r58-recorder/scripts/update-ninja-turn.sh"
echo ""

