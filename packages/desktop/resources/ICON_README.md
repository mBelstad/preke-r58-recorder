# App Icon

Place your app icon files here:

## macOS
- `icon.icns` - macOS app icon (required for DMG builds)

### Creating icon.icns from PNG

1. Prepare a 1024x1024 PNG
2. Use iconutil or online converter:

```bash
# Create iconset folder
mkdir icon.iconset

# Create required sizes (from 1024x1024 source)
sips -z 16 16     icon-1024.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon-1024.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon-1024.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon-1024.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon-1024.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon-1024.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon-1024.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon-1024.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon-1024.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon-1024.png --out icon.iconset/icon_512x512@2x.png

# Convert to icns
iconutil -c icns icon.iconset -o icon.icns
```

## Windows
- `icon.ico` - Windows icon

## Linux
- `icons/` folder with PNG files in various sizes:
  - 16x16.png
  - 32x32.png
  - 48x48.png
  - 64x64.png
  - 128x128.png
  - 256x256.png
  - 512x512.png

## Temporary Solution

For development builds without icons, the app will use Electron's default icon.

