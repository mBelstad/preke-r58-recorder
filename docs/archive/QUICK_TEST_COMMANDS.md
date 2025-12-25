# Quick Test Commands - Plugin Refactor

## Deploy to R58

```bash
./deploy_plugin_refactor.sh --remote
```

## SSH to R58

```bash
ssh rock@192.168.1.58
cd /home/rock/preke-r58-recorder
```

## Quick Health Check

```bash
# Service status
sudo systemctl status preke-recorder

# Watch logs
sudo journalctl -u preke-recorder -f

# Check plugin initialization
sudo journalctl -u preke-recorder -n 100 | grep -i "plugin\|initialized"
```

## Test Core (Must Work)

```bash
# Recording
curl -X POST http://localhost:5000/api/recording/start
curl http://localhost:5000/api/status
curl -X POST http://localhost:5000/api/recording/stop

# Ingest
curl http://localhost:5000/api/ingest/status
curl http://localhost:5000/api/cameras
```

## Test Plugins

```bash
# Graphics
curl http://localhost:5000/api/graphics/templates

# Mixer
curl -X POST http://localhost:5000/api/mixer/start
curl http://localhost:5000/api/mixer/status
curl -X POST http://localhost:5000/api/mixer/stop

# Scenes
curl http://localhost:5000/api/scenes
```

## Test File Upload

```bash
# Upload test file
curl -X POST http://localhost:5000/api/files \
  -F "file=@test.jpg" \
  -F "loop=false"

# List files
curl http://localhost:5000/api/files
```

## Check for Errors

```bash
# Python errors
sudo journalctl -u preke-recorder -n 200 | grep -i "error\|exception\|traceback"

# Import errors
sudo journalctl -u preke-recorder -n 200 | grep -i "import\|module"
```

## Rollback (If Needed)

```bash
sudo systemctl stop preke-recorder
ls -la src.backup.*
sudo rm -rf src
sudo mv src.backup.YYYYMMDD_HHMMSS src
sudo systemctl start preke-recorder
```

## Success Indicators

✅ Service starts: `sudo systemctl status preke-recorder` shows "active (running)"
✅ No errors: Logs don't show Python exceptions
✅ Recording works: Can start/stop recording
✅ Plugins load: See "Graphics plugin initialized" and "Mixer plugin initialized" in logs
✅ APIs respond: All curl commands return valid JSON (not 500 errors)

## Configuration Changes

Edit `/home/rock/preke-r58-recorder/config.yml`:

```yaml
# Enable/disable graphics
graphics:
  enabled: true  # or false

# Enable/disable mixer
mixer:
  enabled: true  # or false
```

Then restart: `sudo systemctl restart preke-recorder`



