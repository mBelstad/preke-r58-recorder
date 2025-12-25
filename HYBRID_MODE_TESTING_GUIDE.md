# Hybrid Mode Testing Guide

**Date**: December 24, 2025  
**Purpose**: Comprehensive testing checklist for hybrid mode implementation

---

## Prerequisites

- R58 device powered on and connected to network
- SSH access to R58 (via `r58.itagenten.no`)
- Local network access (192.168.1.x) or remote access via FRP
- Browser with WebRTC support

---

## Test 1: Mode Control UI Access

### Local Access
```
URL: http://192.168.1.24:8000/static/mode_control.html
```

**Expected:**
- [ ] Page loads successfully
- [ ] Shows current mode (Recorder or VDO.ninja)
- [ ] Displays service status
- [ ] Shows quick access links
- [ ] Mode toggle buttons visible

### Remote Access
```
URL: https://r58-api.itagenten.no/static/mode_control.html
```

**Expected:**
- [ ] Page loads with valid SSL certificate
- [ ] Same functionality as local access
- [ ] Quick links show remote URLs

---

## Test 2: Recorder Mode - Local Access

### Step 1: Switch to Recorder Mode
1. Open mode control UI
2. Click "Switch to Recorder" button
3. Wait for confirmation message

**Expected:**
- [ ] Success message appears
- [ ] Service status updates
- [ ] Ingest pipelines show "streaming"
- [ ] VDO.ninja services show "inactive"

### Step 2: Test Switcher
```
URL: http://192.168.1.24:8000/static/switcher.html
```

**Expected:**
- [ ] Switcher interface loads
- [ ] Camera previews appear
- [ ] Video plays smoothly
- [ ] Program/Preview switching works

### Step 3: Test Camera Viewer
```
URL: http://192.168.1.24:8000/static/camera_viewer.html
```

**Expected:**
- [ ] All cameras load
- [ ] Video streams play
- [ ] Connection status shows "Connected"
- [ ] Low latency (<100ms)

### Step 4: Test Direct WHEP
```
URL: http://192.168.1.24:8889/cam0
```

**Expected:**
- [ ] MediaMTX player loads
- [ ] Video plays
- [ ] Controls work

---

## Test 3: Recorder Mode - Remote Access

### Step 1: Access Mode Control Remotely
```
URL: https://r58-api.itagenten.no/static/mode_control.html
```

**Expected:**
- [ ] Mode shows as "Recorder"
- [ ] Services show correct status

### Step 2: Test Remote Switcher
```
URL: https://r58-api.itagenten.no/static/switcher.html
```

**Expected:**
- [ ] Switcher loads over HTTPS
- [ ] Camera previews appear
- [ ] Latency acceptable (<200ms)

### Step 3: Test Remote WHEP
```
URL: https://r58-mediamtx.itagenten.no/cam0
```

**Expected:**
- [ ] Stream loads over HTTPS
- [ ] Video plays smoothly
- [ ] Valid SSL certificate

---

## Test 4: VDO.ninja Mode - Local Access

### Step 1: Switch to VDO.ninja Mode
1. Open mode control UI
2. Click "Switch to VDO.ninja" button
3. Wait for confirmation message

**Expected:**
- [ ] Success message appears
- [ ] Service status updates
- [ ] VDO.ninja services show "active"
- [ ] Ingest pipelines show "idle"

### Step 2: Test Director View
```
URL: https://192.168.1.24:8443/?director=r58studio
```

**Expected:**
- [ ] Accept self-signed certificate
- [ ] Director interface loads
- [ ] Camera tiles appear (r58-cam1, r58-cam2, r58-cam3)
- [ ] Video plays in tiles
- [ ] Can drag and arrange cameras

### Step 3: Test Individual Camera View
```
URL: https://192.168.1.24:8443/?view=r58-cam1
```

**Expected:**
- [ ] Single camera view loads
- [ ] Video plays fullscreen
- [ ] Low latency

### Step 4: Test Mixer
```
URL: https://192.168.1.24:8443/mixer.html
```

**Expected:**
- [ ] Mixer interface loads
- [ ] Can add camera sources
- [ ] Scene controls work

---

## Test 5: VDO.ninja Mode - Remote Access

### Step 1: Test Remote Director
```
URL: https://r58-vdo.itagenten.no/?director=r58studio
```

