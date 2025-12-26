# 🏗️ vdo.itagenten.no Complete Architecture Plan

**Goal**: Connect R58 HDMI cameras to `vdo.itagenten.no` for remote VDO.ninja mixing  
**Date**: December 25, 2025  
**Status**: 🔧 **PLANNING**

---

## 🎯 The Complete Solution

### Architecture Overview

```
R58 Device (HDMI Cameras)
    ↓ WHIP (WebRTC publish)
MediaMTX on Coolify (vdo.itagenten.no)
    ↓ WHEP (WebRTC subscribe)
VDO.ninja on Coolify (vdo.itagenten.no)
    ↓
Users Worldwide (Browser)
```

### Why This Works

1. **R58 → Coolify MediaMTX**: Use WHIP to publish streams (TCP-based, works through FRP)
2. **Coolify MediaMTX**: Central relay server with public domain and SSL
3. **VDO.ninja Integration**: Pull streams via WHEP or use native MediaMTX support
4. **Clean URLs**: `https://vdo.itagenten.no/cam0` or VDO.ninja mixer

---

## 🏗️ Infrastructure Components

### 1. R58 Device (Source)
- **Current**: 3x HDMI cameras → MediaMTX → Local only
- **New**: 3x HDMI cameras → Local MediaMTX → **WHIP publish to Coolify**

### 2. Coolify Server (Relay)
- **MediaMTX Instance**: Receives WHIP streams, serves WHEP
- **VDO.ninja Instance**: Mixer/Director interface
- **Domain**: `vdo.itagenten.no` with SSL
- **Ports**: 443 (HTTPS), 8889 (MediaMTX), others as needed

### 3. VDO.ninja Integration
- **Option A**: Native MediaMTX v28 integration (`&mediamtx=` parameter)
- **Option B**: WHEP streams to VDO.ninja mixer
- **Option C**: Custom mixer pulling from Coolify MediaMTX

---

## 📋 Implementation Plan

### Phase 1: Deploy MediaMTX on Coolify ✅ (Todo: arch-2)

**Steps**:
1. Create new service in Coolify
2. Use MediaMTX Docker image: `bluenviron/mediamtx:latest`
3. Configure domain: `mediamtx.vdo.itagenten.no` or `vdo.itagenten.no:8889`
4. Enable SSL/HTTPS
5. Configure MediaMTX for WHIP ingestion and WHEP distribution

**MediaMTX Coolify Configuration**:

```yaml
# mediamtx.yml for Coolify deployment
logLevel: info

# API for monitoring
api: yes
apiAddress: :9997

# WHIP (for R58 to publish)
webrtc: yes
webrtcAddress: :8889
webrtcEncryption: yes  # Use SSL on Coolify
webrtcServerKey: /path/to/server.key
webrtcServerCert: /path/to/server.crt
webrtcAllowOrigins: ['*']

# TCP support for reliable connections
webrtcLocalUDPAddress: :8189
webrtcLocalTCPAddress: :8190

# Public access
webrtcAdditionalHosts:
  - vdo.itagenten.no
  - mediamtx.vdo.itagenten.no

webrtcIPsFromInterfaces: yes

webrtcICEServers2:
  - url: stun:stun.l.google.com:19302
  - url: stun:stun.cloudflare.com:3478

# Camera paths
paths:
  cam0:
    source: publisher  # Will receive WHIP from R58
  cam1:
    source: publisher
  cam2:
    source: publisher
  cam3:
    source: publisher
```

**Docker Compose for Coolify**:

```yaml
version: '3.8'

services:
  mediamtx:
    image: bluenviron/mediamtx:latest
    container_name: mediamtx-relay
    restart: unless-stopped
    ports:
      - "8889:8889"   # WebRTC HTTP
      - "8189:8189/udp"  # WebRTC UDP
      - "8190:8190"   # WebRTC TCP
      - "9997:9997"   # API
    volumes:
      - ./mediamtx.yml:/mediamtx.yml
      - ./ssl:/ssl
    environment:
      - MTX_PROTOCOLS=webrtc
```

---

### Phase 2: Configure R58 to Publish via WHIP ✅ (Todo: arch-3)

**Current R58 Setup**:
- MediaMTX receives RTSP from preke-recorder
- Streams available locally

**New R58 Setup**:
- Keep local MediaMTX for local access
- Add WHIP publisher to send to Coolify

**Option A: GStreamer WHIP Plugin**

