# Simplified Media Flow Map - R58 Video Recorder & Mixer

This document provides a high-level overview of the media flow in the R58 Video Recorder & Mixer application.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     R58 VIDEO RECORDER & MIXER                      │
│                    Professional Video Production System              │
└─────────────────────────────────────────────────────────────────────┘
```

## 1. High-Level Architecture

```
┌────────────────┐
│  HDMI Sources  │  (External Cameras, Computers, etc.)
└───────┬────────┘
        │
        ↓
┌────────────────┐
│ HDMI Capture   │  4x LT6911UXE Bridges + RK3588 Hardware
│  Hardware      │  /dev/video0, /dev/video11, /dev/video21, /dev/video60
└───────┬────────┘
        │
        ↓
┌────────────────────────────────────────────────────────────────┐
│              GSTREAMER PROCESSING LAYER                        │
│                                                                │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │  Recording  │  │   Preview    │  │  Mixer (Program)  │   │
│  │  Pipelines  │  │  Pipelines   │  │     Pipeline      │   │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬─────────┘   │
│         │                 │                     │             │
└─────────┼─────────────────┼─────────────────────┼─────────────┘
          │                 │                     │
          ↓                 ↓                     ↓
  ┌──────────────┐  ┌──────────────┐    ┌──────────────┐
  │   MP4/MKV    │  │   MediaMTX   │    │   MediaMTX   │
  │    Files     │  │   Streams    │    │   Streams    │
  └──────────────┘  └──────┬───────┘    └──────┬───────┘
                           │                    │
                           ↓                    ↓
                    ┌──────────────────────────────┐
                    │        Web Browser UI        │
                    │  - Multiview Display         │
                    │  - Scene Switcher            │
                    │  - Graphics Control          │
                    │  - Recording Control         │
                    └──────────────────────────────┘
```

## 2. Three Main Workflows

### Workflow 1: Recording
**Purpose**: Record camera feeds to MP4 files

```
HDMI Input → GStreamer Pipeline → MP4 File
               ↓
            (optional)
               ↓
           MediaMTX → Web Browser (monitoring)
```

**Key Features:**
- Records each camera independently
- Hardware-accelerated encoding (H.264/H.265)
- Timestamps in filenames
- Can stream while recording (via tee)

**User Actions:**
- Start/stop recording per camera
- View recordings
- Download recordings

---

### Workflow 2: Preview (Multiview)
**Purpose**: Live preview of all cameras without recording

```
HDMI Input → GStreamer Pipeline → MediaMTX → Web Browser
                                      ↓
                                  HLS/WebRTC
                                      ↓
                              Low-latency video
```

**Key Features:**
- Streaming-only (no recording)
- Optimized for low latency (~700ms HLS, ~100ms WebRTC)
- Automatic signal detection and recovery
- Resolution change handling

**User Actions:**
- View all cameras simultaneously
- Monitor HDMI signal status
- No files created

---

### Workflow 3: Mixer (Program Output)
**Purpose**: Composite multiple sources with scene-based switching

```
Camera 1 ─┐
Camera 2 ─┤
Camera 3 ─┼→ GStreamer Compositor → Encoded Video → MediaMTX
Camera 4 ─┤      (Scene Layout)                         ↓
Files    ─┤                                         Web Browser
Graphics ─┘                                             ↓
                                                    (optional)
                                                        ↓
                                                    Recording
```

**Key Features:**
- Scene-based switching (quad, 2-up, PiP, fullscreen, etc.)
- Mix cameras, videos, images, and graphics
- Real-time scene switching
- Program output recording (optional)
- Streaming to web viewers

**User Actions:**
- Switch between scenes
- Create custom layouts
- Add graphics overlays
- Record program output

## 3. Data Flow Simplified

### Simple Flow Diagram
```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  HDMI    │ --> │ GStreamer│ --> │ MediaMTX │ --> │  Browser │
│  Input   │     │ Pipeline │     │  Server  │     │    UI    │
└──────────┘     └──────┬───┘     └──────────┘     └──────────┘
                        │
                        ↓
                 ┌──────────┐
                 │   File   │
                 │  Storage │
                 └──────────┘
