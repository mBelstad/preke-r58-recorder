# ZeroTier Route Configuration - Step by Step

**Issue**: Can't find where to add routes in ZeroTier Central  
**Solution**: Multiple methods below

---

## Method 1: ZeroTier Central Web UI (2024 Version)

The UI may have changed. Here's where to look:

### Step-by-Step with Screenshots Description

1. **Go to**: https://my.zerotier.com
2. **Click** on your network name/ID
3. **Scroll down** - Look for one of these sections:
   - **"Advanced"** section
   - **"Managed Routes"** section
   - **"Routes"** tab
   - **"Settings"** section

4. **Look for**:
   - A table with columns: "Destination" and "Via"
   - Or a button: "+ Add Route" or "Add Managed Route"
   - Or an input field labeled "Route"

### Common Locations in UI:

**Option A - In "Settings" tab**:
```
Networks → [Your Network] → Settings → Managed Routes
```

**Option B - In main network view**:
```
Networks → [Your Network] → (scroll down) → Managed Routes section
```

**Option C - In "Advanced" section**:
```
Networks → [Your Network] → Advanced → IPv4 Auto-Assign → Managed Routes
```

---

## Method 2: Use ZeroTier CLI (Easier!)

If you can't find the UI option, you can configure routing directly from your Windows PC or Mac.

### On Windows PC (Your Gateway)

Open **Command Prompt as Administrator**:

```cmd
REM Find your ZeroTier network ID
"C:\Program Files (x86)\ZeroTier\One\zerotier-cli.bat" listnetworks

REM Note your network ID (16-character hex)
```

**Important**: Routes are managed in ZeroTier Central, but we can work around this by configuring your Mac directly.

---

## Method 3: Direct Configuration (No Route Needed!)

Since you're already on the same ZeroTier network, you might not need a route if both devices can see each other!

### Test Direct Connection First

**On your Mac**, try this:

```bash
# Check ZeroTier status
sudo zerotier-cli listnetworks

# Get your Windows PC's ZeroTier IP
# (You'll need to check this on Windows)

# Try pinging R58 directly
ping 192.168.1.24
```

**If the ping works**, you don't need to add a route! Your Windows PC is already routing traffic.

**If the ping fails**, continue to Method 4 below.

---

## Method 4: Windows PC as Router (Manual Setup)

Since you're on the same ZeroTier network, we can configure Windows to route traffic without needing ZeroTier Central routes.

### On Windows PC (Run as Administrator)

#### Step 1: Enable IP Forwarding

**Option A - PowerShell (Recommended)**:
```powershell
# Run PowerShell as Administrator
Set-NetIPInterface -Forwarding Enabled

# Or specific interfaces:
Set-NetIPInterface -InterfaceAlias "ZeroTier One" -Forwarding Enabled
Set-NetIPInterface -InterfaceAlias "Ethernet" -Forwarding Enabled
```

**Option B - Registry**:
```powershell
# Enable IP routing in registry
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" -Name "IPEnableRouter" -Value 1

# Restart required
Restart-Computer
```

#### Step 2: Add Windows Firewall Rules

```powershell
# Allow forwarding between ZeroTier and local network
New-NetFirewallRule -DisplayName "ZeroTier Forward" -Direction Inbound -Action Allow -Protocol Any -InterfaceAlias "ZeroTier One"
New-NetFirewallRule -DisplayName "ZeroTier Forward Out" -Direction Outbound -Action Allow -Protocol Any -InterfaceAlias "ZeroTier One"
```

#### Step 3: Configure NAT (if needed)

```powershell
# Get your local network adapter name
Get-NetAdapter

# Enable NAT (replace "Ethernet" with your adapter name)
New-NetNat -Name "ZeroTierNAT" -InternalIPInterfaceAddressPrefix "192.168.1.0/24"
```

---

## Method 5: Manual Route on Mac

Instead of configuring routes in ZeroTier Central, add a route directly on your Mac.

### On Your Mac

```bash
# Get Windows PC's ZeroTier IP
# (Check on Windows: ipconfig | findstr "ZeroTier")
# Example: 10.147.20.123

# Add route on Mac
sudo route add -net 192.168.1.0/24 <windows-zerotier-ip>

# Example:
sudo route add -net 192.168.1.0/24 10.147.20.123

# Test
ping 192.168.1.24
```

**To make it persistent** (survives reboot), create a script:

```bash
# Create startup script
cat > ~/zerotier-route.sh << 'EOF'
#!/bin/bash
# Replace with your Windows PC's ZeroTier IP
GATEWAY_IP="10.147.20.123"
sudo route add -net 192.168.1.0/24 $GATEWAY_IP
EOF

chmod +x ~/zerotier-route.sh

# Run after connecting to ZeroTier
```

---

## Quick Diagnostic

Let's figure out what's happening:

### On Windows PC

```cmd
REM 1. Get ZeroTier IP
ipconfig | findstr "ZeroTier"

REM 2. Get local network IP
ipconfig | findstr "192.168"

REM 3. Check if you can reach R58
ping 192.168.1.24

REM 4. Check ZeroTier status
"C:\Program Files (x86)\ZeroTier\One\zerotier-cli.bat" listnetworks
```

### On Your Mac

```bash
# 1. Get ZeroTier IP
sudo zerotier-cli listnetworks

# 2. Try to ping Windows PC's ZeroTier IP
ping <windows-zerotier-ip>

# 3. Try to ping R58
ping 192.168.1.24

# 4. Check routing table
netstat -rn | grep 192.168.1
```

---

## What Information Do You See?

Please check and tell me:

### In ZeroTier Central (https://my.zerotier.com)

When you click on your network, do you see:

- [ ] A "Settings" tab or section?
- [ ] An "Advanced" section?
- [ ] A section called "Managed Routes"?
- [ ] A table showing routes?
- [ ] Any input fields or buttons to add routes?

### Alternative: Screenshot

If you can describe what you see on the network page, I can guide you to the exact location.

---

## Workaround: Test Without Route

Let's test if routing already works:

### On Your Mac (Quick Test)

```bash
# 1. Make sure ZeroTier is connected
sudo zerotier-cli listnetworks

# 2. Try to reach R58 directly
ping -c 3 192.168.1.24

# 3. If that works, try HTTPS
curl -k https://192.168.1.24:8443
```

**If this works**, you don't need to configure routes! Your Windows PC is already routing traffic automatically.

---

## ZeroTier Central UI Variations

The UI has changed over time. Here are the different versions:

### Old UI (pre-2023)
```
Network → Advanced → Managed Routes → Add Route
```

### New UI (2023+)
```
Network → Settings → IPv4 Management → Routes
```

### Current UI (2024)
```
Network → (scroll down) → Routes section → + Add
```

---

## Need Help?

Tell me:

1. **What do you see** when you click on your network in ZeroTier Central?
2. **Can you ping R58** (192.168.1.24) from your Mac?
3. **What's the Windows PC's ZeroTier IP?** (from `ipconfig`)

With this info, I can give you exact instructions for your setup!

---

## Quick Solution (Try This First!)

Since you're on the same ZeroTier network, try this:

```bash
# On your Mac
# Get Windows PC's ZeroTier IP first (from Windows: ipconfig)
# Then add route manually:

sudo route add -net 192.168.1.0/24 <windows-zerotier-ip>

# Test
ping 192.168.1.24

# If it works, access VDO.ninja:
open "https://192.168.1.24:8443/?director=r58studio"
```

This bypasses the need to configure routes in ZeroTier Central!

