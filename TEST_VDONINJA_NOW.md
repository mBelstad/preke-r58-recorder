# Test VDO.ninja Remote Mixing - Ready Now!

**Status**: ✅ **READY TO TEST**

---

## 🎬 Your Cameras Are Live!

The R58 cameras are now publishing to VDO.ninja with TURN relay configured.

---

## 🔗 Access URLs

### View Individual Cameras

Open these URLs in your browser:

**Camera 1** (HDMI N60):
```
https://vdo.ninja/?view=r58-cam1&wss=wss.vdo.ninja:443
```

**Camera 2** (HDMI N11):
```
https://vdo.ninja/?view=r58-cam2&wss=wss.vdo.ninja:443
```

**Camera 3** (HDMI N21):
```
https://vdo.ninja/?view=r58-cam3&wss=wss.vdo.ninja:443
```

### Director/Mixer View

Open this to see all cameras and mix them:
```
https://vdo.ninja/?director=r58studio&wss=wss.vdo.ninja:443
```

---

## 🎯 What You Can Do Now

### 1. View Cameras
- Open any of the camera view URLs above
- You should see the live feed
- Low latency WebRTC streaming

### 2. Mix Cameras (Director View)
- Open the director URL
- You'll see all 3 cameras
- Drag and drop to arrange
- Add scenes, transitions, etc.
- Mix in real-time!

### 3. Test TURN Relay
- The cameras are using Cloudflare TURN
- WebRTC will work even through NAT/firewalls
- TURN credentials refresh every 12 hours automatically

---

## 🏗️ Architecture

```
R58 Cameras (at venue)
    ↓
raspberry.ninja publishers
    ↓ WebRTC + TURN
Public VDO.ninja Server (wss://wss.vdo.ninja:443)
    ↓ WebRTC + TURN
Your Browser (anywhere)
    ↓
Mix and control remotely!
```

**Key Points**:
- ✅ Cameras publish to public VDO.ninja
- ✅ TURN relay configured (NAT traversal)
- ✅ You can access from anywhere
- ✅ Low latency WebRTC
- ✅ No Cloudflare Tunnel interference

---

## 📊 Service Status

All camera publishers are running:
- ✅ ninja-publish-cam1: Active (r58-cam1)
- ✅ ninja-publish-cam2: Active (r58-cam2)
- ✅ ninja-publish-cam3: Active (r58-cam3)

Configuration:
- Server: `wss://wss.vdo.ninja:443` (public)
- Room: `r58studio`
- TURN: Cloudflare TURN with auto-refresh
- Bitrate: 8000 kbps
- Resolution: 1920x1080 @ 30fps

---

## 🎥 Recording the Mix

### Option 1: OBS on Your PC
1. Open VDO.ninja director
2. Open OBS Studio
3. Add Browser Source
4. Use the director URL
5. Record in OBS

### Option 2: VDO.ninja Built-in Recording
1. In director view
2. Click "Record" button
3. Downloads to your browser

### Option 3: Stream Back to R58 (Future)
- Configure mix output to publish back via WHIP
- R58 records the mix locally
- Requires additional setup

---

## 🧪 Test It Now!

**Open this URL in your browser**:
```
https://vdo.ninja/?director=r58studio&wss=wss.vdo.ninja:443
```

You should see:
- All 3 cameras available
- Live video feeds
- Mixing controls
- Low latency

---

## 🔧 Troubleshooting

### No cameras visible
- Check publisher logs: `./connect-r58.sh "sudo journalctl -u ninja-publish-cam1 -f"`
- Verify TURN credentials: `curl https://api.r58.itagenten.no/turn-credentials`

### High latency
- TURN relay adds ~50-200ms (normal)
- Still much better than HLS (1-3 seconds)

### Connection fails
- Check if cameras have signal: `./connect-r58.sh "sudo systemctl status ninja-publish-cam*"`
- Verify VDO.ninja server: `curl -I https://vdo.ninja`

---

## ✅ What's Working

- ✅ Cameras publishing to VDO.ninja
- ✅ TURN relay configured
- ✅ WebRTC connections established
- ✅ Remote access working
- ✅ No Cloudflare Tunnel interference

---

**Go ahead and test the director view!** 🎬

Open: `https://vdo.ninja/?director=r58studio&wss=wss.vdo.ninja:443`

