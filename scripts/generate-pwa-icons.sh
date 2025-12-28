#!/bin/bash
# Generate PWA icons from favicon.svg
# Requires: librsvg (rsvg-convert) or ImageMagick (convert)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PUBLIC_DIR="$PROJECT_ROOT/packages/frontend/public"
SVG_FILE="$PUBLIC_DIR/favicon.svg"

echo "Generating PWA icons from $SVG_FILE..."

# Check if rsvg-convert is available (preferred - better SVG support)
if command -v rsvg-convert &> /dev/null; then
    echo "Using rsvg-convert..."
    
    rsvg-convert -w 192 -h 192 "$SVG_FILE" -o "$PUBLIC_DIR/pwa-192x192.png"
    echo "  Created pwa-192x192.png"
    
    rsvg-convert -w 512 -h 512 "$SVG_FILE" -o "$PUBLIC_DIR/pwa-512x512.png"
    echo "  Created pwa-512x512.png"
    
    rsvg-convert -w 180 -h 180 "$SVG_FILE" -o "$PUBLIC_DIR/apple-touch-icon.png"
    echo "  Created apple-touch-icon.png"

# Fallback to ImageMagick
elif command -v convert &> /dev/null; then
    echo "Using ImageMagick..."
    
    convert -background none -resize 192x192 "$SVG_FILE" "$PUBLIC_DIR/pwa-192x192.png"
    echo "  Created pwa-192x192.png"
    
    convert -background none -resize 512x512 "$SVG_FILE" "$PUBLIC_DIR/pwa-512x512.png"
    echo "  Created pwa-512x512.png"
    
    convert -background none -resize 180x180 "$SVG_FILE" "$PUBLIC_DIR/apple-touch-icon.png"
    echo "  Created apple-touch-icon.png"

else
    echo "Error: Neither rsvg-convert nor ImageMagick is installed."
    echo ""
    echo "Install one of the following:"
    echo "  macOS:   brew install librsvg"
    echo "  Ubuntu:  sudo apt install librsvg2-bin"
    echo "  Arch:    sudo pacman -S librsvg"
    exit 1
fi

echo ""
echo "PWA icons generated successfully!"
ls -la "$PUBLIC_DIR"/*.png

