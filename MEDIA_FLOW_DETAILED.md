# Detailed Media Flow Map - R58 Video Recorder & Mixer

This document provides a detailed technical map of all media flows in the R58 Video Recorder & Mixer application.

## Overview

The system manages multiple video pipelines simultaneously:
- **Recording Pipelines**: Capture HDMI input to MP4/MKV files
- **Preview Pipelines**: Stream camera feeds to MediaMTX for live multiview
- **Mixer Pipeline**: Composite multiple sources with scene-based switching
- **Graphics Pipelines**: Overlay graphics, lower-thirds, presentations

## 1. Hardware Input Layer

### HDMI Inputs (4x LT6911UXE Bridges)
```
Physical HDMI → LT6911UXE Bridge → rkcif Driver → V4L2 Device
                                                         ↓
                ┌──────────────────────────────────────────┐
                │  /dev/video0   (cam0 - HDMI Port 1)     │
                │  /dev/video11  (cam1 - HDMI Port 2)     │
                │  /dev/video21  (cam2 - HDMI Port 3)     │
                │  /dev/video60  (cam3 - HDMI Port 4 / hdmirx) │
                └──────────────────────────────────────────┘
```

**Device Detection & Initialization:**
```python
detect_device_type(device) → "hdmirx" | "hdmi_rkcif" | "usb" | "unknown"
initialize_rkcif_device(device) → sets format on /dev/v4l-subdevX
get_device_capabilities(device) → {format, width, height, framerate, has_signal}
```

**Formats:**
- **video60 (hdmirx)**: NV16 (YUV 4:2:2) at source resolution/60fps
- **video0/11/21 (rkcif)**: NV16/YVYU/Bayer at source resolution
- **Signal Loss**: Returns black test pattern (1920x1080@30fps NV12)

## 2. Recording Pipeline (per camera)

### Pipeline Flow
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RECORDING PIPELINE                                │
└─────────────────────────────────────────────────────────────────────────┘

[HDMI Input] → [v4l2src] → [Format Conversion] → [Encoding] → [Outputs]
                   ↓              ↓                    ↓           ↓
              device=/dev/video60  NV24→NV12      x264enc/mpp   tee
              io-mode=mmap         videoconvert   bitrate=5000   ├→ File
              format=NV24          videoscale                    └→ MediaMTX
              width=1920           to 1920x1080
              height=1080
              framerate=60/1
```

### Detailed GStreamer Pipeline
```
HDMI (hdmirx):
  v4l2src device=/dev/video60 io-mode=mmap !
  video/x-raw,format=NV24,width=1920,height=1080,framerate=60/1 !
  videoconvert !
  video/x-raw,format=NV12 !
  videoscale !
  video/x-raw,width=1920,height=1080 !
  timeoverlay !
  x264enc tune=zerolatency bitrate=5000 speed-preset=superfast !
  video/x-h264 !
  tee name=t
    t. ! queue ! h264parse ! mp4mux ! filesink location=/path/to/recording.mp4
    t. ! queue ! flvmux streamable=true ! rtmpsink location=rtmp://127.0.0.1:1935/cam0

HDMI (rkcif with NV16):
  v4l2src device=/dev/video0 io-mode=mmap !
  video/x-raw,format=NV16,width={src_w},height={src_h},framerate={src_fps}/1 !
  videorate ! video/x-raw,framerate=30/1 !
  videoconvert !
  videoscale !
  video/x-raw,width=1920,height=1080,format=NV12 !
  timeoverlay !
  x264enc tune=zerolatency bitrate=5000 speed-preset=superfast !
  video/x-h264 !
  tee name=t
    t. ! queue ! h264parse ! mp4mux ! filesink location=/path/to/recording.mp4
    t. ! queue ! flvmux streamable=true ! rtmpsink location=rtmp://127.0.0.1:1935/cam0

