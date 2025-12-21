#!/bin/bash
# Deploy Cloudflare TURN integration to R58 via Cloudflare Tunnel

set -e

R58_HOST="r58.itagenten.no"
R58_USER="linaro"
R58_PASSWORD="${R58_PASSWORD:-linaro}"
REMOTE_DIR="/opt/preke-r58-recorder"

echo "🚀 Deploying Cloudflare TURN integration to R58 via Cloudflare Tunnel..."

# Check if sshpass is available
if ! command -v sshpass >/dev/null 2>&1; then
    echo "❌ Error: sshpass required for password auth."
    echo "Install: brew install sshpass"
    exit 1
fi

SSH_CMD=(sshpass -p "${R58_PASSWORD}" ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no)
SCP_CMD=(sshpass -p "${R58_PASSWORD}" scp -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no)

echo "✅ Connecting to R58..."

# Copy updated guest_join.html
echo "📤 Uploading updated guest_join.html..."
"${SCP_CMD[@]}" src/static/guest_join.html ${R58_USER}@${R58_HOST}:${REMOTE_DIR}/src/static/guest_join.html

# Copy updated service file
echo "📤 Uploading updated service file..."
"${SCP_CMD[@]}" preke-recorder.service ${R58_USER}@${R58_HOST}:/tmp/preke-recorder.service

# Move service file and restart
echo "🔄 Installing service file and restarting..."
"${SSH_CMD[@]}" ${R58_USER}@${R58_HOST} << 'EOF'
    sudo mv /tmp/preke-recorder.service /etc/systemd/system/preke-recorder.service
    sudo systemctl daemon-reload
    sudo systemctl restart preke-recorder
    sleep 3
    sudo systemctl status preke-recorder --no-pager
EOF

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🧪 Testing TURN credentials API..."
sleep 2
curl -s https://recorder.itagenten.no/api/turn-credentials | jq '.' || echo "⚠️  API not responding yet, give it a moment..."

echo ""
echo "📋 Next steps:"
echo "1. Test remote guest connection: https://recorder.itagenten.no/guest_join"
echo "2. Open browser console to see TURN credentials being fetched"
echo "3. Check connection state reaches 'connected'"
echo "4. Verify guest appears in switcher: https://recorder.itagenten.no/switcher"
echo ""
echo "🔍 To check logs:"
echo "   ./connect-r58.sh"
echo "   sudo journalctl -u preke-recorder -f"