**Expected:**
- [ ] Valid SSL certificate (Let's Encrypt)
- [ ] Director interface loads
- [ ] Camera tiles appear
- [ ] Video plays via TURN relay
- [ ] Latency acceptable (<200ms)

### Step 2: Test Remote Camera View
```
URL: https://r58-vdo.itagenten.no/?view=r58-cam1
```

**Expected:**
- [ ] Camera view loads
- [ ] Video plays
- [ ] TURN relay working

### Step 3: Test Remote Mixer
```
URL: https://r58-vdo.itagenten.no/mixer.html
```

**Expected:**
- [ ] Mixer loads
- [ ] Can add sources
- [ ] Mixing works remotely

---

## Test 6: Mode Switching

### Test A: Recorder → VDO.ninja
1. Start in Recorder Mode
2. Verify cameras streaming to MediaMTX
3. Switch to VDO.ninja Mode
4. Wait for services to switch
5. Verify cameras now publishing to VDO.ninja

**Expected:**
- [ ] Clean transition (no errors)
- [ ] Services stop/start correctly
- [ ] No device conflicts
- [ ] State persists

### Test B: VDO.ninja → Recorder
1. Start in VDO.ninja Mode
2. Verify publishers active
3. Switch to Recorder Mode
4. Wait for services to switch
5. Verify cameras now streaming to MediaMTX

**Expected:**
- [ ] Clean transition
- [ ] Publishers stop cleanly
- [ ] Ingest starts successfully
- [ ] State persists

### Test C: Rapid Switching
1. Switch modes 3 times in quick succession
2. Wait for final state to settle

**Expected:**
- [ ] System handles rapid switches
- [ ] No hung processes
- [ ] Final state is correct

---

## Test 7: Offline Local Access

### Step 1: Disconnect Internet
1. Disconnect R58 from internet (keep local network)
2. Verify local IP still accessible

### Step 2: Test Recorder Mode Offline
```
URL: http://192.168.1.24:8000/static/mode_control.html
```

**Expected:**
- [ ] Mode control loads
- [ ] Can switch modes
- [ ] Switcher works locally
- [ ] Camera viewer works
- [ ] No internet required

### Step 3: Test VDO.ninja Mode Offline
```
URL: https://192.168.1.24:8443/?director=r58studio&lanonly
```

**Expected:**
- [ ] Director loads
- [ ] Cameras appear
- [ ] LAN-only WebRTC works
- [ ] No TURN needed locally

---

## Test 8: State Persistence

### Step 1: Set Mode and Reboot
1. Switch to VDO.ninja Mode
2. Verify mode is active
3. SSH to R58 and reboot: `sudo reboot`
4. Wait for R58 to come back online
5. Check mode control UI

**Expected:**
- [ ] Mode persists after reboot
- [ ] VDO.ninja services start automatically
- [ ] State file exists: `/tmp/r58_mode_state.json`

### Step 2: Change Default Mode
1. Edit config.yml: `mode.default: vdoninja`
2. Delete state file: `rm /tmp/r58_mode_state.json`
3. Restart preke-recorder service
4. Check current mode

**Expected:**
- [ ] Starts in VDO.ninja mode
- [ ] Default mode respected

---

## Test 9: API Endpoints

### Test GET /api/mode
```bash
curl http://192.168.1.24:8000/api/mode
```

**Expected:**
```json
{
  "current_mode": "recorder",
  "available_modes": ["recorder", "vdoninja"]
}
```

### Test GET /api/mode/status
```bash
curl http://192.168.1.24:8000/api/mode/status
```

**Expected:**
```json
{
  "current_mode": "recorder",
  "recorder_services": {...},
  "vdoninja_services": {...},
  "can_switch": true
}
```

### Test POST /api/mode/recorder
```bash
curl -X POST http://192.168.1.24:8000/api/mode/recorder
```

**Expected:**
```json
{
  "success": true,
  "mode": "recorder",
  "message": "Switched to Recorder Mode..."
}
```

---

## Test 10: Error Handling

### Test A: Device Conflict
1. Manually start a ninja publisher
2. Try to switch to Recorder Mode
3. Observe behavior

**Expected:**
- [ ] System detects conflict
- [ ] Stops conflicting service
- [ ] Completes switch successfully

### Test B: Service Failure
1. Manually stop a required service
2. Check mode status
3. Try to use features

**Expected:**
- [ ] Status shows service down
- [ ] Error messages clear
- [ ] Can restart service

---

## Performance Benchmarks

### Recorder Mode
- [ ] Local WHEP latency: <50ms
- [ ] Remote WHEP latency: <100ms
- [ ] Switching time: <5 seconds
- [ ] CPU usage: <30%

### VDO.ninja Mode
- [ ] Local WebRTC latency: <50ms
- [ ] Remote WebRTC latency: <150ms (via TURN)
- [ ] Switching time: <5 seconds
- [ ] CPU usage: <40%

---

## Troubleshooting Tests

### If Mode Won't Switch
```bash
# Check logs
ssh linaro@r58.itagenten.no
journalctl -u preke-recorder -n 50 | grep -i mode

# Check service status
systemctl status ninja-publish-cam1
systemctl status ninja-publish-cam2
```

### If Services Conflict
```bash
# Check what's using devices
lsof /dev/video60
lsof /dev/video11
lsof /dev/video22

# Manually stop all
sudo systemctl stop ninja-publish-cam{1,2,3}
curl -X POST http://localhost:8000/api/ingest/stop/cam1
```

### If State Not Persisting
```bash
# Check state file
cat /tmp/r58_mode_state.json

# Check permissions
ls -la /tmp/r58_mode_state.json

# Manually create
echo '{"mode": "recorder"}' | sudo tee /tmp/r58_mode_state.json
```

---

## Test Results Template

```
Date: _______________
Tester: _______________

✅ = Pass
❌ = Fail
⚠️ = Partial/Issue

[ ] Test 1: Mode Control UI Access
[ ] Test 2: Recorder Mode - Local
[ ] Test 3: Recorder Mode - Remote
[ ] Test 4: VDO.ninja Mode - Local
[ ] Test 5: VDO.ninja Mode - Remote
[ ] Test 6: Mode Switching
[ ] Test 7: Offline Local Access
[ ] Test 8: State Persistence
[ ] Test 9: API Endpoints
[ ] Test 10: Error Handling

Notes:
_________________________________
_________________________________
_________________________________
```

---

## Success Criteria

All tests must pass for hybrid mode to be considered production-ready:

- ✅ Both modes work locally
- ✅ Both modes work remotely
- ✅ Mode switching is reliable
- ✅ State persists across reboots
- ✅ No device conflicts
- ✅ Offline local access works
- ✅ API endpoints functional
- ✅ Error handling graceful

---

**Ready to test!** Start with Test 1 and work through systematically.

