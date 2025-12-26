# VDO.ninja Practical Solutions - Making It Work

**Date:** December 25, 2025  
**Goal:** Get VDO.ninja working remotely with raspberry.ninja publishers

---

## ✅ What We Know Works

1. **Signaling is perfect** - Browser and publishers communicate through FRP
2. **Publishers are configured correctly** - Stream IDs, TURN server, relay mode
3. **Local network would work** - If browser was on same network as R58

## ❌ What's Broken

**WebRTC media connection fails** - After signaling succeeds, no video flows

---

## 🎯 Three Practical Solutions

### Solution 1: Use Public VDO.ninja (Test First) ⭐ RECOMMENDED TEST

**Try publishing to the public `vdo.ninja` servers instead of self-hosted.**

```bash
# Stop current publishers
sudo systemctl stop ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3

# Test with public VDO.ninja
/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --server wss://wss.vdo.ninja:443 \
    --room r58studio-test \
    --streamid r58-cam1-public \
    --v4l2 /dev/video60 \
    --noaudio --h264 --bitrate 8000 \
    --width 1920 --height 1080 --framerate 30 --nored
```

**Then view at:** `https://vdo.ninja/?view=r58-cam1-public&room=r58studio-test`

**Why this works:**
- Public VDO.ninja has professional TURN infrastructure
- Their servers handle NAT traversal properly
- If this works, we know the issue is our self-hosted setup

---

### Solution 2: ZeroTier VPN (Easiest Long-term) ⭐ RECOMMENDED

**Create a virtual LAN between R58 and your viewing devices.**

**Steps:**
1. Install ZeroTier on R58 (already done?)
2. Install ZeroTier on viewing computer
3. Join both to same network
4. Access VDO.ninja using R58's ZeroTier IP

**Why this works:**
- Makes remote devices appear on same LAN
- No NAT traversal needed
- VDO.ninja works as if local
- Simple, reliable, secure

**Access:** `https://[zerotier-ip]:8443/?director=r58studio`

---

### Solution 3: Deploy TURN Server on VPS

**Run your own TURN server on the VPS (65.109.32.111).**

**Steps:**
1. Install coturn on VPS
2. Configure with proper credentials
3. Update publishers to use VPS TURN
4. Update browser to use VPS TURN

**Why this might work:**
- TURN server on public IP
- Can relay traffic between R58 and browser
- Both sides use same TURN server

**Complexity:** High  
**Success rate:** Uncertain

---

## 🧪 Immediate Test Plan

### Step 1: Test with Public VDO.ninja (5 minutes)

This will tell us if the issue is:
- ❌ Our self-hosted VDO.ninja setup
- ❌ Our TURN configuration
- ✅ Or something else entirely

```bash
# SSH to R58
./connect-r58-frp.sh

# Stop services
sudo systemctl stop ninja-publish-cam1

# Test with public server
/opt/preke-r58-recorder/venv/bin/python3 /opt/raspberry_ninja/publish.py \
    --server wss://wss.vdo.ninja:443 \
    --room r58test$(date +%s) \
    --streamid testcam \
    --v4l2 /dev/video60 \
    --noaudio --h264 --bitrate 2500 \
    --width 1280 --height 720 --framerate 30 --nored
```

Watch the output for the viewing URL, then test in browser.

---

### Step 2: If Public Works, Fix Self-Hosted

**The issue is our VDO.ninja signaling server or TURN config.**

Possible fixes:
1. Configure self-hosted VDO.ninja to use public TURN servers
2. Set up proper TURN server on VPS
3. Configure ICE server settings in vdo-server.js

---

### Step 3: If Public Fails Too, Use ZeroTier

**The issue is R58's network/NAT configuration.**

ZeroTier bypasses all these issues by creating a virtual LAN.

---

## 📊 Comparison Table

| Solution | Complexity | Reliability | Latency | Cost |
|----------|-----------|-------------|---------|------|
| Public VDO.ninja | Low | High | Low | Free |
| ZeroTier VPN | Low | High | Low | Free |
| Self-hosted + VPS TURN | High | Medium | Low | VPS cost |
| Current FRP approach | N/A | **Broken** | N/A | N/A |

---

## 🎯 My Recommendation

1. **Test with public VDO.ninja** (5 min) - Diagnostic
2. **If that works:** Set up ZeroTier for production use
3. **If that fails:** Deep dive into R58 network configuration

**ZeroTier is the best long-term solution because:**
- Simple to set up
- Works reliably
- No complex TURN configuration
- VDO.ninja works exactly as designed
- Can also access other R58 services

---

## 💡 Why raspberry.ninja Works for Others

Most raspberry.ninja users either:
1. **Use public VDO.ninja** - Professional TURN infrastructure
2. **Have public IP** - No NAT traversal needed
3. **Use VPN** - ZeroTier, Tailscale, WireGuard
4. **Port forward** - Open WebRTC ports on router
5. **Same LAN** - No internet involved

**We're trying to do something unusual:** Self-hosted VDO.ninja + NAT + FRP proxy

---

## 🔄 Next Action

**Let's test with public VDO.ninja right now.** This 5-minute test will tell us everything we need to know about where the problem actually is.

Shall I run the test?

