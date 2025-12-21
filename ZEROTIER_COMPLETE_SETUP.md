# Complete ZeroTier Setup - Final Steps

**Network ID**: `8d1c312afa48ac9f`  
**R58 Status**: ✅ Joined network (waiting for authorization)

---

## What's Done

- ✅ ZeroTier installed on R58
- ✅ ZeroTier installed on your Mac
- ✅ R58 joined network `8d1c312afa48ac9f`
- ⏳ Awaiting authorization in ZeroTier dashboard

---

## Complete These Steps

### Step 1: Authorize R58 in ZeroTier Dashboard

1. **Open**: https://my.zerotier.com/
2. **Click** on your network (`8d1c312afa48ac9f`)
3. **Scroll** to "Members" section
4. **Find** the R58 device:
   - Address: `3ebbb67a22`
   - Name: (will show as random string initially)
5. **Check** the "Auth" checkbox ✅
6. **Optional**: Give it a name like "R58-Studio"
7. **Note** the assigned IP address (e.g., `10.147.17.x`)

### Step 2: Join Your Mac to the Network

**Option A - Via GUI** (Recommended):
1. Open **ZeroTier One** from Applications or menu bar
2. Click **"Join Network..."**
3. Enter network ID: `8d1c312afa48ac9f`
4. Click **"Join"**

**Option B - Via Terminal**:
```bash
sudo zerotier-cli join 8d1c312afa48ac9f
# Enter your Mac password when prompted
```

### Step 3: Authorize Your Mac

1. Go back to https://my.zerotier.com/
2. Your Mac should now appear in "Members"
3. **Check** the "Auth" checkbox ✅
4. **Note** your Mac's IP address

### Step 4: Test SSH via ZeroTier

Once both devices are authorized:

```bash
# Get R58's ZeroTier IP from the dashboard (e.g., 10.147.17.123)
ssh linaro@<R58_ZEROTIER_IP>
# Password: linaro
```

**Example**:
```bash
ssh linaro@10.147.17.123
```

If this works, you have backup access! ✅

---

## Verification Commands

### Check ZeroTier Status on Mac
```bash
zerotier-cli listnetworks
```

Should show:
```
200 listnetworks 8d1c312afa48ac9f <name> <mac> OK PRIVATE zt0 <your-ip>
```

### Check ZeroTier Status on R58
```bash
./connect-r58.sh "sudo zerotier-cli listnetworks"
```

Should show similar output with R58's IP.

### Test Connectivity
```bash
# Ping R58 from Mac
ping <R58_ZEROTIER_IP>

# SSH to R58 from Mac
ssh linaro@<R58_ZEROTIER_IP>
```

---

## Next Steps After ZeroTier Works

Once SSH via ZeroTier is verified:

### 1. Run WiFi AP Setup
```bash
scp scripts/setup-wifi-ap.sh linaro@<R58_ZEROTIER_IP>:/tmp/
ssh linaro@<R58_ZEROTIER_IP>
sudo bash /tmp/setup-wifi-ap.sh
```

### 2. Continue with Phase 1
See `DIRECT_ACCESS_IMPLEMENTATION.md` for the complete deployment guide.

---

## Troubleshooting

### R58 not appearing in Members
- Wait 1-2 minutes for device to register
- Check R58 ZeroTier service: `./connect-r58.sh "sudo systemctl status zerotier-one"`
- Check R58 logs: `./connect-r58.sh "sudo journalctl -u zerotier-one -n 50"`

### Mac not appearing in Members
- Check ZeroTier is running: `zerotier-cli info`
- Try rejoining: `sudo zerotier-cli leave 8d1c312afa48ac9f && sudo zerotier-cli join 8d1c312afa48ac9f`

### Can't SSH via ZeroTier
- Verify both devices show "OK" status in dashboard
- Check both devices are authorized (checkbox checked)
- Verify firewall isn't blocking SSH on R58
- Try ping first: `ping <R58_ZEROTIER_IP>`

---

## Summary

**Current Status**:
- R58: Joined network, waiting for authorization
- Mac: Needs to join network and be authorized

**Your Actions**:
1. Go to https://my.zerotier.com/
2. Authorize R58 (address: `3ebbb67a22`)
3. Join Mac to network (via GUI or terminal)
4. Authorize Mac
5. Test SSH: `ssh linaro@<R58_ZEROTIER_IP>`

**Once working**: You have permanent backup access to R58! 🎉

