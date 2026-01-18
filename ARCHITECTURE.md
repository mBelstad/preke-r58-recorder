# Mixer Core Architecture

## Overview

The Mixer Core is a scene-based video mixer that composites up to 4 HDMI inputs into a single program output. It is designed to run alongside the existing per-camera recorder, providing complete isolation and independent operation.

## Architecture Principles

### 1. Isolation
- **Separate Pipeline**: Mixer uses its own GStreamer pipeline, independent of recorder/preview pipelines
- **Independent Configuration**: Mixer settings in `config.yml` under `mixer:` section
- **No Cross-Dependencies**: Mixer failures do not affect existing recorder functionality
- **Separate Resources**: Uses same video devices but manages them independently

### 2. Robustness
- **Timeout-Based State Transitions**: All GStreamer state changes have 10-second timeouts
- **Health Monitoring**: Watchdog tracks pipeline state, buffer activity, and errors
- **Automatic Recovery**: Health check thread detects hangs and attempts graceful recovery
- **Graceful Teardown**: EOS handling and proper state cleanup prevent device locks

### 3. Modularity
- **Focused Pipelines**: Mixer pipeline only handles capture → mix → encode → outputs
- **Clear Lifecycle**: Well-defined start/stop methods with proper cleanup
- **Component Separation**: Scene Manager, Mixer Core, and Watchdog are separate modules

## Component Details

### Scene Manager (`src/mixer/scenes.py`)

**Responsibilities:**
- Load scene definitions from JSON files
- Convert relative coordinates (0-1) to absolute pixels
- Provide scene CRUD operations

**Scene Format:**
```json
{
  "id": "quad",
  "label": "4-up grid",
  "resolution": {"width": 1920, "height": 1080},
  "slots": [
    {
      "source": "cam0",
      "x_rel": 0.0,
      "y_rel": 0.0,
      "w_rel": 0.5,
      "h_rel": 0.5,
      "z": 0,
      "alpha": 1.0
    }
  ]
}
```

**Default Scenes:**
- `quad`: 2x2 grid of all 4 cameras
- `two_up`: Side-by-side (2 cameras)
- `cam0_full` through `cam3_full`: Fullscreen per camera
- `pip_cam1_over_cam0`: Picture-in-picture

### Mixer Core (`src/mixer/core.py`)

**Pipeline Structure:**
```
[4x v4l2src] → [videoconvert/scale] → [compositor] → [encoder] → [tee] → [outputs]
                                                                    ├─→ [recording]
                                                                    └─→ [MediaMTX]
```

**Key Features:**
- **Dynamic Scene Application**: Updates compositor pad properties at runtime
- **Pipeline Rebuild**: Rebuilds pipeline if scene requires different sources
- **Timeout Protection**: All state transitions use `_set_state_with_timeout()`
- **Bus Message Handling**: Comprehensive error/warning/state change logging

**State Management:**
- `NULL`: Pipeline not created or stopped
- `PLAYING`: Pipeline active and mixing
- State transitions are atomic and timeout-protected

### Watchdog (`src/mixer/watchdog.py`)

**Health Checks:**
- Pipeline state verification (should be PLAYING when active)
- Buffer activity monitoring (detects stalls)
- Error tracking and classification

**Health Status:**
- `HEALTHY`: Normal operation
- `DEGRADED`: Minor issues (state mismatch, occasional errors)
- `UNHEALTHY`: Serious issues (no buffers, persistent errors)
- `FAILED`: Pipeline failure

**Recovery Process:**
1. Health check detects unhealthy state
2. Logs problem with full details
3. Stops current pipeline gracefully (EOS → NULL)
4. Waits for device release (0.5s)
5. Rebuilds pipeline with current scene
6. Restarts pipeline
7. Verifies successful recovery

## API Integration

### Endpoints

All mixer endpoints are under `/api/` prefix:

- `GET /api/scenes` - List all scenes
- `GET /api/scenes/{id}` - Get scene definition
- `POST /api/mixer/set_scene` - Apply scene
- `POST /api/mixer/start` - Start mixer
- `POST /api/mixer/stop` - Stop mixer
- `GET /api/mixer/status` - Get status and health

### Error Handling

- Returns `503 Service Unavailable` if mixer is disabled
- Returns `404 Not Found` for invalid scene IDs
- Returns `500 Internal Server Error` for pipeline failures
- All errors include descriptive messages

## Configuration

### Mixer Settings (`config.yml`)

```yaml
mixer:
  enabled: false  # Enable/disable mixer
  output_resolution: 1920x1080
  output_bitrate: 8000  # kbps
  output_codec: h264  # h264 or h265
  recording_enabled: false
  recording_path: /var/recordings/mixer/program_%Y%m%d_%H%M%S.mp4
  mediamtx_enabled: true
  mediamtx_path: mixer_program
  scenes_dir: scenes
```

### MediaMTX Integration

