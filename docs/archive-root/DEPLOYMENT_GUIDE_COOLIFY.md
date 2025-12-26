# 🚀 vdo.itagenten.no Deployment Guide

**Complete step-by-step guide to deploy the R58 camera system to Coolify**

---

## 📋 Prerequisites

### Required

- ✅ Coolify server (accessible and running)
- ✅ Domain: `vdo.itagenten.no` (DNS configured)
- ✅ R58 device with cameras streaming locally
- ✅ SSH access to both Coolify server and R58

### Recommended

- Coolify server with at least 2GB RAM, 2 CPU cores
- Good upload bandwidth on R58 (~30 Mbps for 3 cameras)
- Good download bandwidth on Coolify (~30 Mbps + user bandwidth)

---

## 🎯 What We're Building

```
┌─────────────────┐
│  R58 Device     │
│  ┌───┐ ┌───┐   │
│  │C0 │ │C2 │   │  WHIP (WebRTC publish)
│  └─┬─┘ └─┬─┘   │        ↓
│    └─────┴─────┼───────────────────────┐
└─────────────────┘                       │
                                          │
                                          ↓
                          ┌───────────────────────────┐
                          │  Coolify Server           │
                          │  vdo.itagenten.no         │
                          │                           │
                          │  ┌──────────────────────┐ │
                          │  │  MediaMTX (Relay)    │ │
                          │  │  - WHIP ingestion    │ │
                          │  │  - WHEP distribution │ │
                          │  └──────────────────────┘ │
                          │                           │
                          │  ┌──────────────────────┐ │
                          │  │  VDO.ninja Signaling│ │
                          │  │  - WebSocket server  │ │
                          │  └──────────────────────┘ │
                          └───────────────────────────┘
                                          │
                                          │ WHEP (WebRTC subscribe)
                                          ↓
                            ┌───────────────────────┐
                            │  Remote Users         │
                            │  - VDO.ninja mixer    │
                            │  - Direct viewers     │
                            └───────────────────────┘
```

---

## 📦 Step 1: Deploy to Coolify

### Upload Deployment Files

```bash
# On your local machine
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder/deployment"

# Upload to Coolify server
scp -r ./* your-server:/opt/vdo-itagenten/
```

### Run Deployment Script

```bash
# SSH to Coolify server
ssh your-coolify-server

# Navigate to deployment directory
cd /opt/vdo-itagenten

# Run deployment
sudo ./deploy-coolify.sh
```

The script will:
- ✅ Create Docker network
- ✅ Generate SSL certificates
- ✅ Start MediaMTX container
- ✅ Start VDO.ninja signaling server
- ✅ Start Nginx reverse proxy
- ✅ Display access URLs

---

## 📡 Step 2: Configure R58 Publishing

### Deploy WHIP Publisher to R58

```bash
# Copy publisher script to R58
scp deployment/r58-whip-publisher.sh linaro@r58.itagenten.no:/opt/

# SSH to R58
ssh linaro@r58.itagenten.no

# Make executable
chmod +x /opt/r58-whip-publisher.sh

# Start publishing
sudo /opt/r58-whip-publisher.sh start
```

### Verify Streaming

```bash
# Check publisher status
sudo /opt/r58-whip-publisher.sh status

# View logs
sudo /opt/r58-whip-publisher.sh logs cam0
```

Expected output:
```
✅ cam0: Running (PID: 12345)
   📡 Stream active on Coolify
✅ cam2: Running (PID: 12346)
   📡 Stream active on Coolify
✅ cam3: Running (PID: 12347)
   📡 Stream active on Coolify
```

---

## 🌐 Step 3: Configure DNS

### Required DNS Records

```dns
; A Record pointing to Coolify server
vdo.itagenten.no.             300  IN  A     [YOUR_COOLIFY_IP]

; Optional CNAME for MediaMTX subdomain
mediamtx.vdo.itagenten.no.   300  IN  CNAME vdo.itagenten.no.
```

### Verify DNS

```bash
# Check DNS resolution
dig +short vdo.itagenten.no

# Should return your Coolify server IP
```

---

## 🔐 Step 4: Setup SSL Certificates

### Option A: Let's Encrypt (Recommended)

```bash
# On Coolify server
sudo apt-get install certbot

# Get certificates
sudo certbot certonly --standalone \
  -d vdo.itagenten.no \
  -d mediamtx.vdo.itagenten.no

# Copy to deployment directory
sudo cp /etc/letsencrypt/live/vdo.itagenten.no/fullchain.pem \
  /opt/vdo-itagenten/ssl/cert.pem
sudo cp /etc/letsencrypt/live/vdo.itagenten.no/privkey.pem \
  /opt/vdo-itagenten/ssl/key.pem

# Restart services
cd /opt/vdo-itagenten
sudo docker-compose restart
```

### Option B: Self-Signed (Testing)

The deployment script already generated self-signed certificates.

**Note**: Browsers will show security warnings with self-signed certs.

---

## 🧪 Step 5: Test the System

### Test MediaMTX Direct Access

```bash
# Open in browser
https://vdo.itagenten.no/cam0
https://vdo.itagenten.no/cam2
https://vdo.itagenten.no/cam3
```

Expected: Live video from each camera

