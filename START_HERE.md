# VDO.Ninja Testing - START HERE

**Date**: December 20, 2025  
**Status**: ✅ Ready for Manual Testing

---

## Quick Start (3 Steps)

### Step 1: Find R58 IP

Run the helper script:

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./connect-r58-local.sh
```

**When prompted**:
1. Passphrase: **Press ENTER** (don't type anything)
2. Password: Type **`linaro`**

This will try common IPs and connect when found.

---

### Step 2: Check Services

Once connected to R58, run:

```bash
# Check VDO.Ninja services
sudo systemctl status vdo-ninja ninja-publish-cam1 ninja-publish-cam2

# If not running, start them
sudo systemctl start vdo-ninja ninja-publish-cam1 ninja-publish-cam2

# Exit SSH
exit
```

---

### Step 3: Test in Browser

Replace `XX` with your R58 IP:

```bash
open "https://192.168.68.XX:8443/?director=r58studio"
```

1. Accept SSL warning (click "Advanced" → "Proceed")
2. VDO.Ninja director should load
3. Camera feeds should appear (if HDMI connected)

---

## Test Preke Studio

```bash
# Launch app
open -a "/Applications/Preke Studio.app"
```

**In the app**:
1. Select "Local R58 Device"
2. IP: `192.168.68.XX` (your R58 IP)
3. Room ID: `r58studio`
4. Click "Connect"
5. Go to "Live Mixer" tab

---

## Important Notes

### SSH Authentication
- **Passphrase prompt**: Press ENTER
- **Password prompt**: Type `linaro`

### Common IPs to Try
- 192.168.68.50
- 192.168.68.51
- 192.168.68.55
- 192.168.68.58

### Room ID
Always use: `r58studio` (lowercase)

### SSL Certificate
SSL warning is normal for local network - safe to proceed

---

## Files Created

| File | Purpose |
|------|---------|
| **START_HERE.md** | This file - quick start |
| **MANUAL_TESTING_GUIDE.md** | Complete step-by-step guide |
| **connect-r58-local.sh** | Helper script to find/connect R58 |
| **VDO_NINJA_TEST_REPORT.md** | Detailed test report |
| **TESTING_INSTRUCTIONS.md** | Full testing workflow |

---

## Need Help?

1. **Can't find R58?** → See MANUAL_TESTING_GUIDE.md Step 1
2. **SSH not working?** → Remember: Press ENTER, then type `linaro`
3. **Services not running?** → See MANUAL_TESTING_GUIDE.md "Troubleshooting"
4. **No camera feeds?** → Check if HDMI sources are connected to R58

---

## Testing Checklist

- [ ] Found R58 IP address
- [ ] Connected via SSH (ENTER + linaro)
- [ ] VDO.Ninja services running
- [ ] Director loads in browser
- [ ] Preke Studio connects
- [ ] Camera feeds visible
- [ ] Mixer controls work

---

**Ready to start!** Run: `./connect-r58-local.sh`


