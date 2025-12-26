# Mixer Core and Scene System

## Overview

The Mixer Core extends the R58 Recorder with a scene-based video mixer that can composite up to 4 HDMI inputs into a single program output. The mixer runs alongside the existing per-camera recorder, providing isolation and allowing both systems to operate independently.

## Architecture

### Components

1. **Scene Manager** (`src/mixer/scenes.py`)
   - Manages scene definitions stored as JSON files
   - Uses relative coordinates (0-1) for resolution-independent layouts
   - Provides default scenes (quad, 2-up, fullscreen, PiP)

2. **Mixer Core** (`src/mixer/core.py`)
   - GStreamer compositor pipeline
   - Handles 4 video sources → compositor → encoder → outputs
   - Supports recording and MediaMTX streaming
   - Implements timeout-based state transitions

3. **Watchdog** (`src/mixer/watchdog.py`)
   - Monitors pipeline health
   - Detects hangs and errors
   - Tracks buffer activity

## Configuration

Enable the mixer in `config.yml`:

```yaml
mixer:
  enabled: true
  output_resolution: 1920x1080
  output_bitrate: 8000  # kbps
  output_codec: h264
  recording_enabled: false
  recording_path: /var/recordings/mixer/program_%Y%m%d_%H%M%S.mp4
  mediamtx_enabled: true
  mediamtx_path: mixer_program
  scenes_dir: scenes
```

## API Endpoints

### List Scenes
```
GET /api/scenes
```
Returns all available scenes with their IDs, labels, and slot counts.

### Get Scene
```
GET /api/scenes/{scene_id}
```
Returns the full scene definition including slot layouts.

### Set Scene
```
POST /api/mixer/set_scene
Body: {"id": "quad"}
```
Applies a scene to the mixer. If the mixer is not running, the scene will be stored and applied when it starts.

### Start Mixer
```
POST /api/mixer/start
```
Starts the mixer pipeline with the current scene.

### Stop Mixer
```
POST /api/mixer/stop
```
Stops the mixer pipeline gracefully.

### Get Mixer Status
```
GET /api/mixer/status
```
Returns current mixer state, scene, health status, and error information.

## Scene Definitions

Scenes are stored as JSON files in the `scenes/` directory. Each scene defines:

- `id`: Unique identifier
- `label`: Human-readable name
- `resolution`: Output resolution (width, height)
- `slots`: Array of source slots with:
  - `source`: Camera ID (cam0, cam1, etc.)
  - `x_rel`, `y_rel`: Position (0.0-1.0)
  - `w_rel`, `h_rel`: Size (0.0-1.0)
  - `z`: Z-order (higher = on top)
  - `alpha`: Opacity (0.0-1.0)

### Default Scenes

- `quad`: 4-up grid (2x2)
- `two_up`: Side-by-side (2 cameras)
- `cam0_full`, `cam1_full`, `cam2_full`, `cam3_full`: Fullscreen per camera
- `pip_cam1_over_cam0`: Picture-in-picture

## Health Monitoring

The mixer includes robust health monitoring:

- **State Timeouts**: All state transitions have a 10-second timeout
- **Buffer Monitoring**: Tracks buffer activity to detect pipeline stalls
- **Error Detection**: Captures GStreamer bus errors and warnings
- **Health Status**: Reports healthy/degraded/unhealthy states

## Recovery

When the mixer detects an unhealthy state:

1. Logs the problem with full details
2. Attempts graceful teardown (EOS → NULL state)
3. Can be restarted via API without device reboot

## Usage Examples

### Start Mixer with Quad Scene
```bash
# Set scene
curl -X POST http://localhost:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "quad"}'

# Start mixer
curl -X POST http://localhost:8000/api/mixer/start

# Check status
curl http://localhost:8000/api/mixer/status
```

### Switch to Fullscreen
```bash
curl -X POST http://localhost:8000/api/mixer/set_scene \
  -H "Content-Type: application/json" \
  -d '{"id": "cam0_full"}'
```

## Isolation

The mixer is completely isolated from the existing recorder:

- Separate pipeline (does not interfere with per-camera recording)
- Independent configuration
- Can run simultaneously with recorder/preview
- Failures in mixer do not affect recorder

## Logging

Mixer operations are logged with the `mixer` prefix:

- `INFO`: State changes, scene applications, pipeline start/stop
- `WARNING`: Health degradation, state mismatches
- `ERROR`: Pipeline errors, failures, timeouts

## Future Enhancements

- ISO recording (individual camera recordings from mixer)
- Hardware encoder support (mpph264enc) for better performance
- GUI-based scene editor
- Transition effects between scenes
- Audio mixing support

