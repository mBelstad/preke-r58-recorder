# R58 Testing Guide

This guide covers testing the application on the Mekotronics R58 4x4 3S device.

## Prerequisites

1. **R58 device** with:
   - Network connectivity (SSH access)
   - HDMI-IN devices connected to /dev/video0-3
   - Root or sudo access

2. **From your macOS machine**:
   - SSH access to R58
   - Git repository access (already set up)

## Step 1: Verify R58 Access

```bash
# Test SSH connection
ssh root@r58.local

# Or if using different hostname/IP
ssh root@<r58_ip_address>
```

## Step 2: Check Hardware on R58

### 2.1 Verify Video Devices
```bash
# SSH into R58
ssh root@r58.local

# List video devices
ls -l /dev/video*

# You should see /dev/video0, /dev/video1, /dev/video2, /dev/video3
```

### 2.2 Test Video Capture
```bash
# Test v4l2 source (replace video0 with your device)
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=30 ! \
  video/x-raw,width=1920,height=1080 ! \
  autovideosink

# If autovideosink doesn't work (no display), test with filesink
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=100 ! \
  video/x-raw,width=1920,height=1080 ! \
  jpegenc ! \
  multifilesink location=/tmp/test_%02d.jpg
```

### 2.3 Verify Hardware Encoders
```bash
# Check available encoders
gst-inspect-1.0 v4l2h264enc
gst-inspect-1.0 mpph264enc
gst-inspect-1.0 mpph265enc

# Test hardware encoding
gst-launch-1.0 v4l2src device=/dev/video0 num-buffers=100 ! \
  video/x-raw,width=1920,height=1080 ! \
  v4l2h264enc bitrate=5000 ! \
  h264parse ! \
  mp4mux ! \
  filesink location=/tmp/test_hw.mp4

# Verify file was created
ls -lh /tmp/test_hw.mp4
```

## Step 3: Deploy Application to R58

### 3.1 From macOS - Deploy Script
```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"

# Deploy (replace with your R58 hostname/IP)
./deploy.sh r58.local root

# Or with custom hostname
./deploy.sh <r58_ip_address> root
```

### 3.2 Manual Deployment (Alternative)

If deploy script doesn't work, deploy manually:

```bash
# On R58
ssh root@r58.local

# Create directory
mkdir -p /opt/preke-r58-recorder
cd /opt/preke-r58-recorder

# Clone repository
git clone https://github.com/mBelstad/preke-r58-recorder.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create recordings directory
mkdir -p /var/recordings/{cam0,cam1,cam2,cam3}

# Install systemd service
cp preke-recorder.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable preke-recorder.service
systemctl start preke-recorder.service
```

## Step 4: Verify Installation

### 4.1 Check Service Status
```bash
# On R58
systemctl status preke-recorder.service

# View logs
journalctl -u preke-recorder.service -f
```

### 4.2 Check API is Running
```bash
# From macOS or R58
curl http://r58.local:8000/health

# Expected response:
# {"status":"healthy","platform":"r58"}
```

## Step 5: Test API Endpoints

### 5.1 Health Check
```bash
curl http://r58.local:8000/health
```

### 5.2 Check Status
```bash
curl http://r58.local:8000/status | python3 -m json.tool
```

### 5.3 Start Recording
```bash
# Start recording for cam0
curl -X POST http://r58.local:8000/record/start/cam0

# Check status
curl http://r58.local:8000/status/cam0
```

### 5.4 Monitor Recording
```bash
# On R58, check if file is being created
ssh root@r58.local "watch -n 1 'ls -lh /var/recordings/cam0/'"

# Or check file size
ssh root@r58.local "ls -lh /var/recordings/cam0/"
```

### 5.5 Stop Recording
```bash
curl -X POST http://r58.local:8000/record/stop/cam0

# Verify file was finalized
ssh root@r58.local "ls -lh /var/recordings/cam0/"
```

## Step 6: Test Multiple Cameras

```bash
# Start all cameras
for i in 0 1 2 3; do
  curl -X POST http://r58.local:8000/record/start/cam$i
  sleep 1
done

# Check all statuses
curl http://r58.local:8000/status | python3 -m json.tool

# Monitor all recordings
ssh root@r58.local "watch -n 1 'du -sh /var/recordings/*'"

# Stop all cameras
for i in 0 1 2 3; do
  curl -X POST http://r58.local:8000/record/stop/cam$i
  sleep 1
done
```

