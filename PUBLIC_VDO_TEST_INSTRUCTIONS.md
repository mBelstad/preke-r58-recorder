# Public VDO.ninja Test - Instructions

**Date:** December 25, 2025  
**Status:** Test in progress

---

## 🧪 Test Setup

**Publisher running on R58:**
- Server: `wss://wss.vdo.ninja:443` (public VDO.ninja)
- Room: `r58publictest`
- Stream ID: `testcam1`
- Camera: `/dev/video60` (HDMI N60)
- Resolution: 1280x720 @ 30fps
- Bitrate: 2500 kbps

**View URL:** `https://vdo.ninja/?view=testcam1&room=r58publictest`

---

## 📋 What to Check in Browser

### ✅ If Video Appears:

**This means:**
- raspberry.ninja CAN work over the internet
- The issue is with our self-hosted VDO.ninja setup
- Public VDO.ninja has proper TURN infrastructure

**Next steps:**
1. Use ZeroTier for local VDO.ninja access
2. OR fix our self-hosted VDO.ninja TURN configuration
3. OR continue using public VDO.ninja for remote access

---

### ❌ If Video Does NOT Appear:

**Check browser console for errors:**
- Press F12 to open developer tools
- Look for WebRTC errors
- Look for ICE connection failures
- Look for TURN server errors

**This could mean:**
- R58's network blocks outgoing WebRTC
- Firewall issues on R58
- Need to configure TURN on R58 side
- May need ZeroTier regardless

---

## 🎯 Expected Outcomes

### Scenario 1: Works with Public VDO.ninja ✅

**Conclusion:** Our self-hosted setup needs fixing

**Solutions:**
1. **Best:** Use ZeroTier for self-hosted VDO.ninja
2. **Alternative:** Fix TURN configuration on self-hosted
3. **Workaround:** Use public VDO.ninja for remote, self-hosted for local

---

### Scenario 2: Fails with Public VDO.ninja ❌

**Conclusion:** R58 network/NAT configuration issue

**Solutions:**
1. **Best:** Use ZeroTier (bypasses all NAT issues)
2. **Alternative:** Configure port forwarding on R58's router
3. **Alternative:** Deploy TURN server on VPS

---

## 📊 Comparison

| Setup | Signaling | Media | Result |
|-------|-----------|-------|--------|
| Self-hosted via FRP | ✅ Works | ❌ Fails | No video |
| Public VDO.ninja | ? Testing | ? Testing | **Check browser** |

---

## 🔍 What We're Learning

This test will tell us:
1. Can raspberry.ninja work from R58 at all?
2. Is the issue our self-hosted VDO.ninja?
3. Or is it R58's network configuration?

---

## 💡 Reminder

**raspberry.ninja IS designed for internet use**, so if this test works, it confirms that:
- The tool works as designed
- Our self-hosted setup needs configuration
- ZeroTier or proper TURN setup will solve it

---

## 📝 Test Results

**Please check the browser and report:**
1. Do you see video? (Yes/No)
2. Any errors in console? (Copy/paste)
3. Does the page show "connecting" or any status?

This will determine our next steps!

