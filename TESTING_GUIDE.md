# Plugin Refactor Testing Guide

## Pre-Deployment Checklist

- [x] All plugin files created
- [x] Configuration updated
- [x] Import tests passed
- [x] Original files preserved as backup

## Deployment Steps

### 1. Local Verification (Run First)

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./deploy_plugin_refactor.sh
```

This verifies:
- File structure is correct
- Python imports work
- Configuration is valid

### 2. Deploy to R58

```bash
./deploy_plugin_refactor.sh --remote
```

This will:
1. Stop the preke-recorder service
2. Backup current installation
3. Sync new code to R58
4. Restart the service
5. Show service status

### 3. SSH to R58 for Manual Testing

```bash
ssh rock@192.168.1.58
cd /home/rock/preke-r58-recorder
```

## Testing Scenarios

### Test 1: Core Functionality (Recording/Ingest)

**Goal:** Verify core recording still works (not affected by plugin changes)

```bash
# Check service status
sudo systemctl status preke-recorder

# Watch logs
sudo journalctl -u preke-recorder -f

# Test recording API
curl -X POST http://localhost:5000/api/recording/start
curl -X GET http://localhost:5000/api/status
curl -X POST http://localhost:5000/api/recording/stop

# Test ingest API
curl http://localhost:5000/api/ingest/status
curl http://localhost:5000/api/cameras
```

**Expected Results:**
- ✅ Service starts without errors
- ✅ Recording API works
- ✅ Ingest API works
- ✅ No errors in logs about missing modules

### Test 2: Shared Infrastructure (Database/Files)

**Goal:** Verify shared infrastructure is accessible

```bash
# Test file upload API
curl -X POST http://localhost:5000/api/files \
  -F "file=@/path/to/test.jpg" \
  -F "loop=false"

# List files
curl http://localhost:5000/api/files

# Test database (scenes should load)
curl http://localhost:5000/api/scenes
```

**Expected Results:**
- ✅ File uploads work
- ✅ Database queries work
- ✅ Scenes can be listed

### Test 3: Graphics Plugin Only

**Goal:** Test graphics plugin independently

**Config:** Set in config.yml:
```yaml
graphics:
  enabled: true
mixer:
  enabled: false
```

```bash
# Restart service
sudo systemctl restart preke-recorder

# Test graphics templates API
curl http://localhost:5000/api/graphics/templates

# Test specific template
curl http://localhost:5000/api/graphics/templates/lower_third_standard
```

**Expected Results:**
- ✅ Service starts successfully
- ✅ Graphics templates API returns templates
- ✅ Mixer API returns 503 (disabled)
- ✅ Recording still works

### Test 4: Mixer Plugin Only (No Graphics)

**Goal:** Test mixer works without graphics plugin

**Config:** Set in config.yml:
```yaml
graphics:
  enabled: false
mixer:
  enabled: true
```

```bash
# Restart service
sudo systemctl restart preke-recorder

# Check logs for "Mixer running without graphics plugin"
sudo journalctl -u preke-recorder -n 50 | grep -i graphics

# Test mixer API
curl -X POST http://localhost:5000/api/mixer/start
curl http://localhost:5000/api/mixer/status
curl -X POST http://localhost:5000/api/mixer/stop
```

**Expected Results:**
- ✅ Service starts successfully
- ✅ Logs show "Mixer running without graphics plugin"
- ✅ Mixer API works
- ✅ Graphics API returns 503 (disabled)
- ✅ Scenes without presentations work
- ⚠️ Scenes with presentations log warning (no graphics available)

### Test 5: Both Plugins Enabled (Full Functionality)

**Goal:** Test complete system with all plugins

**Config:** Set in config.yml:
```yaml
graphics:
  enabled: true
mixer:
  enabled: true
```

```bash
# Restart service
sudo systemctl restart preke-recorder

# Check logs for successful initialization
sudo journalctl -u preke-recorder -n 100 | grep -i "initialized"

# Should see:
# - "Graphics plugin initialized"
# - "Mixer using graphics plugin for presentations/overlays"
# - "Mixer plugin initialized"

