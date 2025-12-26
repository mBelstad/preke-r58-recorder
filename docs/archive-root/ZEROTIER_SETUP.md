# ZeroTier Setup for R58 - Backup Access

**Date**: December 21, 2025  
**Status**: ⏳ Partially Complete - Requires User Action

---

## Progress

### ✅ Completed

1. **ZeroTier installed on R58**
   - Version: 1.16.0-2
   - ZeroTier Address: `3ebbb67a22`
   - Service: Running and enabled

---

## Required User Actions

### 1. Create ZeroTier Network

You need to create a ZeroTier network for the R58 to join:

1. **Go to**: https://my.zerotier.com/
2. **Sign up** or **log in** (free account)
3. **Create a new network**:
   - Click "Create A Network"
   - Note the **Network ID** (16-character hex, e.g., `a0cbf4b62a1234567`)
4. **Configure network settings**:
   - Name: `R58-Backup-Access`
   - Access Control: `Private` (recommended)
   - IPv4 Auto-Assign: Enable (e.g., `10.147.x.x/16`)

### 2. Join R58 to Network

Once you have the Network ID, run this command:

```bash
./connect-r58.sh "sudo zerotier-cli join YOUR_NETWORK_ID"
```

Replace `YOUR_NETWORK_ID` with the 16-character network ID from step 1.

### 3. Authorize R58 in ZeroTier Dashboard

1. Go back to https://my.zerotier.com/
2. Click on your network
3. Scroll to "Members" section
4. Find the R58 device (address: `3ebbb67a22`)
5. **Check the "Auth" checkbox** to authorize it
6. Optionally, give it a name like "R58-Studio"

### 4. Get R58 ZeroTier IP

After authorization, run:

```bash
./connect-r58.sh "sudo zerotier-cli listnetworks"
```

This will show the assigned IP address (e.g., `10.147.17.123`).

### 5. Install ZeroTier on Your Mac

**MANUAL STEP REQUIRED**: Installation requires sudo password.

Option A - Via Homebrew (recommended):
```bash
brew install --cask zerotier-one
# Enter your Mac password when prompted
```

Option B - Direct download:
1. Go to: https://www.zerotier.com/download/
2. Download "ZeroTier One" for macOS
3. Run the installer
4. Enter your Mac password when prompted

### 6. Join Your Mac to the Same Network

1. Open ZeroTier app on Mac
2. Click "Join Network"
3. Enter the same Network ID
4. Go back to ZeroTier dashboard and authorize your Mac

### 7. Test SSH via ZeroTier

```bash
ssh linaro@<R58_ZEROTIER_IP>
# Password: linaro
```

If this works, you have backup access! ✅

---

## Why ZeroTier Instead of Tailscale?

Tailscale was blocked on R58 because the kernel lacks TUN module support. ZeroTier uses **userspace networking** and does NOT require kernel TUN support, making it compatible with the R58's current kernel.

---

## Next Steps

Once ZeroTier SSH is verified working:
- ✅ Safe to proceed with WiFi AP configuration
- ✅ Safe to modify network settings
- ✅ Safe to remove Cloudflare Tunnel (if desired)

ZeroTier provides a permanent backup access method regardless of network configuration changes.

---

## Troubleshooting

### R58 not appearing in Members list
- Wait 1-2 minutes for the device to register
- Check ZeroTier service: `sudo systemctl status zerotier-one`
- Check logs: `sudo journalctl -u zerotier-one -n 50`

### Can't SSH via ZeroTier IP
- Verify both devices are authorized in the network
- Check firewall rules on R58
- Ensure ZeroTier is running on both devices

### ZeroTier service not starting
- Check logs: `sudo journalctl -u zerotier-one -xe`
- Restart service: `sudo systemctl restart zerotier-one`

---

**IMPORTANT**: Do NOT proceed with Phase 1 (WiFi AP setup) until ZeroTier SSH access is verified working!

