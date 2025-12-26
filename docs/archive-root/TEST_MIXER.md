# Mixer Testing Guide

## Quick Start

### 1. Check Mixer Status
```bash
curl http://192.168.1.104:8000/api/mixer/status
```

Expected response:
```json
{
  "state": "NULL",
  "current_scene": null,
  "health": "healthy",
  "last_error": null,
  "last_buffer_seconds_ago": null,
  "recording_enabled": false,
  "mediamtx_enabled": true
}
```

### 2. List Available Scenes
```bash
curl http://192.168.1.104:8000/api/scenes
```

You should see 7 scenes: `quad`, `two_up`, `cam0_full`, `cam1_full`, `cam2_full`, `cam3_full`, `pip_cam1_over_cam0`

### 3. Set a Scene
```bash
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "cam0_full"}'
```

Response: `{"status":"applied","scene_id":"cam0_full"}`

### 4. Start the Mixer
```bash
curl -X POST http://192.168.1.104:8000/api/mixer/start
```

Response: `{"status":"started"}`

### 5. Check Status Again
```bash
curl http://192.168.1.104:8000/api/mixer/status
```

Expected:
```json
{
  "state": "PLAYING",
  "current_scene": "cam0_full",
  "health": "healthy",
  ...
}
```

### 6. Switch Scenes (while running)
```bash
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'
```

The pipeline will automatically rebuild if the scene uses different cameras.

### 7. Stop the Mixer
```bash
curl -X POST http://192.168.1.104:8000/api/mixer/stop
```

Response: `{"status":"stopped"}`

## View Mixer Output Stream

### Via MediaMTX HLS
Open in browser or VLC:
```
http://192.168.1.104:8888/mixer_program/index.m3u8
```

### Via MediaMTX WebRTC (if enabled)
```
http://192.168.1.104:8554/mixer_program/whep
```

### Check if Stream is Available
```bash
curl http://192.168.1.104:8888/mixer_program/index.m3u8
```

Should return HLS playlist if stream is active.

## Test Scenarios

### Scenario 1: Single Camera Fullscreen
```bash
# Set scene
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "cam0_full"}'

# Start
curl -X POST http://192.168.1.104:8000/api/mixer/start

# Wait 5 seconds, check status
sleep 5
curl http://192.168.1.104:8000/api/mixer/status

# Stop
curl -X POST http://192.168.1.104:8000/api/mixer/stop
```

### Scenario 2: Quad View (4 cameras)
```bash
# Set scene
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'

# Start
curl -X POST http://192.168.1.104:8000/api/mixer/start

# Check status - should show "PLAYING"
curl http://192.168.1.104:8000/api/mixer/status | python3 -m json.tool
```

**Note:** If only cam0 is connected, the mixer will automatically skip unavailable cameras and only use cam0.

### Scenario 3: Scene Switching
```bash
# Start with cam0_full
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "cam0_full"}'
curl -X POST http://192.168.1.104:8000/api/mixer/start

# Wait 3 seconds
sleep 3

# Switch to quad (pipeline will rebuild)
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'

# Check status
curl http://192.168.1.104:8000/api/mixer/status
```

### Scenario 4: Health Monitoring
```bash
# Start mixer
curl -X POST http://192.168.1.104:8000/api/mixer/start

# Monitor status every 5 seconds
for i in {1..6}; do
  echo "=== Check $i ==="
  curl -s http://192.168.1.104:8000/api/mixer/status | \
    python3 -c "import sys, json; d=json.load(sys.stdin); \
    print(f\"State: {d['state']}, Health: {d['health']}, \
    Last buffer: {d.get('last_buffer_seconds_ago', 'None')}\")"
  sleep 5
done
```

## Browser Testing

### 1. Open the Web Interface
Navigate to:
```
http://192.168.1.104:8000
```

### 2. Check Browser Console
Open Developer Tools (F12) and check for:
- WebRTC connection status
- HLS player status
- Any errors

### 3. View Mixer Stream Directly
If MediaMTX is running, you can view the mixer output:
```
http://192.168.1.104:8888/mixer_program/index.m3u8
```

Or use VLC:
```
vlc http://192.168.1.104:8888/mixer_program/index.m3u8
```

## Troubleshooting

### Mixer Won't Start
1. Check if device is busy:
   ```bash
   lsof /dev/video60
   ```

2. Check logs:
   ```bash
   journalctl -u preke-recorder.service --since '5 minutes ago' | grep -i mixer
   ```

3. Check status for errors:
   ```bash
   curl http://192.168.1.104:8000/api/mixer/status | python3 -m json.tool
   ```

### No Video Output
1. Verify MediaMTX is running:
   ```bash
   systemctl status mediamtx.service
   ```

2. Check if stream is available:
   ```bash
   curl http://192.168.1.104:8888/mixer_program/index.m3u8
   ```

3. Check mixer status:
   ```bash
   curl http://192.168.1.104:8000/api/mixer/status
   ```
   State should be "PLAYING"

### Scene Switching Fails
1. Check if mixer is running:
   ```bash
   curl http://192.168.1.104:8000/api/mixer/status
   ```

2. Check scene exists:
   ```bash
   curl http://192.168.1.104:8000/api/scenes | grep -i "quad"
   ```

3. Check logs for errors:
   ```bash
   journalctl -u preke-recorder.service --since '1 minute ago' | tail -20
   ```

## Advanced Testing

### Test All Scenes
```bash
for scene in quad two_up cam0_full cam1_full cam2_full cam3_full pip_cam1_over_cam0; do
  echo "Testing scene: $scene"
  curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"$scene\"}"
  sleep 2
  curl -s http://192.168.1.104:8000/api/mixer/status | \
    python3 -c "import sys, json; d=json.load(sys.stdin); \
    print(f\"  State: {d['state']}, Scene: {d['current_scene']}\")"
  echo ""
done
```

### Monitor Mixer Health
```bash
watch -n 2 'curl -s http://192.168.1.104:8000/api/mixer/status | python3 -m json.tool'
```

### Test Start/Stop Cycle
```bash
for i in {1..5}; do
  echo "Cycle $i:"
  curl -X POST http://192.168.1.104:8000/api/mixer/start
  sleep 5
  curl -X POST http://192.168.1.104:8000/api/mixer/stop
  sleep 2
done
```

## Expected Behavior

✅ **Working:**
- Mixer starts with any scene
- Scene switching works (pipeline rebuilds if needed)
- Only available cameras are used
- Health status shows "healthy" when playing
- MediaMTX stream is available when mixer is running

⚠️ **Expected:**
- Buffer tracking may show "None" (this is normal, pipeline is still working)
- Quad scene with only 1 camera will only show that camera
- Scene switching may take 1-2 seconds (pipeline rebuild)

❌ **Should Not Happen:**
- Mixer stuck in "PLAYING" but no video
- Health status "unhealthy" when mixer is running
- Errors about device busy (should be handled automatically)
- Pipeline hangs (should timeout and recover)

