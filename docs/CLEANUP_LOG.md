# Cleanup Log - Domain Architecture Update

**Date**: 2026-01-08

## Summary

Updated the codebase to use the new domain architecture:
- `app.itagenten.no` - Vue web frontend (Preke Studio)
- `r58-api.itagenten.no` - Backend API (proxied to R58)
- `r58-vdo.itagenten.no` - Self-hosted VDO.ninja

## Files Removed

### `src/static/vue/` (entire directory)
- **Reason**: Old Vue build artifacts that were no longer being used
- **Contents**: 33+ files including JS bundles, CSS, images, service worker
- **Now served from**: `packages/frontend/dist/` (the current Vue build)
- **Impact**: None - the main.py was already serving from `packages/frontend/dist/`

## Files Updated

### `packages/frontend/src/lib/api.ts`
- Added domain detection for `app.itagenten.no`
- API calls now route to `https://r58-api.itagenten.no`
- WebSocket calls use `wss://r58-api.itagenten.no`

### `src/static/js/wiki-content.js`
- Updated web interface URLs from old static pages to new Vue URLs

### `src/static/js/wiki-content-part2.js`
- Updated "Available Interfaces" section with new Vue URLs
- Removed references to deprecated static HTML pages
- Added VDO.ninja mixer documentation

### `REMOTE_ACCESS.md`
- Updated with new domain architecture
- Added comprehensive URL list for all services

## Legacy Files (Kept for Compatibility)

These files still exist but have hardcoded URLs. They are kept for backward compatibility and internal testing:

### `src/static/camera-bridge.html`
- Still referenced in main.py
- Contains hardcoded `r58-vdo.itagenten.no` (correct)
- **Status**: Keep - used for camera bridge functionality

### `src/static/studio-control.html`
- Has configurable inputs with default values
- Users can change VDO.ninja host and API host
- **Status**: Keep - useful for manual testing

### `src/static/vdoninja-guest-bridge.html`
- Guest bridge page for VDO.ninja integration
- Has hardcoded defaults that can be overridden
- **Status**: Keep - used for guest connections

### `src/static/js/guests.js`
- Has hardcoded director URL for VDO.ninja
- **Status**: Keep - legacy functionality

### `scripts/vdoninja-bridge.service`
- Systemd service with environment variable defaults
- Uses `VDONINJA_HOST=r58-vdo.itagenten.no`
- Uses `API_HOST=r58-api.itagenten.no`
- **Status**: Keep - configurable via env vars

### `scripts/start-vdoninja-bridge.sh`
- Bridge startup script with env var defaults
- **Status**: Keep - configurable via env vars

## VPS Configuration

Updated nginx configuration on VPS (`/opt/r58-proxy/nginx/conf.d/r58-api.conf`):
- Added CORS headers for `app.itagenten.no`
- Handles OPTIONS preflight requests
- Proxies to R58 via FRP

## Domain Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ app.itagenten.no │  │r58-api.itagenten │  │r58-vdo.itagenten │
│   Vue Frontend   │  │   Backend API    │  │    VDO.ninja     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
           │                    │                    │
           │                    ▼                    │
           │            ┌──────────────────┐        │
           └───────────▶│   R58 Device     │◀───────┘
                        │  (via FRP/LAN)   │
                        └──────────────────┘
```

## Cross-Origin Requests

The frontend at `app.itagenten.no` makes cross-origin API calls to `r58-api.itagenten.no`.
CORS is configured in the nginx proxy on the VPS (not in FastAPI).

Headers added:
- `Access-Control-Allow-Origin: https://app.itagenten.no`
- `Access-Control-Allow-Methods: GET, POST, OPTIONS, PUT, DELETE, PATCH`
- `Access-Control-Allow-Headers: Content-Type, Authorization, Cache-Control, X-Requested-With`
- `Access-Control-Allow-Credentials: true`
