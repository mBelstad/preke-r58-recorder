#!/bin/bash

# R58 Let's Encrypt SSL Setup Script
# Configures trusted SSL certificates for VDO.ninja

set -e

echo "=== R58 Let's Encrypt SSL Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Get domain parameter
DOMAIN="$1"

if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 <domain>"
    echo ""
    echo "Example: $0 r58-studio.duckdns.org"
    echo ""
    echo "Prerequisites:"
    echo "  1. Domain must be configured and pointing to this server"
    echo "  2. Port 80 must be accessible from the internet (for verification)"
    echo "  3. Port forwarding must be configured on router"
    echo ""
    exit 1
fi

echo "Configuration:"
echo "  Domain: $DOMAIN"
echo ""

# Step 1: Install certbot
echo "Step 1: Installing certbot..."
apt-get update
apt-get install -y certbot

# Step 2: Stop services that might use port 80
echo "Step 2: Temporarily stopping services..."
systemctl stop vdo-ninja 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true
systemctl stop apache2 2>/dev/null || true

# Step 3: Obtain certificate
echo "Step 3: Obtaining Let's Encrypt certificate..."
echo "  This will use port 80 for verification"
echo "  Make sure port 80 is forwarded to this server!"
echo ""

certbot certonly --standalone \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email \
    -d "$DOMAIN"

if [ $? -eq 0 ]; then
    echo "✓ Certificate obtained successfully"
else
    echo "✗ Certificate request failed"
    echo ""
    echo "Common issues:"
    echo "  - Domain not pointing to this server"
    echo "  - Port 80 not accessible from internet"
    echo "  - Firewall blocking port 80"
    echo ""
    exit 1
fi

# Step 4: Update VDO.ninja server configuration
echo "Step 4: Updating VDO.ninja server configuration..."

VDO_SERVER="/opt/vdo-signaling/vdo-server.js"

if [ ! -f "$VDO_SERVER" ]; then
    echo "Warning: VDO.ninja server not found at $VDO_SERVER"
    echo "You'll need to manually update the SSL certificate paths"
else
    # Backup original
    cp "$VDO_SERVER" "$VDO_SERVER.backup.$(date +%Y%m%d)"
    
    # Update certificate paths
    sed -i "s|key: fs.readFileSync.*|key: fs.readFileSync('/etc/letsencrypt/live/$DOMAIN/privkey.pem'),|" "$VDO_SERVER"
    sed -i "s|cert: fs.readFileSync.*|cert: fs.readFileSync('/etc/letsencrypt/live/$DOMAIN/fullchain.pem')|" "$VDO_SERVER"
    
    echo "✓ VDO.ninja server configuration updated"
fi

# Step 5: Set up auto-renewal
echo "Step 5: Setting up automatic renewal..."

# Create renewal hook to restart VDO.ninja
mkdir -p /etc/letsencrypt/renewal-hooks/deploy

cat > /etc/letsencrypt/renewal-hooks/deploy/restart-vdo-ninja.sh <<'EOF'
#!/bin/bash
# Restart VDO.ninja after certificate renewal
systemctl restart vdo-ninja
EOF

chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-vdo-ninja.sh

# Test renewal (dry run)
echo "  Testing renewal process..."
certbot renew --dry-run

if [ $? -eq 0 ]; then
    echo "✓ Auto-renewal configured successfully"
else
    echo "✗ Auto-renewal test failed"
fi

# Step 6: Restart VDO.ninja
echo "Step 6: Restarting VDO.ninja..."
systemctl start vdo-ninja

if systemctl is-active --quiet vdo-ninja; then
    echo "✓ VDO.ninja is running"
else
    echo "✗ VDO.ninja failed to start"
    systemctl status vdo-ninja --no-pager -l
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "SSL Certificate Details:"
echo "  Domain: $DOMAIN"
echo "  Certificate: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
echo "  Private Key: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
echo "  Auto-renewal: Enabled (certbot timer)"
echo ""
echo "To verify:"
echo "  1. Open: https://$DOMAIN:8443"
echo "  2. Check for trusted certificate (no browser warning)"
echo ""
echo "Certificate will auto-renew every 60 days"
echo "Check renewal status: certbot renew --dry-run"
echo ""

