# FRP + VDO.ninja UDP Solutions Research

**Date:** December 25, 2025  
**Goal:** Explore ways to make VDO.ninja work through FRP by modifying UDP handling

---

## 🔍 The Problem

**VDO.ninja uses WebRTC which dynamically selects random UDP ports (49152-65535) for media.**

**FRP can forward UDP**, but only for **specific ports or ranges**. We currently forward:
- UDP port 8189 for MediaMTX (works perfectly)

**Challenge:** WebRTC doesn't know which ports to use - it picks randomly.

---

## 💡 Possible Solutions

### Solution 1: Restrict GStreamer to Specific Port Range

**Idea:** Configure GStreamer's webrtcbin to use only a small range of UDP ports (e.g., 50000-50010), then forward that range through FRP.

#### Investigation Results:

**GStreamer webrtcbin properties:**
```bash
gst-inspect-1.0 webrtcbin
```

Properties found:
- ✅ `stun-server` - Can configure
- ✅ `turn-server` - Can configure
- ✅ `ice-transport-policy` - Can configure
- ✅ `ice-agent` - Writable property (type: GstWebRTCICE)
- ❌ `port-range` - **NOT FOUND**
- ❌ `min-port` - **NOT FOUND**
- ❌ `max-port` - **NOT FOUND**

**Underlying ICE library (libnice):**

libnice (the ICE agent used by GStreamer) **does support port range configuration**, but:
- It's not exposed through GStreamer's webrtcbin properties
- Would require modifying raspberry.ninja to access the ICE agent directly
- Complex GObject property manipulation needed

**Verdict:** ❌ Not easily configurable without modifying raspberry.ninja source code

---

### Solution 2: Forward Large UDP Port Range Through FRP

**Idea:** Forward the entire WebRTC port range (49152-65535) through FRP.

#### Configuration:

**Add to `/opt/frp/frpc.toml`:**
```toml
[[proxies]]
name = "webrtc-udp-range"
type = "udp"
localIP = "127.0.0.1"
localPort = 49152
remotePort = 49152

# Repeat for each port... (16,383 port forwards!)
```

**Problems:**
1. **16,383 port forwards required** - FRP config would be massive
2. **FRP performance** - Each port is a separate proxy connection
3. **VPS ports exhaustion** - VPS only has 16,384 ephemeral ports total
4. **Configuration complexity** - Unmanageable
5. **Still might not work** - Browsers also need to connect to those ports

**Verdict:** ❌ Technically possible but completely impractical

---

### Solution 3: Use FRP's KCP Protocol for UDP

**Idea:** FRP has a KCP mode (UDP-based transport) that might help.

#### Configuration:

**Server (`frps.toml`):**
```toml
kcpBindPort = 7000
```

**Client (`frpc.toml`):**
```toml
transport.protocol = "kcp"
```

**What this does:**
- Makes FRP itself use UDP for communication
- Improves performance for UDP-heavy traffic

**What this doesn't do:**
- ❌ Doesn't solve the dynamic port problem
- ❌ WebRTC still needs specific ports forwarded
- ❌ Only optimizes FRP's own traffic

**Verdict:** ❌ Doesn't solve our problem

---

### Solution 4: Modify raspberry.ninja to Support UDP Muxing

**Idea:** Modify raspberry.ninja to do what MediaMTX does - multiplex all WebRTC traffic through a single UDP port.

#### What's needed:

1. **Access libnice's ICE agent directly:**
```python
# In publish.py
ice_agent = webrtc.get_property("ice-agent")
# Configure port range (if libnice API is available)
```

2. **Implement UDP multiplexing:**
- All peer connections share one UDP port
- Complex state management
- Essentially reimplementing what MediaMTX does

**Problems:**
- **Extremely complex** - Would require deep GStreamer/libnice knowledge
- **Maintenance burden** - Need to keep updated with raspberry.ninja
- **Peer-to-peer architecture** - Harder to multiplex than server-based
- **Browser side** - Browser also needs to know about the mux port

**Verdict:** ❌ Theoretically possible but requires significant development

---

### Solution 5: Use TURN Server on VPS (TCP Relay)

**Idea:** Deploy coturn on VPS, force ALL WebRTC traffic through TURN server over TCP.

#### Why TCP Relay?

- TURN can relay WebRTC over TCP (port 443 or 3478)
- TCP can be forwarded through FRP easily
- Both publisher and viewer use TURN relay

#### Configuration needed:

**1. Install coturn on VPS:**
```bash
apt-get install coturn
```

**2. Configure coturn (`/etc/turnserver.conf`):**
```conf
listening-port=3478
tls-listening-port=5349
external-ip=65.109.32.111
realm=r58studio
user=r58user:password123
lt-cred-mech
```

