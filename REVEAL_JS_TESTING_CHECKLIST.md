# Reveal.js Video Source - Testing Checklist

**Implementation Date**: December 19, 2025

---

## Pre-Testing Setup

### 1. Check wpesrc Availability

```bash
# On R58 device
ssh linaro@r58.itagenten.no

# Check if wpesrc is installed
gst-inspect-1.0 wpesrc
```

**Expected**: Plugin details displayed  
**If not found**: Install with `sudo apt install gstreamer1.0-plugins-bad-apps libwpewebkit-1.0-3`

### 2. Verify Configuration

```bash
# Check config.yml has reveal section
cat /opt/preke-r58-recorder/config.yml | grep -A 6 "reveal:"

# Check mediamtx.yml has slides path
cat /opt/preke-r58-recorder/mediamtx.yml | grep -A 2 "slides:"
```

### 3. Restart Services

```bash
# Restart MediaMTX
sudo systemctl restart mediamtx

# Restart R58 recorder
sudo systemctl restart preke-recorder

# Check logs
sudo journalctl -u preke-recorder -f
```

**Look for**: "Reveal.js source manager initialized (renderer: wpe)"

---

## Basic Functionality Tests

### Test 1: Start Reveal.js Source

```bash
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=test&url=http://localhost:8000/graphics?presentation=test"
```

**Expected Response**:
```json
{
  "status": "started",
  "presentation_id": "test",
  "url": "http://localhost:8000/graphics?presentation=test",
  "stream_url": "rtsp://127.0.0.1:8554/slides"
}
```

**Verify**:
- [ ] Status code 200
- [ ] Response contains stream_url
- [ ] No errors in logs

### Test 2: Check Status

```bash
curl http://recorder.itagenten.no/api/reveal/status
```

**Expected**:
```json
{
  "state": "running",
  "presentation_id": "test",
  "renderer": "wpe",
  "stream_url": "rtsp://127.0.0.1:8554/slides"
}
```

**Verify**:
- [ ] State is "running"
- [ ] Renderer is "wpe" (or "chromium")
- [ ] Stream URL is present

### Test 3: Verify MediaMTX Stream

```bash
# Check MediaMTX API
curl http://127.0.0.1:9997/v3/paths/get/slides

# Or from local machine
curl http://recorder.itagenten.no:9997/v3/paths/get/slides
```

**Expected**:
```json
{
  "sourceReady": true,
  ...
}
```

**Verify**:
- [ ] sourceReady is true
- [ ] Path exists

### Test 4: Play Stream (Optional)

```bash
# On local machine with ffplay
ffplay rtsp://recorder.itagenten.no:8554/slides

# Or with VLC
vlc rtsp://recorder.itagenten.no:8554/slides
```

**Verify**:
- [ ] Video plays
- [ ] Presentation slides are visible
- [ ] Frame rate is smooth (30fps)

### Test 5: Stop Reveal.js Source

```bash
curl -X POST http://recorder.itagenten.no/api/reveal/stop
```

**Expected**:
```json
{
  "status": "stopped"
}
```

**Verify**:
- [ ] Status code 200
- [ ] Stream no longer available in MediaMTX

---

## Mixer Integration Tests

### Test 6: Load Presentation Scene

```bash
# Start Reveal.js source first
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=demo"

# Start mixer
curl -X POST http://recorder.itagenten.no/api/mixer/start

# Load presentation scene
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_focus"}'
```

**Verify**:
- [ ] Mixer starts successfully
- [ ] Scene loads without errors
- [ ] Mixer status shows current_scene: "presentation_focus"

### Test 7: Check Mixer Output

```bash
# Check mixer status
curl http://recorder.itagenten.no/api/mixer/status

# Play mixer output
ffplay rtsp://recorder.itagenten.no:8554/mixer_program
```

**Verify**:
- [ ] Mixer is in PLAYING state
- [ ] Program output shows presentation slides
- [ ] No errors in logs

### Test 8: Switch Between Scenes

```bash
# Presentation focus (full screen)
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_focus"}'

# Wait 2 seconds

# Presentation with speaker
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_speaker"}'

# Wait 2 seconds

# Presentation PiP
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_pip"}'
```

**Verify**:
- [ ] Each scene loads successfully
- [ ] Slides visible in each layout
- [ ] Camera (cam1) visible in speaker/pip scenes
- [ ] Smooth transitions

---

## Overlay Tests

### Test 9: Enable Overlay

```bash
# Start with a camera scene
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "cam1_full"}'

# Enable slides overlay
curl -X POST "http://recorder.itagenten.no/api/mixer/overlay/slides?alpha=0.8"
```

**Expected**: Overlay enabled (note: requires pipeline rebuild, may not work yet)

**Verify**:
- [ ] API responds with success or appropriate error
- [ ] Mixer status shows overlay_enabled: true

