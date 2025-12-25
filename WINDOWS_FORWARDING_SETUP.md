# Windows PC - Enable IP Forwarding

**Status**: Route added on Mac ✅, but Windows PC needs to forward traffic

---

## Problem

Your Mac can reach the Windows PC, and the route is configured, but the Windows PC isn't forwarding traffic from ZeroTier to the local network (where R58 is).

---

## Solution: Enable IP Forwarding on Windows

### Method 1: PowerShell (Easiest)

**On your Windows PC**, open **PowerShell as Administrator**:

1. Right-click Start menu
2. Click "Windows PowerShell (Admin)" or "Terminal (Admin)"
3. Run these commands:

```powershell
# Enable IP forwarding
Set-NetIPInterface -Forwarding Enabled

# Check if it worked
Get-NetIPInterface | Where-Object {$_.InterfaceAlias -like "*ZeroTier*" -or $_.InterfaceAlias -like "*Ethernet*"} | Select InterfaceAlias, Forwarding
```

**Expected output**: Should show `Forwarding: Enabled` for both ZeroTier and Ethernet adapters

---

### Method 2: Registry (Permanent)

If Method 1 doesn't work, enable via registry:

**On your Windows PC**, open **PowerShell as Administrator**:

```powershell
# Enable IP routing in registry
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "IPEnableRouter" -Value 1

# Verify
Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "IPEnableRouter"

# Restart computer for changes to take effect
Restart-Computer
```

---

### Method 3: Windows Firewall Rules

Add firewall rules to allow forwarding:

**On your Windows PC**, open **PowerShell as Administrator**:

```powershell
# Allow forwarding from ZeroTier
New-NetFirewallRule -DisplayName "ZeroTier Forward In" -Direction Inbound -Action Allow -Protocol Any -InterfaceAlias "ZeroTier One*"

New-NetFirewallRule -DisplayName "ZeroTier Forward Out" -Direction Outbound -Action Allow -Protocol Any -InterfaceAlias "ZeroTier One*"

# Check firewall rules
Get-NetFirewallRule -DisplayName "ZeroTier*"
```

---

## Quick Test

### On Windows PC

First, verify Windows can reach R58:

```cmd
ping 192.168.1.24
```

**This should work** - if it doesn't, R58 is not reachable from Windows PC.

---

### After Enabling Forwarding

**On your Mac**, test again:

```bash
ping 192.168.1.24
```

**This should now work!**

---

## Troubleshooting

### Windows Can't Reach R58

If Windows PC can't ping R58:

1. **Check network**: Make sure Windows PC is on same network as R58
2. **Check R58 IP**: Verify R58 is at 192.168.1.24
   ```cmd
   arp -a | findstr "192.168.1"
   ```
3. **Check firewall**: Windows firewall might be blocking ping

### Windows Can Reach R58, But Mac Can't

If Windows can ping R58, but Mac still can't:

1. **Check IP forwarding** (see Method 1 above)
2. **Check firewall rules** (see Method 3 above)
3. **Restart Windows** after registry changes
4. **Check NAT**: May need to enable NAT

---

## Enable NAT (If Forwarding Alone Doesn't Work)

**On your Windows PC**, open **PowerShell as Administrator**:

```powershell
# Get your Ethernet adapter name
Get-NetAdapter

# Enable NAT (replace "Ethernet" with your adapter name)
New-NetNat -Name "ZeroTierNAT" -InternalIPInterfaceAddressPrefix "192.168.1.0/24"

# Verify
Get-NetNat
```

---

## Alternative: Use ZeroTier Central Routes

Instead of configuring Windows, you can add the route in ZeroTier Central:

1. Go to https://my.zerotier.com
2. Click on network: **my-first-network**
3. Look for **"Managed Routes"** section (might be under Settings or Advanced)
4. Add route:
   ```
   Destination: 192.168.1.0/24
   Via: 10.76.254.72
   ```
5. Save

This tells ZeroTier to route traffic through your Windows PC automatically.

---

## Summary

**Current Status**:
- ✅ Mac has route configured
- ✅ Mac can reach Windows PC (10.76.254.72)
- ❌ Windows PC not forwarding traffic to R58

**Action Required**:
1. Enable IP forwarding on Windows (Method 1 above)
2. Add firewall rules (Method 3 above)
3. Test: `ping 192.168.1.24` from Mac

**Estimated Time**: 5 minutes

---

## Once Working

When ping succeeds, access VDO.ninja:

```bash
# On your Mac
open "https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443"
```

You'll get **low-latency WebRTC** (10-50ms instead of 100-200ms)! 🚀


