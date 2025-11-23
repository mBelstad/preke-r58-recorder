# R58 Video Recorder & Mixer - Application Description

## Overview

The R58 Video Recorder & Mixer is a professional-grade video capture and streaming application designed for the Mekotronics R58 4x4 3S (RK3588) embedded system. It provides simultaneous multi-camera recording, live preview, and real-time video mixing capabilities, all running on a single Python application without containerization.

## What It Does

### Core Functionality

1. **Multi-Camera Recording**
   - Records from up to 4 HDMI inputs simultaneously
   - Hardware-accelerated encoding (H.264/H.265)
   - Individual camera control (start/stop per camera)
   - Automatic file management with timestamps

2. **Live Preview & Streaming**
   - Ultra-low latency live preview (<100ms with WebRTC)
   - Multiview display of all active cameras
   - WebRTC and HLS streaming support
   - Real-time camera status monitoring

3. **Video Mixer**
   - Scene-based video compositing
   - Multiple layout presets (quad, 2-up, fullscreen, PiP)
   - Real-time scene switching
   - Program output recording and streaming
   - Automatic camera availability detection

4. **Web Interface**
   - Modern, responsive UI
   - Real-time status monitoring
   - One-click recording control
   - Camera status indicators
   - Professional broadcaster-style layout

## Technology Stack

### Backend

**Python 3.11+**
- FastAPI web framework for REST API
- Type hints throughout for code safety
- Async/await for non-blocking operations

**GStreamer**
- Core media processing framework
- Hardware-accelerated encoding (MPP encoders on RK3588)
- Software fallback (x264enc) for reliability
- Pipeline-based architecture for flexibility

**MediaMTX**
- RTSP/RTMP/SRT/WebRTC streaming server
- HLS output for web playback
- Low-latency streaming support

### Frontend

**HTML5/CSS3/JavaScript**
- Vanilla JavaScript (no frameworks)
- HLS.js for adaptive streaming
- WebRTC API for ultra-low latency
- Responsive CSS Grid/Flexbox layouts

### Hardware

**Mekotronics R58 4x4 3S (RK3588)**
- Rockchip RK3588S SoC
- 4x HDMI-IN via LT6911UXE chips
- Hardware video encoders (MPP)
- Linux kernel 6.1.99 with custom drivers

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Web Browser                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Multiview  │  │   Controls   │  │    Stats     │ │
│  │   Display    │  │   Panel      │  │    Panel     │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
                        │ HTTP/WebRTC/HLS
                        │
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application (Python)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Recorder   │  │   Preview    │  │    Mixer     │ │
│  │   Manager    │  │   Manager    │  │    Core      │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Scene      │  │   Watchdog    │  │   Pipeline  │ │
│  │   Manager    │  │   (Health)    │  │   Builder   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
                        │ GStreamer Pipelines
                        │
┌─────────────────────────────────────────────────────────┐
│              GStreamer Processing Layer                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  v4l2src     │  │  Compositor  │  │   Encoders   │ │
│  │  (Capture)   │  │  (Mixing)    │  │  (x264/MPP)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Tee        │  │   Muxers     │  │   Sinks      │ │
│  │  (Split)     │  │  (MP4/MKV)   │  │ (File/RTMP)  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
                        │ V4L2 / RTMP
                        │
┌─────────────────────────────────────────────────────────┐
│              Hardware & MediaMTX                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ /dev/video60 │  │  MediaMTX    │  │   Storage    │ │
│  │ (HDMI-IN)    │  │  (Streaming) │  │  (Recordings)│ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Video Capture

**GStreamer Pipeline Structure:**
```
v4l2src (device=/dev/video60) 
  → video/x-raw,format=NV24 
  → videoconvert (NV24→NV12) 
  → videoscale 
  → encoder (x264enc/mpph264enc) 
  → muxer (mp4mux/matroskamux) 
  → filesink
```

