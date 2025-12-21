#!/bin/bash

# R58 Local Network Setup Script
# Configures R58 as a local network hub with DHCP server

set -e

echo "=== R58 Local Network Setup ==="
echo ""

# Configuration
R58_IP="10.58.0.1"
R58_NETMASK="255.255.255.0"
DHCP_RANGE_START="10.58.0.100"
DHCP_RANGE_END="10.58.0.200"
DOMAIN="r58.local"
INTERFACE="eth0"  # Change if needed

echo "Configuration:"
echo "  Interface: $INTERFACE"
echo "  IP: $R58_IP"
echo "  DHCP Range: $DHCP_RANGE_START - $DHCP_RANGE_END"
echo "  Domain: $DOMAIN"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root"
  exit 1
fi

# Install dnsmasq if not present
echo "Installing dnsmasq..."
apt-get update -qq
apt-get install -y dnsmasq

# Stop dnsmasq while we configure
systemctl stop dnsmasq

# Configure static IP for R58
echo "Configuring static IP..."
cat > /etc/network/interfaces.d/r58-lan << EOF
# R58 Local Network Configuration
auto $INTERFACE
iface $INTERFACE inet static
    address $R58_IP
    netmask $R58_NETMASK
    # Gateway will be venue's router if connected
EOF

# Configure dnsmasq for DHCP
echo "Configuring DHCP server..."
cat > /etc/dnsmasq.d/r58-lan.conf << EOF
# R58 DHCP Configuration
interface=$INTERFACE
bind-interfaces

# DHCP range
dhcp-range=$DHCP_RANGE_START,$DHCP_RANGE_END,12h

# Domain
domain=$DOMAIN
local=/$DOMAIN/

# DNS servers (use venue's DNS or public DNS)
dhcp-option=option:dns-server,8.8.8.8,8.8.4.4

# Router option (R58 can act as gateway if needed)
# dhcp-option=option:router,$R58_IP

# Log DHCP requests
log-dhcp

# Don't read /etc/hosts
no-hosts

# Static hostname for R58
address=/r58.$DOMAIN/$R58_IP
address=/r58/$R58_IP
EOF

# Enable IP forwarding (in case R58 needs to route traffic)
echo "Enabling IP forwarding..."
cat > /etc/sysctl.d/99-r58-forwarding.conf << EOF
# R58 IP Forwarding
net.ipv4.ip_forward=1
EOF

sysctl -p /etc/sysctl.d/99-r58-forwarding.conf

# Restart network interface
echo "Restarting network interface..."
ifdown $INTERFACE 2>/dev/null || true
ifup $INTERFACE

# Start dnsmasq
echo "Starting DHCP server..."
systemctl enable dnsmasq
systemctl start dnsmasq

# Verify
echo ""
echo "=== Setup Complete ==="
echo ""
echo "R58 IP: $R58_IP"
echo "DHCP Status:"
systemctl status dnsmasq --no-pager -l | head -10
echo ""
echo "Test DHCP by connecting a PC to the R58 network."
echo "The PC should receive an IP in range $DHCP_RANGE_START - $DHCP_RANGE_END"
echo ""
echo "Access R58 from local network:"
echo "  http://$R58_IP:8443"
echo "  http://r58.$DOMAIN:8443"

