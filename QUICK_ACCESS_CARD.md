# 🎥 R58 Remote Streaming - Quick Access Card

**Last Updated**: December 25, 2025  
**Status**: ✅ WORKING

---

## 🌐 Watch Cameras Remotely (Works from Anywhere)

### MediaMTX Direct Viewer (Instant Access)
```
Camera 0: http://65.109.32.111:18889/cam0
Camera 2: http://65.109.32.111:18889/cam2
Camera 3: http://65.109.32.111:18889/cam3
```

### VDO.ninja WHEP Viewer (Advanced Features)
```
Camera 0: http://insecure.vdo.ninja/?view=cam0&whep=http://65.109.32.111:18889/cam0/whep
Camera 2: http://insecure.vdo.ninja/?view=cam2&whep=http://65.109.32.111:18889/cam2/whep
Camera 3: http://insecure.vdo.ninja/?view=cam3&whep=http://65.109.32.111:18889/cam3/whep
```

---

## 🏠 Local Access (On R58 Network)

### Direct Camera Access
```
http://192.168.1.24:8889/cam0
http://192.168.1.24:8889/cam2
http://192.168.1.24:8889/cam3
```

### Custom Mixer
```
http://192.168.1.24:8000/static/mediamtx_mixer.html
```

### Recorder API
```
http://192.168.1.24:8000/api/status
```

---

## 🔧 Quick Troubleshooting

### If streams don't load:

1. **Check service status** (via SSH):
   ```bash
   ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" linaro@r58.itagenten.no
   sudo systemctl status mediamtx preke-recorder frpc
   ```

2. **Restart services**:
   ```bash
   sudo systemctl restart mediamtx preke-recorder
   ```

3. **Check camera status**:
   ```bash
   curl http://localhost:9997/v3/paths/list | grep cam
   ```

---

## 📱 Use in OBS Studio

1. Add **Browser Source**
2. URL: `http://65.109.32.111:18889/cam0` (or cam2, cam3)
3. Width: 1920, Height: 1080
4. Check "Control audio via OBS"

---

## 🎯 What's Working

✅ All 3 cameras streaming remotely via WebRTC/TCP  
✅ Works through FRP tunnel (no VPN needed)  
✅ Low latency (~1-2 seconds remote, ~200-500ms local)  
✅ MediaMTX v1.15.5 with TCP WebRTC support  
✅ VDO.ninja WHEP integration  
✅ Custom mixer for local multi-cam viewing

---

## ⚡ Key Technical Details

- **MediaMTX TCP WebRTC** on port 8190 (proxied through FRP)
- **Resolution**: 1920x1080 @ 30fps
- **Codec**: H.264, ~8 Mbps per camera
- **No authentication** (add later for security)

---

## 📞 Support

**SSH Access**: `ssh -o ProxyCommand="cloudflared access ssh --hostname r58.itagenten.no" linaro@r58.itagenten.no`  
**Password**: linaro  
**VPS IP**: 65.109.32.111  
**R58 Local IP**: 192.168.1.24

---

**BOOKMARK THIS PAGE FOR QUICK ACCESS TO YOUR CAMERA STREAMS!** 📌

