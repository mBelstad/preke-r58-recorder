# VDO.Ninja WebRTC Mixer - Test Report

**Date**: December 20, 2025  
**Status**: ⚠️ Network Configuration Required

---

## Test Summary

### Phase 1: Network Connectivity - ❌ BLOCKED

**Issue**: R58 device not reachable at configured IP address (192.168.1.25)

**Your Network**: 192.168.68.52/22 (192.168.68.0 - 192.168.71.255)  
**Configured R58 IP**: 192.168.1.25 (different subnet)

**Visible Hosts on Your Network**:
- 192.168.68.1 (gateway)
- 192.168.68.50
- 192.168.68.51
- 192.168.68.52 (your Mac)

---

## Required Actions

### Option 1: Find R58 on Current Network

The R58 device might have a different IP on your network. Try these methods:

#### Method A: Check Router/DHCP

1. Log into your router (usually http://192.168.68.1)
2. Look for DHCP client list
3. Find device named "r58" or "rock64" or similar
4. Note the IP address

#### Method B: Scan for SSH Services

```bash
# Install nmap if not available
brew install nmap

# Scan for SSH services on your network
nmap -p 22 --open 192.168.68.0/22 | grep -B 4 "open"
```

#### Method C: Try Common Hostnames

```bash
# Try these hostnames
ping -c 2 r58.local
ping -c 2 rock64.local  
ping -c 2 orangepi.local
```

### Option 2: Connect R58 to Your Network

If R58 is on a different network:

1. Connect R58 to your current network (192.168.68.x)
2. R58 should get an IP via DHCP
3. Find the IP using methods above
4. Update configuration files

---

## Once R58 IP is Found

### Step 1: Update Configuration Files

Replace `192.168.1.25` with the correct IP in these files:

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"

# Update launch scripts
sed -i '' 's/192.168.1.25/NEW_IP_HERE/g' launch-director.sh
sed -i '' 's/192.168.1.25/NEW_IP_HERE/g' launch-cam0.sh
sed -i '' 's/192.168.1.25/NEW_IP_HERE/g' launch-cam2.sh
sed -i '' 's/192.168.1.25/NEW_IP_HERE/g' launch-mixer.sh
sed -i '' 's/192.168.1.25/NEW_IP_HERE/g' test-mac-app.sh
```

### Step 2: Test Connectivity

```bash
# Replace NEW_IP with actual R58 IP
export R58_IP="NEW_IP"

# Test ping
ping -c 3 $R58_IP

# Test SSH
ssh linaro@$R58_IP "hostname"
```

### Step 3: Check VDO.Ninja Services

```bash
# Check VDO.Ninja server
ssh linaro@$R58_IP "sudo systemctl status vdo-ninja"

# Check camera publishers
ssh linaro@$R58_IP "sudo systemctl status ninja-publish-cam1 ninja-publish-cam2"

# Start services if needed
ssh linaro@$R58_IP "sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2"
```

### Step 4: Test in Browser

1. Open: `https://$R58_IP:8443/`
2. Accept SSL certificate warning (click "Advanced" → "Proceed")
3. Open Director: `https://$R58_IP:8443/?director=r58studio`
4. Verify camera feeds appear

### Step 5: Test Preke Studio

```bash
# Launch Preke Studio
open -a "/Applications/Preke Studio.app"

# In the app:
# 1. Select "Local R58 Device"
# 2. Enter IP: $R58_IP
# 3. Enter Room ID: r58studio
# 4. Click "Connect"
# 5. Go to "Live Mixer" tab
# 6. Verify director interface loads
```

---

## Alternative: Test via Cloudflare Tunnel

If R58 is accessible via Cloudflare Tunnel, you can test remotely:

### VDO.Ninja via Tunnel

The documentation mentions `vdo.itagenten.no` - try:

```bash
# Test if VDO.Ninja is accessible via tunnel
curl -I https://vdo.itagenten.no 2>&1 | head -5

# If accessible, open in browser
open "https://vdo.itagenten.no/?director=r58studio"
```

### Preke Studio via Cloud

In Preke Studio:
1. Select "Preke Cloud"
2. Enter Room ID: `r58studio`
3. Click "Connect"

---

## Testing Checklist

Once R58 is accessible, complete these tests:

### ✅ Phase 1: Network & Services
- [ ] Ping R58 device
- [ ] SSH to R58
- [ ] Check vdo-ninja service status
- [ ] Check ninja-publish-cam1 status
- [ ] Check ninja-publish-cam2 status
- [ ] Start services if stopped

### ✅ Phase 2: Browser Testing
- [ ] Accept SSL certificate
- [ ] Load VDO.Ninja home page
- [ ] Load Director interface
- [ ] Verify cam1 feed appears
- [ ] Verify cam2 feed appears
- [ ] Test audio controls
- [ ] Test video quality settings

### ✅ Phase 3: Preke Studio Testing
- [ ] Apply bug fixes (if not done)
- [ ] Launch Preke Studio
- [ ] Connect to Local R58
- [ ] Navigate to Live Mixer tab
- [ ] Verify director interface loads
- [ ] Verify camera feeds visible
- [ ] Toggle Director/Mixer view
- [ ] Test adding cameras to mix
- [ ] Test audio mixing
- [ ] Test scene switching

### ✅ Phase 4: Advanced Features
- [ ] Test guest join (second browser)
- [ ] Test remote guest connection
- [ ] Test mixer output view
- [ ] Test individual camera views
- [ ] Test in Electron Capture app

---

## Expected Results

| Component | Expected State |
|-----------|---------------|
| VDO.Ninja Server | Active on port 8443 |
| ninja-publish-cam1 | Active, streaming to r58-cam1 |
| ninja-publish-cam2 | Active, streaming to r58-cam2 |
| Director Interface | Shows 2 camera feeds |
| Preke Studio | Connects and displays mixer |
| WebRTC Connection | Low latency (<500ms) |

---

## Troubleshooting

### Services Not Running

```bash
# Start VDO.Ninja server
ssh linaro@$R58_IP "sudo systemctl start vdo-ninja"

# Start camera publishers
ssh linaro@$R58_IP "sudo systemctl start ninja-publish-cam1 ninja-publish-cam2"

# Enable on boot
ssh linaro@$R58_IP "sudo systemctl enable vdo-ninja ninja-publish-cam1 ninja-publish-cam2"
```

### No Camera Feeds in Director

```bash
# Check logs
ssh linaro@$R58_IP "sudo journalctl -u ninja-publish-cam1 -n 50"

# Verify HDMI sources connected
ssh linaro@$R58_IP "ls -l /dev/video60 /dev/video11"

# Restart publishers
ssh linaro@$R58_IP "sudo systemctl restart ninja-publish-cam1 ninja-publish-cam2"
```

### SSL Certificate Issues

- Click "Advanced" in browser
- Click "Proceed to [IP] (unsafe)"
- This is expected for self-signed certificates on local network

### Preke Studio Connection Failed

```bash
# Verify IP is correct
# Verify Room ID is: r58studio
# Try Cloud connection instead of Local
```

---

## Next Steps

1. **Find R58 IP address** using methods above
2. **Update configuration files** with correct IP
3. **Run connectivity tests** to verify R58 is accessible
4. **Complete testing checklist** in order
5. **Document results** for each phase

---

## Contact Information

**R58 Device**:
- Default User: `linaro`
- Default Password: `linaro`
- SSH Port: 22
- VDO.Ninja Port: 8443
- Room ID: `r58studio`

**VDO.Ninja Streams**:
- cam1: `r58-cam1`
- cam2: `r58-cam2`
- cam3: `r58-cam3`

---

**Test Status**: Waiting for network configuration  
**Blocker**: R58 device IP address unknown  
**Next Action**: Find R58 IP and update configuration
