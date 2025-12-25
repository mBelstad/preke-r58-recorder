# VDO.Ninja Testing Instructions

**Date**: December 20, 2025  
**Status**: Ready for Manual Testing (R58 IP Required)

---

## Current Situation

✅ **Network scan completed**  
✅ **Test scripts created**  
✅ **Documentation prepared**  
⚠️ **R58 device IP address needed**

**Your Network**: 192.168.68.53  
**Possible R58**: 192.168.68.55 (requires password)  
**Configured IP**: 192.168.1.25 (incorrect - different subnet)

---

## Quick Start: Find R58 IP

### Method 1: Try 192.168.68.55

```bash
# Try SSH with password
ssh linaro@192.168.68.55
# Password: linaro

# If that works, check for VDO.Ninja
sudo systemctl status vdo-ninja
```

### Method 2: Check Router

1. Open: http://192.168.68.1
2. Find "DHCP Clients" or "Connected Devices"
3. Look for: r58, rock64, orangepi, or rk3588

### Method 3: Use Cloudflare Tunnel

If R58 is accessible remotely:

```bash
# Test VDO.Ninja
open "https://vdo.itagenten.no/?director=r58studio"

# Or test recorder API
curl https://recorder.itagenten.no/api/status
```

---

## Complete Testing Workflow

### Step 1: Set R58 IP

```bash
# Once you know the IP, set it
export R58_IP="192.168.68.XX"  # Replace XX with actual IP

# Verify connectivity
ping -c 3 $R58_IP
ssh linaro@$R58_IP "hostname"
```

### Step 2: Update Configuration

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"

# Update all launch scripts
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-director.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-cam0.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-cam2.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" launch-mixer.sh
sed -i '' "s/192.168.1.25/$R58_IP/g" test-mac-app.sh
```

### Step 3: Check R58 Services

```bash
# Check VDO.Ninja server
ssh linaro@$R58_IP "sudo systemctl status vdo-ninja"

# Check camera publishers
ssh linaro@$R58_IP "sudo systemctl status ninja-publish-cam1 ninja-publish-cam2"

# Start services if needed
ssh linaro@$R58_IP "sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2"

# View logs
ssh linaro@$R58_IP "sudo journalctl -u vdo-ninja -n 20"
ssh linaro@$R58_IP "sudo journalctl -u ninja-publish-cam1 -n 20"
```

### Step 4: Test in Browser

```bash
# Open VDO.Ninja Director
open "https://$R58_IP:8443/?director=r58studio"
```

**In browser**:
1. Accept SSL certificate warning (click "Advanced" → "Proceed")
2. Verify VDO.Ninja director interface loads
3. Check if camera feeds (cam1, cam2) appear
4. Test audio/video controls

### Step 5: Test Preke Studio

```bash
# Launch Preke Studio
open -a "/Applications/Preke Studio.app"
```

**In Preke Studio**:
1. Select "Local R58 Device"
2. Enter IP: `$R58_IP`
3. Enter Room ID: `r58studio`
4. Click "Connect"
5. Go to "Live Mixer" tab
6. Verify director interface loads
7. Check camera feeds appear
8. Toggle "Director" / "Mixer" view
9. Test adding cameras to mix

---

## Testing Checklist

### ✅ Phase 1: Network & Services
- [ ] Find R58 IP address
- [ ] Update configuration files
- [ ] Ping R58 device successfully
- [ ] SSH to R58 successfully
- [ ] vdo-ninja service is active
- [ ] ninja-publish-cam1 is active
- [ ] ninja-publish-cam2 is active

### ✅ Phase 2: Browser Testing
- [ ] Accept SSL certificate
- [ ] VDO.Ninja home page loads
- [ ] Director interface loads
- [ ] cam1 feed appears
- [ ] cam2 feed appears
- [ ] Audio controls work
- [ ] Video quality settings work

### ✅ Phase 3: Preke Studio
- [ ] Preke Studio launches
- [ ] Connects to Local R58
- [ ] Live Mixer tab loads
- [ ] Director interface displays
- [ ] Camera feeds visible
- [ ] Director/Mixer toggle works
- [ ] Can add cameras to mix
- [ ] Audio mixing works

### ✅ Phase 4: Advanced (Optional)
- [ ] Guest join works (second browser)
- [ ] Remote guest connection
- [ ] Mixer output view
- [ ] Individual camera views
- [ ] Electron Capture app

---

## Troubleshooting

### Can't Find R58 IP

```bash
# Run the finder script
./find-r58.sh

# Or check router DHCP list
# Or connect monitor to R58 and run: ip addr show
```

### Services Not Running

```bash
# Start all services
ssh linaro@$R58_IP "sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2"

# Enable on boot
ssh linaro@$R58_IP "sudo systemctl enable vdo-ninja ninja-publish-cam1 ninja-publish-cam2"
```

### No Camera Feeds

```bash
# Check HDMI sources are connected
ssh linaro@$R58_IP "ls -l /dev/video60 /dev/video11"

# Check publisher logs
ssh linaro@$R58_IP "sudo journalctl -u ninja-publish-cam1 -f"

# Restart publishers
ssh linaro@$R58_IP "sudo systemctl restart ninja-publish-cam1 ninja-publish-cam2"
```

### SSL Certificate Warning

- This is expected for self-signed certificates
- Click "Advanced" → "Proceed to [IP] (unsafe)"
- Safe for local network use

### Preke Studio Won't Connect

- Verify IP is correct
- Verify Room ID is: `r58studio`
- Try "Preke Cloud" instead of "Local R58"
- Check if VDO.Ninja works in browser first

---

## Alternative: Test via Cloudflare Tunnel

If you can't find R58 on local network, try via tunnel:

### Browser Test

```bash
# Open VDO.Ninja via tunnel
open "https://vdo.itagenten.no/?director=r58studio"
```

### Preke Studio Test

1. Launch Preke Studio
2. Select "Preke Cloud"
3. Room ID: `r58studio`
4. Click "Connect"

---

## Expected Results

| Test | Expected Result |
|------|----------------|
| VDO.Ninja Server | Active on port 8443 |
| Camera Publishers | 2 active (cam1, cam2) |
| Director Interface | Shows 2 camera feeds |
| Preke Studio | Connects and displays mixer |
| WebRTC Latency | < 500ms |
| Video Quality | 1080p @ 30fps |

---

## Files Created

- `VDO_NINJA_TEST_REPORT.md` - Detailed test report
- `FIND_R58_RESULTS.md` - Network scan results
- `TESTING_INSTRUCTIONS.md` - This file
- `find-r58.sh` - R58 finder script

---

## Next Steps

1. **Find R58 IP** - Try 192.168.68.55 or check router
2. **Update configs** - Replace 192.168.1.25 with actual IP
3. **Test services** - Verify VDO.Ninja and publishers running
4. **Test browser** - Open director interface
5. **Test Preke Studio** - Connect and verify mixer works

---

**Status**: Ready for testing once R58 IP is found  
**Estimated Time**: 15-30 minutes for complete testing  
**Support**: See VDO_NINJA_TEST_REPORT.md for detailed instructions


