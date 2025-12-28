#!/bin/bash
# Set up TLS certificates for MediaMTX WebRTC encryption
# This creates symlinks to the certificates managed by nginx/Coolify

set -e

CERT_DIR="/etc/ssl/r58"
DOMAIN="r58-api.itagenten.no"

echo "=== Setting up MediaMTX TLS Certificates ==="

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo: sudo $0"
    exit 1
fi

# Function to generate self-signed certificate
generate_self_signed() {
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$CERT_DIR/privkey.pem" \
        -out "$CERT_DIR/fullchain.pem" \
        -days 365 -nodes \
        -subj "/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:localhost"
    
    echo "Generated self-signed certificate (browser will show warning)"
}

# Create certificate directory
mkdir -p "$CERT_DIR"

# Look for Let's Encrypt certificates in common locations
CERTBOT_DIR="/etc/letsencrypt/live/$DOMAIN"
COOLIFY_CERT_DIR="/data/coolify/proxy/certs"

if [ -d "$CERTBOT_DIR" ]; then
    echo "Found Let's Encrypt certificates for $DOMAIN"
    ln -sf "$CERTBOT_DIR/privkey.pem" "$CERT_DIR/privkey.pem"
    ln -sf "$CERTBOT_DIR/fullchain.pem" "$CERT_DIR/fullchain.pem"
    echo "Created symlinks to Let's Encrypt certs"

elif [ -d "$COOLIFY_CERT_DIR" ]; then
    echo "Found Coolify proxy certificates"
    # Coolify uses Traefik which stores certs in a different format
    # Check for the domain-specific cert
    if [ -f "$COOLIFY_CERT_DIR/$DOMAIN.crt" ]; then
        ln -sf "$COOLIFY_CERT_DIR/$DOMAIN.key" "$CERT_DIR/privkey.pem"
        ln -sf "$COOLIFY_CERT_DIR/$DOMAIN.crt" "$CERT_DIR/fullchain.pem"
        echo "Created symlinks to Coolify certs"
    else
        echo "Coolify cert for $DOMAIN not found, generating self-signed..."
        generate_self_signed
    fi

else
    echo "No Let's Encrypt or Coolify certificates found."
    echo "Generating self-signed certificate for development..."
    generate_self_signed
fi

# Ensure r58 user can read the certs
chmod 644 "$CERT_DIR/"*.pem 2>/dev/null || true

echo ""
echo "=== Certificate Setup Complete ==="
ls -la "$CERT_DIR/"
echo ""
echo "Now restart MediaMTX to use the new certificates:"
echo "  sudo systemctl restart r58-mediamtx"