```

### Recording Flow
1. **Capture**: HDMI signal captured by LT6911UXE bridge
2. **Process**: GStreamer converts format and encodes video
3. **Store**: Video saved to MP4 file
4. **(Optional)** Stream: Video sent to MediaMTX for monitoring

### Preview Flow
1. **Capture**: HDMI signal captured by LT6911UXE bridge
2. **Process**: GStreamer converts format and encodes video
3. **Stream**: Video sent to MediaMTX
4. **Deliver**: MediaMTX serves HLS/WebRTC to browsers

### Mixer Flow
1. **Capture**: Multiple HDMI signals + file sources
2. **Composite**: GStreamer compositor combines sources per scene
3. **Encode**: Combined video encoded to H.264
4. **Output**: 
   - Stream to MediaMTX for viewers
   - (Optional) Save to file

## 4. Component Roles

### Hardware Layer
```
┌─────────────────────────────────────────────────────────┐
│                    Mekotronics R58                      │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────┐  │
│  │ 4x HDMI-IN │  │  RK3588    │  │  Hardware Video │  │
│  │ LT6911UXE  │  │   SoC      │  │    Encoders     │  │
│  └────────────┘  └────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```
- **4x HDMI Input**: Capture up to 4 HDMI sources
- **RK3588 SoC**: Powerful ARM processor with video acceleration
- **Hardware Encoders**: H.264/H.265 encoding with low CPU usage

### Software Layer
```
┌─────────────────────────────────────────────────────────┐
│                   Python Application                     │
│  ┌──────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │ FastAPI  │  │ GStreamer │  │  Managers:         │  │
│  │ Web API  │  │ Pipelines │  │  - Recorder        │  │
│  │          │  │           │  │  - Preview         │  │
│  │          │  │           │  │  - Mixer           │  │
│  │          │  │           │  │  - Scene           │  │
│  │          │  │           │  │  - Graphics        │  │
│  └──────────┘  └───────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```
- **FastAPI**: REST API for control and status
- **GStreamer**: Media processing framework
- **Managers**: Python classes that manage pipelines and state

### Streaming Layer
```
┌─────────────────────────────────────────────────────────┐
│                       MediaMTX                          │
│  Input: RTMP (port 1935) from GStreamer                │
│  Output:                                                │
│    - RTSP (port 8554)  → Professional tools            │
│    - HLS  (port 8888)  → Web browsers                  │
│    - WebRTC (port 8889) → Low-latency web              │
│    - SRT  (port 8890)  → Remote streaming              │
└─────────────────────────────────────────────────────────┘
```
- **Input**: Receives RTMP streams from GStreamer
- **Output**: Converts to multiple formats for different use cases

### User Interface Layer
```
┌─────────────────────────────────────────────────────────┐
│                      Web Browser                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Multiview   │  │   Switcher   │  │   Graphics   │ │
│  │   Display    │  │   Controls   │  │    Editor    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│  ┌──────────────┐  ┌──────────────┐                   │
│  │   Control    │  │     Scene    │                   │
│  │    Panel     │  │    Editor    │                   │
│  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
```
- **Multiview**: View all cameras at once
- **Switcher**: Control mixer scenes
- **Graphics**: Create overlays and lower-thirds
- **Control**: Unified control panel
- **Scene Editor**: Visual scene creation

## 5. Key Features Summary

### Recording
✓ Record 4 cameras simultaneously  
✓ Hardware-accelerated encoding  
✓ Automatic file naming with timestamps  
✓ H.264 and H.265 codec support  
✓ Optional streaming while recording  

### Preview
✓ Live multiview of all cameras  
✓ Low-latency streaming (~700ms HLS, ~100ms WebRTC)  
✓ Automatic signal detection  
✓ Resolution change handling  
✓ No recording overhead  

### Mixer
✓ Scene-based video mixing  
✓ Mix cameras, videos, images, graphics  
✓ Real-time scene switching  
✓ Custom scene creation  
✓ Graphics overlays (lower-thirds, timers, etc.)  
✓ Optional program recording  

### Graphics
✓ Lower-third overlays  
✓ Presentation slides (Reveal.js)  
✓ Timers and scoreboards  
✓ Stinger transitions  
✓ Template system  

## 6. Typical Use Cases

### Use Case 1: Multi-Camera Event Recording
**Goal**: Record a multi-camera event with ISO recordings

**Workflow**:
1. Connect 4 HDMI cameras to R58
2. Start recording on all 4 cameras
3. Let event run
4. Stop recording when done
5. Download all 4 recordings

**Result**: 4 separate MP4 files (one per camera)

---

### Use Case 2: Live Switched Production
**Goal**: Create a live-switched program output with graphics

**Workflow**:
1. Connect cameras and start preview on all
2. Start mixer with default scene
3. Switch between scenes during event:
   - Quad view for general shots
   - 2-up for interviews
   - Fullscreen for presentations
4. Add lower-thirds when speakers are introduced
5. (Optional) Record program output

**Result**: Live stream with professional switching + optional recording

---

### Use Case 3: Remote Monitoring
**Goal**: Monitor cameras remotely via web

**Workflow**:
1. Start preview on all cameras
2. Access web UI from remote location
3. View multiview display
4. Monitor HDMI signal status
5. No recording needed

**Result**: Low-latency remote monitoring

---

### Use Case 4: Presentation Recording
**Goal**: Record a presentation with camera and slides

**Workflow**:
1. Camera 1: Presenter camera
2. Camera 2: Audience camera
3. Computer: Slides via HDMI
4. Use mixer with "presentation_focus" scene
5. Add lower-third with presenter name
6. Record program output

**Result**: Professional presentation recording with slides and graphics

## 7. System States

### Camera States
- **idle**: Camera available but not in use
- **recording**: Camera recording to file
- **preview**: Camera streaming (no recording)
- **error**: Pipeline error occurred
- **no_signal**: No HDMI signal detected

### Mixer States
- **NULL**: Mixer not running
- **PLAYING**: Mixer active and mixing
- **UNHEALTHY**: Pipeline issues detected (auto-recovery)

## 8. Configuration Overview

### Simple Configuration (config.yml)
```yaml
# Platform (auto-detected)
platform: r58

