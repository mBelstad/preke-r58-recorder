# Mixer User Guide

## Quick Start

### 1. Enable the Mixer

First, ensure the mixer is enabled in `config.yml`:

```yaml
mixer:
  enabled: true
  output_resolution: 1920x1080
  output_bitrate: 8000  # kbps
  output_codec: h264
  recording_enabled: false  # Set to true to record program output
  mediamtx_enabled: true
  mediamtx_path: mixer_program
  scenes_dir: scenes
```

Restart the service if you changed the config:
```bash
sudo systemctl restart preke-recorder.service
```

### 2. Check Mixer Status

```bash
curl http://192.168.1.104:8000/api/mixer/status
```

You should see:
```json
{
  "state": "NULL",
  "current_scene": null,
  "health": "healthy",
  "recording_enabled": false,
  "mediamtx_enabled": true
}
```

## Basic Operations

### Starting the Mixer

**Step 1: Set a Scene**
```bash
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "cam0_full"}'
```

**Step 2: Start the Mixer**
```bash
curl -X POST http://192.168.1.104:8000/api/mixer/start
```

**Step 3: Verify It's Running**
```bash
curl http://192.168.1.104:8000/api/mixer/status
```

Expected response:
```json
{
  "state": "PLAYING",
  "current_scene": "cam0_full",
  "health": "healthy",
  "last_error": null,
  "mediamtx_enabled": true
}
```

### Stopping the Mixer

```bash
curl -X POST http://192.168.1.104:8000/api/mixer/stop
```

## Available Scenes

### List All Scenes

```bash
curl http://192.168.1.104:8000/api/scenes
```

### Scene Descriptions

1. **`quad`** - 4-up grid (2x2 layout)
   - All 4 cameras in equal-sized quadrants
   - Best for: Monitoring all inputs simultaneously

2. **`two_up`** - Side-by-side (2 cameras)
   - Two cameras side-by-side, full height
   - Best for: Comparing two sources

3. **`cam0_full`** - CAM 1 fullscreen
   - Single camera fills entire output
   - Best for: Focusing on one camera

4. **`cam1_full`** - CAM 2 fullscreen
   - Single camera fills entire output

5. **`cam2_full`** - CAM 3 fullscreen
   - Single camera fills entire output

6. **`cam3_full`** - CAM 4 fullscreen
   - Single camera fills entire output

7. **`pip_cam1_over_cam0`** - Picture-in-Picture
   - CAM 2 as small overlay over CAM 1
   - Best for: Main view with secondary source

### Get Scene Details

```bash
curl http://192.168.1.104:8000/api/scenes/quad
```

## Switching Scenes

### While Mixer is Running

You can switch scenes while the mixer is playing:

```bash
# Current: cam0_full, switch to quad
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'
```

**What Happens:**
- If the new scene uses the same cameras: Pad properties update instantly
- If the new scene uses different cameras: Pipeline rebuilds automatically (takes 1-2 seconds)

### While Mixer is Stopped

If the mixer is stopped, setting a scene just stores it for when you start:

```bash
# Mixer is stopped
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'

# Scene is stored, now start
curl -X POST http://192.168.1.104:8000/api/mixer/start
```

## Viewing Mixer Output

### Via Web Browser (HLS)

Open in browser or VLC player:
```
http://192.168.1.104:8888/mixer_program/index.m3u8
```

**In Browser:**
- Works in Chrome, Firefox, Safari
- ~300ms latency
- Automatic quality adaptation

**In VLC:**
```bash
vlc http://192.168.1.104:8888/mixer_program/index.m3u8
```

### Via WebRTC (Ultra-Low Latency)

If WebRTC is enabled in MediaMTX:
```
http://192.168.1.104:8554/mixer_program/whep
```

- <100ms latency
- Requires WebRTC-capable browser
- Best for: Real-time monitoring

### Check if Stream is Active

```bash
curl http://192.168.1.104:8888/mixer_program/index.m3u8
```

If stream is active, you'll get an HLS playlist. If not, you'll get an error.

## Recording Mixer Output

### Enable Recording

Edit `config.yml`:
```yaml
mixer:
  recording_enabled: true
  recording_path: /var/recordings/mixer/program_%Y%m%d_%H%M%S.mp4
```

