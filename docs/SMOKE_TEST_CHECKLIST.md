# R58 Smoke Test Checklist

> **Version:** 2.0.0  
> **Last Updated:** 2024-12-28  
> **Duration:** 15-20 minutes

## Pre-Release Smoke Test

Run this checklist before every release to verify core functionality.

---

## Test Environment

**Tester:** ____________________  
**Date:** ____________________  
**R58 Device ID:** ____________________  
**Firmware Version:** ____________________  
**Frontend Version:** ____________________  

---

## 1. Device Boot & System Health

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 1.1 | Power on R58 device | Boot completes in < 60s | ☐ | ☐ | |
| 1.2 | Check systemd services | `systemctl status r58-api r58-pipeline mediamtx` shows active | ☐ | ☐ | |
| 1.3 | Open PWA at `http://r58.local:8000` | UI loads without JavaScript errors | ☐ | ☐ | |
| 1.4 | Check browser console | No critical errors (red) | ☐ | ☐ | |
| 1.5 | Call `GET /api/v1/health` | Returns `{"status": "healthy"}` | ☐ | ☐ | |
| 1.6 | Call `GET /api/v1/health/detailed` | All services show "healthy" | ☐ | ☐ | |

**Command for 1.5:**
```bash
curl http://localhost:8000/api/v1/health
```

**Command for 1.6:**
```bash
curl http://localhost:8000/api/v1/health/detailed | jq
```

---

## 2. Recorder Functionality

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 2.1 | Connect HDMI cable to port 1 (cam2) | Signal indicator turns green within 5s | ☐ | ☐ | |
| 2.2 | Navigate to Recorder tab | Input preview shows video | ☐ | ☐ | |
| 2.3 | Click "Start Recording" button | Recording indicator appears, timer starts | ☐ | ☐ | |
| 2.4 | Wait 30 seconds | Duration shows ~00:00:30 | ☐ | ☐ | |
| 2.5 | Verify bytes counter increases | Input bytes counter > 0 | ☐ | ☐ | |
| 2.6 | Click "Stop Recording" button | Recording stops, timer resets to 00:00:00 | ☐ | ☐ | |
| 2.7 | Check recordings directory | New .mp4 file exists | ☐ | ☐ | |
| 2.8 | Play recording file | Video plays correctly | ☐ | ☐ | |

**Command to check recordings:**
```bash
ls -la /opt/r58/recordings/
ffprobe /opt/r58/recordings/*.mp4 | head -20
```

**Command to start recording via API:**
```bash
curl -X POST http://localhost:8000/api/v1/recorder/start \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["cam2"]}'
```

**Command to stop recording via API:**
```bash
curl -X POST http://localhost:8000/api/v1/recorder/stop
```

---

## 3. Mixer / VDO.ninja Functionality

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 3.1 | Navigate to Mixer tab | VDO.ninja iframe loads | ☐ | ☐ | |
| 3.2 | Wait for VDO.ninja to initialize | No "loading" spinner after 10s | ☐ | ☐ | |
| 3.3 | Verify camera appears in mixer | Video visible in VDO.ninja grid | ☐ | ☐ | |
| 3.4 | Test scene switch (if available) | Scene changes without error | ☐ | ☐ | |
| 3.5 | Test audio mute button | Audio mutes/unmutes | ☐ | ☐ | |
| 3.6 | Check for custom R58 styling | VDO.ninja shows custom CSS theme | ☐ | ☐ | |

**VDO.ninja local URL:**
```
http://r58.local:8443/?director=studio
```

---

## 4. WebSocket / Realtime Events

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 4.1 | Open browser DevTools Network tab | WebSocket connection established | ☐ | ☐ | |
| 4.2 | Disconnect network for 5 seconds | UI shows disconnected state | ☐ | ☐ | |
| 4.3 | Reconnect network | UI reconnects within 10s | ☐ | ☐ | |
| 4.4 | Start recording, check WebSocket | Progress events received | ☐ | ☐ | |
| 4.5 | Open second browser tab | Both tabs show same recording state | ☐ | ☐ | |

