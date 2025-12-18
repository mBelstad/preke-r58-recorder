# R58 Recorder - Quick Start Guide
**Get recording in 30 seconds!**

---

## 🎬 Start Recording

### Via Web Dashboard
1. Open: http://recorder.itagenten.no/
2. Click **"Start All Recordings"** button
3. Watch session ID and disk space appear
4. Click **"Stop All Recordings"** when done

### Via API
```bash
# Start
curl -X POST http://recorder.itagenten.no/api/trigger/start

# Stop
curl -X POST http://recorder.itagenten.no/api/trigger/stop

# Check status
curl http://recorder.itagenten.no/api/trigger/status
```

---

## 📚 View Recordings

### Library Page
- URL: http://recorder.itagenten.no/static/library.html
- Browse by date and session
- Copy session IDs
- Download metadata
- Play recordings

### Direct Access
- SMB/NFS: `/mnt/sdcard/recordings/`
- cam1: `/mnt/sdcard/recordings/cam1/`
- cam2: `/mnt/sdcard/recordings/cam2/`
- cam3: `/mnt/sdcard/recordings/cam3/`

---

## 📊 Monitor Recording

### Real-Time Monitor
```bash
./monitor_recording.sh
```

Shows:
- Duration
- Disk space
- Camera status
- Estimated file size

### Quick Status Check
```bash
curl -s http://recorder.itagenten.no/api/trigger/status | python3 -m json.tool
```

---

## 🎯 Recording Quality

### Current Settings
- **Resolution**: 1920x1080 (Full HD)
- **Bitrate**: 7-8 Mbps (actual)
- **Codec**: H.264
- **Frame Rate**: 30 fps
- **Keyframes**: 1 per second
- **Format**: Fragmented MP4

### Perfect For
- ✅ Social media (Instagram, YouTube, TikTok)
- ✅ Proxy editing in DaVinci Resolve
- ✅ Live editing on growing files
- ✅ Multi-camera synchronization

---

## 💾 Storage

- **Available**: 443 GB
- **Usage**: ~9.7 GB/hour (3 cameras)
- **Capacity**: ~45 hours of recording

---

## 🔧 Quick Troubleshooting

### Recording Won't Start
```bash
# Check disk space (need > 10 GB)
curl http://recorder.itagenten.no/api/trigger/status | grep free_gb
```

### Check Service Status
```bash
ssh linaro@r58.itagenten.no
ps aux | grep uvicorn
```

### View Logs
```bash
ssh linaro@r58.itagenten.no
tail -50 /tmp/r58-service.log
```

---

## 📖 Full Documentation

- **PRODUCTION_MONITORING_GUIDE.md** - Complete monitoring guide
- **PRODUCTION_TEST_RESULTS.md** - Test results and analysis
- **DEPLOYMENT_TEST_REPORT.md** - Full deployment report
- **RECORDING_FILE_ANALYSIS.md** - File quality analysis
- **ISSUES_AND_RECOMMENDATIONS.md** - Known issues and fixes

---

## 🎉 You're Ready!

The system is production-ready. Start recording and enjoy! 🚀

**Support**: Check the documentation files for detailed guides and troubleshooting.
