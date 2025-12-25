# Production Monitoring Guide
**R58 Recorder - Real-World Usage & Monitoring**

## 🎯 Purpose
This guide helps you monitor and validate the R58 recorder in production use, ensuring quality and reliability.

---

## 📊 Monitoring Tools

### 1. Real-Time Monitor Script
**Location**: `monitor_recording.sh`

**Usage**:
```bash
./monitor_recording.sh
```

**What it shows**:
- ✅ Recording status (active/idle)
- ✅ Session ID
- ✅ Duration (HH:MM:SS)
- ✅ Disk space remaining
- ✅ Camera statuses
- ✅ Estimated file size

**When to use**: During long recordings to monitor progress

---

### 2. API Status Checks

**Quick Status Check**:
```bash
curl -s http://recorder.itagenten.no/api/trigger/status | python3 -m json.tool
```

**Check Disk Space**:
```bash
curl -s http://recorder.itagenten.no/api/trigger/status | \
  python3 -c "import sys, json; d=json.load(sys.stdin)['disk']; print(f\"Free: {d['free_gb']:.1f} GB ({100-d['percent_used']:.1f}% free)\")"
```

**Check Recording Duration**:
```bash
curl -s http://recorder.itagenten.no/api/trigger/status | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Duration: {data['duration']} seconds\" if data['active'] else 'Not recording')"
```

---

### 3. Web Dashboard
**URL**: http://recorder.itagenten.no/

**Features**:
- Live camera previews
- Start/Stop recording buttons
- Session ID display
- Disk space indicator (color-coded)
- Recording duration counter

**Color Codes**:
- 🟢 Green: > 10 GB free (healthy)
- 🟠 Orange: 5-10 GB free (warning)
- 🔴 Red: < 5 GB free (critical)

---

### 4. Library Page
**URL**: http://recorder.itagenten.no/static/library.html

**Features**:
- Browse all recordings by date
- Session grouping
- Copy session IDs
- Download metadata
- Video thumbnails and playback

---

## 📈 Key Metrics to Monitor

### During Recording

| Metric | How to Check | Good Value | Warning Value |
|--------|--------------|------------|---------------|
| **Duration** | API status | Any | N/A |
| **Disk Space** | API status | > 10 GB | < 5 GB |
| **Camera Status** | API status | "recording" | "idle" or "error" |
| **File Growth** | SSH + ls -lh | Growing | Stuck at same size |

### After Recording

| Metric | How to Check | Expected Value |
|--------|--------------|----------------|
| **File Size** | ls -lh | ~3-5 GB/hour/camera |
| **Bitrate** | ffprobe | 12-15 Mbps |
| **Duration** | ffprobe | Matches recording time |
| **Keyframes** | ffprobe | ~1 per second |
| **Codec** | ffprobe | H.264 |
| **Resolution** | ffprobe | 1920x1080 |

---

## 🔍 Quality Validation

### Check Recording Quality

**1. File Properties**:
```bash
# On device
ssh linaro@r58.itagenten.no
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,width,height,r_frame_rate \
  /mnt/sdcard/recordings/cam1/recording_YYYYMMDD_HHMMSS.mp4
```

**2. Bitrate Analysis**:
```bash
# Get actual bitrate
ffprobe -v error -show_entries format=bit_rate -of default=noprint_wrappers=1:nokey=1 \
  /mnt/sdcard/recordings/cam1/recording_YYYYMMDD_HHMMSS.mp4 | \
  awk '{print $1/1000000 " Mbps"}'
```

**3. Keyframe Count**:
```bash
# Count I-frames
ffprobe -v quiet -show_frames -select_streams v:0 \
  /mnt/sdcard/recordings/cam1/recording_YYYYMMDD_HHMMSS.mp4 | \
  grep "pict_type=I" | wc -l
```

**Expected**: ~1 keyframe per second (60 keyframes for 60-second recording)

---

## 📋 Production Testing Checklist

### Short Recording Test (5 minutes)
- [ ] Start recording via dashboard or API
- [ ] Verify all 3 cameras show "recording" status
- [ ] Check disk space is decreasing
- [ ] Monitor for 5 minutes
- [ ] Stop recording
- [ ] Verify session metadata created
- [ ] Check file sizes (~1-2 GB per camera)
- [ ] Verify bitrate is 12-15 Mbps
- [ ] Test playback in browser
- [ ] Test opening in DaVinci Resolve

### Medium Recording Test (30 minutes)
- [ ] Start recording
- [ ] Check status every 5 minutes
- [ ] Monitor disk space usage
- [ ] Verify files are growing consistently
- [ ] Stop recording
- [ ] Check file sizes (~6-9 GB per camera)
- [ ] Verify no corruption
- [ ] Test scrubbing in DaVinci Resolve

### Long Recording Test (2+ hours)
- [ ] Start recording
- [ ] Monitor periodically (every 15 minutes)
- [ ] Check for any pipeline failures
- [ ] Verify disk space doesn't run out
- [ ] Stop recording
- [ ] Check file sizes (~24-36 GB per camera)
- [ ] Verify session metadata complete
- [ ] Test editing workflow

---

## 🚨 Troubleshooting

