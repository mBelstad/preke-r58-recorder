#!/bin/bash
# Fix Preke Studio macOS tray/dock icon
# This script fixes the broken icon that appears after a few seconds

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo "Preke Studio Icon Fix"
echo "======================================"
echo ""

# Check if app exists
APP_PATH="/Applications/Preke Studio.app"
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}✗${NC} Preke Studio app not found at $APP_PATH"
    exit 1
fi
echo -e "${GREEN}✓${NC} Found Preke Studio app"

# Check if npx is available
if ! command -v npx &> /dev/null; then
    echo -e "${RED}✗${NC} npx not found. Please install Node.js first."
    exit 1
fi
echo -e "${GREEN}✓${NC} npx available"

# Check if iconutil is available (built into macOS)
if ! command -v iconutil &> /dev/null; then
    echo -e "${RED}✗${NC} iconutil not found. This should be built into macOS."
    exit 1
fi
echo -e "${GREEN}✓${NC} iconutil available"

# Create backup
BACKUP_PATH="$HOME/preke-studio-backup-icon-$(date +%Y%m%d-%H%M%S).asar"
echo ""
echo "Creating backup..."
cp "$APP_PATH/Contents/Resources/app.asar" "$BACKUP_PATH"
echo -e "${GREEN}✓${NC} Backup created: $BACKUP_PATH"

# Extract app
WORK_DIR="$HOME/preke-studio-icon-fix"
echo ""
echo "Extracting app source..."
rm -rf "$WORK_DIR"
npx asar extract "$APP_PATH/Contents/Resources/app.asar" "$WORK_DIR"
echo -e "${GREEN}✓${NC} Source extracted to $WORK_DIR"

# Fix the icon path in main.js
echo ""
echo "Fixing dock icon code..."
sed -i.bak 's|256x256-white-rounded\.png|256x256.png|g' "$WORK_DIR/main.js"
sed -i.bak2 's|256x256-white\.png|256x256.png|g' "$WORK_DIR/main.js"
echo -e "${GREEN}✓${NC} Updated main.js to use correct icon"

# Generate proper .icns file from the good PNG
echo ""
echo "Generating new .icns file..."
ICONSET_DIR="$WORK_DIR/icon.iconset"
mkdir -p "$ICONSET_DIR"

# Use the good 256x256.png as source
SOURCE_ICON="$WORK_DIR/assets/icons/png/256x256.png"

# Generate all required sizes using sips (built into macOS)
sips -z 16 16     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_16x16.png" > /dev/null 2>&1
sips -z 32 32     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_16x16@2x.png" > /dev/null 2>&1
sips -z 32 32     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_32x32.png" > /dev/null 2>&1
sips -z 64 64     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_32x32@2x.png" > /dev/null 2>&1
sips -z 128 128   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_128x128.png" > /dev/null 2>&1
sips -z 256 256   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_128x128@2x.png" > /dev/null 2>&1
sips -z 256 256   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_256x256.png" > /dev/null 2>&1
sips -z 512 512   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_256x256@2x.png" > /dev/null 2>&1
sips -z 512 512   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_512x512.png" > /dev/null 2>&1
sips -z 1024 1024 "$SOURCE_ICON" --out "$ICONSET_DIR/icon_512x512@2x.png" > /dev/null 2>&1

# Convert iconset to icns
iconutil -c icns "$ICONSET_DIR" -o "$WORK_DIR/assets/icons/mac/icon.icns"
echo -e "${GREEN}✓${NC} Generated new icon.icns"

# Clean up iconset directory
rm -rf "$ICONSET_DIR"

# Rebuild ASAR
echo ""
echo "Rebuilding app..."
npx asar pack "$WORK_DIR" "$APP_PATH/Contents/Resources/app.asar"
echo -e "${GREEN}✓${NC} App rebuilt successfully"

# Replace the main bundle icon as well
echo ""
echo "Replacing bundle icon..."
cp "$WORK_DIR/assets/icons/mac/icon.icns" "$APP_PATH/Contents/Resources/icon.icns"
echo -e "${GREEN}✓${NC} Bundle icon replaced"

# Touch the app to update modification date (helps macOS refresh the icon cache)
touch "$APP_PATH"

echo ""
echo "======================================"
echo -e "${GREEN}Icon fix applied successfully!${NC}"
echo "======================================"
echo ""
echo "Changes made:"
echo "  ✓ Updated dock icon to use 256x256.png (the good one)"
echo "  ✓ Generated new .icns file from good icon"
echo "  ✓ Replaced bundle icon"
echo ""
echo "Backup location: $BACKUP_PATH"
echo "Source location: $WORK_DIR"
echo ""
echo "Next steps:"
echo "  1. Quit Preke Studio if it's running"
echo "  2. Clear icon cache: sudo rm -rf /Library/Caches/com.apple.iconservices.store"
echo "  3. Restart Dock: killall Dock"
echo "  4. Launch Preke Studio: open -a '/Applications/Preke Studio.app'"
echo ""
echo "To restore from backup:"
echo "  cp '$BACKUP_PATH' '$APP_PATH/Contents/Resources/app.asar'"
echo ""


