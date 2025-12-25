# VPN Limitation on R58

**Date**: December 21, 2025  
**Status**: ⚠️ **BLOCKED**

---

## Summary

Both Tailscale and ZeroTier are **blocked** on the R58 device due to kernel limitations.

---

## Root Cause

The R58's Linux kernel (version 6.1.99) does not have TUN/TAP device support.

### Tailscale Error
```
is CONFIG_TUN enabled in your kernel? `modprobe tun` failed with: modprobe: FATAL: Module tun not found
tun module not loaded nor found on disk
```

### ZeroTier Error
```
ERROR: unable to configure virtual network port: could not open TUN/TAP device: No such file or directory
```

Both VPN solutions require `/dev/net/tun` which is not available on this kernel.

---

## Attempted Solutions

1. ✅ **Tailscale**: Installed but service failed to start
2. ✅ **ZeroTier**: Installed, joined network, but cannot create virtual interface

---

## Resolution

**Use Cloudflare Tunnel as primary access method.**

The Cloudflare Tunnel is already running and provides:
- ✅ Remote SSH access
- ✅ Remote web UI access  
- ✅ HTTPS/WSS for VDO.ninja
- ✅ No kernel modifications needed

---

## Revised Architecture

Since VPN backup is not possible, we'll proceed with:

1. **Primary Access**: Cloudflare Tunnel (already working)
2. **Local Network**: WiFi AP for on-site control
3. **Public Access**: Dynamic DNS + port forwarding (optional)
4. **Backup Access**: Cloudflare Tunnel (keep enabled)

---

## Impact on Plan

### Original Plan
- Phase 0: Install VPN backup (Tailscale/ZeroTier)
- Phase 1: Local network + DynDNS
- Phase 2: VPN documentation

### Revised Plan
- ~~Phase 0~~: Cancelled (VPN not possible)
- Phase 1: Local network + DynDNS (proceed via Cloudflare Tunnel)
- Keep Cloudflare Tunnel enabled permanently

---

## Recommendation

**Keep Cloudflare Tunnel enabled** as the primary remote access method. It provides:
- Secure remote access without port forwarding
- No kernel dependencies
- Already proven to work
- Easy SSH and web access

The WiFi AP and DynDNS setup can still proceed for local/direct access, but Cloudflare Tunnel remains the reliable backup.

---

## Next Steps

Proceed with Phase 1 setup using Cloudflare Tunnel for SSH access:

```bash
# Use existing tunnel access
./connect-r58.sh "command"

# Or direct SSH
ssh linaro@r58.itagenten.no
```

All Phase 1 scripts are ready to run.