### Test 10: Adjust Overlay Alpha

```bash
curl -X PUT "http://recorder.itagenten.no/api/mixer/overlay/slides/alpha?alpha=0.5"
```

**Verify**:
- [ ] API responds
- [ ] Overlay transparency changes (if implemented)

### Test 11: Disable Overlay

```bash
curl -X DELETE http://recorder.itagenten.no/api/mixer/overlay/slides
```

**Verify**:
- [ ] API responds with success
- [ ] Mixer status shows overlay_enabled: false

---

## Error Handling Tests

### Test 12: Start Without wpesrc

```bash
# If wpesrc not available, check error handling
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=test"
```

**Expected**: Error message if renderer not available

### Test 13: Start While Already Running

```bash
# Start once
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=test1"

# Try to start again
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=test2"
```

**Verify**:
- [ ] Second start either succeeds (replacing first) or returns appropriate error

### Test 14: Use in Mixer Without Starting

```bash
# Stop Reveal.js if running
curl -X POST http://recorder.itagenten.no/api/reveal/stop

# Try to use in mixer
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_focus"}'
```

**Verify**:
- [ ] Mixer skips slides source gracefully
- [ ] Logs show "Reveal.js stream not available"
- [ ] Mixer continues with other sources

---

## Performance Tests

### Test 15: Check CPU Usage

```bash
# On R58 device
ssh linaro@r58.itagenten.no

# Start Reveal.js source
curl -X POST "http://localhost:8000/api/reveal/start?presentation_id=test"

# Monitor CPU
top -b -n 1 | grep -E "PID|python|gst"

# Or use htop
htop
```

**Expected**: 
- wpesrc process: ~5-10% CPU
- mpph265enc (VPU): minimal CPU (hardware encoding)
- Total system: <30% CPU

**Verify**:
- [ ] CPU usage is reasonable
- [ ] No CPU spikes
- [ ] System remains responsive

### Test 16: Check Memory Usage

```bash
free -h
ps aux | grep -E "python|gst" | awk '{print $6, $11}'
```

**Expected**: <500MB total for Reveal.js pipeline

**Verify**:
- [ ] Memory usage is stable
- [ ] No memory leaks over time

### Test 17: Latency Test

```bash
# Measure end-to-end latency
# 1. Start Reveal.js source
# 2. Start mixer with presentation scene
# 3. Play mixer output
# 4. Observe delay from browser to video output
```

**Expected**: 100-300ms latency

**Verify**:
- [ ] Latency is acceptable for live production
- [ ] No significant buffering

---

## Integration Tests

### Test 18: Full Production Workflow

```bash
# 1. Start all services
sudo systemctl restart mediamtx preke-recorder

# 2. Start ingest for cameras
curl -X POST http://recorder.itagenten.no/api/ingest/start-all

# 3. Start Reveal.js source
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=demo"

# 4. Start mixer
curl -X POST http://recorder.itagenten.no/api/mixer/start

# 5. Load presentation scene
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_speaker"}'

# 6. Switch between scenes
# (presentation_focus, presentation_speaker, presentation_pip, cam1_full, etc.)

# 7. Stop everything
curl -X POST http://recorder.itagenten.no/api/mixer/stop
curl -X POST http://recorder.itagenten.no/api/reveal/stop
```

**Verify**:
- [ ] All components start successfully
- [ ] Scene switching works smoothly
- [ ] No crashes or errors
- [ ] Clean shutdown

---

## Checklist Summary

### Pre-Testing
- [ ] wpesrc installed and working
- [ ] Configuration files updated
- [ ] Services restarted
- [ ] Logs show successful initialization

### Basic Functionality
- [ ] Start Reveal.js source
- [ ] Check status
- [ ] Verify MediaMTX stream
- [ ] Play stream
- [ ] Stop source

### Mixer Integration
- [ ] Load presentation scenes
- [ ] Check mixer output
- [ ] Switch between scenes

### Overlay (Optional)
- [ ] Enable overlay
- [ ] Adjust alpha
- [ ] Disable overlay

### Error Handling
- [ ] Graceful degradation
- [ ] Appropriate error messages
- [ ] Recovery from failures

### Performance
- [ ] CPU usage acceptable
- [ ] Memory usage stable
- [ ] Latency acceptable

### Full Integration
- [ ] Complete production workflow
- [ ] All components working together
- [ ] Clean startup and shutdown

---

## Known Limitations

1. **Slide Navigation**: Not yet implemented (placeholder API)
2. **Dynamic Overlay**: Requires pipeline rebuild
3. **Chromium Fallback**: Not fully implemented
4. **Multiple Presentations**: Only one active at a time

---

## Next Steps After Testing

1. Document any issues found
2. Optimize performance if needed
3. Implement slide navigation
4. Add UI controls in switcher
5. Create user documentation

---

**Testing Status**: Ready for initial testing on R58 hardware