# Test all APIs
curl http://localhost:5000/api/graphics/templates
curl -X POST http://localhost:5000/api/mixer/start
curl http://localhost:5000/api/mixer/status
curl http://localhost:5000/api/scenes
```

**Expected Results:**
- ✅ Service starts successfully
- ✅ Both plugins initialize
- ✅ Mixer uses graphics for presentations
- ✅ All APIs work
- ✅ Full functionality available

### Test 6: Error Handling (Plugin Failure)

**Goal:** Verify app continues if plugin fails to load

**Method:** Temporarily rename a plugin file to cause import error

```bash
# Cause graphics plugin to fail
sudo mv src/graphics/renderer.py src/graphics/renderer.py.bak
sudo systemctl restart preke-recorder

# Check logs
sudo journalctl -u preke-recorder -n 50 | grep -i "failed to initialize"

# Verify core still works
curl http://localhost:5000/api/cameras

# Restore file
sudo mv src/graphics/renderer.py.bak src/graphics/renderer.py
sudo systemctl restart preke-recorder
```

**Expected Results:**
- ✅ Service starts despite plugin failure
- ✅ Error logged: "Failed to initialize graphics plugin"
- ✅ Core recording/ingest still works
- ✅ Mixer API returns 503 if mixer depends on failed plugin

## Monitoring During Tests

### Watch Logs in Real-Time

```bash
# In one terminal
sudo journalctl -u preke-recorder -f

# In another terminal, run tests
```

### Check for Errors

```bash
# Check for Python errors
sudo journalctl -u preke-recorder -n 200 | grep -i "error\|traceback\|exception"

# Check for import errors
sudo journalctl -u preke-recorder -n 200 | grep -i "import\|module"

# Check plugin initialization
sudo journalctl -u preke-recorder -n 200 | grep -i "plugin\|initialized"
```

### Monitor Resource Usage

```bash
# CPU and memory
htop

# Check if GStreamer processes are running
ps aux | grep gst
```

## Rollback Procedure

If issues occur:

```bash
# On R58
cd /home/rock/preke-r58-recorder

# Stop service
sudo systemctl stop preke-recorder

# Restore backup (find latest backup)
ls -la src.backup.*
sudo rm -rf src
sudo mv src.backup.YYYYMMDD_HHMMSS src

# Restore old config
git checkout config.yml

# Restart service
sudo systemctl start preke-recorder
```

## Success Criteria

### Must Pass (Critical)
- [ ] Service starts without errors
- [ ] Recording API works (start/stop)
- [ ] Ingest API works (camera status)
- [ ] File upload API works
- [ ] Scenes can be listed

### Should Pass (Important)
- [ ] Graphics plugin loads when enabled
- [ ] Mixer plugin loads when enabled
- [ ] Mixer works without graphics
- [ ] Graphics templates API works
- [ ] Plugin failures don't crash app

### Nice to Have (Optional)
- [ ] Mixer uses graphics for presentations
- [ ] All scene types work
- [ ] Graphics rendering works
- [ ] No performance degradation

## Troubleshooting

### Issue: Service won't start

```bash
# Check detailed error
sudo journalctl -u preke-recorder -n 100 --no-pager

# Check Python syntax
cd /home/rock/preke-r58-recorder
python3 -m py_compile src/config.py
python3 -m py_compile src/database.py
python3 -m py_compile src/files.py
```

### Issue: Import errors

```bash
# Test imports manually
python3 -c "from src.database import Database; print('OK')"
python3 -c "from src.graphics import create_graphics_plugin; print('OK')"
python3 -c "from src.mixer import create_mixer_plugin; print('OK')"
```

### Issue: Plugin not loading

```bash
# Check config
cat config.yml | grep -A 3 "graphics:"
cat config.yml | grep -A 3 "mixer:"

# Verify files exist
ls -la src/graphics/
ls -la src/mixer/
```

## Post-Testing

After successful testing:

1. **Document Results**
   - Note which tests passed/failed
   - Record any errors encountered
   - Document performance observations

2. **Update Configuration**
   - Set desired plugin states in config.yml
   - Commit working configuration

3. **Monitor Production**
   - Watch logs for first 24 hours
   - Check for memory leaks
   - Verify recording quality

4. **Clean Up**
   - Remove old backup directories (keep most recent)
   - Remove test files
   - Update documentation

## Contact

If issues occur:
- Check PLUGIN_REFACTOR_COMPLETE.md for architecture details
- Review logs for error messages
- Rollback if critical functionality broken


