# Port Forwarding Configuration for R58

**Goal**: Forward port 8443 from the internet to R58 for direct VDO.ninja access

---

## What You Need

1. **R58's Local IP Address**: Find it first
2. **Router Access**: Via AnyDesk to on-site PC
3. **Port to Forward**: 8443

---

## Step 1: Find R58's Local IP

From the on-site PC (via AnyDesk), open Command Prompt or Terminal and run:

```bash
ping r58.itagenten.no
```

Or check the router's DHCP client list for a device named "linaro-alip" or with MAC address starting with the R58's MAC.

Alternatively, I can find it for you:

```bash
# From here
./connect-r58.sh "hostname -I"
```

---

## Step 2: Access Router Configuration

**Common router addresses**:
- `192.168.1.1`
- `192.168.0.1`
- `10.0.0.1`

From the on-site PC (via AnyDesk):
1. Open web browser
2. Go to router IP (try the addresses above)
3. Log in with router credentials

---

## Step 3: Configure Port Forwarding

Look for settings named:
- "Port Forwarding"
- "Virtual Server"
- "NAT"
- "Applications & Gaming"

**Add this rule**:
| Setting | Value |
|---------|-------|
| Service Name | `R58-VDO-Ninja` |
| External Port | `8443` |
| Internal IP | `<R58_LOCAL_IP>` (from Step 1) |
| Internal Port | `8443` |
| Protocol | `TCP` (or `TCP/UDP`) |

**Optional - Standard HTTPS**:
| Setting | Value |
|---------|-------|
| Service Name | `R58-HTTPS` |
| External Port | `443` |
| Internal IP | `<R58_LOCAL_IP>` |
| Internal Port | `8443` |
| Protocol | `TCP` |

---

## Step 4: Verify Port Forwarding

After configuring, test from your Mac:

```bash
# Test if port 8443 is open
nc -zv r58-studio.duckdns.org 8443
```

Or use an online tool:
- https://www.yougetsignal.com/tools/open-ports/
- Enter: `r58-studio.duckdns.org` and port `8443`

---

## Common Router Interfaces

### TP-Link
- Advanced → NAT Forwarding → Virtual Servers

### Netgear
- Advanced → Advanced Setup → Port Forwarding

### ASUS
- WAN → Virtual Server / Port Forwarding

### Linksys
- Security → Apps and Gaming → Single Port Forwarding

### UniFi
- Settings → Routing & Firewall → Port Forwarding

---

## Security Note

**Only forward port 8443** (VDO.ninja).

**Do NOT forward**:
- Port 22 (SSH) - Keep via Cloudflare Tunnel only
- Port 8000 (Web UI) - Keep via tunnel
- Port 8888/8889 (MediaMTX) - Internal only

This keeps management secure via tunnel while allowing direct WebRTC access.

---

## Troubleshooting

### Can't access router
- Check if router has remote management enabled
- May need physical access
- Could use router's mobile app if available

### Port already in use
- Check if another device is using port 8443
- Use a different external port (e.g., 8444) if needed

### Firewall blocking
- Some ISPs block certain ports
- Try port 443 instead of 8443

---

## After Port Forwarding Works

Run the SSL setup:
```bash
./connect-r58.sh "sudo bash /tmp/setup-letsencrypt.sh r58-studio.duckdns.org"
```

Then update publishers:
```bash
./connect-r58.sh "sudo bash /tmp/update-ninja-turn.sh"
```

---

**Let me know when port forwarding is configured and I'll continue with SSL setup!**

