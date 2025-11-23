# Troubleshooting Guide - Mixer Core

## ⚠️ CRITICAL: Device Stability

**IMPORTANT:** The R58 device can become completely unresponsive and require a **power cycle** (unplugging power) to recover. This typically happens when:

1. **Multiple pipelines access the same device simultaneously** - Causes kernel lockup
2. **GStreamer pipelines hang during state transitions** - Device becomes unresponsive
3. **Disk I/O exhaustion** - System freezes
4. **Memory exhaustion** - System hangs

**Prevention:**
- Always ensure exclusive device access (one pipeline per device)
- Use timeouts on all state transitions (already implemented)
- Monitor disk and memory usage
- Avoid starting multiple pipelines simultaneously
- If device becomes unresponsive, **immediately request power cycle** - do not wait

**If Device Gets Stuck:**
- Do NOT wait for timeout
- Immediately ask user to power cycle (unplug power)
- Document what operation caused the hang
- Review logs after reboot to identify root cause

---

## Critical Issues Found and Fixed

### 1. Disk Space Exhaustion (100% Full)

**Problem:**
- R58 device ran out of disk space (14GB full, 0 bytes available)
- Prevented git pull, file creation, and service restarts
- Caused "No space left on device" errors

**Root Cause:**
- Large video recordings accumulating in `/var/recordings/`
- One recording file was 8.6GB (`recording_20251122_235557.mp4`)
- Log files also consuming space

**Solution:**
```bash
# Clean up old recordings
sudo find /var/recordings -type f -name '*.mp4' -mtime +1 -delete

# Truncate large log files
sudo truncate -s 0 /var/log/user.log /var/log/kern.log

# Clean temporary files
sudo rm -rf /tmp/* /var/tmp/*
```

**Prevention:**
- Implement automatic cleanup of recordings older than X days
- Monitor disk usage and alert when >80% full
- Consider external storage for long-term recordings

---

### 2. GStreamer Pipeline Syntax Error

**Problem:**
- Mixer pipeline failed to start with: `gst_parse_error: syntax error (0)`
- Pipeline string construction had incorrect compositor pad property syntax

**Root Cause:**
- Initial implementation tried to set pad properties inline: `compositor.sink_{i}::{pad_props}`
- This syntax is invalid in GStreamer pipeline strings
- Pad properties must be set on the compositor element itself, not on the pad reference

**Solution:**
Changed from:
```python
# WRONG - Invalid syntax
source_parts.append(f"{source_str} ! compositor.sink_{i}::{pad_props}")
```

To:
```python
# CORRECT - Pad properties on compositor element
source_parts.append(f"{source_str} ! compositor.sink_{i}")
# Then set properties on compositor element:
compositor_pad_props.append(f"sink_{i}::xpos={x} sink_{i}::ypos={y} ...")
pipeline_str = f"... compositor name=compositor {' '.join(compositor_pad_props)} ! ..."
```

**Correct GStreamer Syntax:**
```
source1 ! compositor.sink_0 source2 ! compositor.sink_1 \
compositor name=compositor \
  sink_0::xpos=0 sink_0::ypos=0 sink_0::width=960 sink_0::height=540 \
  sink_1::xpos=960 sink_1::ypos=0 sink_1::width=960 sink_1::height=540 \
! video/x-raw,width=1920,height=1080 ! ...
```

**Key Points:**
- Pad properties are set on the compositor element, not on pad references
- Properties use `sink_N::property=value` syntax
- All pad properties must be set before the `!` separator

---

### 3. File Deployment Issues

**Problem:**
- Git pull failed due to disk space
- Manual file copy via SCP also failed
- Files appeared corrupted or incomplete

**Root Cause:**
- Disk full prevented file writes
- Partial writes resulted in corrupted files
- Service crashed with "source code string cannot contain null bytes"

