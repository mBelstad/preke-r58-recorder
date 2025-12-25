# VDO.ninja Realization - It SHOULD Work Over Internet

**Date:** December 25, 2025  
**Status:** Investigating why it's not working

---

## 💡 Key Realization

**raspberry.ninja IS designed for internet streaming!**

From the documentation:
> "Achieve very low streaming latency **over the Internet or a LAN**"

This means the issue is **NOT architectural** - it's a **configuration problem**.

---

## ✅ What IS Working

### Signaling Server Logs Show Success:
```
[2025-12-25T00:16:52.752Z] Notified viewer 9231bcec about publisher: r58-cam2
[2025-12-25T00:16:52.753Z] Notified viewer 9231bcec about publisher: r58-cam3
[2025-12-25T00:16:52.753Z] Notified viewer 9231bcec about publisher: r58-cam1
[2025-12-25T00:16:52.753Z] Publisher seeding: r58-cam3
[2025-12-25T00:16:52.755Z] Publisher seeding: r58-cam1
[2025-12-25T00:16:52.759Z] Publisher seeding: r58-cam2
[2025-12-25T00:23:15.324Z] Play request for: r58-cam1fc7e43
```

**This proves:**
1. ✅ Publishers are connected to signaling server
2. ✅ Browser viewers are connected to signaling server  
3. ✅ Signaling messages are being exchanged
4. ✅ Browser is requesting to play the streams

---

## ❌ What's NOT Working

**WebRTC media connection fails after signaling succeeds.**

The browser and publishers complete the signaling handshake, but the actual video/audio media stream doesn't flow.

---

## 🔍 Possible Root Causes

### 1. **ICE Candidate Exchange Failure**
- Publishers might be advertising local IP addresses (192.168.x.x)
- Browser can't reach those IPs from the internet
- **Solution:** Publishers need to know their public IP or use TURN

### 2. **TURN Server Not Working**
- Cloudflare TURN credentials might be invalid
- TURN server might not be reachable from R58
- **Solution:** Test TURN connectivity, try different TURN server

### 3. **Browser Not Using TURN**
- Publishers are configured with `--ice-transport-policy relay`
- But browser might still be trying direct connection
- **Solution:** Browser also needs to be forced to use TURN

### 4. **NAT Traversal Issue**
- R58 is behind NAT (local network)
- Browser is on internet
- Without proper STUN/TURN, they can't find each other
- **Solution:** Configure NAT traversal properly

### 5. **FRP WebRTC Incompatibility**
- Even though signaling works through FRP (TCP)
- WebRTC media might need special handling
- **Solution:** May need to expose R58's public IP to publishers

---

## 🧪 What Needs Testing

### Test 1: Verify TURN Server Connectivity
```bash
# From R58, test if Cloudflare TURN is reachable
curl -v https://turn.cloudflare.com:5349
```

### Test 2: Check ICE Candidates Being Generated
- Look at publisher logs for ICE candidate types
- Should see "relay" candidates if TURN is working
- Should NOT only see "host" candidates (local IPs)

### Test 3: Force Browser to Use TURN
- Add `&relay` parameter to VDO.ninja URL
- This forces browser to also use relay-only mode
- Both sides need to be configured for relay

### Test 4: Test on Public VDO.ninja
- Try publishing to public `vdo.ninja` (not self-hosted)
- If it works there, the issue is with our self-hosted setup
- If it fails there too, the issue is with R58's network/TURN config

### Test 5: Check Publisher's Advertised IP
- Publishers might be advertising `127.0.0.1` or `192.168.1.24`
- Need to advertise the VPS public IP (`65.109.32.111`)
- May need `--external-ip` parameter

---

## 📋 Next Steps

1. **Test TURN connectivity** from R58
2. **Check what ICE candidates** publishers are generating
3. **Try forcing browser to relay mode** with `&relay` parameter
4. **Research if raspberry.ninja has NAT configuration** options
5. **Consider if publishers need to know their public IP**

---

## 🎯 The Real Question

**How do other people use raspberry.ninja over the internet?**

They must either:
1. Have R58 directly on public IP (no NAT)
2. Use port forwarding for WebRTC ports
3. Use TURN server correctly
4. Use VPN (ZeroTier/Tailscale)
5. Have some configuration we're missing

**We need to find documentation or examples of raspberry.ninja working through NAT/firewall.**

---

## 💭 Hypothesis

The issue might be that **publishers need to advertise the VPS IP** instead of their local IP.

With MediaMTX, we configured:
```yaml
webrtcICEHostNAT1To1IPs:
  - 65.109.32.111
```

**Maybe raspberry.ninja needs similar configuration?**

Let me search for `--external-ip` or similar parameters in publish.py...

