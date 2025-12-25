# Can WebRTC Use a Single Static UDP Port?

**Date:** December 25, 2025  
**Question:** Why can MediaMTX use one port but VDO.ninja can't?

---

## 🎯 Short Answer

**Yes, WebRTC CAN use a single static UDP port** - but it requires:
1. **Server-side architecture** (SFU/MCU, not peer-to-peer)
2. **ICE UDP multiplexing support** in the software
3. **Both sides to support it**

**MediaMTX does this. VDO.ninja/raspberry.ninja does not.**

---

## 🔍 Technical Explanation

### How WebRTC Normally Works:

**Traditional WebRTC (peer-to-peer like VDO.ninja):**
```
Peer A ←→ Random UDP Port 49152-65535 ←→ Peer B
       ←→ Random UDP Port 51234-63421 ←→
       (Different port for each connection)
```

**Problems for NAT/firewall:**
- Each peer connection = new random UDP port
- Can't predict which ports to forward
- Need to forward entire range (16,000+ ports)
- Impossible to do through simple proxy like FRP

---

### How MediaMTX Works:

**MediaMTX (Server/SFU architecture):**
```
All Clients ←→ Single UDP Port 8189 ←→ MediaMTX Server
Client 1    ←→         :8189         ←→    
Client 2    ←→         :8189         ←→ [Multiplexes internally]
Client 3    ←→         :8189         ←→
```

**Configuration in MediaMTX:**
```yaml
webrtcICEUDPMuxAddress: :8189  # All WebRTC traffic on this ONE port
webrtcICEHostNAT1To1IPs:
  - 65.109.32.111  # Tell clients to connect to VPS IP
```

**Why this works:**
- ✅ **UDP multiplexing** - All connections share one port
- ✅ **Server architecture** - MediaMTX manages all connections
- ✅ **NAT configuration** - MediaMTX knows about public IP
- ✅ **Easy to forward** - Just forward port 8189 through FRP

---

## 📊 Architecture Comparison

| Feature | MediaMTX | VDO.ninja/raspberry.ninja |
|---------|----------|---------------------------|
| **Architecture** | Server (SFU) | Peer-to-peer (Mesh) |
| **UDP Ports** | Single (8189) | Random per connection |
| **Multiplexing** | Yes (`webrtcICEUDPMuxAddress`) | No |
| **NAT Config** | `webrtcICEHostNAT1To1IPs` | Not exposed |
| **FRP Compatible** | ✅ Yes | ❌ No |

---

## 🤔 Can We Make VDO.ninja Use One Port?

### The Challenge:

**raspberry.ninja uses GStreamer's webrtcbin**, which uses **libnice** as the ICE agent.

**libnice DOES support port restrictions**, but:
- Not exposed through GStreamer webrtcbin properties
- Would need to access ICE agent directly
- Requires modifying raspberry.ninja source code

### What Would Be Needed:

**1. Access the ICE agent in raspberry.ninja:**
```python
# In publish.py
webrtc = pipeline.get_by_name("sendrecv")
ice_agent = webrtc.get_property("ice-agent")

# Configure port range (if exposed)
ice_agent.set_property("min-rtp-port", 50000)
ice_agent.set_property("max-rtp-port", 50010)
```

**2. Configure UDP multiplexing:**
```python
# This would need libnice support
# Not sure if libnice has UDP mux like pion (Go WebRTC library)
```

**3. Tell ICE agent about public IP:**
```python
# Similar to MediaMTX's webrtcICEHostNAT1To1IPs
ice_agent.set_property("nat-1-to-1-ips", ["65.109.32.111"])
```

**4. Forward ports through FRP:**
```toml
[[proxies]]
name = "webrtc-range"
type = "udp"
localIP = "127.0.0.1"
localPort = 50000
remotePort = 50000
# ... repeat for 50001-50010
```

---

## ⚠️ Why This Is Hard

### Technical Challenges:

1. **GStreamer webrtcbin abstraction**
   - Hides low-level ICE agent configuration
   - Not designed for port restrictions
   - Would need to bypass abstraction layer

2. **libnice limitations**
   - Port range restriction exists but may not be well-exposed
   - UDP multiplexing might not be implemented
   - Different from pion (Go) WebRTC which has better mux support

3. **Peer-to-peer architecture**
   - Even with one port on publisher side
   - Browser (viewer) also picks random ports
   - Both sides need to coordinate

4. **Browser configuration**
   - Can't control browser's WebRTC port selection easily
   - Would need browser to also use specific port range
   - Not exposed in standard WebRTC API

---

