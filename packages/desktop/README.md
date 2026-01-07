# R58 Studio Desktop

Electron desktop application for remote control of R58 devices.

## Overview

R58 Studio Desktop wraps the Vue.js web interface in an Electron shell, providing:

- **Offline Capability**: Frontend bundled locally, only needs network for device API
- **Multi-Device Support**: Connect to multiple R58 devices, switch between them
- **Secure Storage**: Device configurations stored with encryption
- **Native Experience**: macOS menu, keyboard shortcuts, file logging

## Development

### Prerequisites

- Node.js 20+
- npm 10+

### Setup

```bash
# Install dependencies
cd packages/desktop
npm install

# Also install frontend dependencies if not done
cd ../frontend
npm install
```

### Running in Development

```bash
# Build frontend for Electron and run
npm run dev

# Or watch for changes (requires frontend already built)
npm run dev:watch
```

### Building

```bash
# Full build (frontend + main process + preload)
npm run build

# Build and package (no signing)
npm run pack

# macOS builds
npm run dist:mac              # Signed + notarized DMG
npm run dist:mac:unsigned     # Unsigned DMG

# Windows builds
npm run dist:win              # Signed installer (if certs available)
npm run dist:win:unsigned     # Unsigned installer

# All platforms
npm run dist:all              # All platforms (signed)
npm run dist:all:unsigned    # All platforms (unsigned)

# Convert icons (run before first build)
npm run convert-icons
```

## Project Structure

```
packages/desktop/
├── src/
│   ├── main/           # Main process (Node.js)
│   │   ├── index.ts    # App entry, lifecycle, IPC handlers
│   │   ├── window.ts   # BrowserWindow management, security
│   │   ├── menu.ts     # Application menu
│   │   ├── deviceStore.ts  # Encrypted device config storage
│   │   └── logger.ts   # File logging, support bundle
│   └── preload/        # Preload scripts (bridge to renderer)
│       └── index.ts    # contextBridge API exposure
├── app/                # Build output
│   ├── main/           # Compiled main process
│   ├── preload/        # Compiled preload
│   └── renderer/       # Vue frontend build
├── resources/          # Build resources
│   ├── icon.icns       # macOS app icon
│   └── entitlements.mac.plist
├── dist/               # Packaged app output
└── electron-builder.yml
```

## Code Signing and Notarization

### Requirements for Distribution

To distribute the app outside the Mac App Store (Developer ID distribution), you need:

1. **Apple Developer Program membership** ($99/year)
2. **Developer ID Application certificate**
3. **App-specific password** for notarization

### Environment Variables

Set these for signed builds:

| Variable | Description | How to Get |
|----------|-------------|------------|
| `CSC_LINK` | Path to .p12 certificate OR base64-encoded content | Export from Keychain Access |
| `CSC_KEY_PASSWORD` | Certificate password | Set when exporting from Keychain |
| `APPLE_ID` | Your Apple ID email | Your Apple Developer account email |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password | [appleid.apple.com](https://appleid.apple.com) → Security → App-Specific Passwords |
| `APPLE_TEAM_ID` | 10-character Team ID | [developer.apple.com](https://developer.apple.com/account) → Membership |

### Getting Your Certificate

1. Go to [Apple Developer Certificates](https://developer.apple.com/account/resources/certificates/list)
2. Create a "Developer ID Application" certificate
3. Download and install in Keychain Access
4. Export as .p12 with a password

### Creating App-Specific Password

1. Go to [appleid.apple.com](https://appleid.apple.com)
2. Sign in → Security → App-Specific Passwords
3. Generate a new password for "R58 Studio Notarization"
4. Save securely - you won't see it again!

### Building Signed Release

```bash
# Set environment variables
export CSC_LINK="/path/to/certificate.p12"
export CSC_KEY_PASSWORD="your-certificate-password"
export APPLE_ID="your-apple-id@example.com"
export APPLE_APP_SPECIFIC_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="XXXXXXXXXX"

# Build signed and notarized DMG
npm run dist:mac
```

### Unsigned Development Builds

For local testing without signing:

```bash
npm run dist:mac:unsigned
```

Note: Unsigned builds will show Gatekeeper warnings when opened.

## Security Model

### Electron Security Checklist

- ✅ `contextIsolation: true` - Renderer cannot access Node.js
- ✅ `sandbox: true` - Additional process isolation
- ✅ `nodeIntegration: false` - No Node.js in renderer
- ✅ `webSecurity: true` - Enforce same-origin policy
- ✅ Navigation allowlist - Only file:// allowed
- ✅ Window open handler - External URLs open in system browser
- ✅ Certificate bypass only for configured devices

### IPC Communication

All renderer ↔ main communication goes through the preload script's `contextBridge`:

```typescript
// In renderer (Vue components)
const devices = await window.electronAPI.getDevices()
await window.electronAPI.setActiveDevice(deviceId)
```

### Self-Signed Certificates

For LAN devices with self-signed TLS certificates:

1. Add the device via Device Setup
2. The app will allow certificate errors ONLY for that specific URL
3. Users explicitly trust devices they configure

## Logs and Debugging

### Log Location

- macOS: `~/Library/Logs/R58 Studio/main.log`
- Windows: `%USERPROFILE%\AppData\Roaming\R58 Studio\logs\main.log`

### Exporting Support Bundle

From the menu: Help → Export Support Bundle...

This creates a ZIP containing:
- Application logs
- Device configuration (URLs only)
- App version and system info

### DevTools

In development builds, use View → Toggle Developer Tools or `Cmd+Option+I`.

## Configuration Storage

Device configurations are stored encrypted in:

- macOS: `~/Library/Application Support/R58 Studio/r58-devices.json`
- Windows: `%APPDATA%\R58 Studio\r58-devices.json`

## Troubleshooting

### App won't connect to device

1. Check device URL is correct (include protocol: `https://` or `http://`)
2. Test the health endpoint: `curl https://your-device/api/v1/health`
3. For LAN devices, ensure you're on the same network
4. Check logs for connection errors

### Gatekeeper blocks the app

For unsigned builds:
1. Right-click → Open
2. Click "Open" in the dialog

For signed builds that still show warnings:
- The app may not be notarized properly
- Check the build logs for notarization errors

### WebSocket doesn't connect

- WebSocket uses the same base URL as HTTP
- Check that port 8000 is accessible (or the configured port)
- Look for WS errors in the DevTools console

## Installation Guides

For end-user installation instructions, see:
- [macOS Installation Guide](INSTALL_MACOS.md)
- [Windows Installation Guide](INSTALL_WINDOWS.md)

## Future Enhancements

- [ ] Auto-update via electron-updater
- [x] Windows distribution
- [ ] Linux AppImage
- [ ] Device discovery via mDNS/Bonjour

