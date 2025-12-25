# R58 Device Search Results

**Date**: December 20, 2025  
**Your Network**: 192.168.68.53/24

---

## Search Results

### Network Scan Complete

**Hostnames Tested** (not found):
- r58.local
- rock64.local
- orangepi.local
- rk3588.local

**SSH Services Found**:
- ✅ 192.168.68.55 (requires password)

---

## Next Steps to Find R58

### Option 1: Test 192.168.68.55 with Password

This device has SSH but requires authentication:

```bash
# Try with linaro user and password
ssh linaro@192.168.68.55

# Or try with rock user
ssh rock@192.168.68.55

# Default passwords to try:
# - linaro
# - rock
# - orangepi
```

### Option 2: Check Your Router

1. Open router admin page (usually http://192.168.68.1)
2. Look for "DHCP Clients" or "Connected Devices"
3. Find device named:
   - r58
   - rock64
   - orangepi
   - rk3588
   - Or any device with MAC starting with: 02:, 12:, 22:

### Option 3: Physical Access to R58

If you have physical access:

1. Connect monitor and keyboard to R58
2. Login locally
3. Run: `ip addr show`
4. Note the IP address
5. Update configuration files

### Option 4: Use Cloudflare Tunnel

If R58 is accessible via Cloudflare:

```bash
# Test recorder API
curl https://recorder.itagenten.no/api/status

# Test VDO.Ninja
open "https://vdo.itagenten.no/?director=r58studio"
```

---

## Once You Have the IP

### Update Configuration

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"

# Set the IP
export R58_IP="YOUR_R58_IP_HERE"

# Update all scripts
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-director.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-cam0.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-cam2.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-mixer.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" test-mac-app.sh
```

### Test Connectivity

```bash
# Test ping
ping -c 3 $R58_IP

# Test SSH
ssh linaro@$R58_IP "hostname"

# Check VDO.Ninja service
ssh linaro@$R58_IP "sudo systemctl status vdo-ninja"
```

### Start Testing

```bash
# Open browser to VDO.Ninja
open "https://$R58_IP:8443/?director=r58studio"

# Or launch Preke Studio
open -a "/Applications/Preke Studio.app"
# Then connect to: $R58_IP with room: r58studio
```

---

## Quick Test Commands

Once R58 IP is known:

```bash
# Set IP variable
export R58_IP="192.168.68.XX"

# Test services
ssh linaro@$R58_IP "sudo systemctl status vdo-ninja ninja-publish-cam1 ninja-publish-cam2"

# Start services if needed
ssh linaro@$R58_IP "sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2"

# Open director in browser
open "https://$R58_IP:8443/?director=r58studio"
```

---

## Alternative: Test Without Finding R58

If R58 is accessible via Cloudflare Tunnel, you can test immediately:

### Test VDO.Ninja via Tunnel

```bash
# Check if accessible
curl -I https://vdo.itagenten.no 2>&1 | head -5

# Open director
open "https://vdo.itagenten.no/?director=r58studio"
```

### Test Preke Studio with Cloud

1. Launch: `open -a "/Applications/Preke Studio.app"`
2. Select: "Preke Cloud"
3. Room ID: `r58studio`
4. Click: "Connect"

---

## Summary

**Status**: R58 device not automatically found  
**Possible Device**: 192.168.68.55 (requires password)  
**Next Action**: Try SSH to 192.168.68.55 or check router DHCP list

**Alternative**: Test via Cloudflare Tunnel if available


