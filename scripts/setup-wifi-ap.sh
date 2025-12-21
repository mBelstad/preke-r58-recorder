#!/bin/bash

# R58 WiFi Access Point Setup Script
# Configures the R58's WiFi as a hotspot for local network access

set -e

echo "=== R58 WiFi Access Point Setup ==="
echo ""

# Configuration
SSID="R58-Studio"
PASSWORD="r58studio2025"
WIFI_INTERFACE="wlan0"
WIFI_IP="10.58.0.1"
DHCP_RANGE_START="10.58.0.100"
DHCP_RANGE_END="10.58.0.200"
DOMAIN="r58.local"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

echo "Configuration:"
echo "  SSID: $SSID"
echo "  Password: $PASSWORD"
echo "  IP Address: $WIFI_IP"
echo "  DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
echo "  Domain: $DOMAIN"
echo ""

# Step 1: Install required packages
echo "Step 1: Installing required packages..."
apt-get update
apt-get install -y hostapd dnsmasq

# Stop services while we configure
systemctl stop hostapd dnsmasq 2>/dev/null || true

# Step 2: Configure hostapd
echo "Step 2: Configuring hostapd..."
cat > /etc/hostapd/hostapd.conf <<EOF
# Interface configuration
interface=$WIFI_INTERFACE
driver=nl80211

# Network configuration
ssid=$SSID
hw_mode=a
channel=36
ieee80211n=1
ieee80211ac=1
wmm_enabled=1

# Security configuration
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_passphrase=$PASSWORD
rsn_pairwise=CCMP

# Access control
macaddr_acl=0
ignore_broadcast_ssid=0
EOF

# Point hostapd to config file
sed -i 's|^#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd || \
    echo 'DAEMON_CONF="/etc/hostapd/hostapd.conf"' >> /etc/default/hostapd

# Step 3: Configure dnsmasq
echo "Step 3: Configuring dnsmasq..."

# Backup original config
if [ -f /etc/dnsmasq.conf ] && [ ! -f /etc/dnsmasq.conf.backup ]; then
    cp /etc/dnsmasq.conf /etc/dnsmasq.conf.backup
fi

cat > /etc/dnsmasq.d/r58-ap.conf <<EOF
# Interface to listen on
interface=$WIFI_INTERFACE
bind-interfaces

# DHCP configuration
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,255.255.255.0,24h
dhcp-option=option:router,$WIFI_IP
dhcp-option=option:dns-server,$WIFI_IP

# Domain configuration
domain=$DOMAIN
address=/$DOMAIN/$WIFI_IP

# Logging (optional, comment out for production)
log-queries
log-dhcp
EOF

# Step 4: Configure static IP for wlan0
echo "Step 4: Configuring static IP..."

# Create network interfaces config
cat > /etc/network/interfaces.d/wlan0 <<EOF
auto $WIFI_INTERFACE
iface $WIFI_INTERFACE inet static
    address $WIFI_IP
    netmask 255.255.255.0
    # Don't set gateway - this is the gateway
EOF

# Step 5: Enable IP forwarding
echo "Step 5: Enabling IP forwarding..."
sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf || \
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p

# Step 6: Configure NAT (iptables)
echo "Step 6: Configuring NAT..."

# Determine the internet-facing interface (usually eth0)
INTERNET_INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n 1)
if [ -z "$INTERNET_INTERFACE" ]; then
    INTERNET_INTERFACE="eth0"
    echo "Warning: Could not detect internet interface, using $INTERNET_INTERFACE"
fi

echo "  Internet interface: $INTERNET_INTERFACE"

# Set up NAT rules
iptables -t nat -A POSTROUTING -o $INTERNET_INTERFACE -j MASQUERADE
iptables -A FORWARD -i $INTERNET_INTERFACE -o $WIFI_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i $WIFI_INTERFACE -o $INTERNET_INTERFACE -j ACCEPT

# Save iptables rules
iptables-save > /etc/iptables.rules

# Create script to restore iptables on boot
cat > /etc/network/if-pre-up.d/iptables <<'EOF'
#!/bin/sh
/sbin/iptables-restore < /etc/iptables.rules
EOF
chmod +x /etc/network/if-pre-up.d/iptables

# Step 7: Enable and start services
echo "Step 7: Enabling and starting services..."

# Unmask hostapd (it's sometimes masked by default)
systemctl unmask hostapd

# Enable services
systemctl enable hostapd
systemctl enable dnsmasq

# Restart network interface
echo "  Restarting network interface..."
ifdown $WIFI_INTERFACE 2>/dev/null || true
sleep 2
ifup $WIFI_INTERFACE

# Start services
echo "  Starting hostapd..."
systemctl start hostapd

echo "  Starting dnsmasq..."
systemctl start dnsmasq

# Step 8: Verify
echo ""
echo "=== Verification ==="
echo ""

# Check hostapd status
if systemctl is-active --quiet hostapd; then
    echo "✓ hostapd is running"
else
    echo "✗ hostapd failed to start"
    systemctl status hostapd --no-pager -l
fi

# Check dnsmasq status
if systemctl is-active --quiet dnsmasq; then
    echo "✓ dnsmasq is running"
else
    echo "✗ dnsmasq failed to start"
    systemctl status dnsmasq --no-pager -l
fi

# Check IP address
CURRENT_IP=$(ip addr show $WIFI_INTERFACE | grep "inet " | awk '{print $2}' | cut -d/ -f1)
if [ "$CURRENT_IP" = "$WIFI_IP" ]; then
    echo "✓ WiFi interface has correct IP: $CURRENT_IP"
else
    echo "✗ WiFi interface IP mismatch. Expected: $WIFI_IP, Got: $CURRENT_IP"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "WiFi Access Point Details:"
echo "  SSID: $SSID"
echo "  Password: $PASSWORD"
echo "  IP Address: $WIFI_IP"
echo "  Domain: $DOMAIN"
echo ""
echo "To connect:"
echo "  1. Connect to WiFi network '$SSID'"
echo "  2. Enter password: $PASSWORD"
echo "  3. Your device will get an IP in range $DHCP_RANGE_START-$DHCP_RANGE_END"
echo "  4. Access R58 at: https://$WIFI_IP:8443"
echo ""
echo "Troubleshooting:"
echo "  - Check hostapd: sudo journalctl -u hostapd -n 50"
echo "  - Check dnsmasq: sudo journalctl -u dnsmasq -n 50"
echo "  - Check WiFi interface: ip addr show $WIFI_INTERFACE"
echo "  - Check DHCP leases: cat /var/lib/misc/dnsmasq.leases"
echo ""

