# Testing Guide for Preke R58 Recorder

This guide covers testing the application on both macOS (development) and R58 (production).

## Prerequisites

### macOS Testing
- GStreamer installed via Homebrew
- Python 3.11+
- Virtual environment set up

### R58 Testing
- GStreamer with hardware acceleration plugins
- Python 3.11+
- Network access to R58 device

## Step 1: Setup (macOS)

```bash
cd preke-r58-recorder

# Run setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Verify GStreamer Installation

### macOS
```bash
# Check GStreamer version
gst-launch-1.0 --version

# Test videotestsrc (used in mock pipeline)
gst-launch-1.0 videotestsrc pattern=ball num-buffers=100 ! autovideosink

# Test x264 encoder
gst-inspect-1.0 x264enc
```

### R58
```bash
# Check GStreamer version
gst-launch-1.0 --version

# Test v4l2 source
gst-launch-1.0 v4l2src device=/dev/video0 ! video/x-raw ! autovideosink

# Check hardware encoders
gst-inspect-1.0 v4l2h264enc
gst-inspect-1.0 mpph264enc
gst-inspect-1.0 mpph265enc
```

## Step 3: Start the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Start the application
./start.sh

# Or directly:
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

## Step 4: Test API Endpoints

### 4.1 Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "platform": "macos"
}
```

### 4.2 Check Status (Before Recording)
```bash
curl http://localhost:8000/status
```

Expected response:
```json
{
  "cameras": {
    "cam0": {"status": "idle", "config": true},
    "cam1": {"status": "idle", "config": true},
    "cam2": {"status": "idle", "config": true},
    "cam3": {"status": "idle", "config": true}
  }
}
```

### 4.3 Start Recording
```bash
# Start recording for cam0
curl -X POST http://localhost:8000/record/start/cam0
```

Expected response:
```json
{
  "status": "started",
  "camera": "cam0"
}
```

### 4.4 Check Status (During Recording)
```bash
curl http://localhost:8000/status/cam0
```

Expected response:
```json
{
  "camera": "cam0",
  "status": "recording"
}
```

### 4.5 Verify Recording File (macOS)
```bash
# On macOS, check the recordings directory
ls -lh recordings/cam0/

# Or check the path specified in config.yml
# The file should be created and growing in size
```

### 4.6 Stop Recording
```bash
curl -X POST http://localhost:8000/record/stop/cam0
```

Expected response:
```json
{
  "status": "stopped",
  "camera": "cam0"
}
```

### 4.7 Verify Recording File
```bash
# Check file was created and has content
ls -lh recordings/cam0/*.mp4

# On macOS, you can play it with:
open recordings/cam0/*.mp4

# Or with ffplay:
ffplay recordings/cam0/*.mp4
```

## Step 5: Test Multiple Cameras (macOS)

```bash
# Start all cameras
curl -X POST http://localhost:8000/record/start/cam0
curl -X POST http://localhost:8000/record/start/cam1
curl -X POST http://localhost:8000/record/start/cam2
curl -X POST http://localhost:8000/record/start/cam3

# Check status of all
curl http://localhost:8000/status

# Stop all cameras
curl -X POST http://localhost:8000/record/stop/cam0
curl -X POST http://localhost:8000/record/stop/cam1
curl -X POST http://localhost:8000/record/stop/cam2
curl -X POST http://localhost:8000/record/stop/cam3
```

## Step 6: Test Error Handling

### Test Invalid Camera
```bash
curl -X POST http://localhost:8000/record/start/invalid_cam
```

Expected: 404 error

### Test Starting Already Recording Camera
```bash
curl -X POST http://localhost:8000/record/start/cam0
curl -X POST http://localhost:8000/record/start/cam0  # Should warn
```

## Step 7: Test on R58

### 7.1 Deploy to R58
```bash
# From macOS
./deploy.sh r58.local root
```

### 7.2 SSH into R58
```bash
ssh root@r58.local
```

### 7.3 Verify Hardware
```bash
# Check video devices
ls -l /dev/video*

# Test v4l2 source
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=30 ! \
  video/x-raw,width=1920,height=1080 ! \
  autovideosink
```