Restart service:
```bash
sudo systemctl restart preke-recorder.service
```

### Start Recording

When you start the mixer with recording enabled, it automatically records:

```bash
curl -X POST http://192.168.1.104:8000/api/mixer/start
```

**Recording Location:**
- Default: `/var/recordings/mixer/program_YYYYMMDD_HHMMSS.mp4`
- Customizable in config.yml

### Stop Recording

Stopping the mixer stops the recording:

```bash
curl -X POST http://192.168.1.104:8000/api/mixer/stop
```

The file is finalized when the mixer stops.

## Common Workflows

### Workflow 1: Live Production with Scene Switching

```bash
# 1. Start with quad view
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'
curl -X POST http://192.168.1.104:8000/api/mixer/start

# 2. Switch to single camera when needed
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "cam0_full"}'

# 3. Switch back to quad
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'

# 4. Stop when done
curl -X POST http://192.168.1.104:8000/api/mixer/stop
```

### Workflow 2: Record Program Output

```bash
# 1. Ensure recording is enabled in config.yml
# 2. Start mixer (recording starts automatically)
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'
curl -X POST http://192.168.1.104:8000/api/mixer/start

# 3. Switch scenes as needed (recording continues)
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "cam0_full"}'

# 4. Stop mixer (recording stops and file is finalized)
curl -X POST http://192.168.1.104:8000/api/mixer/stop
```

### Workflow 3: Monitor All Cameras

```bash
# Start with quad view
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'
curl -X POST http://192.168.1.104:8000/api/mixer/start

# View in browser: http://192.168.1.104:8888/mixer_program/index.m3u8
# Or monitor status:
watch -n 2 'curl -s http://192.168.1.104:8000/api/mixer/status | python3 -m json.tool'
```

## Monitoring & Status

### Check Mixer Status

```bash
curl http://192.168.1.104:8000/api/mixer/status | python3 -m json.tool
```

**Status Fields:**
- `state`: "NULL", "PLAYING", or "PAUSED"
- `current_scene`: ID of active scene
- `health`: "healthy", "degraded", or "unhealthy"
- `last_error`: Last error message (if any)
- `last_buffer_seconds_ago`: Time since last video buffer (health indicator)
- `recording_enabled`: Whether recording is enabled
- `mediamtx_enabled`: Whether streaming is enabled

### Monitor Health in Real-Time

```bash
watch -n 2 'curl -s http://192.168.1.104:8000/api/mixer/status | python3 -m json.tool'
```

### Check Logs

```bash
# Recent mixer activity
journalctl -u preke-recorder.service --since '5 minutes ago' | grep -i mixer

# All mixer logs
journalctl -u preke-recorder.service | grep -i mixer
```

## Troubleshooting

### Mixer Won't Start

**Check Status:**
```bash
curl http://192.168.1.104:8000/api/mixer/status
```

Look for `last_error` field - it will tell you what went wrong.

**Common Issues:**

1. **"No scene selected"**
   - Solution: Set a scene before starting
   ```bash
   curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
     -H "Content-Type: application/json" \
     -d '{"id": "quad"}'
   ```

2. **"Device busy"**
   - Solution: Stop other pipelines (recorder/preview) using the same camera
   - Or wait a few seconds and try again

3. **"No valid source branches"**
   - Solution: Scene uses cameras that don't exist or aren't available
   - Try a different scene or check camera configuration

### Mixer Stops Unexpectedly

**Check Health:**
```bash
curl http://192.168.1.104:8000/api/mixer/status
```

If `health` is "unhealthy":
- Check logs: `journalctl -u preke-recorder.service --since '5 minutes ago'`
- Try restarting: Stop and start again
- Check if cameras are still connected

### No Video Output

**Check if Mixer is Running:**
```bash
curl http://192.168.1.104:8000/api/mixer/status
```
State should be "PLAYING"

**Check MediaMTX:**
```bash
systemctl status mediamtx.service
curl http://192.168.1.104:8888/mixer_program/index.m3u8
```

**Check Camera Status:**
```bash
curl http://192.168.1.104:8000/status
```
Ensure cameras show as "ready" or "preview"

### Scene Switching Takes Too Long

**Normal Behavior:**
- Same cameras: Instant (pad property update)
- Different cameras: 1-2 seconds (pipeline rebuild)

