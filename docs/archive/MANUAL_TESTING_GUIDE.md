# VDO.Ninja Manual Testing Guide

**Date**: December 20, 2025  
**Status**: Ready for Manual Testing

---

## Important: SSH Password Authentication

**Issue**: SSH keys require passphrase, but we don't have it.  
**Solution**: Press ENTER when asked for passphrase, then enter password: `linaro`

---

## Step-by-Step Testing Instructions

### Step 1: Find R58 IP Address

Open a new terminal and run:

```bash
# Try common IPs on your network
for ip in 192.168.68.{50..60}; do
  echo "Testing $ip..."
  ssh linaro@$ip
  # When prompted for passphrase: Press ENTER
  # When prompted for password: Type "linaro"
  # If connected, run: hostname
  # Then: exit
done
```

**Or check your router**:
1. Open: http://192.168.68.1
2. Find "Connected Devices" or "DHCP Clients"
3. Look for device named: r58, rock64, orangepi, or rk3588

---

### Step 2: Connect to R58 and Check Services

Once you have the IP (let's say it's `192.168.68.XX`):

```bash
# Connect to R58
ssh linaro@192.168.68.XX
# Press ENTER at passphrase prompt
# Type "linaro" at password prompt

# Once connected, check VDO.Ninja server
sudo systemctl status vdo-ninja

# Check camera publishers
sudo systemctl status ninja-publish-cam1
sudo systemctl status ninja-publish-cam2

# If not running, start them
sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2

# Check logs
sudo journalctl -u vdo-ninja -n 20
sudo journalctl -u ninja-publish-cam1 -n 20

# Exit SSH
exit
```

**Expected Output**:
- vdo-ninja: `active (running)`
- ninja-publish-cam1: `active (running)`
- ninja-publish-cam2: `active (running)`

---

### Step 3: Test VDO.Ninja in Browser

```bash
# Replace XX with your R58 IP
open "https://192.168.68.XX:8443/?director=r58studio"
```

**In Browser**:
1. You'll see SSL certificate warning
2. Click "Advanced"
3. Click "Proceed to 192.168.68.XX (unsafe)"
4. VDO.Ninja director interface should load
5. Look for camera feeds (r58-cam1, r58-cam2)

**Expected Result**:
- Director interface loads
- 2 camera feeds visible (if HDMI sources connected)
- Audio/video controls available

---

### Step 4: Test Preke Studio

```bash
# Launch Preke Studio
open -a "/Applications/Preke Studio.app"
```

**In Preke Studio**:
1. Select "Local R58 Device"
2. Enter IP: `192.168.68.XX` (your R58 IP)
3. Enter Room ID: `r58studio`
4. Click "Connect"
5. Go to "Live Mixer" tab
6. Verify director interface loads
7. Check camera feeds appear

**Expected Result**:
- Connection successful
- Live Mixer tab shows VDO.Ninja director
- Camera feeds visible
- Can toggle Director/Mixer view

---

### Step 5: Test Camera Feeds

**In Director Interface** (browser or Preke Studio):

1. **Add Camera to Mix**:
   - Click on a camera feed
   - Click "Add to Scene" or similar
   - Camera should appear in mixer output

2. **Test Audio**:
   - Click audio icon on camera
   - Adjust volume slider
   - Mute/unmute

3. **Test Video Quality**:
   - Right-click on feed
   - Check resolution and bitrate
   - Should show 1080p @ 30fps

4. **Toggle Views**:
   - In Preke Studio: Click "Director" / "Mixer" toggle
   - Director: Shows all sources
   - Mixer: Shows mixed output

---

## Testing Checklist

### ✅ Phase 1: R58 Connection
- [ ] Found R58 IP address
- [ ] SSH connection works (Enter + linaro password)
- [ ] vdo-ninja service is running
- [ ] ninja-publish-cam1 is running
- [ ] ninja-publish-cam2 is running

### ✅ Phase 2: Browser Test
- [ ] Opened https://R58_IP:8443/?director=r58studio
- [ ] Accepted SSL certificate
- [ ] Director interface loaded
- [ ] Camera feeds visible (if HDMI connected)