---

## 5. Admin / Developer Tools

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 5.1 | Navigate to Admin/Dev Tools | Admin interface loads | ☐ | ☐ | |
| 5.2 | Check Device Status section | Shows device info (ID, uptime) | ☐ | ☐ | |
| 5.3 | Check Logs Viewer | Recent logs display | ☐ | ☐ | |
| 5.4 | Download Support Bundle | ZIP file downloads successfully | ☐ | ☐ | |
| 5.5 | Verify support bundle contents | Contains logs, config, metrics | ☐ | ☐ | |

**Command to get support bundle:**
```bash
curl http://localhost:8000/api/v1/support/bundle -o support.zip
unzip -l support.zip
```

---

## 6. PWA / Kiosk Mode

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 6.1 | Check PWA installability | "Install" prompt available | ☐ | ☐ | |
| 6.2 | Install PWA (if not installed) | App icon appears on desktop | ☐ | ☐ | |
| 6.3 | Launch PWA | Opens in standalone window | ☐ | ☐ | |
| 6.4 | Test kiosk mode (F11) | Full screen, no browser chrome | ☐ | ☐ | |
| 6.5 | Test touch interactions | Buttons respond to touch | ☐ | ☐ | |

---

## 7. Multi-Device Access (Optional)

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 7.1 | Access from laptop on same network | R58 device discovered | ☐ | ☐ | |
| 7.2 | Connect to R58 from laptop | UI loads successfully | ☐ | ☐ | |
| 7.3 | Start recording remotely | Recording starts on R58 | ☐ | ☐ | |
| 7.4 | Stop recording remotely | Recording stops on R58 | ☐ | ☐ | |

---

## 8. Storage & Performance

| # | Test Step | Expected Result | Pass | Fail | Notes |
|---|-----------|-----------------|:----:|:----:|-------|
| 8.1 | Check available storage | > 10GB free | ☐ | ☐ | |
| 8.2 | Check CPU usage during recording | < 80% sustained | ☐ | ☐ | |
| 8.3 | Check memory usage | < 80% of available RAM | ☐ | ☐ | |
| 8.4 | Verify no dropped frames | Encoder stats show 0 drops | ☐ | ☐ | |

**Commands:**
```bash
df -h /opt/r58/recordings
htop
```

---

## Test Summary

| Category | Passed | Failed | Total |
|----------|:------:|:------:|:-----:|
| 1. Device Boot & Health | /6 | | 6 |
| 2. Recorder | /8 | | 8 |
| 3. Mixer/VDO.ninja | /6 | | 6 |
| 4. WebSocket | /5 | | 5 |
| 5. Admin Tools | /5 | | 5 |
| 6. PWA/Kiosk | /5 | | 5 |
| 7. Multi-Device (Optional) | /4 | | 4 |
| 8. Storage & Performance | /4 | | 4 |
| **TOTAL** | **/43** | | **43** |

---

## Sign-Off

**All critical tests passed:** ☐ Yes / ☐ No

**Blockers identified:**
1. ____________________________________________________________
2. ____________________________________________________________
3. ____________________________________________________________

**Notes:**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

**Tester Signature:** ____________________  
**Date:** ____________________

---

## Quick Commands Reference

### Start All Services
```bash
sudo systemctl start r58-api r58-pipeline mediamtx
```

### Check Service Status
```bash
sudo systemctl status r58-api r58-pipeline mediamtx
```

### View Logs
```bash
sudo journalctl -u r58-api -f
sudo journalctl -u r58-pipeline -f
```

### Quick Recording Test
```bash
# Start
curl -X POST http://localhost:8000/api/v1/recorder/start -H "Content-Type: application/json" -d '{"inputs": ["cam2"]}'

# Wait 10 seconds
sleep 10

# Stop
curl -X POST http://localhost:8000/api/v1/recorder/stop

# Check files
ls -la /opt/r58/recordings/
```

### Health Check
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/detailed | jq
curl http://localhost:8000/api/v1/capabilities | jq
```

