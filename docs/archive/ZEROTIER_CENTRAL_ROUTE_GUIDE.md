# ZeroTier Central - Add Route (Visual Guide)

**Easier Alternative**: Configure route in ZeroTier Central instead of Windows

---

## Step-by-Step Instructions

### 1. Go to ZeroTier Central
Open: https://my.zerotier.com

### 2. Click on Your Network
Network name: **my-first-network**  
Network ID: `8d1c312afa48ac9f`

### 3. Find the Routes Section

The UI varies by version. Look for **ONE** of these:

#### Option A: "Settings" Tab
```
[Networks] → [my-first-network] → [Settings] → scroll down
```

#### Option B: Main Page
```
[Networks] → [my-first-network] → scroll down past "Members"
```

#### Option C: "Advanced" Section
```
[Networks] → [my-first-network] → [Advanced] → scroll down
```

### 4. Look for Section Named:
- **"Managed Routes"**
- **"Routes"**
- **"IPv4 Auto-Assign"** (routes might be under this)

### 5. Add the Route

You should see a table or form with these fields:

**Destination**: `192.168.1.0/24`  
**Via** (or "Gateway"): `10.76.254.72`

Click **"Submit"** or **"Add Route"** or **"+"**

---

## What Each Field Means

| Field | Value | Explanation |
|-------|-------|-------------|
| **Destination** | `192.168.1.0/24` | The network where R58 is located |
| **Via** | `10.76.254.72` | Your Windows PC's ZeroTier IP (the gateway) |

---

## If You Can't Find It

### Alternative 1: Share a Screenshot

If you can describe what you see on the network page, I can guide you to the exact location.

### Alternative 2: Use ZeroTier CLI (On Windows)

**On your Windows PC**, open Command Prompt as Administrator:

```cmd
cd "C:\Program Files (x86)\ZeroTier\One"

REM This won't add the route, but shows network info
zerotier-cli.bat listnetworks
```

Unfortunately, routes must be configured in ZeroTier Central web UI, not via CLI.

---

## What the Route Does

Once configured in ZeroTier Central:
- ✅ All devices on the ZeroTier network can reach 192.168.1.0/24
- ✅ Traffic automatically routes through Windows PC (10.76.254.72)
- ✅ No need to configure Windows forwarding
- ✅ Works for all devices (Mac, phone, tablet, etc.)

---

## Current UI (2024) - Most Common Location

1. Click network: **my-first-network**
2. **Scroll down** past the "Members" section
3. Look for a section with a table showing:
   ```
   Destination | (via) | Action
   ```
4. There should be existing routes like:
   ```
   10.76.254.0/24 | (LAN) | ✓
   ```
5. Click **"+"** or **"Add Route"** button
6. Enter:
   - Destination: `192.168.1.0/24`
   - Via: `10.76.254.72`
7. Click **Submit** or **Save**

---

## If Route Configuration Doesn't Exist

Some ZeroTier plans or older versions might not show route configuration. In that case:

### Workaround: Use Windows as Router (Simpler Method)

Instead of complex PowerShell commands, try this simple approach:

**On Windows PC**, open Command Prompt as Administrator:

```cmd
REM Enable IP forwarding (simple method)
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters" /v IPEnableRouter /t REG_DWORD /d 1 /f

REM Restart networking
netsh interface set interface "ZeroTier One [8d1c312afa48ac9f]" admin=disable
netsh interface set interface "ZeroTier One [8d1c312afa48ac9f]" admin=enable
```

Then test from Mac:
```bash
ping 192.168.1.24
```

---

## Test Without Forwarding

Let's verify Windows can reach R58 first:

**On Windows PC**:
```cmd
ping 192.168.1.24
```

**Does this work?**
- ✅ **YES**: Windows can reach R58, just need forwarding
- ❌ **NO**: Windows can't reach R58 - network issue

If Windows can't reach R58, check:
1. Is Windows on same network as R58? (192.168.1.x)
2. Is R58 powered on?
3. Check Windows network adapter settings

---

## Summary

**Easiest Solution**: Add route in ZeroTier Central web UI  
**Location**: Network page → scroll down → Managed Routes section  
**Route**: `192.168.1.0/24` via `10.76.254.72`

**If you can't find it**: Tell me what sections you see on the network page and I'll help locate it!


