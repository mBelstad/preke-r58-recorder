# ZeroTier Gateway - Quick Start

**Your Setup**: Windows PC with ZeroTier on same network as R58  
**Goal**: Access R58's VDO.ninja remotely with low latency

---

## 3-Step Setup

### Step 1: Configure Route (ZeroTier Central)

1. Go to https://my.zerotier.com
2. Click your network
3. Scroll to **"Managed Routes"**
4. Click **"Add Route"**:
   ```
   Destination: 192.168.1.0/24
   Via: <your-windows-zerotier-ip>
   ```
5. Click **Submit**

**To find Windows ZeroTier IP**: Open Command Prompt on Windows:
```cmd
ipconfig | findstr "ZeroTier"
```

---

### Step 2: Install ZeroTier on Mac

```bash
# Install
brew install zerotier-one

# Join your network
sudo zerotier-cli join <your-network-id>
```

Then authorize your Mac in ZeroTier Central (https://my.zerotier.com)

---

### Step 3: Test Connection

```bash
# Run test script
./test-zerotier-gateway.sh

# If successful, access VDO.ninja:
open "https://192.168.1.24:8443/?director=r58studio"
```

---

## Expected Results

✅ **Latency**: 10-50ms (vs 100-200ms with TURN)  
✅ **Connection**: Direct WebRTC (no relay)  
✅ **Cost**: Free (no TURN bandwidth)  
✅ **Performance**: As if you're on local network

---

## Troubleshooting

### Can't ping R58 (192.168.1.24)

**Check route in ZeroTier Central**:
- Verify: `192.168.1.0/24 via <windows-ip>`
- Make sure it's not disabled

**Enable IP forwarding on Windows** (run as Administrator):
```cmd
netsh interface ipv4 set interface "ZeroTier One" forwarding=enabled
netsh interface ipv4 set interface "Ethernet" forwarding=enabled
```

---

## URLs to Test

Once connected:

**Director View**:
```
https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443
```

**Camera 1**:
```
https://192.168.1.24:8443/?view=r58-cam1&room=r58studio&wss=192.168.1.24:8443
```

**Mixer**:
```
https://192.168.1.24:8443/mixer?push=MIXOUT&room=r58studio&wss=192.168.1.24:8443
```

---

## Full Guide

See `ZEROTIER_GATEWAY_SETUP.md` for complete documentation.

---

**This solves your WebRTC latency problem!** 🎉