Add mixer path to `mediamtx.yml`:
```yaml
paths:
  mixer_program:
    source: publisher
```

## Pipeline Design

### Source Handling

Each camera source is processed independently:
- HDMI inputs (`/dev/video60`): NV24 → NV12 conversion, proper framerate handling
- Other devices: Standard v4l2src with videoconvert/scale
- All sources scaled to compositor output resolution

### Compositor

- Uses GStreamer `compositor` element
- Pad properties set per scene slot:
  - `xpos`, `ypos`: Position
  - `width`, `height`: Size
  - `zorder`: Layer ordering
  - `alpha`: Opacity

### Encoding

- **Current**: `x264enc` (software, reliable)
- **Future**: `mpph264enc` (hardware, better performance)
- Encoder settings optimized for real-time mixing

### Outputs

- **Recording**: Optional MP4/MKV file output
- **MediaMTX**: RTMP push for streaming
- Both outputs use `tee` element (single encode, multiple outputs)

## Health Monitoring

### Metrics Tracked

1. **Pipeline State**: Current GStreamer state vs expected
2. **Buffer Activity**: Time since last buffer processed
3. **Error Count**: GStreamer bus errors and warnings
4. **State Transitions**: Success/failure of state changes

### Health Check Loop

- Runs every 5 seconds
- Checks pipeline state and buffer activity
- Triggers recovery if unhealthy
- Logs all health status changes

### Recovery Strategy

1. **Detection**: Health check identifies problem
2. **Teardown**: Graceful pipeline stop (EOS → NULL)
3. **Wait**: 0.5s delay for device release
4. **Rebuild**: Create new pipeline with current scene
5. **Restart**: Start pipeline with timeout protection
6. **Verify**: Check state and buffer activity

## Logging

All mixer operations are logged with appropriate levels:

- **INFO**: Normal operations (start/stop, scene changes, state transitions)
- **WARNING**: Health degradation, state mismatches
- **ERROR**: Pipeline errors, failures, timeouts
- **DEBUG**: Detailed pipeline construction, pad property updates

## Testing

### Scene Manager Tests

Located in `tests/test_scenes.py`:
- Default scene creation
- Scene loading and retrieval
- Coordinate conversion (relative → absolute)
- Scene serialization/deserialization

### Manual Testing

1. **Enable Mixer**: Set `mixer.enabled: true` in `config.yml`
2. **Start Application**: Run `./start.sh` or `python -m src.main`
3. **List Scenes**: `curl http://localhost:8000/api/scenes`
4. **Start Mixer**: `curl -X POST http://localhost:8000/api/mixer/start`
5. **Set Scene**: `curl -X POST http://localhost:8000/api/mixer/set_scene -d '{"id": "quad"}'`
6. **Check Status**: `curl http://localhost:8000/api/mixer/status`

## Future Enhancements

1. **ISO Recording**: Record individual camera feeds from mixer
2. **Hardware Acceleration**: Switch to `mpph264enc` for better performance
3. **Scene Editor GUI**: Web-based scene editor
4. **Transitions**: Smooth transitions between scenes
5. **Audio Mixing**: Mix audio from multiple sources
6. **Advanced Layouts**: Custom layouts, borders, labels

### SFU for Multiple Viewers

**Current Architecture**: Each browser creates a direct WebRTC connection to MediaMTX. This works well for a few viewers but can overwhelm the R58 device with many simultaneous connections.

**Future Enhancement Options**:

1. **VDO.ninja Meshcast Mode**: Use VDO.ninja's `&meshcast` mode as a relay SFU. This would have the VPS act as a relay, reducing load on the R58.

2. **MediaMTX Cascading/Replication**: Set up MediaMTX replication from R58 to VPS, allowing the VPS to serve multiple viewers while R58 only needs to stream to the VPS once.

3. **Cloudflare Stream**: For high-scale distribution, integrate Cloudflare Stream which provides global CDN distribution for live video with automatic transcoding and adaptive bitrate.

**Considerations**:
- SFU adds latency (extra hop)
- Requires additional infrastructure (VPS resources)
- Only needed for scenarios with many simultaneous viewers (>10)
- Current P2P architecture is optimal for low-latency, small-scale use cases

## Troubleshooting

### Pipeline Won't Start

- Check device availability: `v4l2-ctl --list-devices`
- Verify scene sources match configured cameras
- Check logs for GStreamer errors
- Ensure MediaMTX is running (if enabled)

### Pipeline Hangs

- Health check should detect and recover automatically
- Check logs for timeout messages
- Verify no other processes are using video devices
- Manual recovery: Stop mixer, wait 2s, restart

### Scene Not Applying

- Verify scene ID exists: `GET /api/scenes`
- Check mixer is running: `GET /api/mixer/status`
- If sources changed, pipeline will rebuild automatically
- Check logs for pad property errors

### Poor Performance

- Reduce output bitrate
- Lower output resolution
- Consider hardware encoder (when stable)
- Check system resources (CPU, memory)

