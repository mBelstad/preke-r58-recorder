# R58 WiFi Access Point Status

**Date**: December 21, 2025  
**Status**: ✅ **CONFIGURED AND RUNNING**

---

## Configuration

| Setting | Value |
|---------|-------|
| SSID | `R58-Studio` |
| Password | `r58studio2025` |
| IP Address | `10.58.0.1` |
| DHCP Range | `10.58.0.100 - 10.58.0.200` |
| Domain | `r58.local` |
| WiFi Band | 2.4GHz (Channel 6) |
| Security | WPA2-PSK |

---

## Services Status

### hostapd ✅
```
● hostapd.service - Access point and authentication server
     Active: active (running)
     Status: wlan0: AP-ENABLED
```

### dnsmasq ✅
```
● dnsmasq.service - A lightweight DHCP and caching DNS server
     Active: active (running)
     DHCP Range: 10.58.0.100 -- 10.58.0.200
     Interface: wlan0 (bound exclusively)
```

---

## How to Connect

### From Your Mac/PC:

1. **Open WiFi settings**
2. **Look for network**: `R58-Studio`
3. **Connect** with password: `r58studio2025`
4. **You'll get an IP**: `10.58.0.100 - 10.58.0.200`

### Access R58 Services:

Once connected to R58-Studio WiFi:

| Service | URL |
|---------|-----|
| VDO.ninja | `https://10.58.0.1:8443` |
| R58 Web UI | `http://10.58.0.1:8000` |
| R58 API | `http://10.58.0.1:8000/docs` |

---

## Verification

### Check WiFi Network Visible
From your Mac, scan for WiFi networks:
```bash
# macOS WiFi scan
/System/Library/PrivateFrameworks/Apple80211.framework/Resources/airport -s | grep R58
```

Or just open System Settings → WiFi and look for "R58-Studio"

### Check DHCP Leases
On R58:
```bash
cat /var/lib/misc/dnsmasq.leases
```

### Check Connected Clients
On R58:
```bash
sudo iw dev wlan0 station dump
```

---

## Troubleshooting

### WiFi Network Not Visible

**Check hostapd status**:
```bash
./connect-r58.sh "sudo systemctl status hostapd"
```

**Check hostapd logs**:
```bash
./connect-r58.sh "sudo journalctl -u hostapd -n 50"
```

**Restart hostapd**:
```bash
./connect-r58.sh "sudo systemctl restart hostapd"
```

### Can't Get IP Address

**Check dnsmasq status**:
```bash
./connect-r58.sh "sudo systemctl status dnsmasq"
```

**Check dnsmasq logs**:
```bash
./connect-r58.sh "sudo journalctl -u dnsmasq -n 50"
```

**Check DHCP range**:
```bash
./connect-r58.sh "cat /etc/dnsmasq.d/r58-ap.conf"
```

### Can't Access R58 Services

**Check wlan0 IP**:
```bash
./connect-r58.sh "ip addr show wlan0"
```

**Ping R58**:
```bash
ping 10.58.0.1
```

---

## Next Steps

1. ✅ WiFi AP configured and running
2. ⏳ **Connect to R58-Studio WiFi from your device**
3. ⏳ **Test access to VDO.ninja**: `https://10.58.0.1:8443`
4. ⏳ Configure DynDNS for remote access
5. ⏳ Set up port forwarding
6. ⏳ Install SSL certificates
7. ⏳ Update publishers with TURN

---

## Technical Details

### Network Interface
- Interface: `wlan0`
- MAC: `40:d9:5a:25:aa:3a`
- Mode: Access Point
- Channel: 6 (2.4GHz)
- TX Power: 31.00 dBm

### NAT Configuration
- Internet interface: `enP3p49s0`
- IP forwarding: Enabled
- iptables: Configured (using legacy mode)

---

**Status**: WiFi AP is ready! Try connecting to "R58-Studio" from your Mac.