HDMI (rkcif with Bayer):
  v4l2src device=/dev/video21 io-mode=mmap !
  video/x-bayer,format=rggb,width={src_w},height={src_h} !
  bayer2rgb !
  videoconvert !
  videoscale !
  video/x-raw,width=1920,height=1080,format=NV12 !
  timeoverlay !
  x264enc tune=zerolatency bitrate=5000 speed-preset=superfast !
  video/x-h264 !
  tee name=t
    t. ! queue ! h264parse ! mp4mux ! filesink location=/path/to/recording.mp4
    t. ! queue ! flvmux streamable=true ! rtmpsink location=rtmp://127.0.0.1:1935/cam0
```

### Encoder Options
**Software (x264enc)**: Used by default, reliable
- `tune=zerolatency`: Low latency encoding
- `bitrate=5000`: 5 Mbps (kbps)
- `speed-preset=superfast`: Fast encoding for real-time

**Hardware (mpph264enc/mpph265enc)**: Optional, for high-quality recordings
- `bps={bitrate*1000}`: Bits per second
- `bps-max={bitrate*2000}`: Max bitrate for VBR

### Output Formats
- **Recording**: MP4 (H.264) or MKV (H.265)
  - Path: `/var/recordings/{cam_id}/recording_%Y%m%d_%H%M%S.mp4`
  - Uses mp4mux (H.264) or matroskamux (H.265)
  
- **MediaMTX Stream**: RTMP → MediaMTX (if enabled)
  - Path: `rtmp://127.0.0.1:1935/{cam_id}`
  - Uses flvmux (H.264 only, FLV doesn't support H.265)

### Recording Manager (recorder.py)
**State Management:**
```
States: 'idle' | 'recording' | 'error'
Pipeline Management:
  - Cleanup stuck processes before start
  - Exclusive device access (stops preview if running)
  - EOS handling for graceful stop
  - Automatic error recovery
```

## 3. Preview Pipeline (per camera)

### Pipeline Flow
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PREVIEW PIPELINE                                  │
│                   (Streaming Only - No Recording)                        │
└─────────────────────────────────────────────────────────────────────────┘

[HDMI Input] → [v4l2src] → [Format Conversion] → [Encoding] → [MediaMTX]
                   ↓              ↓                    ↓            ↓
              device=/dev/video60  NV24→NV12       x264enc     RTMP
              io-mode=mmap         videoconvert    optimized   port 1935
              format=NV24          videoscale      for preview  ↓
              width=1920           to 1920x1080                HLS/WebRTC
              height=1080          framerate=30/1
              framerate=60/1
```

### Detailed GStreamer Pipeline
```
Preview (optimized for low latency and quality):
  v4l2src device=/dev/video60 io-mode=mmap !
  video/x-raw,format=NV16,width=1920,height=1080,framerate=60/1 !
  videorate ! video/x-raw,framerate=30/1 !
  videoconvert !
  video/x-raw,format=NV12 !
  queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream !
  x264enc tune=zerolatency bitrate=4000 speed-preset=veryfast key-int-max=30 threads=2 sync-lookahead=2 !
  video/x-h264 !
  queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream !
  flvmux streamable=true !
  rtmpsink location=rtmp://127.0.0.1:1935/cam0_preview sync=false
```

### Preview Optimizations
- **Bitrate**: 80% of recording bitrate (4000 kbps vs 5000 kbps)
- **Preset**: `veryfast` (better quality than ultrafast, still low latency)
- **Keyframes**: Every 1 second (`key-int-max=30` at 30fps)
- **Threading**: `threads=2` for better quality without much latency
- **Queue**: Leaky downstream queues for minimal buffering
- **Sync**: `sync=false` on rtmpsink to prevent blocking

### Preview Manager (preview.py)
**Features:**
- **Signal Detection**: Monitors HDMI signal presence via v4l2-ctl
- **Resolution Change Detection**: Restarts pipeline on resolution change
- **Automatic Recovery**: Restarts on signal loss and recovery
- **Health Monitoring**: Checks MediaMTX stream activity every 10s
- **Graceful Degradation**: Switches to "no_signal" state on signal loss

**States:**
```
'idle' | 'preview' | 'error' | 'no_signal'

Signal State Tracking:
  - signal_states[cam_id]: bool (has HDMI signal)
  - signal_loss_times[cam_id]: timestamp or None
  - current_resolutions[cam_id]: (width, height) tuple
```

**Health Check Loop (every 10s):**
1. Check HDMI signal status (via subdev)
2. Detect resolution changes
3. Verify MediaMTX stream is active
4. Restart pipeline if stale (>15s no data)

## 4. MediaMTX Streaming Server

### MediaMTX Configuration
```yaml
# Ports
rtspAddress: :8554      # RTSP input/output
rtmpAddress: :1935      # RTMP input (from pipelines)
hlsAddress: :8888       # HLS output (to browsers)
webrtcAddress: :8889    # WebRTC output (low latency)
srtAddress: :8890       # SRT output

# HLS Settings (optimized for minimum latency)
hlsSegmentCount: 7           # 7 segments
hlsSegmentDuration: 100ms    # 100ms per segment
hlsPartDuration: 50ms        # 50ms partial segments (LL-HLS)
# Total buffer: 7 × 100ms = 700ms

# Paths (auto-created by pipelines)
paths:
  cam0: {source: publisher}           # Recording/Preview
  cam0_preview: {source: publisher}   # Preview only
  cam1: {source: publisher}
  cam1_preview: {source: publisher}
  cam2: {source: publisher}
  cam2_preview: {source: publisher}
  cam3: {source: publisher}
  cam3_preview: {source: publisher}
  mixer_program: {source: publisher}  # Mixer output
```

### Protocol Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                        MediaMTX Server                          │
└─────────────────────────────────────────────────────────────────┘

GStreamer Pipeline (RTMP)
         ↓
    Port 1935 (RTMP Input)
         ↓
    MediaMTX Processing
         ↓
    ┌────┴────┬─────────┬─────────┐
    ↓         ↓         ↓         ↓
  RTSP     HLS      WebRTC     SRT
  :8554    :8888    :8889      :8890
    ↓         ↓         ↓         ↓
  VLC/OBS  Browser  Browser   Remote
```

### Stream URLs
**Recording Streams:**
- RTMP: `rtmp://localhost:1935/cam0`
- RTSP: `rtsp://localhost:8554/cam0`
- HLS: `http://localhost:8888/cam0/index.m3u8`
- WebRTC: `http://localhost:8889/cam0/whep`

**Preview Streams:**
- RTMP: `rtmp://localhost:1935/cam0_preview`
- RTSP: `rtsp://localhost:8554/cam0_preview`
- HLS: `http://localhost:8888/cam0_preview/index.m3u8` ← Used by web UI
- WebRTC: `http://localhost:8889/cam0_preview/whep` ← Ultra-low latency

**Mixer Program:**
- RTMP: `rtmp://localhost:1935/mixer_program`
- RTSP: `rtsp://localhost:8554/mixer_program`
- HLS: `http://localhost:8888/mixer_program/index.m3u8`
- WebRTC: `http://localhost:8889/mixer_program/whep`

### Latency Characteristics
- **RTMP Input**: ~50ms (from pipeline to MediaMTX)
- **HLS Output**: ~700ms (7 × 100ms segments)
- **WebRTC Output**: ~100ms (peer-to-peer with WHEP)
- **RTSP Output**: ~200ms (depends on buffer settings)

## 5. Mixer Pipeline (Compositor)

### Pipeline Architecture
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MIXER PIPELINE                                  │
│                  (Scene-Based Multi-Source Compositor)                   │
└─────────────────────────────────────────────────────────────────────────┘

Input Sources (up to 4):
  [Camera 0]  →  v4l2src (NV24→NV12) → queue → compositor.sink_0
  [Camera 1]  →  v4l2src (NV24→NV12) → queue → compositor.sink_1
  [Camera 2]  →  v4l2src (NV24→NV12) → queue → compositor.sink_2
  [Camera 3]  →  v4l2src (NV24→NV12) → queue → compositor.sink_3
  [File/Video]→  filesrc → decode → convert/scale → queue → compositor.sink_N
  [Image]     →  filesrc → decode → imagefreeze → convert/scale → queue → compositor.sink_N
  [Graphics]  →  graphics pipeline → convert/scale → queue → compositor.sink_N

                              ↓
                    ┌─────────────────┐
                    │   Compositor    │
                    │  (GStreamer)    │
                    │                 │
                    │  Pad Properties:│
                    │  - xpos, ypos   │
                    │  - width, height│
                    │  - zorder       │
                    │  - alpha        │
                    │  - crop (left,  │
                    │    top, right,  │
                    │    bottom)      │
                    └─────────────────┘
                              ↓
                    video/x-raw,1920x1080
                              ↓
                        timeoverlay
                              ↓
                    x264enc (bitrate=8000)
                              ↓
                        video/x-h264
                              ↓
                          tee name=t
                    ┌───────┴───────┐
                    ↓               ↓
                Recording        MediaMTX
                (optional)       (RTMP)
                    ↓               ↓
              h264parse        flvmux
                    ↓               ↓
              mp4mux/mkv      rtmpsink
                    ↓               ↓
              filesink        rtmp://127.0.0.1:1935/mixer_program
                    ↓
         /var/recordings/mixer/program_%Y%m%d_%H%M%S.mp4
```

### Scene System

**Scene Definition (JSON):**
```json
{
  "id": "quad",
  "label": "4-up grid",
  "resolution": {"width": 1920, "height": 1080},
  "slots": [
    {
      "source": "cam0",           // Source ID or file path
      "source_type": "camera",    // camera|file|image|graphics
      "x_rel": 0.0,              // Relative position (0.0-1.0)
      "y_rel": 0.0,
      "w_rel": 0.5,              // Relative size (0.0-1.0)
      "h_rel": 0.5,
      "z": 0,                    // Layer order
      "alpha": 1.0,              // Opacity (0.0-1.0)
      "crop_x": 0.0,             // Crop region (relative)
      "crop_y": 0.0,
      "crop_w": 1.0,
      "crop_h": 1.0,
      "file_path": null,         // For file/image sources
      "loop": false,             // For video files
      "duration": 10             // For images
    }
  ]
}
```

**Scene Manager (scenes.py):**
- Loads scenes from JSON files in `scenes/` directory
- Converts relative coords to absolute pixels
- Provides CRUD operations for scenes
- Database migration from JSON to SQLite

**Default Scenes:**
- `quad`: 2×2 grid (all 4 cameras)
- `two_up`: Side-by-side (2 cameras)
- `cam0_full` through `cam3_full`: Fullscreen per camera
- `pip_cam1_over_cam0`: Picture-in-picture
- `interview`: Two people side-by-side
- `presentation_focus`: Presenter + slides
- Custom scenes can be created via web UI

### Source Types

**Camera Sources:**
```
v4l2src device=/dev/video60 io-mode=mmap !
video/x-raw,format=NV24,width=1920,height=1080,framerate=60/1 !
videoconvert !
video/x-raw,format=NV12 !
videoscale !
video/x-raw,width=1920,height=1080 !
queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream !
video/x-raw,format=NV12,width=1920,height=1080
```

**File Sources (Video):**
```
filesrc location=/path/to/video.mp4 loop=true !
decodebin !
videoconvert !
videoscale !
video/x-raw,width=1920,height=1080 !
queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream
```

**Image Sources:**
```
filesrc location=/path/to/image.png !
pngdec !
imagefreeze duration=10 !
videoconvert !
videoscale !
video/x-raw,width=1920,height=1080 !
queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream
```

**Graphics Sources:**
```
[Graphics Pipeline] !
videoscale !
video/x-raw,width=1920,height=1080 !
queue max-size-buffers=2 max-size-time=0 max-size-bytes=0 leaky=downstream
```

### Scene Switching

**Dynamic Scene Application:**
1. **Same Sources**: Update compositor pad properties (instant)
   - xpos, ypos, width, height, zorder, alpha
   - No pipeline rebuild required
   
2. **Different Sources**: Rebuild entire pipeline
   - Stop current pipeline (send EOS, wait, set NULL)
   - Wait 0.5s for device release
   - Build new pipeline with new sources
   - Start pipeline and verify state

### Mixer Core (core.py)

**State Management:**
```
States: 'NULL' | 'PLAYING'

Pipeline Lifecycle:
  1. start() → _cleanup_stuck_pipelines()
             → _build_pipeline()
             → _set_state_with_timeout(PLAYING)
             → watchdog.start()
             → _start_health_check()
  
  2. apply_scene(scene_id) → Check if sources changed
                            → If same: Update pad properties
                            → If different: Rebuild pipeline
  
  3. stop() → _stop_health_check()
            → watchdog.stop()
            → pipeline.send_event(EOS)
            → _set_state_with_timeout(NULL)
```

**Health Monitoring:**
- **Watchdog**: Tracks buffer activity, errors, state
- **Health Check Thread**: Runs every 5 seconds
- **Recovery**: Automatic pipeline restart on unhealthy state
- **Timeout Protection**: 10-second timeout on all state changes

## 6. Graphics & Overlays

### Graphics Renderer (graphics.py)

**Graphics Types:**

**1. Lower-Third:**
```python
# Configuration
{
  "source_id": "lt1",
  "line1": "John Doe",
  "line2": "Senior Engineer",
  "background_color": "#000000",
  "background_alpha": 0.8,
  "text_color": "#FFFFFF",
  "line1_font": "Sans Bold 32",
  "line2_font": "Sans 24",
  "position": "bottom-left",
  "width": 600,
  "height": 120
}

# Pipeline (using Cairo overlay)
videotestsrc pattern=black !
video/x-raw,format=BGRA,width=600,height=120 !
cairooverlay !  # Render text with Cairo
videoconvert !
video/x-raw,format=NV12
```

**2. Presentation (Reveal.js Integration):**
```python
# Uses Reveal.js for slide rendering
# Served via /graphics endpoint
# Captured via browser automation or HTML rendering
```

**3. Stinger Transitions:**
```python
# Video transition overlay
filesrc location=/uploads/videos/stinger.mp4 !
decodebin !
videoconvert !
videoscale !
video/x-raw,width=1920,height=1080
```

**4. Timer/Scoreboard:**
```python
# Dynamic text overlay
videotestsrc pattern=black !
cairooverlay !  # Render timer/score with Cairo
videoconvert
```

### Graphics Templates (graphics_templates.py)

**Template System:**
```python
@dataclass
class GraphicsTemplate:
    id: str
    name: str
    type: str  # lower_third, stinger, timer, scoreboard
    description: str
    default_config: Dict[str, Any]

# Built-in templates
templates = [
    GraphicsTemplate(
        id="broadcast_news",
        name="Broadcast News",
        type="lower_third",
        default_config={
            "background_color": "#0066CC",
            "text_color": "#FFFFFF",
            "line1_font": "Sans Bold 36",
            "line2_font": "Sans 28"
        }
    )
]
```

## 7. Web API & Frontend

### FastAPI Application (main.py)

**API Endpoints:**

**Recording:**
- `POST /record/start/{cam_id}` - Start recording
- `POST /record/stop/{cam_id}` - Stop recording
- `POST /record/start-all` - Start all recordings
- `POST /record/stop-all` - Stop all recordings
- `GET /status` - Get all camera statuses
- `GET /recordings/{cam_id}` - List recordings

**Preview:**
- `POST /preview/start-all` - Start all previews
- `POST /preview/stop-all` - Stop all previews
- `GET /preview/status` - Get preview status
- `GET /api/preview/status` - Detailed preview status with signal info

**Mixer:**
- `GET /api/scenes` - List scenes
- `GET /api/scenes/{id}` - Get scene
- `POST /api/scenes` - Create scene
- `PUT /api/scenes/{id}` - Update scene
- `DELETE /api/scenes/{id}` - Delete scene
- `POST /api/mixer/set_scene` - Apply scene
- `POST /api/mixer/start` - Start mixer
- `POST /api/mixer/stop` - Stop mixer
- `GET /api/mixer/status` - Get mixer status

**Graphics:**
- `POST /api/graphics/lower_third` - Create lower-third
- `POST /api/graphics/graphics` - Create graphics source
- `GET /api/graphics/templates` - List templates
- `GET /api/graphics/{source_id}` - Get graphics config
- `DELETE /api/graphics/{source_id}` - Delete graphics

**HLS Proxy:**
- `GET /hls/{stream_path:path}` - Proxy MediaMTX HLS streams
- `GET /api/streams` - List available streams
- `GET /api/mediamtx/status` - Check MediaMTX connectivity

**File Management:**
- `POST /api/files/upload` - Upload video/image
- `GET /api/files` - List files
- `GET /api/files/{file_id}` - Get file metadata
- `DELETE /api/files/{file_id}` - Delete file

**Scene Queue:**
- `GET /api/queue` - Get queue
- `POST /api/queue` - Add to queue
- `PUT /api/queue/{index}` - Update queue item
- `POST /api/queue/jump/{index}` - Jump to position
- `DELETE /api/queue/{index}` - Remove from queue
- `POST /api/queue/advance` - Manually advance
- `POST /api/queue/start` - Start auto-advance
- `POST /api/queue/stop` - Stop auto-advance

### Frontend Pages

**1. Multiview (switcher.html):**
- HLS.js video players for all camera previews
- Real-time status indicators
- Touch-optimized scene buttons
- Multiview grid layout

**2. Scene Editor (editor.html):**
- Drag-and-drop scene creation
- Visual layout editor
- Source selection (cameras, files, graphics)
- Crop and positioning controls

**3. Graphics App (graphics.html):**
- Reveal.js presentation creator
- Slide editor with templates
- Export to mixer as graphics source

**4. Broadcast Graphics (broadcast_graphics.html):**
- Lower-third creator
- Template selection
- Live preview
- Export to mixer

**5. Control Panel (control.html):**
- Comprehensive device control
- Recording controls
- Preview controls
- Mixer controls
- All in one interface

## 8. Data Flow Summary

### Recording Flow
```
HDMI Input → v4l2src → videoconvert/scale → encoder → tee
                                                       ├→ mp4mux → filesink (MP4)
                                                       └→ flvmux → rtmpsink (RTMP) → MediaMTX
```

### Preview Flow
```
HDMI Input → v4l2src → videoconvert/scale → encoder → flvmux → rtmpsink → MediaMTX
                                                                              ├→ HLS (Browser)
                                                                              └→ WebRTC (Browser)
```

### Mixer Flow
```
Sources (Cameras/Files/Graphics) → compositor → encoder → tee
                                                           ├→ mp4mux → filesink (optional)
                                                           └→ flvmux → rtmpsink → MediaMTX
```

### Graphics Flow
```
Graphics Source → cairooverlay/filesrc → videoconvert → Compositor Slot
```

### Web UI Flow
```
Browser → FastAPI (/api/*) → Python Managers (Recorder/Preview/Mixer)
                                     ↓
                                GStreamer Pipelines
                                     ↓
                                MediaMTX (RTMP)
                                     ↓
Browser ← HLS/WebRTC (/hls/*) ← MediaMTX (HLS/WebRTC)
```

## 9. Configuration & State Management

### Configuration (config.yml)
```yaml
platform: r58  # auto-detects: r58 or macos

cameras:
  cam0:
    device: /dev/video60
    resolution: 1920x1080
    bitrate: 5000
    codec: h264
    output_path: /var/recordings/cam0/recording_%Y%m%d_%H%M%S.mp4
    mediamtx_enabled: true

mixer:
  enabled: true
  output_resolution: 1920x1080
  output_bitrate: 8000
  output_codec: h264
  recording_enabled: false
  recording_path: /var/recordings/mixer/program_%Y%m%d_%H%M%S.mp4
  mediamtx_enabled: true
  mediamtx_path: mixer_program
  scenes_dir: scenes

mediamtx:
  enabled: true
  rtsp_port: 8554
  rtmp_port: 1935
  hls_port: 8888
  webrtc_port: 8889
```

### State Tracking

**Recorder States:**
```python
states: Dict[str, str] = {
    'cam0': 'idle' | 'recording' | 'error',
    'cam1': 'idle' | 'recording' | 'error',
    # ...
}
```

**Preview States:**
```python
preview_states: Dict[str, str] = {
    'cam0': 'idle' | 'preview' | 'error' | 'no_signal',
    'cam1': 'idle' | 'preview' | 'error' | 'no_signal',
    # ...
}
signal_states: Dict[str, bool] = {'cam0': True, 'cam1': False}
signal_loss_times: Dict[str, Optional[float]] = {'cam0': None, 'cam1': 1640000000.0}
current_resolutions: Dict[str, Tuple[int, int]] = {'cam0': (1920, 1080)}
```

**Mixer States:**
```python
state: str = 'NULL' | 'PLAYING'
current_scene: Optional[Scene] = Scene(id='quad', ...)
watchdog.health: HealthStatus = HEALTHY | DEGRADED | UNHEALTHY | FAILED
```

## 10. Hardware Acceleration

### Rockchip MPP Encoders
```
mpph264enc: Hardware H.264 encoder
  - bps={bitrate*1000}: Bitrate in bits/second
  - bps-max={bitrate*2000}: Max bitrate for VBR
  - Low latency: ~50-100ms pipeline latency
  - CPU usage: ~5-10% per stream

mpph265enc: Hardware H.265 encoder
  - Better compression than H.264
  - Used for high-quality recordings
  - CPU usage: ~5-10% per stream
```

### Rockchip RGA (Raster Graphics Acceleration)
```
Hardware-accelerated:
  - videoscale: Scaling (e.g., 3840x2160 → 1920x1080)
  - videoconvert: Format conversion (e.g., NV24 → NV12)
  - rotation: 90/180/270 degree rotation
```

### CPU vs Hardware Encoding
**Software (x264enc):**
- CPU usage: ~30-40% per stream (1080p@60fps)
- Quality: Better quality control, more reliable
- Latency: ~100-200ms

**Hardware (MPP):**
- CPU usage: ~5-10% per stream (1080p@60fps)
- Quality: Good, less configurable
- Latency: ~50-100ms
- Simultaneous streams: Up to 4x 1080p@60fps

## 11. Error Handling & Recovery

### Recording Pipeline
**Error Detection:**
- Bus message monitoring (ERROR, WARNING)
- State change failures
- Device busy/unavailable

**Recovery:**
1. Log error with full details
2. Attempt pipeline restart
3. If device busy, skip restart
4. Set state to 'error'

### Preview Pipeline
**Error Detection:**
- HDMI signal loss (v4l2-ctl query)
- Resolution changes
- Pipeline stalls (no MediaMTX data >15s)
- State mismatches

**Recovery:**
1. Signal loss: Set 'no_signal' state, stop pipeline
2. Signal recovery: Re-initialize device, restart pipeline
3. Resolution change: Stop, update resolution, restart
4. Stale pipeline: Force restart after 15s

### Mixer Pipeline
**Error Detection:**
- Watchdog monitors: buffer activity, state, errors
- Health check every 5 seconds
- Timeout on state changes (10s)

**Recovery:**
1. Detect unhealthy state
2. Send EOS, wait for EOS message
3. Set to NULL state
4. Wait 0.5s for device release
5. Rebuild pipeline
6. Restart with current scene

### Cleanup Mechanisms
**Stuck Pipeline Cleanup:**
```bash
# Kill any stuck gst-launch processes using video devices
pgrep -f "gst-launch.*video60" | xargs kill -9

# Test device availability with fcntl
fcntl.flock(device_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
```

## 12. Performance Characteristics

### Latency
- **Recording**: Near-zero (direct to file)
- **Preview (HLS)**: ~700ms (7 × 100ms segments)
- **Preview (WebRTC)**: ~100ms (peer-to-peer)
- **Mixer**: ~200ms (encoding + compositing)

### Throughput
- **Recording**: 5-8 MB/s per stream (5000 kbps)
- **Preview**: 4-6 MB/s per stream (4000 kbps)
- **Mixer**: 8-10 MB/s (8000 kbps)
- **4 cameras + mixer**: ~30-40 MB/s total

### Resource Usage
- **CPU (idle)**: ~5-10%
- **CPU (1 camera hardware)**: ~10-15%
- **CPU (1 camera software)**: ~30-40%
- **CPU (4 cameras + mixer)**: ~20-30% (hardware) / ~80-100% (software)
- **Memory**: ~500-600 MB (4 cameras + mixer)
- **Storage**: ~6-8 MB/s per recording

### Simultaneous Operations
- **4 cameras recording**: ✓
- **4 cameras preview**: ✓
- **Mixer + 4 cameras**: ✓ (if cameras not recording)
- **Recording + Preview**: ✗ (same device conflict)
- **Mixer + Recording**: ✗ (same device conflict)

## 13. System Integration

### Systemd Services
```
preke-recorder.service:
  - Runs main FastAPI application
  - Auto-restart on failure
  - Starts on boot

mediamtx.service:
  - Runs MediaMTX server
  - Auto-restart on failure
  - Starts before preke-recorder
```

### File System Layout
```
/opt/preke-r58-recorder/       # Application root
├── src/                       # Python source
├── scenes/                    # Scene JSON files
├── uploads/                   # Uploaded media
│   ├── images/
│   └── videos/
├── data/
│   └── app.db                # SQLite database
├── config.yml                # Configuration
└── venv/                     # Python virtual environment

/var/recordings/              # Recordings
├── cam0/                     # Camera 0 recordings
├── cam1/
├── cam2/
├── cam3/
└── mixer/                    # Mixer program recordings
```

### Network Ports
- **8000**: FastAPI HTTP API & Web UI
- **8554**: MediaMTX RTSP
- **1935**: MediaMTX RTMP (pipeline input)
- **8888**: MediaMTX HLS (web output)
- **8889**: MediaMTX WebRTC
- **8890**: MediaMTX SRT

### Remote Access (Cloudflare Tunnel)
```
Local:
  http://192.168.1.25:8000          → FastAPI
  http://192.168.1.25:8888          → MediaMTX HLS

Remote (via Cloudflare):
  https://recorder.itagenten.no     → FastAPI (proxied)
  https://recorder.itagenten.no/hls → MediaMTX HLS (proxied via FastAPI)
```

## 14. Database Schema (SQLite)

### Tables
**scenes:**
```sql
CREATE TABLE scenes (
    id TEXT PRIMARY KEY,
    label TEXT,
    resolution_width INTEGER,
    resolution_height INTEGER,
    slots TEXT,  -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**files:**
```sql
CREATE TABLE files (
    id TEXT PRIMARY KEY,
    filename TEXT,
    file_type TEXT,  -- video, image
    file_path TEXT,
    loop BOOLEAN,
    uploaded_at TIMESTAMP
);
```

**queue:**
```sql
CREATE TABLE queue (
    position INTEGER PRIMARY KEY,
    scene_id TEXT,
    duration INTEGER,
    transition TEXT,
    auto_advance BOOLEAN
);
```

**graphics:**
```sql
CREATE TABLE graphics (
    source_id TEXT PRIMARY KEY,
    source_type TEXT,  -- lower_third, presentation, timer, scoreboard
    data TEXT,  -- JSON config
    created_at TIMESTAMP
);
```

## Conclusion

This detailed map covers all media flows, from hardware input through GStreamer pipelines, MediaMTX streaming, mixer compositing, graphics overlays, and web delivery. The system is designed for:

- **Reliability**: Automatic error recovery, health monitoring, graceful degradation
- **Performance**: Hardware acceleration, optimized encoding, low latency
- **Flexibility**: Scene-based mixing, multiple source types, dynamic configuration
- **Scalability**: Handles 4 simultaneous streams with mixer output

For a simplified overview, see `MEDIA_FLOW_SIMPLIFIED.md`.
