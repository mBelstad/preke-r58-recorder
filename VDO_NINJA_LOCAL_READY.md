# VDO.ninja Local Ingest - Ready to Test

## ✅ Setup Complete

The VDO.ninja local signaling server has been fixed to support global room routing, 
ensuring compatibility between VDO.ninja browser and raspberry.ninja publishers.

### Active Publishers

The following cameras are publishing to VDO.ninja:

| Camera | Stream ID | Device |
|--------|-----------|--------|
| cam1 | r58-cam1808d64 | /dev/video60 (HDMI N60) |
| cam2 | r58-cam2808d64 | /dev/video11 (HDMI N11) |
| cam3 | r58-cam3808d64 | /dev/video22 (HDMI N21) |
| cam1-test | r58-cam1-test808d64 | /dev/video60 (test) |

## 🎬 Access URLs (Local Network Only)

### Director View (Mixer)
Access the full mixer/director interface:

```
https://192.168.1.24:8443/?director=r58studio&wss=192.168.1.24:8443
```

### Individual Stream Views
View specific camera streams:

- **Camera 1**: `https://192.168.1.24:8443/?view=r58-cam1808d64&wss=192.168.1.24:8443`
- **Camera 2**: `https://192.168.1.24:8443/?view=r58-cam2808d64&wss=192.168.1.24:8443`
- **Camera 3**: `https://192.168.1.24:8443/?view=r58-cam3808d64&wss=192.168.1.24:8443`

### Scene View (OBS Integration)
For importing into OBS as a browser source:

```
https://192.168.1.24:8443/?scene&room=r58studio&wss=192.168.1.24:8443
```

## ⚠️ Notes

1. **SSL Certificate Warning**: You'll see a certificate warning because the R58 uses 
   a self-signed certificate. Click "Advanced" → "Proceed to 192.168.1.24".

2. **Stream ID Suffix**: The `808d64` suffix is automatically added by raspberry.ninja 
   as a hash for uniqueness.

3. **Local Network Only**: These URLs only work when connected to the same network as 
   the R58 device (192.168.1.24).

4. **Global Room**: All connections now use a global room for cross-client compatibility, 
   so the director can see publishers even if their room hashes differ.

## 🔧 Technical Details

### Signaling Server Changes
The VDO.ninja signaling server was updated to:
- Add all connections to a `__global__` room automatically
- Support streamID-based routing
- Handle seed/play requests without requiring matching room hashes

### Publisher Configuration
Each raspberry.ninja publisher is configured with:
- `--server wss://localhost:8443` - Local signaling server
- `--room r58studio` - Room name for grouping
- `--streamid r58-camX` - Unique stream identifier
- `--h264 --bitrate 8000` - H.264 encoding at 8 Mbps

## 📝 Verification

To verify publishers are connected:
```bash
ssh linaro@r58.itagenten.no
journalctl -u vdo-ninja --no-pager -n 20
```

You should see:
- "Publisher seeding: r58-cam1808d64"
- "Publisher seeding: r58-cam2808d64"
- etc.

---
Created: 2025-12-22

