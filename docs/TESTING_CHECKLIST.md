# Testing Checklist - Stability Restoration

**Date:** December 30, 2025  
**Architecture:** Single-Encoder + Subscriber Recording

---

## Pre-Deployment Checklist

- [x] Code changes completed
  - [x] Increased ingest bitrate to 18Mbps
  - [x] Switched to matroskamux for MKV files
  - [x] Verified read-only signal detection
- [x] Service configuration verified (uses src/main.py)
- [x] Deployment script created
- [x] Documentation updated

---

## Deployment Checklist

### 1. Connect to R58

```bash
ssh -i ~/.ssh/r58_key linaro@192.168.1.24
```

- [ ] SSH connection successful
- [ ] Device responds

### 2. Navigate to Deployment Directory

```bash
cd /opt/preke-r58-recorder
```

- [ ] Directory exists
- [ ] Git repository is clean

### 3. Run Deployment Script

```bash
chmod +x scripts/deploy-stability-fix.sh
sudo ./scripts/deploy-stability-fix.sh
```

- [ ] Script runs without errors
- [ ] Service restarts successfully
- [ ] API responds on port 8000

---

## Basic Functionality Tests (15 minutes)

### Test 1: Ingest Status

```bash
curl http://localhost:8000/api/ingest/status | jq
```

**Expected:**
- [ ] All enabled cameras show `"status": "streaming"`
- [ ] Resolution detected correctly (e.g., 1920x1080)
- [ ] Stream URLs present

**If Failed:**
- Check logs: `journalctl -u preke-r58-recorder -n 50`
- Verify HDMI cables connected
- Check device initialization: `v4l2-ctl -d /dev/video0 --get-fmt-video`

### Test 2: Preview Streams

Open in browser: `http://192.168.1.24:8000/static/test_cameras.html`

**Expected:**
- [ ] All camera previews load
- [ ] Video plays smoothly (no stuttering)
- [ ] Latency < 2 seconds

**If Failed:**
- Check MediaMTX: `curl http://localhost:8889/`
- Check WHEP endpoints: `curl http://localhost:8889/cam0/whep`

### Test 3: Start Recording

```bash
# Start recording on all cameras
curl -X POST http://localhost:8000/api/recording/start_all

# Check status
curl http://localhost:8000/api/recording/status | jq
```

**Expected:**
- [ ] All cameras show recording active
- [ ] Recording files created in `/mnt/sdcard/recordings/`

**Verify:**
```bash
ls -lh /mnt/sdcard/recordings/cam0/
ls -lh /mnt/sdcard/recordings/cam2/
ls -lh /mnt/sdcard/recordings/cam3/
```

- [ ] Files exist with `.mkv` extension
- [ ] File sizes increasing over time

### Test 4: Recording Quality

Wait 2 minutes, then:

```bash
# Check file size growth
watch -n 5 'ls -lh /mnt/sdcard/recordings/cam0/'
```

**Expected file size growth (18Mbps):**
- 1 minute: ~135 MB
- 2 minutes: ~270 MB
- 5 minutes: ~675 MB

- [ ] File size matches expected growth rate
- [ ] No errors in logs during recording

### Test 5: Stop Recording

```bash
curl -X POST http://localhost:8000/api/recording/stop_all
```

**Expected:**
- [ ] Recording stops cleanly
- [ ] Files finalized (no corruption)
- [ ] Preview continues streaming

**Verify files are playable:**
```bash
# Copy one file to your machine
scp -i ~/.ssh/r58_key linaro@192.168.1.24:/mnt/sdcard/recordings/cam0/recording_*.mkv ~/Desktop/

# Open in DaVinci Resolve or VLC
# - [ ] File opens without errors
# - [ ] Video plays smoothly
# - [ ] Duration matches recording time
```

---

## Stability Tests (1 hour)

### Test 6: Long-Running Stability

```bash
# Start all recordings
curl -X POST http://localhost:8000/api/recording/start_all

# Monitor logs in real-time
journalctl -u preke-r58-recorder -f
```

**Monitor for 1 hour:**
- [ ] No kernel panics
- [ ] No VPU errors
- [ ] No pipeline crashes
- [ ] No "queue busy" errors
- [ ] CPU usage stable (~10-15%)
- [ ] VPU frequency stable

**Check resource usage:**
```bash
# CPU usage
htop

# VPU frequency
watch -n 1 'cat /sys/class/devfreq/fdab0000.rkvenc-core/cur_freq'
```

**Expected:**
- [ ] CPU: 10-20% average
- [ ] VPU freq: Stable (not constantly at max)
- [ ] Memory: < 2GB used
- [ ] No memory leaks

### Test 7: Concurrent Recording + Preview

While recording is active:

```bash
# Open preview in browser
# http://192.168.1.24:8000/static/test_cameras.html
```

**Expected:**
- [ ] Preview continues smoothly during recording
- [ ] No dropped frames
- [ ] Latency remains low (< 2 seconds)

---

## Hot-Plug Tests (30 minutes)

### Test 8: Signal Loss (Disconnect Cable)

