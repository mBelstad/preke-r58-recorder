# Preke Studio Testing Guide

This guide explains how to test, debug, and troubleshoot Preke Studio during development using Cursor's AI-assisted "vibe coding" workflow.

## Quick Start

```bash
cd packages/desktop
npm run test:launch    # Start app with debugging
npm run test:logs      # View recent logs
npm run test:stop      # Stop the app
```

## Test Helper Commands

| Command | Description |
|---------|-------------|
| `npm run test:launch` | Launch app with Chrome DevTools Protocol (CDP) debugging |
| `npm run test:stop` | Stop the running app |
| `npm run test:status` | Check if app is running and CDP is available |
| `npm run test:logs` | Show last 50 log lines |
| `npm run test:logs:follow` | Follow logs in real-time (like `tail -f`) |
| `npm run test:cdp` | Show CDP endpoints for browser tools |

## Using Cursor Browser Tools

Once the app is running with `npm run test:launch`, you can use Cursor's browser tools to interact with it:

1. **Navigate to CDP interface:**
   ```
   browser_navigate to http://localhost:9222
   ```

2. **Take a snapshot of the app:**
   ```
   browser_snapshot
   ```

3. **Interact with elements:**
   - `browser_click` - Click elements
   - `browser_type` - Type text
   - `browser_evaluate` - Run JavaScript

## Reading Logs

### Log Location
- **macOS:** `~/Library/Logs/preke-studio/main.log`

### Via Test Helper
```bash
npm run test:logs          # Last 50 lines
npm run test:logs:follow   # Real-time following
```

### Via IPC (from renderer)
```typescript
// In the Electron renderer process
const { logs, path } = await window.electronAPI.getRecentLogs(100);
console.log('Log file:', path);
console.log(logs);
```

## Debugging with DevTools

When launched via `test:launch`, DevTools automatically opens in a detached window. You can also:

1. Press `Cmd+Option+I` (macOS) to toggle DevTools
2. Use the View menu → Toggle Developer Tools
3. Connect external tools to `ws://localhost:9222/devtools/...`

## Troubleshooting

### App Won't Start
```bash
npm run test:stop   # Make sure old instance is stopped
npm run test:logs   # Check for errors
npm run test:launch # Try again
```

### CDP Not Available
The CDP debugging port (9222) might be blocked. Check:
```bash
lsof -i :9222       # See what's using the port
```

### Module Errors
If you see TypeScript/module errors after making changes:
```bash
npm run build:main   # Rebuild the main process
npm run test:launch  # Relaunch
```

## Development Workflow

### Typical Session
1. `npm run test:launch` - Start the app
2. Make code changes
3. `npm run build:main` - Rebuild (if you changed main process code)
4. `npm run test:stop && npm run test:launch` - Restart to test changes
5. `npm run test:logs` - Check for errors

### Hot Reload (Renderer Only)
For renderer-only changes with Vite:
```bash
cd ../frontend
npm run dev          # Start Vite dev server

# In another terminal
cd ../desktop
npm run dev:hot      # Launch with Vite dev server URL
```

## File Locations

| File | Purpose |
|------|---------|
| `scripts/test-helper.js` | Test helper script |
| `src/main/` | Main process TypeScript source |
| `src/preload/` | Preload scripts |
| `app/main/` | Compiled main process JavaScript |
| `app/renderer/` | Built frontend files |

## CDP Reference

When the app is running, these endpoints are available:

- **List pages:** `http://localhost:9222/json`
- **Browser WS:** `ws://localhost:9222/devtools/browser/...`
- **Page WS:** `ws://localhost:9222/devtools/page/{id}`

Use `npm run test:cdp` to see the full list of available pages and their WebSocket URLs.