# Camera configuration
cameras:
  cam0:
    device: /dev/video60
    resolution: 1920x1080
    bitrate: 5000
    codec: h264

# Mixer configuration
mixer:
  enabled: true
  output_resolution: 1920x1080
  output_bitrate: 8000
  mediamtx_enabled: true

# Streaming server
mediamtx:
  enabled: true
```

**Key Settings:**
- **resolution**: Output video resolution
- **bitrate**: Video quality (kbps)
- **codec**: h264 or h265
- **mediamtx_enabled**: Enable streaming

## 9. Network Architecture

### Local Network
```
┌──────────────────────────────────────────────┐
│               Local Network                  │
│                                              │
│  R58 Device (192.168.1.25)                  │
│    ├─ Port 8000: Web UI & API              │
│    ├─ Port 8888: HLS Streams               │
│    ├─ Port 8889: WebRTC Streams            │
│    └─ Port 8554: RTSP Streams              │
│                                              │
│  Browser (192.168.1.x)                      │
│    └─ Access: http://192.168.1.25:8000     │
└──────────────────────────────────────────────┘
```

### Remote Access (via Cloudflare Tunnel)
```
┌──────────────────────────────────────────────┐
│              Internet Access                 │
│                                              │
│  Remote Browser                             │
│    └─ Access: https://recorder.itagenten.no│
│                     ↓                        │
│              Cloudflare Tunnel              │
│                     ↓                        │
│              R58 Device                     │
└──────────────────────────────────────────────┘
```

## 10. Performance Summary

### Capacity
- **Simultaneous Recordings**: Up to 4 cameras
- **Preview Streams**: Up to 4 cameras
- **Mixer Inputs**: Up to 4 sources
- **Total Throughput**: ~30-40 MB/s

### Latency
- **Recording**: Near-zero (direct to file)
- **Preview (HLS)**: ~700ms
- **Preview (WebRTC)**: ~100ms
- **Mixer Output**: ~200ms

### Resource Usage
- **CPU**: 20-30% (4 cameras + mixer with hardware encoding)
- **Memory**: ~500-600 MB
- **Storage**: ~6-8 MB/s per recording
- **Network**: ~5-8 Mbps per stream

## 11. Common Operations

### Start Recording All Cameras
```
Web UI → Control Panel → Click "Record All"
  → POST /record/start-all
    → 4 GStreamer pipelines start
      → 4 MP4 files created