**Setup:**
1. Start recording on all cameras
2. Verify all streaming

**Test:**
```bash
# Disconnect HDMI cable from cam2 (video11)
# Wait 30 seconds
# Check logs and status
journalctl -u preke-r58-recorder -n 50
curl http://localhost:8000/api/ingest/status | jq '.cam2'
```

**Expected:**
- [ ] System does NOT crash
- [ ] cam2 shows `"status": "no_signal"`
- [ ] Other cameras continue streaming
- [ ] Recording continues on other cameras
- [ ] Logs show graceful signal loss handling

### Test 9: Signal Recovery (Reconnect Cable)

**Test:**
```bash
# Reconnect HDMI cable to cam2
# Wait 30 seconds
# Check status
curl http://localhost:8000/api/ingest/status | jq '.cam2'
```

**Expected:**
- [ ] cam2 automatically recovers
- [ ] cam2 shows `"status": "streaming"`
- [ ] Resolution detected correctly
- [ ] Preview resumes automatically
- [ ] No errors in logs

### Test 10: Multiple Hot-Plug Events

**Test:**
```bash
# Disconnect and reconnect each camera in sequence:
# 1. Disconnect cam0, wait 20s, reconnect, wait 20s
# 2. Disconnect cam2, wait 20s, reconnect, wait 20s
# 3. Disconnect cam3, wait 20s, reconnect, wait 20s
```

**Expected:**
- [ ] System remains stable throughout
- [ ] All cameras recover successfully
- [ ] No cumulative errors or memory leaks

---

## Stress Tests (Optional)

### Test 11: Resolution Changes

**Test:**
```bash
# Change HDMI source resolution (e.g., 1080p → 4K → 1080p)
# Monitor logs
journalctl -u preke-r58-recorder -f
```

**Expected:**
- [ ] System detects resolution change
- [ ] Pipeline restarts gracefully
- [ ] New resolution detected correctly
- [ ] Recording continues with new resolution

### Test 12: All Cameras 4K Input

**Test:**
```bash
# Connect 4K sources to all cameras
# Start recording
curl -X POST http://localhost:8000/api/recording/start_all
```

**Expected:**
- [ ] All cameras capture 4K input
- [ ] RGA downscales to 1080p
- [ ] CPU usage remains reasonable (~15-20%)
- [ ] No VPU overload

---

## Performance Benchmarks

### Baseline Metrics (4 Cameras, 1080p, 18Mbps)

| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| CPU Usage | < 20% | ___% | [ ] |
| VPU Frequency | Stable | ___MHz | [ ] |
| Memory Usage | < 2GB | ___GB | [ ] |
| Recording Bitrate | 18Mbps | ___Mbps | [ ] |
| Preview Latency | < 2s | ___s | [ ] |
| File Size (5min) | ~675MB | ___MB | [ ] |

### Uptime Test

| Duration | Status | Notes |
|----------|--------|-------|
| 15 minutes | [ ] Pass / [ ] Fail | |
| 1 hour | [ ] Pass / [ ] Fail | |
| 4 hours | [ ] Pass / [ ] Fail | |
| 24 hours | [ ] Pass / [ ] Fail | |

---

## Failure Scenarios

### If Service Won't Start

1. Check logs: `journalctl -u preke-r58-recorder -n 100`
2. Check Python errors: `sudo systemctl status preke-r58-recorder`
3. Test manually: `/opt/preke-r58-recorder/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000`

### If Cameras Won't Stream

1. Check device initialization:
   ```bash
   v4l2-ctl -d /dev/video0 --get-fmt-video
   v4l2-ctl -d /dev/video11 --get-fmt-video
   v4l2-ctl -d /dev/video22 --get-fmt-video
   ```

2. Check MediaMTX:
   ```bash
   curl http://localhost:8889/
   ```

3. Re-initialize devices:
   ```bash
   sudo /opt/preke-r58-recorder/scripts/init_hdmi_inputs.sh
   ```

### If Recording Fails

1. Check disk space: `df -h /mnt/sdcard`
2. Check permissions: `ls -ld /mnt/sdcard/recordings/`
3. Check MediaMTX streams: `curl http://localhost:8554/cam0`

### If System Crashes

1. Check kernel logs: `dmesg | tail -100`
2. Look for VPU errors: `dmesg | grep -i vpu`
3. Check for "queue busy" errors: `dmesg | grep -i "queue busy"`

---

## Sign-Off

### Deployment
- [ ] All code changes deployed
- [ ] Service running on src/main.py
- [ ] API responding

### Basic Functionality
- [ ] All cameras streaming
- [ ] Recording works
- [ ] MKV files playable

### Stability
- [ ] 1+ hour without crashes
- [ ] Hot-plug works
- [ ] Resource usage acceptable

### Ready for Production
- [ ] All tests passed
- [ ] Documentation updated
- [ ] Team notified

**Tested by:** _________________  
**Date:** _________________  
**Signature:** _________________

---

## Notes

Use this space for any observations, issues, or recommendations:

```
[Your notes here]
```

