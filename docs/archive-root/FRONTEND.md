# Frontend Setup Guide

The web frontend is now integrated into the FastAPI application.

## Features

- **Camera Controls**: Start/stop recording for each camera
- **Live Preview**: View HDMI input stream (requires MediaMTX)
- **Recording Management**: List, view, and download recordings
- **Real-time Status**: Auto-refreshing camera status

## Access

Once the application is running, access the frontend at:

```
http://<r58_ip>:8000/
```

The API documentation is available at:
```
http://<r58_ip>:8000/docs
```

## MediaMTX Integration (Optional)

To enable live streaming preview:

### 1. Install MediaMTX

```bash
# On R58
wget https://github.com/bluenviron/mediamtx/releases/latest/download/mediamtx_v1.5.1_linux_arm64v8.tar.gz
tar -xzf mediamtx_v1.5.1_linux_arm64v8.tar.gz
sudo mv mediamtx /usr/local/bin/
sudo chmod +x /usr/local/bin/mediamtx
```

### 2. Configure MediaMTX

Copy the `mediamtx.yml` template to `/opt/mediamtx/mediamtx.yml` and adjust as needed.

### 3. Enable Streaming in config.yml

```yaml
mediamtx:
  enabled: true
  rtsp_port: 8554

cameras:
  cam0:
    mediamtx_enabled: true
```

### 4. Start MediaMTX

```bash
sudo systemctl start mediamtx.service
```

### 5. Update Pipeline for Streaming

The pipeline will automatically tee the stream to MediaMTX when `mediamtx_enabled: true` is set.

## Alternative: Direct HLS Streaming

If you prefer not to use MediaMTX, you can modify the frontend to use direct HLS streaming from GStreamer, or use Vdo.Ninja for WebRTC-based streaming.

## Browser Compatibility

- Chrome/Edge: Full support, HLS via hls.js
- Firefox: Full support
- Safari: Native HLS support

For RTSP streams, use VLC or similar players with the RTSP URL:
```
rtsp://<r58_ip>:8554/cam0
```