### 7.4 Test Hardware Encoders
```bash
# Test v4l2h264enc
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=100 ! \
  video/x-raw,width=1920,height=1080 ! \
  v4l2h264enc bitrate=5000 ! \
  h264parse ! \
  mp4mux ! \
  filesink location=/tmp/test.mp4

# Check if file was created
ls -lh /tmp/test.mp4
```

### 7.5 Test Application on R58
```bash
# Check service status
systemctl status preke-recorder.service

# View logs
journalctl -u preke-recorder.service -f

# Test API (from R58 or from macOS)
curl http://r58.local:8000/health
curl http://r58.local:8000/status
```

### 7.6 Test Recording on R58
```bash
# From macOS or R58
curl -X POST http://r58.local:8000/record/start/cam0

# Wait a few seconds, then check recording
curl http://r58.local:8000/status/cam0

# Check recording file on R58
ssh root@r58.local "ls -lh /var/recordings/cam0/"

# Stop recording
curl -X POST http://r58.local:8000/record/stop/cam0
```

## Step 8: Test MediaMTX Integration (Optional)

### 8.1 Enable MediaMTX in config.yml
```yaml
mediamtx:
  enabled: true
  rtsp_port: 8554

cameras:
  cam0:
    mediamtx_enabled: true
```

### 8.2 Start MediaMTX Service
```bash
# On R58
sudo systemctl start mediamtx.service
sudo systemctl status mediamtx.service
```

### 8.3 Start Recording with MediaMTX
```bash
curl -X POST http://r58.local:8000/record/start/cam0
```

### 8.4 Test RTSP Stream
```bash
# From another machine
ffplay rtsp://r58.local:8554/cam0

# Or with VLC
vlc rtsp://r58.local:8554/cam0
```

## Step 9: Performance Testing

### Test Recording Duration
```bash
# Start recording
curl -X POST http://localhost:8000/record/start/cam0

# Monitor file size growth
watch -n 1 'ls -lh recordings/cam0/*.mp4'

# After 60 seconds, stop
curl -X POST http://localhost:8000/record/stop/cam0

# Verify file size is reasonable (should be ~37MB for 60s at 5Mbps)
ls -lh recordings/cam0/*.mp4
```

### Test Multiple Simultaneous Recordings
```bash
# Start all 4 cameras
for i in 0 1 2 3; do
  curl -X POST http://localhost:8000/record/start/cam$i
done

# Monitor system resources
top
# or
htop

# Check all statuses
curl http://localhost:8000/status

# Stop all
for i in 0 1 2 3; do
  curl -X POST http://localhost:8000/record/stop/cam$i
done
```

## Troubleshooting

### Issue: GStreamer pipeline fails
- Check logs: `journalctl -u preke-recorder.service -f`
- Test pipeline manually with `gst-launch-1.0`
- Verify encoder plugins: `gst-inspect-1.0 <encoder-name>`

### Issue: No video devices on R58
- Check: `ls -l /dev/video*`
- Verify HDMI-IN is connected
- Check dmesg for device detection

### Issue: Recording file not created
- Check output directory permissions
- Verify path in config.yml
- Check disk space: `df -h`

### Issue: API not responding
- Check service is running: `systemctl status preke-recorder.service`
- Check port is open: `netstat -tuln | grep 8000`
- Check firewall rules

## Quick Test Script

Save this as `test_api.sh`:

```bash
#!/bin/bash
BASE_URL="http://localhost:8000"

echo "1. Health check..."
curl -s $BASE_URL/health | jq

echo -e "\n2. Status..."
curl -s $BASE_URL/status | jq

echo -e "\n3. Start cam0..."
curl -s -X POST $BASE_URL/record/start/cam0 | jq

echo -e "\n4. Wait 5 seconds..."
sleep 5

echo -e "\n5. Status..."
curl -s $BASE_URL/status | jq

echo -e "\n6. Stop cam0..."
curl -s -X POST $BASE_URL/record/stop/cam0 | jq

echo -e "\n7. Final status..."
curl -s $BASE_URL/status | jq
```

Run with: `chmod +x test_api.sh && ./test_api.sh`

