# Windows PC Recovery - Network Bridge Issue

**Date**: December 22, 2025  
**Status**: ❌ **Windows PC Offline - Requires Physical Access**

---

## What Happened

Creating a network bridge between the Ethernet adapter and ZeroTier adapter on Windows broke the network configuration:

- ❌ Windows PC not reachable via ZeroTier (10.76.254.72)
- ❌ Windows PC not reachable via local network
- ❌ AnyDesk not working
- ❌ Cannot fix remotely without alternative access

---

## Current Situation

### What We Tried

1. ✅ Pinged Windows PC from Mac via ZeroTier - **Failed** (Host is down)
2. ✅ Scanned local network from R58 - **Windows PC not responding**
3. ✅ Checked neighbor table - **Windows PC not visible**
4. ❌ Cannot access Windows PC remotely

### Network Status

- **R58**: ✅ Online and accessible via SSH (r58.itagenten.no)
- **Your Mac**: ✅ Online, ZeroTier connected (10.76.254.125)
- **Windows PC**: ❌ Offline (both ZeroTier and local network)

---

## Recovery Options

### Option 1: Physical Access (Most Reliable)

**Someone needs to be on-site** to:

1. **Restart the Windows PC** (might auto-recover)
   
2. If restart doesn't work, **boot into Safe Mode**:
   - Restart PC
   - Press **F8** repeatedly during boot
   - Select **Safe Mode with Networking**
   
3. **Remove the network bridge**:
   - Press **Win + R** → type `ncpa.cpl` → Enter
   - Find **"Network Bridge"** adapter
   - Right-click → **Delete**
   
4. **Re-enable adapters**:
   - Right-click **Ethernet** adapter → **Enable**
   - Right-click **ZeroTier One** adapter → **Enable**
   
5. **Restart normally**

---

### Option 2: Alternative Remote Access

Do you have any of these installed on Windows PC?

- **TeamViewer** - Try connecting
- **Chrome Remote Desktop** - Check if accessible
- **Windows Remote Desktop** (RDP) - If port forwarded
- **SSH Server** - If enabled
- **Another remote tool**

If yes, use that to run these commands:

```cmd
REM Remove bridge
netsh bridge destroy

REM Re-enable adapters
netsh interface set interface "Ethernet" admin=enable
netsh interface set interface "ZeroTier One [8d1c312afa48ac9f]" admin=enable

REM Restart ZeroTier
net stop "ZeroTier One"
net start "ZeroTier One"

REM Restart networking
ipconfig /release
ipconfig /renew
```

---

### Option 3: Wait for Auto-Recovery

Sometimes Windows will recover after:
- **Automatic restart** (if configured)
- **DHCP lease renewal**
- **Network timeout and reset**

**Wait 30-60 minutes**, then try:
```bash
ping 10.76.254.72
```

---

### Option 4: Use Current Working Setup

**For now**, use what's already working:

#### Access R58 via Cloudflare Tunnel

```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Web UI
open "https://recorder.itagenten.no"

# VDO.ninja
open "https://vdo.itagenten.no/?director=r58studio"
```

**Trade-off**: WebRTC will use TURN relay (100-200ms latency instead of 10-50ms)

---

## Prevention for Future

### ❌ DON'T: Create Network Bridge

**Never bridge ZeroTier with your main network adapter** - it breaks connectivity.

### ✅ DO: Use Internet Connection Sharing

Instead of bridging, use **Internet Connection Sharing (ICS)**:

1. Right-click **Ethernet** adapter → **Properties**
2. Go to **Sharing** tab
3. Check: **"Allow other network users to connect"**
4. Select: **ZeroTier adapter** from dropdown
5. Click **OK**

This enables forwarding without breaking the adapters.

### ✅ DO: Use Registry Method

Or enable IP forwarding via registry:

```cmd
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v IPEnableRouter /t REG_DWORD /d 1 /f
```

Then restart Windows.

---

## Alternative Solution: Dedicated Gateway

Instead of risking your main Windows PC, consider a **dedicated gateway device**:

### Raspberry Pi 4 as ZeroTier Gateway

**Cost**: ~$80  
**Benefits**:
- Always on (5W power)
- Won't break your main PC
- Reliable gateway
- Easy to reset if issues

**Setup**:
1. Install Raspberry Pi OS
2. Install ZeroTier
3. Enable IP forwarding
4. Configure as gateway

I can help you set this up when you're ready.

---

## Immediate Action Plan

### Step 1: Try Alternative Remote Access

Check if any of these work:
- [ ] TeamViewer
- [ ] Chrome Remote Desktop  
- [ ] Windows RDP (if port forwarded)
- [ ] Other remote tools

### Step 2: If No Remote Access

- [ ] Coordinate physical access to Windows PC
- [ ] Follow Option 1 recovery steps above
- [ ] Remove bridge, re-enable adapters

### Step 3: Use Working Setup Meanwhile

- [ ] Access R58 via Cloudflare Tunnel
- [ ] Use VDO.ninja with TURN relay
- [ ] Accept higher latency temporarily

### Step 4: Plan Better Solution

- [ ] Consider Raspberry Pi gateway
- [ ] Or use proper ICS method (not bridge)
- [ ] Document correct setup

---

## Summary

**Current Status**:
- ❌ Windows PC offline (bridge broke networking)
- ✅ R58 accessible via Cloudflare Tunnel
- ✅ Can use VDO.ninja with TURN (higher latency)

**Recovery**:
- Requires physical access or alternative remote tool
- Simple fix: Remove bridge, re-enable adapters, restart

**Next Time**:
- Use Internet Connection Sharing (ICS), not bridge
- Or use registry method for IP forwarding
- Or get dedicated Raspberry Pi gateway

---

## Need Help?

Once you have access to the Windows PC (physical or remote), I can guide you through:
1. Removing the bridge safely
2. Setting up proper Internet Connection Sharing
3. Testing the ZeroTier gateway setup
4. Or setting up a Raspberry Pi gateway instead

Let me know when you have access!


