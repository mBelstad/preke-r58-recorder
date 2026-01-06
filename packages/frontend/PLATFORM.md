# Platform Development Guide

## Overview
The frontend is a single Vue 3 codebase that runs in two environments:
- **Web App**: Served via nginx/Vite, accessed in browser
- **Electron App**: Desktop app with native OS integration

## Key Differences

| Feature | Web | Electron |
|---------|-----|----------|
| Device discovery | Manual URL | Tailscale + LAN scan |
| Initial route | `/` (Studio) | `/device-setup` |
| Window chrome | Browser | Frameless + custom |
| PWA support | Yes | No |
| File system | Limited | Full (via IPC) |
| macOS traffic lights | N/A | 70px header spacer |

## Platform Detection

```typescript
import { platform } from '@/lib/platform'

// Check environment
if (platform.isElectron()) { /* desktop-specific */ }
if (platform.isWeb()) { /* web-specific */ }

// Check features
if (platform.features.deviceDiscovery()) { /* show discovery UI */ }
```

## CSS Platform Targeting

```css
/* Electron-only styles */
.electron-app .my-component { }

/* macOS-specific */
.is-macos .header__spacer { width: 70px; }

/* Windows-specific */  
.is-windows .header__spacer { width: 0; }
```

## Development Commands

| Command | Description |
|---------|-------------|
| `npm run dev:web` | Start web dev server (port 5173) |
| `npm run dev:electron` | Build and run Electron app |
| `npm run test:web` | Run web app tests |
| `npm run test:electron` | Launch Electron for testing |

