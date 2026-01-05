# Preke Studio Testing Guide

Easy testing, debugging, and troubleshooting for Cursor vibe-coding.

## Quick Start

```bash
cd packages/desktop
npm run test:launch    # Start app with debugging
npm run test:logs      # View recent logs
npm run test:stop      # Stop the app
```

## All Commands

### App Control
| Command | Description |
|---------|-------------|
| `npm run test:launch` | Launch app with CDP debugging |
| `npm run test:stop` | Stop the running app |
| `npm run test:restart` | Stop and relaunch |
| `npm run test:build` | Rebuild main process and restart |

### Debugging
| Command | Description |
|---------|-------------|
| `npm run test:status` | Check app and CDP status |
| `npm run test:logs` | Show last 50 log lines |
| `npm run test:logs:follow` | Follow logs in real-time |
| `npm run test:logs:clear` | Clear the log file |
| `npm run test:cdp` | Show CDP endpoints |
| `npm run test:devtools` | Open DevTools in browser |
| `npm run test:screenshot` | Capture screen to screenshots/ |

## Cursor Browser Tools

When the app is running, use Cursor's browser tools to interact:

```
# Navigate to CDP interface
browser_navigate to http://localhost:9222

# Take a snapshot to see elements
browser_snapshot

# Interact with elements
browser_click, browser_type, browser_evaluate
```

## Log File

- **Location:** `~/Library/Logs/preke-studio/main.log`
- **View:** `npm run test:logs`
- **Follow:** `npm run test:logs:follow`
- **Clear:** `npm run test:logs:clear`

### Reading Logs from Renderer

```typescript
const { logs, path } = await window.electronAPI.getRecentLogs(100);
console.log(logs);
```

## Development Workflow

### Typical Session
```bash
npm run test:launch      # Start app
# Make code changes
npm run test:build       # Rebuild & restart
npm run test:logs        # Check for errors
```

### Hot Reload (Renderer Only)
```bash
# Terminal 1: Start Vite dev server
cd ../frontend && npm run dev

# Terminal 2: Launch with hot reload
cd ../desktop && npm run dev:hot
```

## Troubleshooting

### App Won't Start
```bash
npm run test:stop        # Ensure old instance stopped
npm run test:logs        # Check for errors
npm run test:launch      # Try again
```

### CDP Not Available
```bash
lsof -i :9222            # Check what's using port
npm run test:restart     # Restart the app
```

### Build Errors
```bash
npm run build:main       # Build manually to see errors
npm run test:logs        # Check runtime errors
```

## File Locations

| Path | Purpose |
|------|---------|
| `scripts/test-helper.js` | Test helper script |
| `src/main/` | Main process source |
| `src/preload/` | Preload scripts |
| `app/main/` | Compiled main process |
| `screenshots/` | Captured screenshots |