```bash
# Install GStreamer WHIP plugin on R58
sudo apt-get install gstreamer1.0-plugins-bad gstreamer1.0-plugins-rs

# Create WHIP publisher script
gst-launch-1.0 \
  rtspsrc location=rtsp://localhost:8554/cam0 latency=0 ! \
  rtph264depay ! h264parse ! \
  whipsink url=https://vdo.itagenten.no:8889/cam0/whip
```

**Option B: FFmpeg WHIP (if supported)**

```bash
ffmpeg -i rtsp://localhost:8554/cam0 \
  -c:v copy \
  -f whip https://vdo.itagenten.no:8889/cam0/whip
```

**Option C: MediaMTX Cascading**

Configure R58 MediaMTX to forward streams:

```yaml
# On R58 mediamtx.yml
paths:
  cam0:
    source: publisher
    # Forward to Coolify via WHIP
    runOnReady: curl -X POST https://vdo.itagenten.no:8889/cam0/whip
```

**Option D: Custom Python WHIP Publisher**

Create a script using `aiortc` or similar to publish WHIP streams.

---

### Phase 3: Setup vdo.itagenten.no Domain ✅ (Todo: arch-4)

**DNS Configuration**:
```
A     mediamtx.vdo.itagenten.no → [Coolify Server IP]
CNAME vdo.itagenten.no → mediamtx.vdo.itagenten.no
```

**Coolify SSL**:
- Enable automatic SSL via Let's Encrypt in Coolify
- Or manually configure SSL certificates

**Nginx Reverse Proxy** (if needed):

```nginx
server {
    listen 443 ssl http2;
    server_name vdo.itagenten.no;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # MediaMTX WebRTC
    location / {
        proxy_pass http://mediamtx:8889;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

### Phase 4: Deploy VDO.ninja on Coolify ✅ (Todo: arch-5)

**VDO.ninja Docker Deployment**:

```yaml
version: '3.8'

services:
  vdo-ninja:
    image: node:18-alpine
    container_name: vdo-ninja
    restart: unless-stopped
    working_dir: /app
    ports:
      - "8443:8443"
    volumes:
      - ./vdo.ninja:/app
      - ./ssl:/ssl
    command: node webserver.js
    environment:
      - NODE_ENV=production
```

**Clone VDO.ninja**:

```bash
git clone https://github.com/steveseguin/vdo.ninja.git
cd vdo.ninja
npm install
```

**Configure WebSocket Signaling**:

```javascript
// Simple signaling server for VDO.ninja
const https = require('https');
const fs = require('fs');
const WebSocket = require('ws');

const server = https.createServer({
  cert: fs.readFileSync('/ssl/cert.pem'),
  key: fs.readFileSync('/ssl/key.pem')
});

const wss = new WebSocket.Server({ server });