**Key Technical Details:**
- **NV24 Format**: The R58's HDMI capture outputs YUV 4:4:4 (NV24) format
- **Format Conversion**: Must convert to NV12 (4:2:0) before encoding
- **Hardware Acceleration**: Uses Rockchip MPP encoders when available
- **Software Fallback**: Falls back to x264enc for reliability
- **Device Access**: Uses `io-mode=mmap` for efficient memory mapping

### 2. Live Preview & Streaming

**Preview Pipeline:**
```
v4l2src → videoconvert → videoscale → encoder → flvmux → rtmpsink → MediaMTX
```

**Streaming Flow:**
1. GStreamer pipeline captures from device
2. Encodes video (H.264, optimized for low latency)
3. Streams to MediaMTX via RTMP
4. MediaMTX provides multiple outputs:
   - **HLS**: For web playback (http://host:8888/cam0/index.m3u8)
   - **WebRTC**: For ultra-low latency (WHEP protocol)
   - **RTSP**: For professional streaming tools

**Latency Optimization:**
- **HLS**: 100ms segments, 3-segment buffer (~300ms total)
- **WebRTC**: Direct peer connection (<100ms)
- **Encoder Settings**: `tune=zerolatency`, `key-int-max=30`, minimal buffering

### 3. Video Mixer

**Compositor Pipeline:**
```
v4l2src (cam0) → compositor.sink_0 ─┐
v4l2src (cam1) → compositor.sink_1 ─┤
v4l2src (cam2) → compositor.sink_2 ─┼→ compositor → encoder → tee → outputs
v4l2src (cam3) → compositor.sink_3 ─┘
```

**Scene System:**
- **JSON-Based Scenes**: Stored in `/scenes/` directory
- **Relative Coordinates**: 0.0-1.0 for resolution independence
- **Dynamic Layouts**: Pad properties set at runtime
- **Automatic Rebuild**: Pipeline rebuilds when scene sources change

**Scene Example (Quad View):**
```json
{
  "id": "quad",
  "label": "4-up grid",
  "resolution": {"width": 1920, "height": 1080},
  "slots": [
    {"source": "cam0", "x": 0.0, "y": 0.0, "w": 0.5, "h": 0.5},
    {"source": "cam1", "x": 0.5, "y": 0.0, "w": 0.5, "h": 0.5},
    {"source": "cam2", "x": 0.0, "y": 0.5, "w": 0.5, "h": 0.5},
    {"source": "cam3", "x": 0.5, "y": 0.5, "w": 0.5, "h": 0.5}
  ]
}
```

### 4. Health Monitoring & Recovery

**Watchdog System:**
- **Buffer Monitoring**: Tracks video buffer activity
- **State Checking**: Verifies pipeline state matches expected
- **Error Detection**: Captures GStreamer bus errors
- **Automatic Recovery**: Rebuilds pipeline on failure

**Recovery Process:**
1. Detect unhealthy state (no buffers, errors, wrong state)
2. Graceful teardown (EOS → NULL state)
3. Wait for device release
4. Rebuild pipeline
5. Restart with current scene

### 5. Device Management

**Smart Camera Detection:**
- Checks device file existence (`/dev/video60`, etc.)
- Tests device availability (fcntl lock test)
- Skips unavailable cameras automatically
- Prevents "device busy" errors

**Conflict Prevention:**
- Only one pipeline per device at a time
- Automatic cleanup of stuck processes
- Delays between pipeline start/stop
- Exclusive device access enforcement

## Key Features

### Reliability

- **Timeout Protection**: All state changes have 10-second timeouts
- **Error Recovery**: Automatic pipeline recovery on failure
- **Device Cleanup**: Kills stuck processes before starting
- **Health Monitoring**: Continuous health checks every 5 seconds

### Performance

- **Hardware Acceleration**: Uses RK3588 MPP encoders when available
- **Low Latency**: Optimized for <100ms WebRTC, ~300ms HLS
- **Efficient Encoding**: Tuned for real-time performance
- **Minimal Buffering**: Leaky queues, minimal buffer sizes

### Flexibility

- **Scene System**: Easy to add new layouts via JSON
- **Configurable**: YAML-based configuration
- **Platform Detection**: Auto-detects macOS (dev) vs R58 (prod)
- **Codec Support**: H.264 and H.265 encoding

### Isolation

- **Separate Pipelines**: Recorder, preview, and mixer run independently
- **Failure Isolation**: Mixer failures don't affect recorder
- **Resource Management**: Proper device release and cleanup

## API Endpoints

### Recorder API
- `GET /health` - System health check
- `POST /record/start/{cam_id}` - Start recording for camera
- `POST /record/stop/{cam_id}` - Stop recording for camera
- `GET /status` - Get status of all cameras

### Mixer API
- `GET /api/scenes` - List all available scenes
- `GET /api/scenes/{id}` - Get scene definition
- `POST /api/mixer/set_scene` - Apply scene to mixer
- `POST /api/mixer/start` - Start mixer pipeline
- `POST /api/mixer/stop` - Stop mixer pipeline
- `GET /api/mixer/status` - Get mixer status and health

## Configuration

**config.yml** - Main configuration file:
```yaml
platform: auto  # Auto-detects macOS or R58
log_level: INFO

mixer:
  enabled: true
  output_resolution: 1920x1080
  output_bitrate: 8000  # kbps
  output_codec: h264
  recording_enabled: false
  mediamtx_enabled: true
  scenes_dir: scenes

cameras:
  cam0:
    device: /dev/video60  # HDMI-IN
    resolution: 1920x1080
    bitrate: 5000
    codec: h264
```

## Deployment

**Systemd Services:**
- `preke-recorder.service` - Main application
- `mediamtx.service` - Streaming server

**Automatic Startup:**
- Services start on boot
- Automatic recovery on failure
- Log rotation and management

## Use Cases

1. **Live Production**: Multi-camera live streaming with scene switching
2. **Event Recording**: Simultaneous recording from multiple angles
3. **Broadcast Monitoring**: Real-time multiview of all inputs
4. **Content Creation**: Program output recording with ISO backups
5. **Surveillance**: Continuous recording with live monitoring

## Technical Highlights

### Why GStreamer?
- **Hardware Support**: Direct access to RK3588 MPP encoders
- **Flexibility**: Pipeline-based architecture allows complex workflows
- **Performance**: Low-level control for optimization
- **Maturity**: Battle-tested in professional video applications

### Why FastAPI?
- **Modern**: Async/await support for non-blocking operations
- **Type Safety**: Automatic validation with type hints
- **Documentation**: Auto-generated API docs
- **Performance**: High throughput for concurrent requests

### Why MediaMTX?
- **Protocol Support**: RTSP, RTMP, SRT, WebRTC, HLS all in one
- **Low Latency**: Optimized for real-time streaming
- **WebRTC**: Native WHEP support for browser integration
- **Reliability**: Handles connection management and buffering

## Performance Characteristics

- **Recording Latency**: Near-zero (direct to file)
- **Preview Latency**: <100ms (WebRTC), ~300ms (HLS)
- **Mixer Latency**: ~200ms (encoding + compositing)
- **CPU Usage**: ~30-40% per active camera (with hardware encoding)
- **Memory**: ~200MB base + ~50MB per active pipeline
- **Disk I/O**: Depends on bitrate and number of recordings

## Future Enhancements

- **NDI Support**: Network Device Interface for professional workflows
- **SRT Output**: Secure Reliable Transport for long-distance streaming
- **ISO Recording**: Individual camera recordings from mixer
- **Advanced Scenes**: Transitions, effects, overlays
- **Remote Control**: WebSocket API for real-time control
- **Multi-Device**: Support for multiple R58 units

## Conclusion

The R58 Video Recorder & Mixer is a production-ready solution that combines the power of GStreamer, the flexibility of Python, and the reliability of modern web technologies to deliver professional video capture and streaming capabilities on embedded hardware. Its modular architecture, robust error handling, and comprehensive feature set make it suitable for a wide range of video production and monitoring applications.

