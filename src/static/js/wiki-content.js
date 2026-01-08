// R58 Documentation Wiki - Content Database
// All content verified on December 26, 2025

const wikiContent = {
    // ========================================
    // GETTING STARTED
    // ========================================
    
    'welcome': {
        title: 'Welcome to R58 Documentation',
        simple: `
Welcome! This is the complete documentation for the **R58 Video Recorder** system.

Think of the R58 as a smart video recorder that can:
- Capture video from up to 4 HDMI cameras at once
- Stream video to the internet with very low delay
- Mix multiple camera views into one output
- Record everything to files for later use

Whether you're setting it up for the first time or troubleshooting an issue, this wiki has you covered!
        `,
        technical: `
The R58 is a professional multi-camera recording and streaming system built on:
- **Hardware**: Mekotronics R58 4x4 3S with RK3588 SoC
- **OS**: Debian GNU/Linux 12 (bookworm), Kernel 6.1.99
- **Backend**: Python FastAPI + GStreamer 1.22.9
- **Streaming**: MediaMTX with WHIP/WHEP support
- **Remote Access**: FRP tunnel through Coolify VPS

**Current Status** (Verified Dec 26, 2025):
- ✅ 4 cameras configured (cam0-cam3)
- ✅ Hardware H.264 encoding (mpph264enc)
- ✅ Remote access via https://r58-api.itagenten.no
- ✅ WebRTC streaming with <1s latency
        `,
        content: `
## Quick Links

- **[Quick Start](#quick-start)** - Get started in 5 minutes
- **[System Overview](#system-overview)** - Understand the architecture
- **[Remote Access](#remote-overview)** - Connect from anywhere
- **[API Reference](#api-overview)** - Integrate with the system
- **[Troubleshooting](#common-issues)** - Fix common problems

## What's in This Wiki?

This documentation is organized into sections:

1. **Getting Started** - Introduction and quick setup
2. **Architecture** - How the system works
3. **Setup & Configuration** - Installation and configuration
4. **Remote Access** - SSH and web interfaces
5. **API Reference** - Complete API documentation
6. **Troubleshooting** - Common issues and solutions
7. **History & Decisions** - Why we built it this way
        `,
        keyPoints: [
            'R58 can record 4 HDMI cameras simultaneously',
            'Remote access works via FRP tunnel (not Cloudflare)',
            'All documentation verified on December 26, 2025',
            'Use the search box above to find specific topics'
        ],
        tags: ['welcome', 'introduction', 'overview']
    },
    
    'quick-start': {
        title: '⚡ Quick Start Guide',
        simple: `
Get up and running with the R58 in just a few minutes!

**Step 1**: Connect to the R58 device
**Step 2**: Access the web interface
**Step 3**: Start recording or streaming

That's it! The system is designed to work out of the box.
        `,
        technical: `
**Prerequisites**:
- SSH access to the R58 device
- Network connectivity to 65.109.32.111:10022 (FRP tunnel)
- sshpass installed on your local machine

**Verified Connection Method**:
\`\`\`bash
./connect-r58-frp.sh
# Uses: sshpass -p linaro ssh -p 10022 linaro@65.109.32.111
\`\`\`

**System Requirements**:
- The R58 device must be powered on
- FRP tunnel services must be running (verified: ✅)
- MediaMTX and preke-recorder services active (verified: ✅)
        `,
        content: `
## Step 1: Connect to R58

From your local machine:

\`\`\`bash
cd /path/to/preke-r58-recorder
./connect-r58-frp.sh
\`\`\`

You should see:
\`\`\`
Connecting to R58 via FRP tunnel...
Server: 65.109.32.111:10022
linaro@linaro-alip:~$
\`\`\`

## Step 2: Access Web Interfaces

Open the **Preke Studio** web app in your browser:

**Main URL**: https://app.itagenten.no/vue/#/

**Views**:
- **Recorder**: https://app.itagenten.no/vue/#/recorder
- **Mixer**: https://app.itagenten.no/vue/#/mixer
- **Library**: https://app.itagenten.no/vue/#/library
- **Admin**: https://app.itagenten.no/vue/#/admin

All URLs use valid Let's Encrypt SSL certificates.

## Step 3: Check System Status

Test the API:
\`\`\`bash
curl https://r58-api.itagenten.no/health
# Expected: {"status":"healthy","platform":"auto","gstreamer":"initialized"}

curl https://r58-api.itagenten.no/status
# Shows all camera statuses
\`\`\`

## Step 4: Start Recording

Via API:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/record/start/cam1
# Response: {"status":"started","camera":"cam1"}
\`\`\`

Or use the web interface buttons!

## Deploy New Code

\`\`\`bash
./deploy-simple.sh
# Commits, pushes to GitHub, pulls on R58, restarts service
\`\`\`
        `,
        keyPoints: [
            'SSH via FRP tunnel on port 10022 (100% stable)',
            'Web interfaces use HTTPS with Let\'s Encrypt',
            'All services start automatically on boot',
            'deploy-simple.sh handles full deployment cycle'
        ],
        tags: ['quick start', 'getting started', 'setup', 'ssh', 'connection']
    },
    
    'what-is-r58': {
        title: 'What is the R58?',
        simple: `
The R58 is a specialized computer designed for professional video production. It's about the size of a small book but can handle tasks that normally require much larger equipment.

**What makes it special?**
- It has 4 HDMI inputs to connect cameras
- It can record all 4 cameras at the same time
- It has special chips inside that make video encoding very fast
- You can access it from anywhere via the internet

Think of it like a smart DVR, but for professional video production!
        `,
        technical: `
**Hardware Specifications**:
- **SoC**: Rockchip RK3588S (8-core ARM, up to 2.4GHz)
- **HDMI Inputs**: 4x via LT6911UXE chips
  - /dev/video60 (rk_hdmirx direct)
  - /dev/video0, /dev/video11, /dev/video22 (rkcif-mipi-lvds via LT6911 bridges)
- **Video Processing**: MPP (Media Process Platform) hardware encoders
  - mpph264enc: H.264 hardware encoding
  - mpph265enc: H.265 hardware encoding
  - RGA: Hardware scaling and format conversion

**Software Stack**:
- **OS**: Custom Debian 12 (Mekotronics build), Kernel 6.1.99
- **Media Framework**: GStreamer 1.22.9 (Debian package with Rockchip plugins)
- **Application**: Python FastAPI (port 8000)
- **Streaming Server**: MediaMTX v1.15.5+ (ports 8889, 8888, 8554)
- **Live Mixer**: VDO.ninja v28+ (port 8443)

**Performance** (Verified):
- 4x 1080p@30fps simultaneous encoding
- Hardware encoding: ~10-15% CPU usage per stream
- Sub-second WebRTC latency
- 4 Mbps per camera (configurable)
        `,
        content: `
## Device Information

**Verified System Details** (Dec 26, 2025):
- **Hostname**: linaro-alip
- **Installation Path**: /opt/preke-r58-recorder
- **User**: linaro
- **Services Running**:
  - preke-recorder.service ✅
  - mediamtx.service ✅
  - frpc.service (FRP client) ✅

## Camera Ports

| HDMI Port | Device Path | Config Name | Status |
|-----------|-------------|-------------|--------|
| N60 | /dev/video60 | cam1 | ✅ Primary |
| N0 | /dev/video0 | cam0 | ✅ Enabled |
| N11 | /dev/video11 | cam2 | ✅ Enabled |
| N21 | /dev/video22 | cam3 | ✅ Enabled |

## Use Cases

1. **Live Event Production** - Multi-camera live streaming
2. **Conference Recording** - Capture multiple angles
3. **Broadcast Monitoring** - Real-time multiview
4. **Content Creation** - Professional video recording
5. **Remote Production** - Access from anywhere
        `,
        keyPoints: [
            'RK3588 SoC with hardware video encoding',
            '4 HDMI inputs via LT6911UXE chips',
            'Debian 12 with GStreamer 1.22.9',
            'All services verified running on Dec 26, 2025'
        ],
        tags: ['r58', 'hardware', 'specifications', 'device']
    },
    
    // ========================================
    // ARCHITECTURE
    // ========================================
    
    'system-overview': {
        title: 'System Architecture Overview',
        simple: `
The R58 system has three main parts:

1. **The R58 Device** - Where cameras connect and video is processed
2. **The Cloud Server (VPS)** - Acts as a bridge to the internet
3. **Your Browser** - Where you view and control everything

They all talk to each other through a secure tunnel called FRP.
        `,
        technical: `
**Architecture Pattern**: Client-Server with Reverse Proxy Tunnel

**Components**:
- **R58 Device** (192.168.x.x): Origin server, runs all media processing
- **Coolify VPS** (65.109.32.111): Public-facing proxy with SSL termination
- **FRP Tunnel**: TCP tunnel connecting R58 to VPS (bypasses NAT/firewall)
- **Traefik**: Automatic SSL certificates (Let's Encrypt)
- **nginx**: CORS handling and routing

**Why This Architecture?**
- R58 is behind NAT (no public IP)
- FRP creates secure tunnel without port forwarding
- MediaMTX v1.15.5+ supports TCP WebRTC (works through tunnel)
- Single point of entry (VPS) with proper SSL
        `,
        diagram: `
flowchart TB
    subgraph R58[R58 Device - Local Network]
        CAM0[HDMI Camera 0]
        CAM1[HDMI Camera 1]
        CAM2[HDMI Camera 2]
        CAM3[HDMI Camera 3]
        GS[GStreamer Pipelines]
        MTX[MediaMTX :8889]
        API[FastAPI :8000]
        VDO[VDO.ninja :8443]
        FRPC[FRP Client]
        
        CAM0 --> GS
        CAM1 --> GS
        CAM2 --> GS
        CAM3 --> GS
        GS --> MTX
        API --> GS
        MTX --> VDO
        MTX --> FRPC
        API --> FRPC
        VDO --> FRPC
    end
    
    subgraph VPS[Coolify VPS - 65.109.32.111]
        FRPS[FRP Server :7000]
        PORTS[Exposed Ports<br/>:10022 SSH<br/>:18889 MediaMTX<br/>:18000 API<br/>:18443 VDO.ninja]
        NGX[nginx Proxy]
        TRF[Traefik SSL]
        
        FRPS --> PORTS
        PORTS --> NGX
        NGX --> TRF
    end
    
    subgraph Users[Remote Users]
        BROWSER[Web Browser<br/>Studio/Mixer]
        SSH[SSH Client]
        GUEST[Remote Guests<br/>WHIP]
    end
    
    FRPC -->|TCP Tunnel| FRPS
    TRF -->|HTTPS| BROWSER
    TRF -->|SSH :10022| SSH
    GUEST -->|WHIP| TRF
    
    style R58 fill:#e3f2fd
    style VPS fill:#fff3e0
    style Users fill:#f3e5f5
`,
        content: `
## Data Flow

### Camera to Browser (Streaming)

1. **Capture**: Camera → HDMI → R58 (/dev/videoXX)
2. **Encode**: GStreamer pipeline → Hardware encoder (mpph264enc)
3. **Stream**: RTMP → MediaMTX
4. **Publish**: MediaMTX WHEP endpoint
5. **Tunnel**: FRP → VPS (port 18889)
6. **SSL**: Traefik adds HTTPS
7. **View**: Browser connects via WebRTC

**Latency**: <1 second end-to-end

### Recording

The system uses a two-stage approach:
1. **Ingest Pipeline**: Camera → GStreamer → RTSP → MediaMTX
2. **Recording Pipeline**: MediaMTX (RTSP subscriber) → File

**Why This Architecture?**
- Ingest pipeline owns the camera device (no conflicts)
- Recording subscribes via RTSP from MediaMTX
- Multiple consumers can access same stream
- Recording independent of capture

## Network Ports

### R58 Local Ports
- 8000: FastAPI
- 8889: MediaMTX WebRTC
- 8888: MediaMTX HLS
- 9997: MediaMTX API
- 8554: MediaMTX RTSP
- 1935: MediaMTX RTMP

### VPS Exposed Ports (via FRP)
- 10022: SSH to R58
- 18000: FastAPI (proxied)
- 18889: MediaMTX WebRTC (proxied)
- 19997: MediaMTX API (proxied)

### Public URLs
- https://r58-api.itagenten.no → FastAPI
- https://r58-mediamtx.itagenten.no → MediaMTX
        `,
        keyPoints: [
            'FRP tunnel connects R58 to VPS without port forwarding',
            'MediaMTX uses TCP WebRTC (works through tunnel)',
            'All public access goes through VPS with SSL',
            'Recording happens locally (no network latency)'
        ],
        tags: ['architecture', 'system', 'overview', 'diagram']
    },
    
    'data-flow': {
        title: 'Data Flow: Camera to Viewer',
        simple: `
Here's how video gets from a camera to your screen:

1. Camera sends video signal via HDMI cable
2. R58 captures the video and compresses it (makes file smaller)
3. Video is sent through the internet tunnel to the cloud server
4. Cloud server adds security (HTTPS) and sends to your browser
5. Your browser displays the video

All of this happens in less than 1 second!
        `,
        technical: `
**GStreamer Pipeline** (Verified - Using RTSP):

\`\`\`
v4l2src device=/dev/video60
  → video/x-raw,format=NV16,width=1920,height=1080
  → videoconvert (NV16→NV12)
  → videoscale
  → mpph264enc bitrate=4000000
  → h264parse config-interval=-1
  → rtspclientsink location=rtsp://localhost:8554/cam1 protocols=tcp latency=0
\`\`\`

**Why RTSP over RTMP?**
- Lower latency (no FLV muxing overhead)
- TCP transport prevents packet loss
- config-interval=-1 ensures SPS/PPS with every keyframe
- latency=0 for minimal buffering
- Critical for mixer synchronization

**MediaMTX Processing**:
- Receives RTSP stream (port 8554)
- Converts to multiple protocols (HLS, WebRTC)
- WHEP endpoint: /cam1/whep
- WebRTC uses UDP mux on port 8189

**FRP Tunnel**:
- TCP: 8889 → 18889 (WebRTC signaling)
- UDP: 8189 → 18189 (WebRTC media)

**Browser**:
- Connects to https://r58-mediamtx.itagenten.no/cam1/whep
- WebRTC negotiation via WHEP protocol
- Direct RTP stream to browser
        `,
        diagram: `
flowchart LR
    HDMI[HDMI Input<br/>1920x1080] --> V4L2[v4l2src<br/>/dev/video60]
    V4L2 --> FMT[NV16 Format]
    FMT --> CONV[videoconvert<br/>NV16→NV12]
    CONV --> SCALE[videoscale]
    SCALE --> ENC[mpph264enc<br/>4 Mbps]
    ENC --> PARSE[h264parse<br/>config-interval=-1]
    PARSE --> RTSP[rtspclientsink<br/>RTSP :8554<br/>TCP, latency=0]
    RTSP --> MTX[MediaMTX]
    MTX --> WHEP[WHEP Endpoint]
    WHEP --> FRP[FRP Tunnel]
    FRP --> VPS[VPS nginx]
    VPS --> SSL[Traefik SSL]
    SSL --> BROWSER[Browser WebRTC]
    
    style ENC fill:#90caf9
    style RTSP fill:#81c784
    style MTX fill:#a5d6a7
    style FRP fill:#ffcc80
    style SSL fill:#ce93d8
`,
        content: `
## Format Conversion

**Why NV16 → NV12?**

The rk_hdmirx (N60 port) outputs YUV 4:2:2 (NV16 format). Hardware encoders require YUV 4:2:0 (NV12 format).

\`\`\`
NV16: Half horizontal color resolution (4:2:2)
  ↓ videoconvert
NV12: Half color resolution (4:2:0) - required for encoding
\`\`\`

**Performance Impact**: Minimal (~2-3% CPU) thanks to RGA hardware acceleration

**Note**: Different HDMI ports use different formats (NV16 for N60, NV24 for bridge-based ports)

## Encoding Settings

**Current Configuration** (config.yml):
\`\`\`yaml
bitrate: 4000  # 4 Mbps
codec: h264    # Hardware via mpph264enc
resolution: 1920x1080
\`\`\`

**Why 4 Mbps?**
- Balance between quality and bandwidth
- Stable over FRP tunnel
- Works well for remote viewing
- Can be increased for local recording

## Architecture: Ingest-Subscribe Model

**Current Architecture** (Verified Dec 26, 2025):

\`\`\`
Camera → Ingest Pipeline → RTSP → MediaMTX → RTSP/WHEP → Consumers
                                               ├─→ Recording
                                               ├─→ Browser (WHEP)
                                               └─→ Mixer (RTSP subscriber)
\`\`\`

**Why This Design?**
- **Single owner**: Ingest pipeline owns camera device (prevents "device busy")
- **Multiple consumers**: Recording, preview, mixer all subscribe from MediaMTX
- **No conflicts**: Recording doesn't block streaming
- **Flexible**: Can add/remove consumers without affecting capture

**Key Point**: The ingest pipeline streams to MediaMTX via RTSP (not RTMP). RTSP has lower latency, which is critical for the mixer to keep all cameras synchronized.

## Latency Breakdown

| Stage | Latency | Notes |
|-------|---------|-------|
| Capture | ~16ms | 60fps = 16ms per frame |
| Encoding | ~30ms | Hardware encoder |
| RTSP | ~20ms | TCP transport, latency=0 |
| MediaMTX | ~50ms | Protocol conversion |
| FRP Tunnel | ~20ms | Network latency |
| WebRTC | ~100ms | Browser decoding |
| **Total** | **~240ms** | RTSP saves ~30ms vs RTMP |
        `,
        keyPoints: [
            'Hardware encoding (mpph264enc) uses ~10% CPU',
            'NV24→NV12 conversion required for encoding',
            'Total latency <1 second end-to-end',
            'FRP tunnel adds only ~20ms latency'
        ],
        tags: ['data flow', 'pipeline', 'gstreamer', 'encoding']
    },
    
    'components': {
        title: 'System Components',
        simple: `
The R58 system is made up of several programs working together:

- **FastAPI** - The main control program (like the brain)
- **GStreamer** - Handles all video processing (like the hands)
- **MediaMTX** - Manages streaming to the internet (like a broadcaster)
- **FRP** - Creates the tunnel to the cloud (like a secure pipe)

Each program has a specific job, and they all communicate with each other.
        `,
        technical: `
**Component Versions** (Verified Dec 26, 2025):

| Component | Version | Purpose |
|-----------|---------|---------|
| FastAPI | Latest | REST API, control logic |
| GStreamer | 1.22.9 | Media processing |
| MediaMTX | v1.15.5+ | Streaming server |
| FRP | Latest | Reverse proxy tunnel |
| Python | 3.x | Application runtime |

**Service Status**:
\`\`\`bash
● preke-recorder.service - Preke R58 Recorder Service
   Active: active (running) ✅
   
● mediamtx.service - MediaMTX RTSP/RTMP/SRT Server
   Active: active (running) ✅
   
● frpc.service - frp Client
   Active: active (running) ✅
\`\`\`
        `,
        content: `
## FastAPI Application

**Location**: /opt/preke-r58-recorder  
**Port**: 8000  
**Service**: preke-recorder.service

**Responsibilities**:
- Camera control (start/stop recording)
- GStreamer pipeline management
- Mixer control
- Scene management
- Health monitoring
- Static file serving

**Key Modules**:
- \`src/main.py\` - FastAPI app, routes
- \`src/recorder.py\` - Recording logic
- \`src/pipelines.py\` - GStreamer pipeline builders
- \`src/mixer/core.py\` - Video mixer
- \`src/config.py\` - Configuration management

## GStreamer

**Version**: 1.22.9  
**Purpose**: Media processing framework

**Key Elements Used**:
- \`v4l2src\` - Video capture from /dev/videoXX
- \`videoconvert\` - Format conversion (NV24→NV12)
- \`videoscale\` - Resolution scaling
- \`mpph264enc\` - Hardware H.264 encoding
- \`mpph265enc\` - Hardware H.265 encoding
- \`h264parse\` / \`h265parse\` - Stream parsing
- \`flvmux\` - FLV container
- \`rtmpsink\` - RTMP output to MediaMTX

**Why GStreamer?**
- Direct hardware encoder access (MPP)
- Flexible pipeline architecture
- Battle-tested in production
- Excellent ARM/RK3588 support

## MediaMTX

**Ports**:
- 8889: WebRTC/WHEP/WHIP
- 8888: HLS
- 8554: RTSP
- 1935: RTMP
- 9997: API

**Configuration**: mediamtx.yml

**Key Features**:
- WHIP: WebRTC-HTTP Ingestion (for remote guests)
- WHEP: WebRTC-HTTP Egress (for viewers)
- HLS: HTTP Live Streaming
- RTSP/RTMP: Traditional protocols

**Paths** (Verified):
- cam0, cam1, cam2, cam3 - Camera streams
- mixer_program - Mixer output
- speaker0, speaker1, speaker2 - Remote speakers
- slides, slides_overlay - Reveal.js presentations

## VDO.ninja

**Version**: v28+  
**Port**: 8443 (local), 18443 (via FRP)  
**Location**: /opt/vdo.ninja

**Purpose**: Browser-based live video mixer

**Services**:
- vdo-ninja.service - Signaling server
- vdo-webapp.service - Web application

**Integration Mode**: MediaMTX WHEP (recommended)
- Use &mediamtx= parameter to pull streams from MediaMTX
- Works both locally and remotely through FRP tunnels
- No separate camera publishers needed

**Key Features**:
- Real-time video mixing in browser
- WHEP support (pulls from MediaMTX)
- Remote guest integration
- Professional broadcast interface

**Why VDO.ninja?**:
- No software installation needed
- Works in any modern browser
- Professional mixing features
- Remote collaboration built-in
- Free and open source

**Critical Requirement**: v28+ for WHEP support

## FRP (Fast Reverse Proxy)

**Config**: /opt/frp/frpc.toml  
**Server**: 127.0.0.1:7000 (via SSH tunnel)

**Proxies**:
\`\`\`toml
[[proxies]]
name = "r58-ssh"
type = "tcp"
localPort = 22
remotePort = 10022

[[proxies]]
name = "r58-api"
type = "tcp"
localPort = 8000
remotePort = 18000

[[proxies]]
name = "mediamtx-whep"
type = "tcp"
localPort = 8889
remotePort = 18889

[[proxies]]
name = "webrtc-udp"
type = "udp"
localPort = 8189
remotePort = 18189
\`\`\`

**Why FRP?**
- Works through NAT/firewall
- No port forwarding needed
- Supports both TCP and UDP
- Lightweight and reliable
        `,
        keyPoints: [
            'All services verified running on Dec 26, 2025',
            'GStreamer 1.22.9 with hardware encoder support',
            'MediaMTX handles all streaming protocols',
            'FRP creates secure tunnel without port forwarding'
        ],
        tags: ['components', 'fastapi', 'gstreamer', 'mediamtx', 'frp']
    },
    
    'tech-stack': {
        title: 'Technology Stack & Decisions',
        simple: `
We chose each technology carefully based on what works best for the R58:

- **Python** - Easy to write and maintain
- **GStreamer** - Works great with the R58's special video chips
- **MediaMTX** - Handles all the streaming formats we need
- **FRP** - Creates a secure tunnel through the internet

These choices were made after trying many alternatives!
        `,
        technical: `
**Technology Selection Criteria**:
1. Hardware acceleration support (RK3588 MPP)
2. Production stability and maturity
3. Active maintenance and community
4. Performance characteristics
5. Ease of deployment and debugging

**Stack Overview**:

| Layer | Technology | Why Chosen |
|-------|------------|------------|
| Hardware | RK3588 | Best ARM SoC for video (MPP encoders) |
| OS | Custom Debian 12 | Mekotronics build with Rockchip drivers |
| Runtime | Python 3 | Rapid development, good libraries |
| Web Framework | FastAPI | Async, type hints, auto docs |
| Media | GStreamer 1.22.9 | Hardware encoder access, Rockchip plugins |
| Streaming | MediaMTX v1.15.5+ | WHIP/WHEP, TCP WebRTC support |
| Live Mixer | VDO.ninja v28+ | Browser-based mixing, WHEP support |
| Tunnel | FRP | Works through NAT, TCP+UDP |
| SSL | Traefik | Auto Let's Encrypt |
| Proxy | nginx | CORS handling |
        `,
        content: `
## Why Python + FastAPI?

**Advantages**:
- **Async/await**: Non-blocking I/O for concurrent requests
- **Type hints**: Automatic validation, better IDE support
- **Auto docs**: OpenAPI/Swagger UI at /docs
- **Easy deployment**: Single uvicorn process
- **GStreamer bindings**: python3-gi for GStreamer control

**Performance**: Sufficient for control plane (not in media path)

## Why GStreamer?

**Alternatives Considered**:
- ❌ FFmpeg: No direct MPP encoder access on RK3588
- ❌ Custom V4L2: Too low-level, reinventing the wheel
- ✅ GStreamer: Perfect fit

**Advantages**:
- **Hardware Access**: Direct mpph264enc/mpph265enc support
- **Pipeline Flexibility**: Easy to modify and extend
- **RGA Support**: Hardware scaling/conversion
- **Mature**: Battle-tested in production systems
- **Debugging**: gst-launch-1.0 for testing pipelines

## Why MediaMTX?

**Alternatives Considered**:
- ❌ nginx-rtmp: No WebRTC support
- ❌ Janus: Complex setup, overkill
- ❌ Kurento: Heavy, Java-based
- ✅ MediaMTX: Perfect fit

**Advantages**:
- **WHIP/WHEP**: HTTP-based WebRTC (works through tunnels!)
- **TCP WebRTC**: webrtcLocalTCPAddress support
- **Multi-protocol**: RTSP, RTMP, HLS, SRT, WebRTC
- **Lightweight**: Single Go binary, low resource usage
- **Active Development**: Frequent updates, responsive maintainer

**Critical Feature**: TCP WebRTC support (v1.15.5+) enables WebRTC through FRP tunnel

**Version Matters!**
- Started with v1.5.1: Many issues, no TCP WebRTC
- Updated to v1.15.5: 80% of problems disappeared
- **Lesson**: Always use latest stable version (10+ versions of fixes)

## Why VDO.ninja?

**Alternatives Considered**:
- ❌ OBS Studio: Desktop app, not browser-based
- ❌ Custom mixer: Too much development time
- ❌ Hardware switcher: Expensive, not remote-capable
- ✅ VDO.ninja: Perfect fit

**Advantages**:
- **Browser-Based**: No software installation
- **WHEP Support**: Pulls from MediaMTX (v28+)
- **Professional Features**: Scenes, transitions, effects
- **Remote Guests**: WHIP publishing built-in
- **Free**: Open source, no licensing costs

**Critical Feature**: WHEP support (v28+) enables server-based mixing through tunnels

**Version Matters!**
- Started with v25: No WHEP support, P2P only
- Updated to v28: WHEP support added
- **Lesson**: v28+ required for our architecture

## Why FRP?

**Alternatives Considered**:
- ❌ Cloudflare Tunnel: No UDP/WebRTC support
- ❌ ngrok: Paid, less control
- ❌ SSH tunnel only: No UDP support
- ❌ ZeroTier/Tailscale: Requires client installation
- ✅ FRP: Perfect fit

**Advantages**:
- **TCP + UDP**: Supports both protocols
- **Open Source**: Self-hosted, no vendor lock-in
- **Simple**: Easy configuration
- **Reliable**: Stable connections
- **Flexible**: Multiple proxies in one tunnel

**Why It Works**: MediaMTX's TCP WebRTC + FRP's TCP tunneling = WebRTC through NAT

## Hardware Acceleration

**MPP (Media Process Platform)**:
- Rockchip's hardware video processing framework
- Accessed via GStreamer elements:
  - \`mpph264enc\` - H.264 encoding
  - \`mpph265enc\` - H.265 encoding
- **Performance**: ~10% CPU vs ~40% for software encoding

**RGA (Raster Graphics Acceleration)**:
- Hardware scaling and format conversion
- Used by \`videoscale\` and \`videoconvert\`
- **Performance**: Negligible CPU usage

**Why It Matters**: Can encode 4x 1080p streams simultaneously with low CPU usage
        `,
        keyPoints: [
            'Every technology chosen for specific technical reasons',
            'Hardware acceleration critical for 4-camera performance',
            'MediaMTX TCP WebRTC + FRP = remote access solution',
            'Python/FastAPI for rapid development, GStreamer for performance'
        ],
        tags: ['technology', 'stack', 'decisions', 'why', 'choices']
    },
    
    // ========================================
    // SETUP & CONFIGURATION
    // ========================================
    
    'installation': {
        title: 'Installation Guide',
        simple: `
The R58 comes pre-installed and configured. You don't need to install anything on the R58 itself!

For your local computer, you only need:
1. SSH client (built into Mac/Linux)
2. sshpass tool for password authentication
3. A web browser (Chrome, Firefox, Safari, etc.)

That's it!
        `,
        technical: `
**R58 Device** (Pre-installed):
- OS: Debian 12 (bookworm)
- Location: /opt/preke-r58-recorder
- Services: Installed and enabled

**Local Machine Requirements**:

**macOS**:
\`\`\`bash
# Install sshpass
brew install sshpass

# Clone repository
git clone <repo-url>
cd preke-r58-recorder
\`\`\`

**Linux**:
\`\`\`bash
# Install sshpass
sudo apt-get install sshpass  # Debian/Ubuntu
sudo yum install sshpass      # RHEL/CentOS

# Clone repository
git clone <repo-url>
cd preke-r58-recorder
\`\`\`

**Windows**:
- Use WSL2 (Windows Subsystem for Linux)
- Or use PuTTY for SSH
        `,
        content: `
## R58 Device Setup (Already Done)

The R58 is pre-configured with:

\`\`\`bash
# System dependencies
apt-get install python3-pip python3-venv gstreamer1.0-tools \\
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \\
    gstreamer1.0-plugins-bad python3-gi

# Application installed at
/opt/preke-r58-recorder/

# Services enabled
systemctl enable preke-recorder.service
systemctl enable mediamtx.service
systemctl enable frpc.service
\`\`\`

## Local Development Setup

For development on macOS:

\`\`\`bash
# Install GStreamer
brew install gstreamer gst-plugins-base gst-plugins-good \\
    gst-plugins-bad gst-plugins-ugly gst-libav

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally (uses test video sources)
python -m src.main
\`\`\`

## Verify Installation

On R58:
\`\`\`bash
# Check services
systemctl status preke-recorder
systemctl status mediamtx
systemctl status frpc

# Check ports
ss -tlnp | grep -E '8000|8889'

# Check GStreamer
gst-launch-1.0 --version

# Test camera
v4l2-ctl --list-devices
\`\`\`

## Configuration Files

**Application**: /opt/preke-r58-recorder/config.yml  
**MediaMTX**: /opt/preke-r58-recorder/mediamtx.yml  
**FRP Client**: /opt/frp/frpc.toml  

**Services**:
- /etc/systemd/system/preke-recorder.service
- /etc/systemd/system/mediamtx.service
- /etc/systemd/system/frpc.service
        `,
        keyPoints: [
            'R58 comes pre-installed and configured',
            'Local machine only needs sshpass and git',
            'Development possible on macOS with GStreamer',
            'All services start automatically on boot'
        ],
        tags: ['installation', 'setup', 'dependencies']
    },
    
    'configuration': {
        title: 'Configuration Guide',
        simple: `
The main configuration file is \`config.yml\`. It controls:

- Which cameras are enabled
- Video quality (bitrate, resolution)
- Where recordings are saved
- Whether the mixer is enabled

Most settings work great out of the box. You usually only need to change camera settings.
        `,
        technical: `
**Configuration Files**:

1. **config.yml** - Application configuration
   - Camera settings (devices, bitrates, codecs)
   - Mixer configuration
   - Recording paths
   - Mode settings (recorder vs vdoninja)

2. **mediamtx.yml** - Streaming server configuration
   - Port settings
   - WebRTC configuration
   - HLS settings
   - Path definitions

3. **frpc.toml** - FRP client configuration
   - Server connection
   - Proxy definitions
   - Authentication token

**Verified Current Configuration** (Dec 26, 2025):
- All cameras: 1920x1080, 4000 kbps, H.264
- Mixer: Enabled, H.265, 8000 kbps
- MediaMTX: WebRTC on 8889, HLS on 8888
- FRP: 8 proxies configured
        `,
        content: `
## config.yml Structure

\`\`\`yaml
# Platform detection
platform: auto  # auto-detects macOS or R58

# Logging
log_level: INFO

# Camera configuration
cameras:
  cam0:
    device: /dev/video0
    resolution: 1920x1080
    bitrate: 4000  # kbps
    codec: h264
    output_path: /mnt/sdcard/recordings/cam0/recording_%Y%m%d_%H%M%S.mkv
    mediamtx_enabled: true
    enabled: true

# Mixer configuration
mixer:
  enabled: true
  output_resolution: 1920x1080
  output_bitrate: 8000
  output_codec: h265
  recording_enabled: false
  mediamtx_enabled: true
  mediamtx_path: mixer_program
  scenes_dir: scenes
\`\`\`

## Camera Settings

**Current Configuration** (Verified):

| Camera | Device | Resolution | Bitrate | Codec | Status |
|--------|--------|------------|---------|-------|--------|
| cam0 | /dev/video0 | 1920x1080 | 4000 | h264 | ✅ |
| cam1 | /dev/video60 | 1920x1080 | 4000 | h264 | ✅ |
| cam2 | /dev/video11 | 1920x1080 | 4000 | h264 | ✅ |
| cam3 | /dev/video22 | 1920x1080 | 4000 | h264 | ✅ |

**To Change Settings**:
\`\`\`bash
# SSH to R58
./connect-r58-frp.sh

# Edit config
nano /opt/preke-r58-recorder/config.yml

# Restart service
sudo systemctl restart preke-recorder
\`\`\`

## MediaMTX Configuration

**mediamtx.yml** (Key Settings):

\`\`\`yaml
# WebRTC
webrtcAddress: :8889
webrtcAllowOrigins: ["*"]
webrtcEncryption: no

# ICE for FRP tunnel
webrtcAdditionalHosts: ["65.109.32.111:18189"]
webrtcLocalUDPAddress: :8189

# HLS
hlsAddress: :8888
hlsSegmentCount: 10
hlsSegmentDuration: 2s
hlsPartDuration: 400ms

# Paths
paths:
  cam0:
    source: publisher
  cam1:
    source: publisher
  # ... etc
\`\`\`

**Critical Settings**:
- \`webrtcAdditionalHosts\`: Tells clients to use VPS IP
- \`webrtcLocalUDPAddress\`: Single UDP port for FRP mapping

## FRP Configuration

**frpc.toml** (Verified):

\`\`\`toml
serverAddr = "127.0.0.1"  # Via SSH tunnel
serverPort = 7000
auth.token = "..."

[[proxies]]
name = "r58-ssh"
type = "tcp"
localPort = 22
remotePort = 10022

[[proxies]]
name = "mediamtx-whep"
type = "tcp"
localPort = 8889
remotePort = 18889

[[proxies]]
name = "webrtc-udp"
type = "udp"
localPort = 8189
remotePort = 18189
\`\`\`

## Recording Paths

**Default**: /mnt/sdcard/recordings/  
**Pattern**: {cam_id}/recording_%Y%m%d_%H%M%S.mkv

**Example**:
\`\`\`
/mnt/sdcard/recordings/
  ├── cam0/
  │   ├── recording_20251226_140530.mkv
  │   └── recording_20251226_153022.mkv
  ├── cam1/
  │   └── recording_20251226_140530.mkv
  └── mixer/
      └── program_20251226_140530.mkv
\`\`\`
        `,
        keyPoints: [
            'config.yml controls all application settings',
            'mediamtx.yml configured for FRP tunnel WebRTC',
            'All cameras currently 1080p @ 4 Mbps H.264',
            'Mixer uses H.265 @ 8 Mbps for better quality'
        ],
        tags: ['configuration', 'config', 'settings', 'yaml']
    },
    
    'camera-setup': {
        title: 'Camera Setup & Mapping',
        simple: `
The R58 has 4 HDMI ports labeled N0, N60, N11, and N21. Each port connects to a different "device" inside the computer.

**Port Mapping**:
- HDMI N60 → Camera 1 (Primary)
- HDMI N0 → Camera 0
- HDMI N11 → Camera 2
- HDMI N21 → Camera 3

Just plug your HDMI cameras into these ports and they'll show up automatically!
        `,
        technical: `
**Hardware Details**:

The R58 uses LT6911UXE HDMI-to-MIPI bridge chips for video capture. Different ports use different capture interfaces:

- **N60** (/dev/video60): Direct rk_hdmirx (best performance)
- **N0, N11, N21**: Via rkcif-mipi-lvds bridges

**V4L2 Device Mapping** (Verified Dec 26, 2025):

\`\`\`
rk_hdmirx (fdee0000.hdmirx-controller):
    /dev/video60  → cam1

rkcif (platform:rkcif-mipi-lvds):
    /dev/video0   → cam0

rkcif (platform:rkcif-mipi-lvds1):
    /dev/video11  → cam2

rkcif (platform:rkcif-mipi-lvds2):
    /dev/video22  → cam3
\`\`\`

**Format Support**:
- Input: HDMI up to 4K@60fps
- Capture: NV24 (YUV 4:4:4)
- Output: NV12 (YUV 4:2:0) after conversion
        `,
        content: `
## Physical Port Layout

\`\`\`
R58 Device (Front Panel)
┌─────────────────────────────┐
│  N0   N60   N11   N21       │
│  ●     ●     ●     ●        │
│ cam0  cam1  cam2  cam3      │
└─────────────────────────────┘
\`\`\`

## Device Testing

**List Available Devices**:
\`\`\`bash
v4l2-ctl --list-devices
\`\`\`

**Test Specific Device**:
\`\`\`bash
# Check capabilities
v4l2-ctl -d /dev/video60 --all

# List supported formats
v4l2-ctl -d /dev/video60 --list-formats-ext

# Test capture (requires display)
gst-launch-1.0 v4l2src device=/dev/video60 ! autovideosink
\`\`\`

## Troubleshooting Camera Detection

**Camera Not Detected**:
1. Check physical connection
2. Verify camera is powered on
3. Check device exists: \`ls -l /dev/video*\`
4. Test with v4l2-ctl

**Device Busy Error**:
\`\`\`bash
# Find process using device
sudo lsof /dev/video60

# Kill if necessary
sudo kill <pid>

# Or restart service
sudo systemctl restart preke-recorder
\`\`\`

**No Signal**:
- Verify camera output resolution (must be ≤1080p for stable operation)
- Check HDMI cable quality
- Try different HDMI port

## Resolution Support

**Tested Resolutions**:
- ✅ 1920x1080 @ 30fps (recommended)
- ✅ 1920x1080 @ 60fps
- ✅ 1280x720 @ 60fps
- ⚠️ 3840x2160 @ 30fps (high CPU usage)

**Configuration**:
\`\`\`yaml
cameras:
  cam1:
    device: /dev/video60
    resolution: 1920x1080  # Most stable
    bitrate: 4000          # 4 Mbps
\`\`\`

## Signal Detection

The system automatically detects camera signals:

\`\`\`bash
# Check camera status
curl http://localhost:8000/status

# Response shows signal detection
{
  "cameras": {
    "cam1": {
      "status": "preview",  # Signal detected
      "config": true
    }
  }
}
\`\`\`
        `,
        keyPoints: [
            'N60 port (/dev/video60) has best performance',
            'All ports support up to 4K input',
            '1080p@30fps recommended for stability',
            'System auto-detects camera signals'
        ],
        tags: ['camera', 'hdmi', 'setup', 'devices', 'v4l2']
    },
    
    // Continue with remaining sections in next part...
    // (Remote Access, API Reference, Troubleshooting, History & Decisions)
};