### ✅ Phase 3: Preke Studio
- [ ] Preke Studio launched
- [ ] Connected to Local R58
- [ ] Live Mixer tab opened
- [ ] Director interface visible
- [ ] Camera feeds working

### ✅ Phase 4: Functionality
- [ ] Can add cameras to mix
- [ ] Audio controls work
- [ ] Video quality is good
- [ ] Director/Mixer toggle works
- [ ] No lag or stuttering

---

## Troubleshooting

### Can't Find R58 IP

**Try these IPs manually**:
```bash
ssh linaro@192.168.68.50  # Press ENTER, then type: linaro
ssh linaro@192.168.68.51
ssh linaro@192.168.68.55
ssh linaro@192.168.68.58
```

**Or check router**: http://192.168.68.1

### SSH Connection Issues

**Problem**: Asked for passphrase  
**Solution**: Press ENTER (don't type anything)

**Problem**: Permission denied  
**Solution**: Make sure you typed password correctly: `linaro`

### Services Not Running

```bash
# SSH to R58 first
ssh linaro@192.168.68.XX

# Start services
sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2

# Enable on boot
sudo systemctl enable vdo-ninja ninja-publish-cam1 ninja-publish-cam2

# Check logs if still failing
sudo journalctl -u vdo-ninja -n 50
```

### No Camera Feeds in Director

**Possible causes**:
1. HDMI sources not connected
2. Camera publishers not running
3. Wrong stream IDs

**Check**:
```bash
# SSH to R58
ssh linaro@192.168.68.XX

# Check HDMI devices
ls -l /dev/video60 /dev/video11

# Check publisher logs
sudo journalctl -u ninja-publish-cam1 -f

# Restart publishers
sudo systemctl restart ninja-publish-cam1 ninja-publish-cam2
```

### SSL Certificate Warning

This is **normal** for self-signed certificates on local network.

**Solution**:
1. Click "Advanced"
2. Click "Proceed to [IP] (unsafe)"
3. Safe for local network use

### Preke Studio Won't Connect

**Check**:
1. IP address is correct
2. Room ID is: `r58studio` (lowercase)
3. VDO.Ninja works in browser first
4. Try "Preke Cloud" instead of "Local R58"

---

## Quick Commands Reference

```bash
# SSH to R58 (press ENTER at passphrase, then type: linaro)
ssh linaro@192.168.68.XX

# Check all services
sudo systemctl status vdo-ninja ninja-publish-cam1 ninja-publish-cam2

# Start all services
sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2

# View logs
sudo journalctl -u vdo-ninja -n 20
sudo journalctl -u ninja-publish-cam1 -f

# Open director in browser
open "https://192.168.68.XX:8443/?director=r58studio"

# Launch Preke Studio
open -a "/Applications/Preke Studio.app"
```

---

## Expected Results Summary

| Component | Expected State |
|-----------|---------------|
| R58 SSH | Accessible with password: linaro |
| VDO.Ninja Server | Active on port 8443 |
| Camera Publishers | 2 active (cam1, cam2) |
| Director Interface | Shows camera feeds |
| Preke Studio | Connects and displays mixer |
| WebRTC Latency | < 500ms |
| Video Quality | 1080p @ 30fps |

---

## Success Criteria

✅ **Minimum Success**:
- Can SSH to R58
- VDO.Ninja director loads in browser
- Preke Studio connects to R58

✅ **Full Success**:
- All above +
- Camera feeds visible in director
- Can mix cameras in Preke Studio
- Audio/video controls work
- No performance issues

---

## Notes

- **SSH Password**: Always use `linaro` (press ENTER at passphrase prompt first)
- **Room ID**: Always use `r58studio` (lowercase)
- **SSL Warning**: Normal for local network, safe to proceed
- **Camera Feeds**: Only visible if HDMI sources are connected to R58

---

**Ready to Test!** Follow steps 1-5 above in order.


