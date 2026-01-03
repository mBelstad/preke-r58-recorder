#!/bin/bash
# Configure MediaMTX to include Tailscale/LAN IPs in WebRTC ICE candidates
# This enables P2P discovery even when signaling goes through FRP

set -e

echo "=== Configuring MediaMTX for ICE P2P Discovery ==="

# Get Tailscale IP
TAILSCALE_IP=""
if command -v tailscale &> /dev/null; then
    TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "")
fi

if [ -z "$TAILSCALE_IP" ]; then
    echo "Warning: Tailscale IP not found. P2P through Tailscale won't work."
    echo "Make sure Tailscale is installed and running."
fi

# Get LAN IP (eth0 or wlan0)
LAN_IP=""
for iface in eth0 wlan0 enp1s0; do
    IP=$(ip -4 addr show $iface 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1)
    if [ -n "$IP" ]; then
        LAN_IP=$IP
        break
    fi
done

echo "Detected IPs:"
echo "  Tailscale: ${TAILSCALE_IP:-not found}"
echo "  LAN: ${LAN_IP:-not found}"

# Build the additionalHosts list
ADDITIONAL_HOSTS=""
if [ -n "$TAILSCALE_IP" ]; then
    ADDITIONAL_HOSTS="$TAILSCALE_IP"
fi
if [ -n "$LAN_IP" ]; then
    if [ -n "$ADDITIONAL_HOSTS" ]; then
        ADDITIONAL_HOSTS="$ADDITIONAL_HOSTS,$LAN_IP"
    else
        ADDITIONAL_HOSTS="$LAN_IP"
    fi
fi

if [ -z "$ADDITIONAL_HOSTS" ]; then
    echo "Error: No IPs found to configure. Aborting."
    exit 1
fi

echo "Configuring MediaMTX with additionalHosts: $ADDITIONAL_HOSTS"

# MediaMTX config file location
MEDIAMTX_CONFIG="/opt/mediamtx/mediamtx.yml"
MEDIAMTX_CONFIG_BACKUP="/opt/mediamtx/mediamtx.yml.backup"

if [ ! -f "$MEDIAMTX_CONFIG" ]; then
    echo "Error: MediaMTX config not found at $MEDIAMTX_CONFIG"
    exit 1
fi

# Backup original config
cp "$MEDIAMTX_CONFIG" "$MEDIAMTX_CONFIG_BACKUP"
echo "Backed up config to $MEDIAMTX_CONFIG_BACKUP"

# Check if additionalHosts is already configured
if grep -q "additionalHosts:" "$MEDIAMTX_CONFIG"; then
    # Update existing additionalHosts
    # This is a simple replacement - for complex configs, use yq or python
    sed -i "s/additionalHosts:.*/additionalHosts: [$ADDITIONAL_HOSTS]/" "$MEDIAMTX_CONFIG"
    echo "Updated existing additionalHosts configuration"
else
    # Add additionalHosts under webrtc section
    # Find the webrtc: line and add additionalHosts after it
    sed -i '/^webrtc:/a\  additionalHosts: ['"$ADDITIONAL_HOSTS"']' "$MEDIAMTX_CONFIG"
    echo "Added additionalHosts to webrtc section"
fi

# Verify the change
echo ""
echo "Current webrtc configuration:"
grep -A5 "^webrtc:" "$MEDIAMTX_CONFIG" | head -10

# Restart MediaMTX service
echo ""
echo "Restarting MediaMTX service..."
if systemctl is-active --quiet mediamtx; then
    sudo systemctl restart mediamtx
    sleep 2
    if systemctl is-active --quiet mediamtx; then
        echo "✓ MediaMTX restarted successfully"
    else
        echo "✗ MediaMTX failed to restart. Check logs with: journalctl -u mediamtx -n 50"
        exit 1
    fi
else
    echo "Warning: MediaMTX service not running. Start it with: sudo systemctl start mediamtx"
fi

echo ""
echo "=== Configuration Complete ==="
echo ""
echo "ICE candidates will now include:"
[ -n "$TAILSCALE_IP" ] && echo "  - Tailscale: $TAILSCALE_IP (P2P for remote access)"
[ -n "$LAN_IP" ] && echo "  - LAN: $LAN_IP (P2P for local network)"
echo ""
echo "WebRTC connections will automatically use the fastest path."
echo "Verify P2P by checking the 'P2P' badge in the Recorder view."

