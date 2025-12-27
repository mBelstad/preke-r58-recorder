# 📦 Deployment Package - vdo.itagenten.no

**Ready-to-deploy package for complete R58 camera system**

---

## 📂 Files Included

### Configuration Files

1. **mediamtx-coolify.yml**
   - MediaMTX configuration for Coolify
   - WHIP/WHEP endpoints
   - SSL support
   - Camera stream paths

2. **docker-compose-coolify.yml**
   - Complete Docker Compose stack
   - MediaMTX + VDO.ninja signaling + Nginx
   - Volume and network configuration

3. **nginx.conf**
   - Reverse proxy configuration
   - SSL termination
   - WebSocket support
   - CORS headers

### Scripts

4. **deploy-coolify.sh**
   - Automated deployment script
   - SSL certificate generation
   - Service initialization
   - Status reporting

5. **r58-whip-publisher.sh**
   - R58 camera publishing via WHIP
   - GStreamer pipeline configuration
   - Service management (start/stop/status)
   - Logging

### Documentation

6. **VDO_ITAGENTEN_ARCHITECTURE.md**
   - Complete architecture overview
   - Technical specifications
   - Network flow diagrams

7. **DEPLOYMENT_GUIDE_COOLIFY.md**
   - Step-by-step deployment guide
   - Troubleshooting
   - Maintenance procedures

---

## 🚀 Quick Start

### On Coolify Server

```bash
# 1. Upload deployment files
scp -r deployment/* your-server:/opt/vdo-itagenten/

# 2. SSH to server
ssh your-coolify-server

# 3. Deploy
cd /opt/vdo-itagenten
sudo ./deploy-coolify.sh
```

### On R58 Device

```bash
# 1. Copy publisher script
scp deployment/r58-whip-publisher.sh linaro@r58.itagenten.no:/opt/

# 2. SSH to R58
ssh linaro@r58.itagenten.no

# 3. Start publishing
sudo chmod +x /opt/r58-whip-publisher.sh
sudo /opt/r58-whip-publisher.sh start
```

### Test

```bash
# Open in browser
https://vdo.itagenten.no/cam0
```

---

## 🔧 Customization

### Change Domain

Edit all configuration files and replace:
```
vdo.itagenten.no → your-domain.com
```

### Change Camera Names

In `mediamtx-coolify.yml`, update:
```yaml
paths:
  cam0: → mycam1:
  cam2: → mycam2:
  cam3: → mycam3:
```

### Adjust Bitrate

In `r58-whip-publisher.sh`, modify:
```bash
bitrate=6000  # Change to 4000 for lower bandwidth
```

---

## 📊 System Requirements

### Coolify Server

- **RAM**: 2GB minimum, 4GB recommended
- **CPU**: 2 cores minimum
- **Disk**: 10GB minimum
- **Bandwidth**: 100 Mbps+ recommended
- **OS**: Ubuntu 20.04+ or Debian 11+

### R58 Device

- **Upload Bandwidth**: 30 Mbps+ for 3 cameras
- **Services**: MediaMTX, preke-recorder running
- **GStreamer**: v1.18+ with WHIP plugin

---

## 🎯 Features

✅ **WHIP/WHEP Streaming**: Modern WebRTC protocols  
✅ **SSL/HTTPS**: Secure connections  
✅ **Multi-Camera**: Support for unlimited cameras  
✅ **VDO.ninja Integration**: Full mixer and director  
✅ **TCP Fallback**: Works through firewalls  
✅ **Monitoring**: API and logs  
✅ **Scalable**: Add more viewers/cameras easily

---

## 📞 Support

**Documentation**: See `DEPLOYMENT_GUIDE_COOLIFY.md`  
**Architecture**: See `VDO_ITAGENTEN_ARCHITECTURE.md`  
**Issues**: Check logs with `docker-compose logs -f`

---

**Version**: 1.0.0  
**Date**: December 25, 2025  
**Status**: ✅ Ready for Deployment