**Solution:**
1. Free disk space first (see Issue #1)
2. Deploy files individually via SCP
3. Verify file integrity after copy:
   ```bash
   file src/main.py  # Should show "Python script, ASCII text"
   python3 -m py_compile src/main.py  # Should not error
   ```

**Prevention:**
- Always check disk space before deployment
- Verify file integrity after copy
- Use checksums for critical files

---

### 4. Service Startup Failures

**Problem:**
- Service failed to start after code updates
- Module import errors: `ModuleNotFoundError: No module named 'src.mixer'`

**Root Cause:**
- Mixer module files not deployed
- Directory structure missing (`src/mixer/`, `scenes/`)

**Solution:**
1. Create directory structure:
   ```bash
   mkdir -p /opt/preke-r58-recorder/src/mixer
   mkdir -p /opt/preke-r58-recorder/scenes
   ```
2. Deploy all mixer files
3. Restart service

**Prevention:**
- Include directory creation in deployment script
- Verify module structure before service restart

---

## Common Issues and Solutions

### Pipeline Won't Start

**Symptoms:**
- `Failed to parse pipeline: gst_parse_error`
- Mixer status shows `state: NULL`

**Debug Steps:**
1. Check pipeline string in logs (DEBUG level)
2. Test pipeline syntax manually:
   ```python
   from src.mixer.core import MixerCore
   # ... create mixer instance
   pipeline = mixer._build_pipeline()
   ```
3. Verify GStreamer elements are available:
   ```bash
   gst-inspect-1.0 compositor
   gst-inspect-1.0 x264enc
   ```

**Common Causes:**
- Invalid pad property syntax
- Missing GStreamer plugins
- Device busy (another pipeline using it)

---

### Pipeline Hangs or Stalls

**Symptoms:**
- Pipeline starts but no buffers flow
- Health check reports "unhealthy"
- No video output

**Debug Steps:**
1. Check device availability:
   ```bash
   v4l2-ctl --list-devices
   ls -l /dev/video*
   ```
2. Check for stuck processes:
   ```bash
   ps aux | grep gst
   ```
3. Check logs for device errors:
   ```bash
   journalctl -u preke-recorder | grep -i "device\|busy\|error"
   ```

**Common Causes:**
- Device locked by another process
- Invalid device path
- Missing device permissions

**Solution:**
- Kill stuck GStreamer processes
- Ensure exclusive device access
- Check device permissions

---

### Scene Not Applying

**Symptoms:**
- Scene change API returns success but layout doesn't change
- Mixer status shows different scene than expected

**Debug Steps:**
1. Verify scene exists:
   ```bash
   curl http://localhost:8000/api/scenes
   ```
2. Check mixer is running:
   ```bash
   curl http://localhost:8000/api/mixer/status
   ```
3. Check logs for pad property errors

**Common Causes:**
- Mixer not running (scene stored but not applied)
- Pad properties invalid (negative coordinates, zero size)
- Pipeline needs rebuild (different sources)

---

## Best Practices

### Deployment Checklist

- [ ] Check disk space (`df -h`)
- [ ] Backup current code
- [ ] Deploy files individually
- [ ] Verify file integrity
- [ ] Test module imports
- [ ] Check service logs
- [ ] Verify API endpoints
- [ ] Test mixer functionality

### Monitoring

- Monitor disk usage (alert at 80%)
- Check service health regularly
- Review logs for errors
- Monitor pipeline health status
- Track buffer activity

### Recovery Procedures

1. **Service Won't Start:**
   - Check logs: `journalctl -u preke-recorder`
   - Verify Python syntax: `python3 -m py_compile src/main.py`
   - Check disk space
   - Verify file permissions

2. **Pipeline Errors:**
   - Check device availability
   - Kill stuck processes
   - Verify GStreamer plugins
   - Test pipeline syntax manually

3. **Disk Full:**
   - Clean old recordings
   - Truncate log files
   - Remove temporary files
   - Consider external storage

---

## Notes for Future Development

1. **Always check disk space before deployment**
2. **Test GStreamer pipeline syntax before deploying**
3. **Verify file integrity after SCP transfers**
4. **Use proper compositor pad property syntax**
5. **Implement automatic cleanup for recordings**
6. **Add disk space monitoring**
7. **Test on R58 before marking as complete**

