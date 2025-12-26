# Alternatives to frp for WebRTC Tunneling

**Use Case**: Expose WebRTC (TCP signaling + UDP media) from R58 device without kernel TUN support

---

## Quick Comparison

| Solution | UDP Support | Self-Hosted | Cost | Complexity | R58 Compatible |
|----------|-------------|-------------|------|------------|----------------|
| **frp** | ✅ Yes | ✅ Yes | Free | Medium | ✅ Yes |
| **rathole** | ✅ Yes | ✅ Yes | Free | Medium | ✅ Yes |
| **Cloudflare Spectrum** | ✅ Yes | ❌ No | ~$1/GB | Low | ✅ Yes |
| **TURN on VPS** | ✅ Native | ✅ Yes | Free | Low | ✅ Yes |
| **Inlets Pro** | ✅ Yes | ✅ Yes | $20/mo | Low | ✅ Yes |
| **SSH + socat** | ⚠️ Tricky | ✅ Yes | Free | High | ✅ Yes |
| **ngrok** | ❌ No UDP | ❌ No | Paid | Low | ❌ No |
| **Cloudflare Tunnel** | ❌ No UDP | ❌ No | Free | Low | ✅ Already using |

---

## Detailed Analysis

### 1. frp (Current Choice) ⭐ RECOMMENDED

**Pros:**
- ✅ Full TCP and UDP support
- ✅ Free and open source
- ✅ Battle-tested, mature project
- ✅ Good documentation
- ✅ Dashboard for monitoring
- ✅ ARM64 binaries available

**Cons:**
- ❌ Requires VPS setup
- ❌ Manual configuration

**Best for**: Self-hosters who want full control

---

### 2. rathole (Rust Alternative)

```bash
# Similar to frp but written in Rust
# Slightly faster, lower memory usage
```

**Pros:**
- ✅ Faster than frp (Rust performance)
- ✅ Lower memory footprint
- ✅ Full TCP/UDP support
- ✅ Free and open source
- ✅ ARM64 support

**Cons:**
- ❌ Smaller community than frp
- ❌ Less documentation
- ❌ Fewer features than frp

**GitHub**: https://github.com/rapiz1/rathole

**Verdict**: Consider if frp uses too much resources. Similar setup process.

---

### 3. TURN Server on VPS ⭐ SIMPLEST FOR WEBRTC

**This is the native WebRTC solution!**

```bash
# On VPS: Install coturn
apt install coturn

# Configure /etc/turnserver.conf
listening-port=3478
realm=your-domain.com
user=user:password
```

**Pros:**
- ✅ Native WebRTC solution (no proxy needed)
- ✅ Works with existing VDO.ninja/MediaMTX
- ✅ Free (coturn is open source)
- ✅ Simple - just add TURN server URL to apps
- ✅ No client software on R58 needed!

**Cons:**
- ❌ Higher latency than direct UDP proxy (relay overhead)
- ❌ All media flows through TURN (bandwidth cost)

**How it works**:
```
R58 → VDO.ninja/MediaMTX → TURN server (VPS) → Remote PC
                          (relays WebRTC)
```

**Configuration for VDO.ninja**:
```
https://r58:8443/?view=cam1&turn=turn:VPS_IP:3478?user=password
```

**Verdict**: ⭐ **Best if you just want it to work!** No client needed on R58.

---

### 4. Cloudflare Spectrum

**Pros:**
- ✅ Managed service (no VPS management)
- ✅ Cloudflare's global network
- ✅ DDoS protection included
- ✅ TCP and UDP support

**Cons:**
- ❌ Paid: ~$1/GB egress
- ❌ Requires Enterprise plan for UDP
- ❌ Can get expensive with video

**Verdict**: Only if you have Cloudflare Enterprise or budget for bandwidth

---

### 5. Inlets Pro

```bash
# Commercial version of inlets with UDP support
```

**Pros:**
- ✅ Easy setup with CLI
- ✅ TCP and UDP tunnels
- ✅ Automatic TLS
- ✅ Good documentation

**Cons:**
- ❌ $20/month license
- ❌ Still need your own VPS

**Verdict**: Consider if frp config is too complex

---

### 6. SSH Reverse Tunnel + socat

```bash
# On R58:
ssh -R 8889:localhost:8889 user@VPS  # TCP only

# For UDP, need socat relay (complex)
```

**Pros:**
- ✅ Free
- ✅ Uses existing SSH

**Cons:**
- ❌ UDP tunneling is very hacky
- ❌ Unreliable for media
- ❌ Complex to maintain

**Verdict**: Not recommended for WebRTC

---

## My Recommendations

### For Your Use Case (VDO.ninja + MediaMTX + WebRTC):

#### Option A: TURN Server Only (Simplest) 🥇

**If you just want remote viewing to work:**

1. Install coturn on your VPS
2. Configure TURN credentials
3. Add `&turn=` parameter to VDO.ninja URLs
4. Done - no changes to R58 needed!

**Latency**: ~100-150ms (acceptable for viewing)

#### Option B: frp (Lowest Latency) 🥈

**If you need <80ms latency:**

1. Install frps on VPS
2. Install frpc on R58
3. Configure MediaMTX with NAT1To1
4. Direct WebRTC with VPS as advertised IP

**Latency**: ~40-80ms

#### Option C: rathole (If frp is too heavy) 🥉

Same as frp but uses less resources. Consider if R58 is resource-constrained.

---

## Decision Matrix

| Your Priority | Best Choice |
|---------------|-------------|
| **Simplest setup** | TURN server (coturn) |
| **Lowest latency** | frp / rathole |
| **No VPS management** | Cloudflare Spectrum (paid) |
| **Already have TURN** | Use existing TURN! |
| **Budget conscious** | TURN or frp (both free) |

---

## What You Already Have

You mentioned Cloudflare TURN is already configured. If so:

```
You might not need frp at all!
```

Check if adding `&turn=cloudflare-turn-url` to your VDO.ninja URLs already enables remote viewing. The latency will be ~100-150ms but it works without any additional setup.

---

## Final Recommendation

1. **First**: Test if your existing Cloudflare TURN setup works for remote viewing
2. **If latency is acceptable**: Keep using TURN (simplest)
3. **If you need lower latency**: Implement frp with MediaMTX NAT1To1 config

Would you like me to:
- A) Help test if existing TURN setup works for remote viewing?
- B) Proceed with frp implementation for lowest latency?
- C) Set up coturn on your VPS as an alternative?