### Issue: Recording Won't Start

**Check**:
```bash
# Check disk space
curl -s http://recorder.itagenten.no/api/trigger/status | grep free_gb

# Check camera status
ssh linaro@r58.itagenten.no
ps aux | grep gst-launch
```

**Solutions**:
- Free up disk space (need > 10 GB)
- Restart service: `sudo systemctl restart preke-r58-recorder`
- Check camera connections

---

### Issue: Low Bitrate

**Check**:
```bash
ffprobe -v error -show_entries format=bit_rate \
  /mnt/sdcard/recordings/cam1/recording_*.mp4
```

**Solutions**:
- Normal for short recordings
- Check longer recordings (30+ minutes)
- If consistently low, increase target bitrate in config

---

### Issue: File Not Growing

**Check**:
```bash
# Watch file size
ssh linaro@r58.itagenten.no
watch -n 5 'ls -lh /mnt/sdcard/recordings/cam1/recording_*.mp4 | tail -1'
```

**Solutions**:
- Check if recording is actually active
- Check GStreamer pipeline: `ps aux | grep x264enc`
- Restart recording

---

### Issue: Disk Space Running Out

**Check**:
```bash
curl -s http://recorder.itagenten.no/api/trigger/status | grep free_gb
```

**Solutions**:
- Stop recording immediately
- Delete old recordings
- Move files to external storage
- Increase disk space

---

## 📊 Performance Benchmarks

### Expected Performance

| Duration | File Size (per camera) | Total (3 cameras) | Disk Space Used |
|----------|------------------------|-------------------|-----------------|
| 5 min    | ~1-2 GB               | ~3-6 GB          | ~6 GB           |
| 30 min   | ~6-9 GB               | ~18-27 GB        | ~27 GB          |
| 1 hour   | ~12-18 GB             | ~36-54 GB        | ~54 GB          |
| 2 hours  | ~24-36 GB             | ~72-108 GB       | ~108 GB         |

### Disk Space Planning

**Current Capacity**: 443 GB free

| Recording Length | Sessions Possible |
|------------------|-------------------|
| 5 minutes        | ~70 sessions      |
| 30 minutes       | ~16 sessions      |
| 1 hour           | ~8 sessions       |
| 2 hours          | ~4 sessions       |

---

## 🎬 DaVinci Resolve Workflow

### Opening Growing Files

1. **During Recording**:
   - Navigate to `/mnt/sdcard/recordings/` via SMB/NFS
   - Open MP4 file in DaVinci Resolve
   - File will show available duration (updates as recording continues)
   - Edit available footage while recording continues

2. **After Recording**:
   - Files are complete and ready
   - No need to re-import
   - Timeline will show full duration

### Linking to High-Quality Originals

1. **Record R58 proxies** (12-15 Mbps)
2. **Trigger external cameras** (Blackmagic/Obsbot at high quality)
3. **Edit with R58 proxies** in DaVinci Resolve
4. **Relink to originals** for final export:
   - Right-click clip → Relink Clips
   - Point to Blackmagic/Obsbot recordings
   - Match by timecode or filename

---

## 📝 Logging and Debugging

### View Service Logs

```bash
# Recent logs
ssh linaro@r58.itagenten.no
tail -100 /tmp/r58-service.log

# Follow logs in real-time
tail -f /tmp/r58-service.log

# Search for errors
grep -i error /tmp/r58-service.log | tail -20
```

### Check Recording Files

```bash
# List recent recordings
ssh linaro@r58.itagenten.no
ls -lht /mnt/sdcard/recordings/cam1/ | head -10

# Check session metadata
cat /opt/preke-r58-recorder/data/sessions/session_*.json | jq .
```

---

## 🔄 Maintenance Tasks

### Daily
- [ ] Check disk space
- [ ] Verify recordings from previous day
- [ ] Clear old test recordings

### Weekly
- [ ] Review session metadata
- [ ] Archive completed projects
- [ ] Check for software updates

### Monthly
- [ ] Full system backup
- [ ] Review storage usage trends
- [ ] Test disaster recovery

---

## 📞 Quick Reference

### Start Recording
```bash
curl -X POST http://recorder.itagenten.no/api/trigger/start
```

### Stop Recording
```bash
curl -X POST http://recorder.itagenten.no/api/trigger/stop
```

### Check Status
```bash
curl -s http://recorder.itagenten.no/api/trigger/status | python3 -m json.tool
```

### List Sessions
```bash
curl -s http://recorder.itagenten.no/api/sessions | python3 -m json.tool
```

### Get Session Metadata
```bash
curl -s http://recorder.itagenten.no/api/sessions/SESSION_ID | python3 -m json.tool
```

---

## 🎯 Success Criteria

A successful production recording should have:
- ✅ All cameras recording (3/3 active)
- ✅ Session metadata created
- ✅ Files growing consistently
- ✅ Bitrate 12-15 Mbps
- ✅ 1080p resolution
- ✅ ~1 keyframe per second
- ✅ Fragmented MP4 structure
- ✅ Playable in DaVinci Resolve
- ✅ No corruption or errors

---

**Last Updated**: December 18, 2025  
**Version**: 1.0

