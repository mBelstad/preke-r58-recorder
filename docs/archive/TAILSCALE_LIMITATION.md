# Tailscale Limitation on R58

**Date**: December 21, 2025  
**Status**: BLOCKED - Kernel limitation

## Issue

Tailscale cannot be installed on the R58 device due to missing TUN kernel module support.

### Error Details

```
is CONFIG_TUN enabled in your kernel? `modprobe tun` failed with: 
modprobe: FATAL: Module tun not found in directory /lib/modules/6.1.99
tun module not loaded nor found on disk
```

### Root Cause

The R58's custom kernel (6.1.99) was compiled without CONFIG_TUN support, which is required for Tailscale's VPN functionality.

## Impact on Implementation Plan

- **Phase 0 (Tailscale as safety net)**: Cannot be completed as planned
- **Development access**: Must continue using Cloudflare Tunnel until Phase 1 complete
- **VPN fallback for users**: Need alternative solution

## Alternative Approach

### For Development (Phase 0)
- Keep Cloudflare Tunnel active during implementation
- Remove it only after Phase 1 (Coolify relay) is fully working and tested

### For End Users (Phase 2)
Instead of Tailscale VPN, use:
1. **Primary**: Direct access via Coolify relay (no VPN needed)
2. **Fallback**: WireGuard VPN (if kernel supports it) or OpenVPN

## Next Steps

1. ✅ Backup created
2. ✅ Branch created (`feature/remote-access-v2`)
3. ⏭️ Skip Tailscale installation
4. ➡️ Proceed to Phase 1: Deploy Coolify infrastructure
5. ➡️ Keep Cloudflare Tunnel as development access until relay is working

## Kernel Module Check

To verify TUN support in future:
```bash
lsmod | grep tun
ls /lib/modules/$(uname -r)/kernel/drivers/net/tun.ko
```

Current status: Module not available in this kernel build.