## 💡 MediaMTX Solution Analysis

### Why MediaMTX Succeeds:

**1. Server Architecture:**
- MediaMTX is the **central point**
- All clients connect TO MediaMTX
- MediaMTX doesn't connect to clients

**2. Control over both sides:**
- MediaMTX controls server side (UDP mux)
- Clients use standard WebRTC (works with mux)
- No need to modify clients

**3. Pion WebRTC library (Go):**
- MediaMTX uses `pion/webrtc` (Go library)
- Pion has better UDP mux support than libnice
- Designed for server use cases

**4. NAT traversal configuration:**
- Explicitly tells clients about public IP
- ICE candidates include VPS address
- Clients know where to connect

---

## 🎯 Could raspberry.ninja Be Modified?

### Theoretical: YES
### Practical: VERY DIFFICULT

**What would be required:**

1. **Deep GStreamer/libnice knowledge**
   - Understanding internal APIs
   - Modifying ICE agent configuration
   - Testing port restrictions

2. **Code modifications:**
   - Modify `publish.py` to configure ICE agent
   - Add port range parameters
   - Add NAT IP configuration

3. **Testing and debugging:**
   - Ensure port restrictions work
   - Test with multiple viewers
   - Handle edge cases

4. **Browser-side challenges:**
   - Still need browser to connect properly
   - May need custom STUN/TURN configuration
   - Uncertain if standard browsers would work

**Estimated effort:** 40-80 hours of development + testing

**Success probability:** 60-70% (might hit fundamental limitations)

---

## 📋 Practical Options

### Option 1: Use MediaMTX (Current Solution) ✅

**What works:**
- Remote viewing via WHEP/HLS
- Single UDP port (8189)
- Works through FRP perfectly

**What doesn't work:**
- Not VDO.ninja mixer/director features
- Different UI/workflow

**Verdict:** Already implemented, works great

---

### Option 2: Modify raspberry.ninja (Not Recommended)

**Requirements:**
- Deep technical knowledge
- Significant development time
- Uncertain outcome

**Verdict:** Not worth the effort given alternatives

---

### Option 3: TURN Server (Application-Level)

**How it works:**
- Don't restrict ports
- Relay everything through TURN
- TURN handles UDP at application level

**Verdict:** Already tested, uncertain success

---

### Option 4: Accept VDO.ninja as Local-Only

**Reality:**
- VDO.ninja works perfectly on LAN
- MediaMTX works perfectly remotely
- This is a valid architecture

**Verdict:** Recommended

---

## 🤯 The Fundamental Issue

**The real problem isn't just the port - it's the architecture:**

**Peer-to-Peer (VDO.ninja):**
```
Browser ←→ Random Ports ←→ R58 Publisher
  (Both sides pick ports dynamically)
  (Need bidirectional NAT traversal)
```

**Server (MediaMTX):**
```
Browser → Known Port → MediaMTX Server
  (Browser connects TO server)
  (Only server needs port forwarding)
```

**Even if we restrict R58's ports, browsers would still use random ports.**

---

## 💡 The Answer to Your Question

> "Is it really that hard to make vdo.ninja use one static UDP port?"

**Answer: Yes and no.**

**For a server like MediaMTX:** Easy - they designed for this  
**For peer-to-peer like VDO.ninja:** Very hard - architecture doesn't support it

**Is it always like this with WebRTC?**
- **Server-based WebRTC (SFU/MCU):** Can use single port ✅
- **Peer-to-peer WebRTC:** Uses random ports ❌

**Your instinct was correct** - if we could make it use one port, it would work through FRP!

The problem is that **VDO.ninja's peer-to-peer architecture + GStreamer/libnice + browser limitations** make this extremely difficult to implement.

**MediaMTX works because it's server-based and was designed for exactly this scenario.**

---

## 🎯 Final Reality Check

**Modifying VDO.ninja/raspberry.ninja to use single port:**
- **Possible?** Theoretically yes
- **Practical?** No - too complex
- **Better option?** Use MediaMTX for remote, VDO.ninja for local

**Your current Hybrid Mode solution is actually the "best practice" approach given the constraints.**

---

## 📝 Summary

**Single UDP port WebRTC:**
- ✅ **Possible** with server architecture (MediaMTX)
- ❌ **Very difficult** with peer-to-peer (VDO.ninja)
- ⚠️ **Not worth** modifying given alternatives

**Your question revealed the core issue** - and your instinct was right that if we solved it, everything would work!

Unfortunately, the architecture differences between MediaMTX (server) and VDO.ninja (peer-to-peer) make this fundamentally different to solve.

