#!/bin/bash

# R58 Dynamic DNS Setup Script
# Configures DuckDNS for public access to R58

set -e

echo "=== R58 Dynamic DNS Setup (DuckDNS) ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

# Get parameters
DUCKDNS_DOMAIN="$1"
DUCKDNS_TOKEN="$2"

if [ -z "$DUCKDNS_DOMAIN" ] || [ -z "$DUCKDNS_TOKEN" ]; then
    echo "Usage: $0 <domain> <token>"
    echo ""
    echo "Example: $0 r58-studio abc123def456"
    echo ""
    echo "To get your DuckDNS domain and token:"
    echo "  1. Go to https://www.duckdns.org"
    echo "  2. Sign in (free account)"
    echo "  3. Create a subdomain (e.g., 'r58-studio')"
    echo "  4. Copy your token from the top of the page"
    echo ""
    exit 1
fi

echo "Configuration:"
echo "  Domain: $DUCKDNS_DOMAIN.duckdns.org"
echo "  Token: ${DUCKDNS_TOKEN:0:10}..."
echo ""

# Step 1: Create update script
echo "Step 1: Creating DuckDNS update script..."

mkdir -p /usr/local/bin

cat > /usr/local/bin/duckdns-update.sh <<EOF
#!/bin/bash
# DuckDNS Update Script
# Updates DuckDNS with current public IP

DOMAIN="$DUCKDNS_DOMAIN"
TOKEN="$DUCKDNS_TOKEN"
LOG_FILE="/var/log/duckdns.log"

# Update DuckDNS
echo "\$(date): Updating DuckDNS..." >> "\$LOG_FILE"
RESPONSE=\$(curl -s "https://www.duckdns.org/update?domains=\$DOMAIN&token=\$TOKEN&ip=")
echo "\$(date): Response: \$RESPONSE" >> "\$LOG_FILE"

if [ "\$RESPONSE" = "OK" ]; then
    echo "\$(date): ✓ DuckDNS update successful" >> "\$LOG_FILE"
else
    echo "\$(date): ✗ DuckDNS update failed" >> "\$LOG_FILE"
fi
EOF

chmod +x /usr/local/bin/duckdns-update.sh

# Step 2: Run initial update
echo "Step 2: Running initial update..."
/usr/local/bin/duckdns-update.sh

# Check if it worked
sleep 2
if tail -1 /var/log/duckdns.log | grep -q "successful"; then
    echo "✓ Initial update successful"
else
    echo "✗ Initial update failed. Check /var/log/duckdns.log"
    tail -5 /var/log/duckdns.log
fi

# Step 3: Set up cron job
echo "Step 3: Setting up cron job (updates every 5 minutes)..."

cat > /etc/cron.d/duckdns <<EOF
# DuckDNS Update Cron Job
# Updates every 5 minutes
*/5 * * * * root /usr/local/bin/duckdns-update.sh
EOF

chmod 644 /etc/cron.d/duckdns

# Restart cron to pick up new job
systemctl restart cron

echo ""
echo "=== Setup Complete ==="
echo ""
echo "DuckDNS Configuration:"
echo "  Domain: $DUCKDNS_DOMAIN.duckdns.org"
echo "  Update Interval: Every 5 minutes"
echo "  Log File: /var/log/duckdns.log"
echo ""
echo "To verify:"
echo "  1. Wait 1-2 minutes for DNS propagation"
echo "  2. Check: dig $DUCKDNS_DOMAIN.duckdns.org"
echo "  3. Check logs: tail -f /var/log/duckdns.log"
echo ""
echo "Next steps:"
echo "  1. Configure port forwarding on your router:"
echo "     - Port 443 → R58:8443 (VDO.ninja HTTPS/WSS)"
echo "     - Port 8000 → R58:8000 (API, optional)"
echo "  2. Set up Let's Encrypt SSL certificates"
echo ""