```

### Switch Mixer Scene
```
Web UI → Switcher → Click Scene Button
  → POST /api/mixer/set_scene
    → Mixer updates compositor layout
      → Scene changes instantly
```

### Add Lower-Third
```
Web UI → Graphics → Create Lower-Third
  → POST /api/graphics/lower_third
    → Graphics pipeline created
      → Add to mixer scene
        → Lower-third appears
```

### View Multiview
```
Web UI → Switcher Page
  → GET /api/preview/status (check status)
    → For each camera:
      → Load HLS stream from /hls/{cam_id}_preview/index.m3u8
        → Display in video player
```

## 12. Troubleshooting Quick Reference

### No Video in Preview
**Check:**
1. Is preview started? (`POST /preview/start-all`)
2. Is HDMI cable connected?
3. Is MediaMTX running? (`systemctl status mediamtx`)

### Recording Not Starting
**Check:**
1. Is camera available? (not in preview mode)
2. Is storage available? (`df -h`)
3. Check device: `ls -la /dev/video*`

### Mixer Scene Not Switching
**Check:**
1. Is mixer running? (`GET /api/mixer/status`)
2. Is scene valid? (`GET /api/scenes/{id}`)
3. Are sources available?

### Poor Video Quality
**Adjust:**
1. Increase bitrate in `config.yml`
2. Check HDMI input resolution
3. Use hardware encoder (mpph264enc) if available

## 13. Architecture Principles

### Isolation
- **Separate Pipelines**: Recording, preview, and mixer are independent
- **No Cross-Dependencies**: Failure in one doesn't affect others
- **Exclusive Access**: One pipeline per device at a time

### Reliability
- **Automatic Recovery**: Pipelines auto-restart on errors
- **Signal Detection**: Monitors HDMI signal and adapts
- **Health Monitoring**: Continuous health checks
- **Graceful Degradation**: Falls back to test patterns on signal loss

### Performance
- **Hardware Acceleration**: Uses RK3588 video encoders
- **Efficient Buffering**: Minimal buffers for low latency
- **Parallel Processing**: Multiple streams processed simultaneously

### Flexibility
- **Scene System**: Easy to add new layouts
- **Multiple Codecs**: H.264 and H.265 support
- **Configurable**: YAML-based configuration
- **Extensible**: Plugin-style graphics and sources

## Conclusion

The R58 Video Recorder & Mixer is a professional video production system that provides:

1. **Multi-Camera Recording**: Capture up to 4 HDMI sources
2. **Live Preview**: Monitor all cameras with low latency
3. **Scene-Based Mixing**: Professional video switching
4. **Graphics Overlays**: Lower-thirds, timers, presentations
5. **Web Interface**: Control everything from a browser
6. **Remote Access**: Accessible via Cloudflare Tunnel

**Key Benefit**: All-in-one solution for live video production, recording, and streaming on a single embedded device.

For technical details, see `MEDIA_FLOW_DETAILED.md`.