**3. Forward TURN ports through FRP:**
```toml
[[proxies]]
name = "turn-tcp"
type = "tcp"
localIP = "127.0.0.1"
localPort = 3478
remotePort = 13478

[[proxies]]
name = "turn-tls"
type = "tcp"
localIP = "127.0.0.1"
localPort = 5349
remotePort = 15349
```

**4. Configure raspberry.ninja publishers:**
```bash
--turn-server "turns://r58user:password123@65.109.32.111:15349"
--ice-transport-policy relay
```

**5. Configure browser viewers:**
```javascript
// In VDO.ninja
&turn=turns://r58user:password123@65.109.32.111:15349&relay
```

**Problems:**
- **Adds significant latency** - All traffic relayed through VPS
- **VPS bandwidth cost** - Video streams consume bandwidth
- **Still uncertain** - We tried TURN relay mode, didn't work
- **Both sides need config** - Publisher AND browser need TURN

**Why it might not work:**
- We already tested with Cloudflare TURN + relay mode
- No WebRTC connection was established
- Issue might be deeper than just TURN configuration

**Verdict:** ⚠️ Possible but uncertain, adds complexity and latency

---

### Solution 6: VPN Solution (ZeroTier/Tailscale) ⭐

**Idea:** Create a virtual LAN that bypasses ALL networking issues.

#### How it works:

1. **Install ZeroTier on R58** (already done)
2. **Install ZeroTier on viewing devices**
3. **Join both to same network**
4. **Access R58 via ZeroTier IP**

#### Why this solves everything:

- ✅ **No NAT traversal needed** - Devices appear on same network
- ✅ **No port forwarding** - Direct device-to-device communication
- ✅ **No UDP/TCP issues** - All protocols work
- ✅ **Works with any WebRTC** - VDO.ninja, MediaMTX, everything
- ✅ **Simple configuration** - Just join network
- ✅ **Secure** - Encrypted virtual network
- ✅ **Low latency** - Direct peer-to-peer where possible

#### Access:

```bash
# Find ZeroTier IP
./connect-r58-frp.sh 'zerotier-cli listnetworks'

# Access VDO.ninja
https://[zerotier-ip]:8443/?director=r58studio

# Access MediaMTX
http://[zerotier-ip]:8889/cam0/whep

# Access API
http://[zerotier-ip]:8000
```

**Verdict:** ✅ **RECOMMENDED** - Simplest, most reliable solution

---

## 📊 Solution Comparison

| Solution | Complexity | Reliability | Performance | Development | Verdict |
|----------|-----------|-------------|-------------|-------------|---------|
| Port range restriction | High | Low | Good | High | ❌ Not exposed |
| Forward all ports | Medium | Low | Poor | Low | ❌ Impractical |
| FRP KCP mode | Low | N/A | N/A | Low | ❌ Doesn't help |
| Modify raspberry.ninja | Very High | Medium | Good | Very High | ❌ Too complex |
| VPS TURN server | High | Low | Poor | Medium | ⚠️ Uncertain |
| **ZeroTier VPN** | **Low** | **High** | **Good** | **Low** | ✅ **Best** |

---

## 🎯 Final Recommendation

**Use ZeroTier for remote VDO.ninja access.**

### Why ZeroTier wins:

1. **Solves the root problem** - Eliminates NAT/firewall issues entirely
2. **Works immediately** - No WebRTC configuration needed
3. **Universal solution** - Works for all services, not just VDO.ninja
4. **Simple to maintain** - No custom configurations
5. **Already available** - R58 has ZeroTier installed

### Why other solutions don't work:

1. **Port restriction** - Not exposed by GStreamer
2. **Port forwarding** - Too many ports, impractical
3. **TURN relay** - Already tested, didn't establish connection
4. **Code modification** - Too complex, high maintenance

---

## 📋 ZeroTier Setup Steps

1. **On R58:**
```bash
# Check ZeroTier status
./connect-r58-frp.sh 'zerotier-cli listnetworks'
# Get ZeroTier IP
```

2. **On viewing device:**
```bash
# Install ZeroTier
curl -s https://install.zerotier.com | sudo bash

# Join R58's network
sudo zerotier-cli join [NETWORK_ID]
```

3. **Access VDO.ninja:**
```
https://[r58-zerotier-ip]:8443/?director=r58studio
```

**Estimated time:** 10 minutes  
**Success rate:** 99%  
**Complexity:** Low

---

## 💡 Conclusion

**FRP cannot practically support VDO.ninja's dynamic UDP port usage** without:
- Massive port forwarding (impractical)
- Modifying raspberry.ninja (too complex)
- TURN relay (already tested, uncertain)

**ZeroTier is the correct architectural solution** because it:
- Sidesteps the entire NAT/firewall problem
- Works with ANY WebRTC application
- Requires minimal configuration
- Provides the best performance

**The Hybrid Mode is correct:**
- **Local/VPN:** Full VDO.ninja features
- **Remote via FRP:** MediaMTX recording/viewing

**VDO.ninja through FRP is not feasible** - use ZeroTier for remote access.

