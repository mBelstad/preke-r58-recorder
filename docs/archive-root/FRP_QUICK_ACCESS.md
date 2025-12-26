# frp Quick Access Guide

## 🎯 Access URLs

### Camera Streams (once firewall is configured)
```
http://65.109.32.111:18889/cam0
http://65.109.32.111:18889/cam1
http://65.109.32.111:18889/cam2
http://65.109.32.111:18889/cam3
```

### VDO.ninja Director
```
https://65.109.32.111:18443/?director=r58studio&wss=65.109.32.111:18443
```

### frp Dashboard
```
http://65.109.32.111:7500
Username: admin
Password: R58frpDashboard2024!
```

---

## 🔧 Service Management

### On R58 (via SSH)
```bash
# Check all frp services
sudo systemctl status frp-ssh-tunnel
sudo systemctl status frpc
sudo systemctl status mediamtx

# Restart if needed
sudo systemctl restart frp-ssh-tunnel
sudo systemctl restart frpc
sudo systemctl restart mediamtx

# View logs
sudo tail -f /var/log/frpc.log
sudo journalctl -u mediamtx -f
```

### On Coolify VPS
```bash
# Check frp server
systemctl status frps

# View logs
tail -f /var/log/frps.log
```

---

## ⚠️ Important: Hetzner Cloud Firewall

External access to ports 18xxx is currently blocked by Hetzner's cloud firewall.

**To enable external access:**

1. Log into Hetzner Cloud Console: https://console.hetzner.cloud/
2. Select your server
3. Go to "Firewalls" tab
4. Add inbound rules:
   - **TCP**: 18889, 18443, 19997, 7500
   - **UDP**: 18189

---

## 🧪 Testing

### From VPS (works now)
```bash
ssh root@65.109.32.111
curl http://localhost:19997/v3/paths/list
```

### From External (after firewall config)
```bash
curl http://65.109.32.111:19997/v3/paths/list
```

---

## 📊 Port Mapping

| Service | R58 Port | VPS Port | Protocol |
|---------|----------|----------|----------|
| MediaMTX WHEP | 8889 | **18889** | TCP |
| WebRTC Media | 8189 | **18189** | UDP |
| VDO.ninja | 8443 | **18443** | TCP |
| MediaMTX API | 9997 | **19997** | TCP |
| frp Control | - | 7000 | TCP (via SSH tunnel) |
| frp Dashboard | - | 7500 | TCP |

---

## 🚀 What's Working

✅ frp server running on Coolify VPS  
✅ frp client running on R58  
✅ SSH tunnel bypassing R58 firewall  
✅ MediaMTX configured with VPS IP  
✅ All proxies active  
✅ Tested from VPS localhost  

## 🔜 Next Step

Configure Hetzner Cloud Firewall to allow external access to ports 18xxx.