## Step 7: Verify Recordings

### 7.1 Check Files
```bash
# On R58
ls -lh /var/recordings/cam0/
ls -lh /var/recordings/cam1/
ls -lh /var/recordings/cam2/
ls -lh /var/recordings/cam3/
```

### 7.2 Test Playback
```bash
# Copy file to macOS for testing
scp root@r58.local:/var/recordings/cam0/*.mp4 ~/Downloads/

# Play on macOS
open ~/Downloads/*.mp4

# Or use ffplay
ffplay ~/Downloads/*.mp4
```

### 7.3 Verify File Integrity
```bash
# Check file info
ffprobe /var/recordings/cam0/*.mp4

# Check duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 /var/recordings/cam0/*.mp4
```

## Step 8: Performance Testing

### 8.1 Monitor System Resources
```bash
# On R58, monitor CPU and memory
top

# Or use htop if available
htop

# Monitor disk I/O
iostat -x 1
```

### 8.2 Test Long Recording
```bash
# Start recording
curl -X POST http://r58.local:8000/record/start/cam0

# Wait 60 seconds
sleep 60

# Stop recording
curl -X POST http://r58.local:8000/record/stop/cam0

# Check file size (should be ~37MB for 60s at 5Mbps)
ssh root@r58.local "ls -lh /var/recordings/cam0/"
```

## Step 9: Troubleshooting

### Issue: Service won't start
```bash
# Check logs
journalctl -u preke-recorder.service -n 50

# Check for errors
journalctl -u preke-recorder.service | grep -i error
```

### Issue: No video devices
```bash
# Check dmesg for device detection
dmesg | grep video

# Check v4l2 devices
v4l2-ctl --list-devices
```

### Issue: Encoder not found
```bash
# List all GStreamer plugins
gst-inspect-1.0 | grep -i h264
gst-inspect-1.0 | grep -i mpp

# Try alternative encoder in config.yml
# Change from v4l2h264enc to mpph264enc
```

### Issue: Permission denied
```bash
# Fix recordings directory permissions
chmod 755 /var/recordings
chmod 755 /var/recordings/*

# Or run service as different user (edit service file)
```

### Issue: Pipeline fails
```bash
# Test pipeline manually
gst-launch-1.0 v4l2src device=/dev/video0 ! \
  video/x-raw,width=1920,height=1080 ! \
  v4l2h264enc bitrate=5000 ! \
  h264parse ! \
  mp4mux ! \
  filesink location=/tmp/test.mp4

# Check for specific errors
gst-launch-1.0 --gst-debug=3 v4l2src device=/dev/video0 ! autovideosink
```

## Step 10: Quick Test Script

Create `test_r58.sh` on macOS:

```bash
#!/bin/bash
R58_HOST="${1:-r58.local}"
BASE_URL="http://${R58_HOST}:8000"

echo "=== Testing R58 Recorder ==="
echo "Host: $R58_HOST"
echo ""

echo "1. Health check..."
curl -s $BASE_URL/health | python3 -m json.tool
echo ""

echo "2. Status..."
curl -s $BASE_URL/status | python3 -m json.tool
echo ""

echo "3. Starting cam0..."
curl -s -X POST $BASE_URL/record/start/cam0 | python3 -m json.tool
echo ""

echo "4. Waiting 10 seconds..."
sleep 10
echo ""

echo "5. Status..."
curl -s $BASE_URL/status/cam0 | python3 -m json.tool
echo ""

echo "6. Checking recording file..."
ssh root@${R58_HOST} "ls -lh /var/recordings/cam0/ 2>/dev/null || echo 'No files yet'"
echo ""

echo "7. Stopping cam0..."
curl -s -X POST $BASE_URL/record/stop/cam0 | python3 -m json.tool
echo ""

echo "8. Final file check..."
ssh root@${R58_HOST} "ls -lh /var/recordings/cam0/"
echo ""

echo "=== Test Complete ==="
```

Run with: `./test_r58.sh r58.local`

## Next Steps

1. ✅ Verify all 4 cameras work
2. ✅ Test different resolutions
3. ✅ Test different bitrates
4. ✅ Test H.265 encoding (cam3)
5. ✅ Enable MediaMTX streaming (optional)
6. ✅ Set up automatic startup on boot
7. ✅ Configure log rotation
8. ✅ Set up monitoring/alerts