**If It's Taking Longer:**
- Check logs for errors
- Verify cameras are available
- Check system load

## Advanced Usage

### Create Custom Scenes

1. Create a JSON file in `scenes/` directory:
```json
{
  "id": "custom_layout",
  "label": "My Custom Layout",
  "resolution": {
    "width": 1920,
    "height": 1080
  },
  "slots": [
    {
      "source": "cam0",
      "x": 0.0,
      "y": 0.0,
      "w": 0.75,
      "h": 1.0,
      "z": 0,
      "alpha": 1.0
    },
    {
      "source": "cam1",
      "x": 0.75,
      "y": 0.0,
      "w": 0.25,
      "h": 0.5,
      "z": 1,
      "alpha": 1.0
    }
  ]
}
```

2. Restart service or reload scenes:
```bash
sudo systemctl restart preke-recorder.service
```

3. Use the new scene:
```bash
curl -X POST http://192.168.1.104:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "custom_layout"}'
```

### Coordinate System

- **x, y**: Position (0.0 = left/top, 1.0 = right/bottom)
- **w, h**: Size (0.0 = none, 1.0 = full width/height)
- **z**: Z-order (higher = on top)
- **alpha**: Transparency (0.0 = transparent, 1.0 = opaque)

**Example:**
- `x: 0.0, y: 0.0, w: 0.5, h: 0.5` = Top-left quadrant
- `x: 0.5, y: 0.0, w: 0.5, h: 0.5` = Top-right quadrant
- `x: 0.0, y: 0.5, w: 0.5, h: 0.5` = Bottom-left quadrant
- `x: 0.5, y: 0.5, w: 0.5, h: 0.5` = Bottom-right quadrant

### Mixer + Recorder Simultaneously

The mixer and recorder can run at the same time, but they cannot use the same camera simultaneously.

**Example:**
- Recorder using cam0 → Mixer can use cam1, cam2, cam3
- Mixer using cam0 → Recorder cannot use cam0

**Best Practice:**
- Use mixer for program output (all cameras)
- Use recorder for ISO recordings (individual cameras)
- Or: Use mixer for live production, recorder for backup

## Tips & Best Practices

1. **Start Simple**: Begin with `cam0_full` scene to verify everything works

2. **Check Camera Availability**: Only available cameras will be used in scenes
   - Quad scene with only cam0 connected = cam0 only (not an error)

3. **Monitor Health**: Keep an eye on the health status, especially during long sessions

4. **Storage Space**: If recording, ensure adequate storage space
   - 1080p@60fps @ 8000 kbps ≈ 3.6 GB per hour

5. **Network Bandwidth**: Streaming uses bandwidth
   - 1 stream @ 8000 kbps = ~8 Mbps
   - 4 streams = ~32 Mbps
   - Ensure network can handle it

6. **Scene Planning**: Plan your scenes ahead of time
   - Create custom scenes for your specific needs
   - Test scene switching before going live

7. **Backup Strategy**: 
   - Use mixer for program output
   - Use recorder for ISO backups of individual cameras

## Web Interface

The web interface at `http://192.168.1.104:8000` shows:
- Camera multiview (individual cameras)
- Recording controls
- Camera status

**Note:** The mixer output is separate and can be viewed at:
- `http://192.168.1.104:8888/mixer_program/index.m3u8`

Future versions may include mixer controls in the web interface.

## API Reference

### GET /api/mixer/status
Returns current mixer status and health.

**Response:**
```json
{
  "state": "PLAYING",
  "current_scene": "quad",
  "health": "healthy",
  "last_error": null,
  "last_buffer_seconds_ago": 0.5,
  "recording_enabled": false,
  "mediamtx_enabled": true
}
```

### GET /api/scenes
Lists all available scenes.

**Response:**
```json
{
  "scenes": [
    {
      "id": "quad",
      "label": "4-up grid",
      "resolution": {"width": 1920, "height": 1080},
      "slot_count": 4
    },
    ...
  ]
}
```

### GET /api/scenes/{id}
Gets full scene definition.

### POST /api/mixer/set_scene
Applies a scene to the mixer.

**Body:**
```json
{"id": "quad"}
```

### POST /api/mixer/start
Starts the mixer pipeline.

### POST /api/mixer/stop
Stops the mixer pipeline.