wss.on('connection', (ws) => {
  ws.on('message', (message) => {
    // Broadcast to all clients
    wss.clients.forEach((client) => {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  });
});

server.listen(8443, () => {
  console.log('VDO.ninja signaling server running on :8443');
});
```

---

### Phase 5: Connect Everything ✅ (Todo: arch-6)

**VDO.ninja Mixer Configuration**:

**Option A: Use VDO.ninja v28 Native MediaMTX Support**

```
https://vdo.itagenten.no/mixer?mediamtx=https://vdo.itagenten.no:8889
```

VDO.ninja v28 can natively discover and pull streams from MediaMTX.

**Option B: Use WHEP URLs in VDO.ninja**

```
https://vdo.itagenten.no/?view=cam0&whep=https://vdo.itagenten.no:8889/cam0/whep
```

**Option C: Custom Mixer Pulling from Coolify MediaMTX**

Deploy our custom `mediamtx_mixer.html` on Coolify pointing to the MediaMTX instance.

---

## 🎯 Final User Experience

### For Remote Users

**Mixer Interface**:
```
https://vdo.itagenten.no/mixer
```
- See all 3 HDMI cameras
- Create custom layouts
- Switch between cameras
- Export/record mixed output

**Director View**:
```
https://vdo.itagenten.no/?director=r58studio
```
- Control all camera streams
- Manage guest connections
- Scene composition

**Individual Cameras**:
```
https://vdo.itagenten.no/cam0
https://vdo.itagenten.no/cam2
https://vdo.itagenten.no/cam3
```

---

## 🔧 Technical Details

### Bandwidth Considerations

**R58 → Coolify Upload**:
- 3 cameras × 8 Mbps = 24 Mbps upload
- R58 needs stable upload bandwidth

**Coolify → Users Download**:
- Per user: 1-3 cameras × 8 Mbps = 8-24 Mbps
- Coolify server needs good bandwidth

**Optimization**:
- Use adaptive bitrate
- Enable simulcast in MediaMTX
- Offer HLS fallback for low bandwidth users

### Security

**Authentication**:
```yaml
# MediaMTX with auth
paths:
  cam0:
    readUser: viewer
    readPass: secure_password
```

**VDO.ninja Room Passwords**:
```
https://vdo.itagenten.no/mixer?room=r58studio&password=secure123
```

### Monitoring

**MediaMTX API**:
```bash
curl https://vdo.itagenten.no:9997/v3/paths/list
```

**Health Checks**:
- Monitor R58 → Coolify connection
- Check stream quality
- Alert on failures

---

## 📊 Advantages of This Architecture

### ✅ Benefits

1. **Central Relay**: Coolify MediaMTX acts as SFU for multiple viewers
2. **Clean URLs**: Professional `vdo.itagenten.no` domain
3. **SSL/HTTPS**: Secure connections
4. **VDO.ninja Integration**: Full mixer and director features
5. **Scalable**: Can add more cameras or viewers
6. **Local Fallback**: R58 MediaMTX still works locally
7. **No VPN Required**: Works through existing FRP tunnel

### 🎯 Solves Previous Issues

- ❌ **UDP blocking** → ✅ Use TCP for R58 → Coolify
- ❌ **No VPN support** → ✅ Not needed with WHIP/WHEP
- ❌ **Dynamic ports** → ✅ Static WHIP/WHEP endpoints
- ❌ **Mixed content security** → ✅ Full HTTPS on Coolify
- ❌ **Complex setup** → ✅ Clean Docker deployment

---

## 🚀 Next Steps

### Immediate Actions

1. **Deploy MediaMTX on Coolify** (1-2 hours)
   - Create Docker service
   - Configure domain and SSL
   - Test WHIP endpoint

2. **Configure R58 WHIP Publisher** (1-2 hours)
   - Choose method (GStreamer/FFmpeg/Custom)
   - Test publishing to Coolify
   - Verify stream quality

3. **Setup VDO.ninja** (1-2 hours)
   - Deploy signaling server
   - Configure mixer to pull from MediaMTX
   - Test full workflow

4. **Test End-to-End** (1 hour)
   - Verify all cameras visible
   - Test mixer functionality
   - Check performance and latency

**Total Estimated Time**: 5-7 hours

---

## 📝 Configuration Files Needed

### 1. `mediamtx-coolify.yml`
MediaMTX configuration for Coolify deployment

### 2. `docker-compose-coolify.yml`
Docker Compose for MediaMTX and VDO.ninja

### 3. `r58-whip-publisher.sh`
Script to publish R58 streams via WHIP

### 4. `nginx-vdo.conf`
Nginx config for `vdo.itagenten.no`

### 5. `vdo-signaling-server.js`
VDO.ninja WebSocket signaling server

---

## 🎬 Success Criteria

### Must Have

✅ All 3 R58 cameras visible in `vdo.itagenten.no` mixer  
✅ Low latency (<3 seconds end-to-end)  
✅ HTTPS/SSL everywhere  
✅ VDO.ninja mixer fully functional  
✅ Stable connections

### Nice to Have

⭐ Authentication/passwords  
⭐ Recording capability  
⭐ HLS fallback  
⭐ Mobile responsive  
⭐ Monitoring dashboard

---

## 🆘 Potential Issues & Solutions

### Issue 1: R58 Upload Bandwidth

**Problem**: Not enough bandwidth for 3 cameras @ 8 Mbps  
**Solution**: Reduce bitrate to 4-6 Mbps, use H.265, or selective streaming

### Issue 2: WHIP Publisher Complexity

**Problem**: GStreamer/FFmpeg WHIP support unclear  
**Solution**: Use MediaMTX's built-in SRT/RTSP/RTMP to WHIP bridge

### Issue 3: VDO.ninja Signaling

**Problem**: Custom signaling server needed  
**Solution**: Use public VDO.ninja with WHEP URLs, or deploy official VDO.ninja instance

---

**Ready to implement? Let's start with Phase 1: Deploy MediaMTX on Coolify! 🚀**