### Test WHEP Endpoints

```bash
# Curl test
curl -I https://vdo.itagenten.no/cam0/whep

# Expected: HTTP 200 or 405 (method not allowed is ok)
```

### Test with VDO.ninja

```bash
# Open VDO.ninja mixer with your streams
https://vdo.ninja/?view=cam0&whep=https://vdo.itagenten.no/cam0/whep

# Or use the mixer
https://vdo.ninja/mixer?wss=vdo.itagenten.no/signal&room=r58studio
```

---

## 🔧 Troubleshooting

### Issue: Cameras not visible in Coolify

**Check R58 publishing**:
```bash
# On R58
sudo /opt/r58-whip-publisher.sh status
tail -f /var/log/whip-cam0.log
```

**Check Coolify MediaMTX**:
```bash
# On Coolify
docker-compose logs -f mediamtx
curl https://vdo.itagenten.no/api/v3/paths/list
```

### Issue: SSL Certificate Errors

**Temporarily disable SSL**:
```yaml
# In mediamtx-coolify.yml
webrtcEncryption: no
```

**Or use HTTP for testing**:
```
http://vdo.itagenten.no:8889/cam0
```

### Issue: WebRTC not connecting

**Check firewall ports**:
```bash
# On Coolify server
sudo ufw allow 8189/udp
sudo ufw allow 8190/tcp
sudo ufw allow 8889/tcp
sudo ufw allow 443/tcp
```

**Check MediaMTX logs**:
```bash
docker-compose logs -f mediamtx | grep -i "ice\|webrtc\|error"
```

### Issue: High latency

**Reduce bitrate on R58**:
```bash
# Edit r58-whip-publisher.sh
# Change: bitrate=6000
# To: bitrate=4000
```

**Enable TCP fallback**:
Already enabled in config with `webrtcLocalTCPAddress: :8190`

---

## 📊 Monitoring

### Check System Status

```bash
# On Coolify server
cd /opt/vdo-itagenten

# Container status
docker-compose ps

# Resource usage
docker stats

# MediaMTX paths
curl -s https://vdo.itagenten.no/api/v3/paths/list | jq
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f mediamtx
docker-compose logs -f vdo-nginx
docker-compose logs -f vdo-ninja-signaling
```

### Monitor Streams

```bash
# Check active streams
curl -s https://vdo.itagenten.no/api/v3/paths/list | \
  jq '.items[] | select(.ready==true) | {name, readers}'
```

---

## 🎬 Final User Experience

### For Director/Producer

**Mixer Interface**:
```
https://vdo.ninja/mixer?wss=vdo.itagenten.no/signal&room=r58studio
```

- Add WHEP streams manually:
  - `https://vdo.itagenten.no/cam0/whep`
  - `https://vdo.itagenten.no/cam2/whep`
  - `https://vdo.itagenten.no/cam3/whep`

### For Viewers

**Direct Camera Access**:
```
https://vdo.itagenten.no/cam0
https://vdo.itagenten.no/cam2
https://vdo.itagenten.no/cam3
```

**VDO.ninja Viewer**:
```
https://vdo.ninja/?view=cam0&whep=https://vdo.itagenten.no/cam0/whep
```

### For OBS Studio

Add Browser Source:
- URL: `https://vdo.itagenten.no/cam0`
- Width: 1920
- Height: 1080

---

## 🔄 Maintenance

### Update MediaMTX

```bash
cd /opt/vdo-itagenten
docker-compose pull mediamtx
docker-compose up -d mediamtx
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart mediamtx
```

### Backup Configuration

```bash
# Backup deployment files
tar -czf vdo-itagenten-backup.tar.gz /opt/vdo-itagenten/

# Copy to safe location
scp vdo-itagenten-backup.tar.gz user@backup-server:/backups/
```

---

## 📞 Support

### Useful Commands

```bash
# R58 publisher control
sudo /opt/r58-whip-publisher.sh {start|stop|restart|status|logs}

# Coolify service control
docker-compose {up|down|restart|logs} -f

# Check MediaMTX API
curl -s https://vdo.itagenten.no/api/v3/paths/list | jq

# Test WHEP endpoint
curl -X POST https://vdo.itagenten.no/cam0/whep
```

### Configuration Files

- MediaMTX: `/opt/vdo-itagenten/mediamtx.yml`
- Docker Compose: `/opt/vdo-itagenten/docker-compose.yml`
- Nginx: `/opt/vdo-itagenten/nginx.conf`
- SSL Certs: `/opt/vdo-itagenten/ssl/`

---

## ✅ Deployment Checklist

- [ ] Coolify server accessible
- [ ] DNS records configured
- [ ] Deployment files uploaded
- [ ] `deploy-coolify.sh` executed successfully
- [ ] SSL certificates configured
- [ ] R58 WHIP publisher running
- [ ] MediaMTX receiving streams
- [ ] WHEP endpoints accessible
- [ ] VDO.ninja mixer tested
- [ ] Direct camera viewers tested
- [ ] Documentation reviewed

---

**Deployment Status**: Ready for implementation 🚀

**Estimated Time**: 2-3 hours for complete deployment

**Next Step**: Run `./deploy-coolify.sh` on Coolify server!


