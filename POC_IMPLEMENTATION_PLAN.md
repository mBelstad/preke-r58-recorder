# R58 POC Implementation Plan - Local Network + VPN Mesh

**Date**: December 21, 2025  
**Status**: Ready to implement  
**Estimated Time**: 1-2 days

---

## What We're Building

A headless R58 system that:
- ✅ Works locally without internet (primary use case)
- ✅ Accessible remotely via VPN when needed
- ✅ Runs VDO.Ninja for mixing/control
- ✅ Suitable for commercial product

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    R58 Device                           │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Local Network: 10.58.0.1                        │  │
│  │  - DHCP server for control PCs                   │  │
│  │  - VDO.Ninja on :8443                            │  │
│  │  - Recorder API on :8000                         │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Tailscale VPN                                   │  │
│  │  - IP: 100.x.x.x                                 │  │
│  │  - Hostname: r58.tailnet.ts.net                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  WAN Connection (optional)                       │  │
│  │  - Venue ethernet or 5G (Phase 3)                │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │                           │
         │                           │
    ┌────┴────┐                 ┌───┴────┐
    │ Switch  │                 │Internet│
    └────┬────┘                 └────────┘
         │
    ┌────┴─────────┬──────────┐
    │              │          │
┌───┴───┐    ┌────┴───┐  ┌──┴───┐
│Control│    │Control │  │Camera│
│ PC 1  │    │ PC 2   │  │(IP)  │
└───────┘    └────────┘  └──────┘
```

---

## Implementation Steps

### Step 1: Configure R58 Local Network (30 minutes)

**Files to create on R58**:

1. `/etc/network/interfaces.d/r58-lan`:
```
auto eth0
iface eth0 inet static
    address 10.58.0.1
    netmask 255.255.255.0
```

2. `/etc/dnsmasq.d/r58-lan.conf`:
```
interface=eth0
bind-interfaces
dhcp-range=10.58.0.100,10.58.0.200,255.255.255.0,24h
dhcp-option=option:router,10.58.0.1
dhcp-option=option:dns-server,10.58.0.1
domain=r58.local
local=/r58.local/
address=/r58.local/10.58.0.1
```

3. `/etc/sysctl.d/99-r58-forwarding.conf`:
```
net.ipv4.ip_forward=1
```

4. NAT rules (if internet sharing needed):
```bash
# Detect WAN interface
WAN_IF=$(ip route | grep default | awk '{print $5}' | head -1)
iptables -t nat -A POSTROUTING -s 10.58.0.0/24 -o $WAN_IF -j MASQUERADE
iptables-save > /etc/iptables/rules.v4
```

**Test**:
- Connect PC to switch
- PC should get IP 10.58.0.1xx
- Access: `https://10.58.0.1:8443/?director=r58studio`

---

### Step 2: Install Tailscale on R58 (15 minutes)

```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start Tailscale
sudo tailscale up

# Note the IP address
tailscale ip -4
# Example: 100.101.102.103
```

**Test**:
- Note Tailscale IP
- From your Mac (with Tailscale installed): `ssh linaro@100.x.x.x`

---

### Step 3: Install Tailscale on Your Mac (5 minutes)

```bash
# Using Homebrew
brew install --cask tailscale

# Or download from https://tailscale.com/download/mac
```

**Test**:
- Open Tailscale app
- Should see R58 in device list
- Access: `https://100.x.x.x:8443/?director=r58studio`

---

### Step 4: Update VDO.Ninja Services (15 minutes)

Update raspberry.ninja services to use local signaling:

```bash
# Edit service file
sudo nano /etc/systemd/system/ninja-publish-cam1.service

# Change --server to local
--server wss://10.58.0.1:8443

# Or use Tailscale IP for remote access
--server wss://100.x.x.x:8443

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart ninja-publish-cam1
```

---

### Step 5: Test Complete Workflow (30 minutes)

**Local Test**:
1. Connect control PC to switch
2. Open browser: `https://10.58.0.1:8443/?director=r58studio`
3. Should see cameras in director view
4. Test mixing, switching, etc.

**Remote Test (via Tailscale)**:
1. On your Mac (with Tailscale)
2. Open browser: `https://100.x.x.x:8443/?director=r58studio`
3. Should see same director view
4. Test remote control

