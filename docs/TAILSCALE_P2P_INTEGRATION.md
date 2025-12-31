# Tailscale P2P Integration for R58

## Overview

The R58 system now supports Tailscale for reliable P2P connectivity. This eliminates the need to route video streams through a VPS, reducing bandwidth costs and improving latency.

## How It Works

1. **Tailscale Mesh Network**: Both the R58 device and the Electron app join the same Tailscale tailnet
2. **P2P via Hole Punching**: Tailscale automatically establishes direct P2P connections when possible
3. **DERP Fallback**: If P2P fails (strict NAT), falls back to Tailscale's free DERP relays
4. **Tailscale Funnel**: Public viewers can access streams without installing Tailscale

## Connection Priority

The Electron app discovers R58 devices in this order:

| Priority | Method | Description |
|----------|--------|-------------|
| 1 | **Tailscale** | P2P mesh network (fastest, most reliable) |
| 2 | USB-C Direct | `192.168.42.1` gadget mode |
| 3 | Wi-Fi Hotspot | `192.168.4.1` |
| 4 | mDNS | `r58.local`, `preke.local`, etc. |
| 5 | LAN Scan | Subnet scanning |

## Setup

### On R58 Device

Tailscale is installed and running with userspace networking:

```bash
# Check status
tailscale status

# Tailscale IP
tailscale ip
```

### On Mac (Electron App)

Install Tailscale from the App Store or brew:

```bash
# Via Homebrew
brew install tailscale

# Or download from: https://tailscale.com/download
```

Login to the same tailnet as R58:
```bash
tailscale login
```

### Verify P2P Connection

```bash
# Ping R58 via Tailscale
tailscale ping linaro-alip

# Expected output (P2P):
# pong from linaro-alip (100.98.37.53) via 192.168.1.24:44615 in 2ms
#                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                                      Direct IP = P2P (not DERP)

# If it shows "via DERP(xxx)", connection is relayed
```

## URLs

### P2P URLs (Tailscale users only)

These require the viewer to have Tailscale installed and logged into the same tailnet:

| Service | URL |
|---------|-----|
| API | `http://100.98.37.53:8000` |
| WHEP cam0 | `http://100.98.37.53:8889/cam0/whep` |
| WHEP cam2 | `http://100.98.37.53:8889/cam2/whep` |
| WHEP cam3 | `http://100.98.37.53:8889/cam3/whep` |

### Public URLs (Tailscale Funnel)

These work for anyone on the internet, no Tailscale required:

| Service | URL |
|---------|-----|
| WHEP cam0 | `https://linaro-alip.tailab6fd7.ts.net/cam0/whep` |
| WHEP cam2 | `https://linaro-alip.tailab6fd7.ts.net/cam2/whep` |
| WHEP cam3 | `https://linaro-alip.tailab6fd7.ts.net/cam3/whep` |

VDO.ninja viewer links:
- cam0: `https://vdo.ninja/?whepplay=https://linaro-alip.tailab6fd7.ts.net/cam0/whep`
- cam2: `https://vdo.ninja/?whepplay=https://linaro-alip.tailab6fd7.ts.net/cam2/whep`
- cam3: `https://vdo.ninja/?whepplay=https://linaro-alip.tailab6fd7.ts.net/cam3/whep`

## Bandwidth & Cost

| Method | Video Routes Through | Cost |
|--------|---------------------|------|
| **Tailscale P2P** | Direct device ↔ device | **$0** |
| **Tailscale DERP** | Tailscale's relays | **$0** (Tailscale free tier) |
| **Tailscale Funnel** | Tailscale's ingress | **$0** (Tailscale free tier) |
| FRP/VPS | Your VPS | **You pay bandwidth** |

## Electron App Integration

The app automatically discovers R58 devices on Tailscale:

```typescript
// Check Tailscale status
const status = await window.electronAPI.getTailscaleStatus()
// { installed: true, running: true, loggedIn: true, selfIp: '100.106.198.113' }

// Find R58 devices
const devices = await window.electronAPI.findTailscaleDevices()
// [{ name: 'linaro-alip', tailscaleIp: '100.98.37.53', isP2P: true, ... }]

// Device discovery (automatic)
// Start discovery - Tailscale is checked first
window.electronAPI.startDiscovery()
```

## Troubleshooting

### Not P2P (Using DERP Relay)

If `tailscale ping` shows DERP instead of a direct IP:

1. **Strict NAT**: Some networks block UDP hole punching
2. **Firewall**: Ports may be blocked
3. **Wait**: P2P connection establishes after a few seconds

Tailscale will still work, just with slightly higher latency through DERP.

### R58 Not Visible in Tailscale

```bash
# On R58, check status
tailscale status

# Restart if needed
sudo systemctl restart tailscaled
```

### Tailscale CLI Not Found on Mac

If using the App Store version:
```bash
# Use full path
"/Applications/Tailscale.app/Contents/MacOS/Tailscale" status
```

Or add to PATH:
```bash
# In ~/.zshrc
alias tailscale='"/Applications/Tailscale.app/Contents/MacOS/Tailscale"'
```

## Architecture

```
┌─────────────────┐      P2P (Hole Punching)      ┌─────────────────┐
│  Electron App   │◄────────────────────────────►│   R58 Device    │
│  (Mac/Windows)  │         2ms latency          │  (linaro-alip)  │
│  100.106.198.x  │                              │  100.98.37.53   │
└─────────────────┘                              └─────────────────┘
         │                                                │
         │ (fallback only)                               │ Tailscale Funnel
         ▼                                                ▼
┌─────────────────┐                              ┌─────────────────┐
│  Tailscale DERP │                              │  Public Access  │
│  (Amsterdam)    │                              │  linaro-alip.   │
│  ~50ms latency  │                              │  tailab6fd7.    │
└─────────────────┘                              │  ts.net         │
                                                 └─────────────────┘
```

## Files Modified

- `packages/desktop/src/main/tailscale.ts` - Tailscale detection and device discovery
- `packages/desktop/src/main/discovery.ts` - Integrated Tailscale as priority discovery method
- `packages/desktop/src/preload/index.ts` - Exposed Tailscale APIs to renderer

