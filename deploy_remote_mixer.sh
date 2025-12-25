#!/bin/bash
# Deploy R58 Remote Mixer to R58 device

set -e

echo "🚀 Deploying R58 Remote Mixer..."
echo ""

# Check if cloudflared is available
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared not found. Please install it first:"
    echo "   brew install cloudflare/cloudflare/cloudflared"
    exit 1
fi

# Deploy r58_remote_mixer.html
echo "📦 Deploying r58_remote_mixer.html..."
scp -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" \
    src/static/r58_remote_mixer.html \
    linaro@r58.itagenten.no:/opt/preke-r58-recorder/src/static/

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access the Remote Mixer at:"
echo "   Remote: https://r58-api.itagenten.no/static/r58_remote_mixer.html"
echo "   Local:  http://192.168.1.24:8000/static/r58_remote_mixer.html"
echo ""
echo "📋 Features:"
echo "   • Quick launch VDO.ninja mixer with all cameras pre-loaded"
echo "   • Built-in camera grid with auto-connection"
echo "   • Program output with click-to-select cameras"
echo "   • All cameras mapped to slots automatically"
echo ""