**Offline Test**:
1. Disconnect R58 from internet
2. Local control should still work
3. Remote via Tailscale will fail (expected)
4. Reconnect internet, remote works again

---

## Access URLs Summary

| Location | URL | Notes |
|----------|-----|-------|
| **Local network** | `https://10.58.0.1:8443/?director=r58studio` | Always works |
| **Remote (Tailscale)** | `https://100.x.x.x:8443/?director=r58studio` | Requires Tailscale |
| **Recorder API (local)** | `http://10.58.0.1:8000/` | Control interface |
| **Recorder API (remote)** | `http://100.x.x.x:8000/` | Via Tailscale |

---

## Advantages of This Approach

| Feature | Benefit |
|---------|---------|
| **Local-first** | Works without internet, critical for live events |
| **Low latency** | Direct connection, no cloud relay |
| **Secure** | VPN encrypted, no public exposure |
| **Simple** | One-time VPN setup, then works everywhere |
| **Reliable** | No dependency on Cloudflare Tunnel |
| **Scalable** | Add more R58 units easily |
| **Commercial ready** | Users install VPN app once, then seamless |

---

## For Commercial Product

### User Experience:
1. Customer receives R58
2. Connects to venue network
3. Local PCs connect via switch (auto-discovery)
4. Remote users install Tailscale app
5. Remote users access via Tailscale

### Your Infrastructure:
- No cloud relay needed (Phase 1)
- No TURN server needed (Phase 1)
- Minimal ongoing costs
- Easy to support

### Future Enhancements:
- Phase 2: Add your own Tailscale coordination server (self-hosted)
- Phase 3: Add 5G failover
- Phase 4: Fleet management dashboard

---

## Cost Analysis

| Component | Cost | Notes |
|-----------|------|-------|
| Tailscale (free tier) | $0 | Up to 100 devices, 3 users |
| Tailscale (paid) | $5/user/month | If you exceed free tier |
| R58 hardware | One-time | Already have |
| Your time | 1-2 days | Implementation |
| **Total (POC)** | **$0** | Using free tier |

---

## Deployment Script

Create `setup-r58-poc.sh`:

```bash
#!/bin/bash
# R58 POC Setup - Local Network + Tailscale

set -e

echo "=== R58 POC Setup ==="

# 1. Install packages
apt-get update
apt-get install -y dnsmasq iptables-persistent

# 2. Configure local network
cat > /etc/network/interfaces.d/r58-lan << 'EOF'
auto eth0
iface eth0 inet static
    address 10.58.0.1
    netmask 255.255.255.0
EOF

# 3. Configure DHCP
cat > /etc/dnsmasq.d/r58-lan.conf << 'EOF'
interface=eth0
bind-interfaces
dhcp-range=10.58.0.100,10.58.0.200,255.255.255.0,24h
dhcp-option=option:router,10.58.0.1
dhcp-option=option:dns-server,10.58.0.1
domain=r58.local
local=/r58.local/
address=/r58.local/10.58.0.1
EOF

# 4. Enable IP forwarding
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-r58-forwarding.conf
sysctl -p /etc/sysctl.d/99-r58-forwarding.conf

# 5. Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# 6. Restart services
systemctl restart networking
systemctl restart dnsmasq

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Run: sudo tailscale up"
echo "2. Note Tailscale IP: tailscale ip -4"
echo "3. Connect PC to switch, should get 10.58.0.x IP"
echo "4. Access: https://10.58.0.1:8443/?director=r58studio"
```

---

## Success Criteria

- [ ] Local PC gets IP from R58 DHCP
- [ ] Can access VDO.Ninja locally
- [ ] Cameras appear in director view
- [ ] Mixing works with low latency
- [ ] Tailscale installed and connected
- [ ] Can access via Tailscale from remote Mac
- [ ] Works offline (local control)
- [ ] Works online (remote control)

---

## Next Steps

1. Review this plan
2. Run setup script on R58
3. Test local network
4. Install Tailscale
5. Test remote access
6. Document for users

---

**Ready to implement**: Yes  
**Estimated completion**: 1-2 days  
**Risk level**: Low (proven technology)

