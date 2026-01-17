// R58 Documentation Wiki - Content Database (Part 4)
// VDO.ninja, Hardware Specs, and Product Overview

// Extend the wikiContent object
Object.assign(wikiContent, {
    // ========================================
    // PRODUCT OVERVIEW (For Clients/Partners)
    // ========================================
    
    'product-overview': {
        title: 'R58 Professional Video System',
        simple: `
The R58 transforms a small, affordable device into a **complete broadcast studio**.

**What you get**:
- Record 4 HDMI cameras simultaneously
- Mix cameras live like a TV studio
- Stream to the internet with sub-second delay
- Control everything from your web browser
- Access from anywhere in the world

**All in a device smaller than a book!**

This replaces equipment that typically costs tens of thousands of dollars and fills entire racks.
        `,
        technical: `
**R58 Professional Multi-Camera System**

A complete video production solution built on the Mekotronics R58 4x4 3S hardware platform, providing:

**Core Capabilities**:
- 4x simultaneous HDMI capture (1080p@60fps each)
- Hardware-accelerated H.264/H.265 encoding (RK3588 MPP)
- Real-time video mixing with scene management
- Multi-protocol streaming (WebRTC, HLS, RTSP, RTMP)
- Remote access via secure FRP tunnel
- Browser-based control interface

**Hardware Platform**:
- Mekotronics R58 4x4 3S (RK3588 SoC)
- 8GB RAM, 8-core ARM CPU
- 4x HDMI inputs via LT6911UXE bridges
- Custom Debian 12 OS from Mekotronics
- Hardware video encoders (MPP)

**Performance**:
- 4x 1080p@30fps encoding: ~20-30% CPU
- Sub-second WebRTC latency
- 24/7 operation capable
- Low power consumption (~20-28W)
        `,
        diagram: `
flowchart TB
    subgraph Input[Video Inputs]
        CAM1[HDMI Camera 1]
        CAM2[HDMI Camera 2]
        CAM3[HDMI Camera 3]
        CAM4[HDMI Camera 4]
    end
    
    subgraph R58[R58 Device - Single Small Box]
        CAPTURE[4x HDMI Capture<br/>LT6911UXE Chips]
        ENCODE[Hardware Encoding<br/>RK3588 MPP]
        MIXER[Live Video Mixer<br/>GStreamer Compositor]
        STREAM[Streaming Server<br/>MediaMTX]
        API[Control API<br/>FastAPI]
    end
    
    subgraph Output[Outputs & Access]
        RECORD[Recordings<br/>H.264/H.265 Files]
        WEB[Web Browser<br/>Multiview Studio]
        REMOTE[Remote Access<br/>HTTPS Worldwide]
        LIVE[Live Stream<br/>WebRTC/HLS]
    end
    
    CAM1 --> CAPTURE
    CAM2 --> CAPTURE
    CAM3 --> CAPTURE
    CAM4 --> CAPTURE
    
    CAPTURE --> ENCODE
    ENCODE --> MIXER
    ENCODE --> STREAM
    MIXER --> STREAM
    STREAM --> API
    
    STREAM --> RECORD
    STREAM --> WEB
    API --> REMOTE
    STREAM --> LIVE
    
    style R58 fill:#e3f2fd
    style Input fill:#f3e5f5
    style Output fill:#e8f5e9
`,
        content: `
## What Makes R58 Special?

### Professional Features in a Tiny Package

**Traditional Broadcast Setup**:
- Video switcher: $10,000+
- Multi-camera recorder: $5,000+
- Streaming encoder: $3,000+
- Rack space and cabling: $2,000+
- **Total**: $20,000+ and fills entire rack

**R58 System**:
- All features in one device
- Size: ~6" x 6" x 2"
- Cost: Fraction of traditional equipment
- Power: 20-28W (vs 500W+ for rack)
- Setup time: Minutes (vs hours)

### Key Capabilities

**1. Multi-Camera Recording**
- Capture 4 HDMI sources simultaneously
- Hardware encoding (low CPU, high quality)
- Individual or synchronized recording
- Automatic file management

**2. Live Video Mixing**
- Real-time scene switching
- Multiple layout presets
- Picture-in-picture
- Overlay graphics support

**3. Remote Production**
- Access from anywhere via HTTPS
- Sub-second latency streaming
- Browser-based control
- No VPN required

**4. Professional Streaming**
- WebRTC (ultra-low latency)
- HLS (universal compatibility)
- RTSP (professional tools)
- Multiple simultaneous outputs

## Use Cases

### Live Event Production
- Multi-camera coverage
- Real-time switching
- Remote director control
- Live streaming to audience

### Corporate/Education
- Conference recording
- Lecture capture
- Webinar production
- Training videos

### Houses of Worship
- Service recording
- Multi-angle coverage
- Live streaming
- Archive management

### Content Creation
- Podcast recording
- YouTube production
- Interview shows
- Multi-camera vlogs

### Broadcast Monitoring
- Multi-feed monitoring
- Quality control
- Signal verification
- Archive recording

## Technical Advantages

**Hardware Acceleration**:
- RK3588 MPP encoders
- 4x 1080p@30fps with 20% CPU
- Can handle 4K encoding
- Low power consumption

**Modern Architecture**:
- RESTful API
- WebRTC streaming
- Browser-based UI
- Cloud-ready design

**Flexible Deployment**:
- Standalone operation
- Remote access ready
- Scalable architecture
- Easy integration

## Competitive Advantages

| Feature | Traditional | R58 System |
|---------|-------------|------------|
| Size | Rack-mounted | 6" x 6" x 2" |
| Cost | $20,000+ | Fraction |
| Power | 500W+ | 20-28W |
| Setup | Hours | Minutes |
| Remote Access | Complex VPN | Built-in HTTPS |
| Latency | 3-5 seconds | <1 second |
| Maintenance | Complex | Simple |

## System Components

**Hardware** (Mekotronics R58 4x4 3S):
- Rockchip RK3588 8-core ARM SoC
- 8GB RAM
- 4x HDMI inputs (LT6911UXE bridges)
- Hardware video encoders
- Gigabit Ethernet

**Software Stack**:
- Custom Debian 12 OS (Mekotronics build)
- GStreamer 1.22.9 (media processing)
- MediaMTX v1.15.5+ (streaming server)
- VDO.ninja v28+ (live mixer)
- Python FastAPI (control API)
- FRP tunnel (remote access)

**Remote Infrastructure**:
- Coolify VPS (65.109.32.111)
- FRP reverse proxy
- Traefik SSL (Let's Encrypt)
- nginx CORS handling
        `,
        keyPoints: [
            'Replaces $20,000+ of traditional broadcast equipment',
            'All-in-one: capture, encode, mix, stream, record',
            'Hardware acceleration enables 4-camera performance',
            'Remote access built-in, no VPN required',
            'Browser-based control, works on any device'
        ],
        tags: ['product', 'overview', 'features', 'benefits', 'use cases']
    },
    
    // ========================================
    // VDO.NINJA INTEGRATION
    // ========================================
    
    'vdoninja-overview': {
        title: 'VDO.ninja Live Mixer',
        simple: `
VDO.ninja is a powerful browser-based video mixer that runs LOCALLY on the R58 device.

**What's running on R58**:
- VDO.ninja signaling server (port 8443) ✅ ACTIVE
- VDO.ninja web app (port 8444) ✅ ACTIVE
- raspberry.ninja publishers for cameras ✅ ACTIVE

**Note**: The R58 actually has TWO mixer options:
1. **VDO.ninja** - Browser-based, uses raspberry.ninja publishers
2. **GStreamer Mixer** - Built-in compositor, API-controlled

Think of it as having both a virtual TV studio AND a hardware switcher!
        `,
        technical: `
**VDO.ninja** (formerly OBS.ninja) is an open-source WebRTC-based video mixing platform.

**Verified Running on R58** (Dec 27, 2025):
- **Signaling Server**: vdo-ninja.service (Node.js, port 8443) ✅
- **Web App**: vdo-webapp.service (Python HTTP server, port 8444) ✅

**Integration Mode**: MediaMTX WHEP (recommended)
- VDO.ninja uses &mediamtx= parameter to pull streams
- Works both locally AND remotely through FRP tunnels
- No separate camera publishers needed

**Location**: /opt/vdo.ninja/

**How It Works**:
- Cameras stream to MediaMTX via GStreamer ingest pipelines
- MediaMTX exposes WHEP endpoints (/cam0/whep, /cam1/whep, etc.)
- VDO.ninja mixer uses &mediamtx= parameter to pull streams
- Works remotely through FRP tunnel

**Remote Access**:
- Mixer: https://app.itagenten.no/vdo/mixer.html?mediamtx=app.itagenten.no
- Director: https://app.itagenten.no/vdo/?director=r58studio&mediamtx=app.itagenten.no

**Note**: This is SEPARATE from the GStreamer mixer (MixerCore) in preke-recorder!

**Version**: v28+ (supports &mediamtx= parameter)

**DEPRECATED**: raspberry.ninja P2P publishers - they don't work through FRP tunnels.
        `,
        diagram: `
flowchart TB
    subgraph R58Device[R58 Device]
        CAM[Cameras]
        MTX[MediaMTX<br/>WHEP Endpoints]
        VDO[VDO.ninja Server<br/>:8443]
    end
    
    subgraph VPS[Cloud VPS]
        FRP[FRP Tunnel]
        VDOVPS[VDO.ninja Access<br/>app.itagenten.no/vdo]
    end
    
    subgraph Users[Remote Users]
        MIXER[Mixer Browser<br/>Pulls WHEP Streams]
        DIRECTOR[Director<br/>Controls Mixer]
        GUEST[Remote Guests<br/>WHIP Publishing]
    end
    
    CAM --> MTX
    MTX --> VDO
    VDO --> FRP
    FRP --> VDOVPS
    VDOVPS --> MIXER
    VDOVPS --> DIRECTOR
    GUEST --> VDOVPS
    
    style R58Device fill:#e3f2fd
    style VPS fill:#fff3e0
    style Users fill:#f3e5f5
`,
        content: `
## VDO.ninja Services

**Running Services** (Verified Dec 27, 2025):
- vdo-ninja.service - VDO.ninja signaling server ✅
- vdo-webapp.service - VDO.ninja web application ✅

**DEPRECATED Services** (disabled, do not use):
- ninja-publish-cam1/2/3.service - P2P publishers (don't work through tunnels)

## How It Works (MediaMTX WHEP Mode)

**1. Camera Capture**:
- Cameras stream to MediaMTX via GStreamer ingest pipelines
- MediaMTX provides WHEP endpoints
- Each camera available at: /cam0/whep, /cam1/whep, etc.

**2. VDO.ninja Mixer**:
- Browser-based mixing interface
- Uses &mediamtx= parameter to pull WHEP streams
- Pulls camera streams via WHEP
- No P2P WebRTC (server-based)
- Supports up to 8+ sources

**3. Remote Guests**:
- Join via WHIP protocol
- Publish to MediaMTX (speaker0, speaker1, etc.)
- Mixer pulls guest streams via WHEP
- All through FRP tunnel

## Access URLs

**Local Network**:
- Mixer: https://192.168.x.x:8443/mixer?room=r58studio
- Director: https://192.168.x.x:8443/?director=r58studio

**Remote Access** (via FRP):
- Mixer: https://app.itagenten.no/vdo/mixer?room=r58studio
- Director: https://app.itagenten.no/vdo/?director=r58studio

**WHEP Integration**:
Add WHEP URLs to mixer:
- &whep=https://app.itagenten.no/cam0/whep
- &whep=https://app.itagenten.no/cam1/whep
- etc.

## Why VDO.ninja?

**Advantages**:
- Browser-based (no software installation)
- Professional mixing features
- Remote guest support
- Free and open source
- Active development

**vs Traditional Mixers**:
- No hardware switcher needed
- Works on any device
- Remote operation built-in
- Flexible layouts
- Lower cost

## Version History

**Critical Version Requirements**:
- **VDO.ninja v28+**: Required for WHEP support
- **MediaMTX v1.15.5+**: Required for TCP WebRTC
- **Old versions don't work**: v25 and earlier lack WHEP

**Our Journey**:
- Started with v25: ❌ No WHEP support
- Upgraded to v28: ✅ WHEP support added
- Result: Full remote mixing capability
        `,
        keyPoints: [
            'VDO.ninja server IS running locally on R58 (port 8443)',
            'raspberry.ninja publishers ARE active (cam1, cam2, cam3)',
            'R58 has TWO mixers: VDO.ninja AND GStreamer compositor',
            'VDO.ninja for local network, GStreamer for API control'
        ],
        tags: ['vdo.ninja', 'mixer', 'live', 'webrtc', 'whep']
    },
    
    'two-mixers': {
        title: 'Two Mixer Options Explained',
        simple: `
The R58 has TWO different mixer systems that can work at the same time:

**Option 1: VDO.ninja (Browser-Based)**
- Uses your web browser as the mixer
- Cameras published via raspberry.ninja
- Great for live switching and effects
- Access at: https://app.itagenten.no/vdo/mixer

**Option 2: GStreamer Mixer (Built-In)**
- Runs inside the R58 itself
- Controlled via API
- Outputs to MediaMTX  
- Access via API: /api/mixer/start

You can use either one or both depending on your needs!
        `,
        technical: `
**Two Independent Mixer Architectures**:

**1. VDO.ninja + MediaMTX WHEP** (RECOMMENDED):

Services Running:
- vdo-ninja.service (Node.js signaling, port 8443)
- vdo-webapp.service (HTTP server, port 8444)
- MediaMTX (WHEP endpoints)

Architecture:
Camera → GStreamer Ingest → MediaMTX → WHEP endpoint → VDO.ninja mixer (via &mediamtx=)

Use case: Remote mixing through FRP tunnel, browser-based control

**2. GStreamer Compositor (MixerCore)**:

Code: src/mixer/core.py
API: /api/mixer/*
Config: mixer.enabled in config.yml

Architecture:
Camera (V4L2) → GStreamer v4l2src → compositor → encoder → MediaMTX

Use case: API-controlled mixing, programmatic control, recording

**Key Difference**:
- **VDO.ninja**: Browser is the mixer, cameras publish TO it
- **GStreamer**: R58 is the mixer, output streams FROM it

**Can Run Simultaneously**: Yes! They use different devices/methods.
        `,
        content: `
## When to Use Each Mixer

### Use VDO.ninja When:
- You want browser-based control
- Need VDO.ninja's advanced features
- Working on local network
- Want traditional broadcast mixer feel
- Need director/operator separation

**Access**:
- Local: https://192.168.x.x:8443/mixer?room=r58studio
- Remote: https://app.itagenten.no/vdo/mixer?room=r58studio

### Use GStreamer Mixer When:
- Need API control (automation)
- Want programmatic scene switching
- Need mixer output recording
- Want lower resource usage
- Building custom control interface

**Access**:
- API: POST /api/mixer/start
- Scenes: POST /api/mixer/set_scene

## Resource Usage

**VDO.ninja + raspberry.ninja**:
- 3x raspberry.ninja processes: ~3-5% CPU each
- VDO.ninja signaling: ~1% CPU
- Browser rendering: External (on viewing device)
- Total R58 impact: ~10-15% CPU

**GStreamer Mixer**:
- Compositor: ~15-20% CPU
- Encoding: ~10-15% CPU (hardware)
- Total R58 impact: ~25-35% CPU

## Current Status (Verified Dec 27, 2025)

**VDO.ninja Stack** (MediaMTX WHEP Mode):
- vdo-ninja.service: ✅ ACTIVE
- vdo-webapp.service: ✅ ACTIVE
- MediaMTX: ✅ ACTIVE (provides WHEP endpoints)
- Integration: &mediamtx= parameter

**DEPRECATED** (disabled):
- ninja-publish-cam1/2/3: ❌ DISABLED (P2P doesn't work through tunnels)

**GStreamer Mixer**:
- State: NULL (not running, but available)
- Health: healthy
- Config: mixer.enabled: true

## Why Both Exist

**Historical**:
- VDO.ninja implemented first (Dec 18-22)
- GStreamer mixer added later (Dec 23-25)
- Both kept because each has advantages

**Use Cases**:
- **VDO.ninja**: Live production with operators
- **GStreamer**: Automated recording/streaming

## Integration Possibilities

**Hybrid Approach**:
- Use VDO.ninja for live mixing
- Record GStreamer mixer output
- Route VDO.ninja output to GStreamer (future enhancement)

**Current Best Practice**:
- Local network production: VDO.ninja
- Remote API control: GStreamer mixer
- Can switch between them as needed
        `,
        keyPoints: [
            'R58 has TWO mixers: VDO.ninja AND GStreamer',
            'VDO.ninja services ARE running (verified active)',
            'Both can be used simultaneously',
            'VDO.ninja for browser control, GStreamer for API control'
        ],
        tags: ['mixer', 'vdo.ninja', 'gstreamer', 'compositor', 'comparison']
    },
    
    'raspberry-ninja': {
        title: 'Raspberry.ninja Publishers',
        simple: `
Raspberry.ninja is a tool that can publish camera feeds to VDO.ninja signaling servers.

**What we tried**:
- Used raspberry.ninja to publish cameras
- Tried to work through FRP tunnel
- Attempted P2P WebRTC connections

**Result**: Didn't work through tunnels due to P2P architecture.

**Current approach**: We use MediaMTX WHEP instead (server-based, works through tunnels).
        `,
        technical: `
**Raspberry.ninja** is a lightweight WebRTC publisher designed for Raspberry Pi and ARM devices.

**Version Used**: v9.0.0

**What We Tried**:

Flow: Camera → raspberry.ninja publisher → VDO.ninja signaling → P2P WebRTC → Browser

**Why It Failed**:
1. **P2P Architecture**: Requires direct connections between peers
2. **NAT Traversal**: R58 behind NAT with no port forwarding
3. **Tunnel Incompatibility**: P2P WebRTC doesn't work through FRP tunnel
4. **UDP Requirements**: Needs UDP ports that can't be reliably tunneled

**Services Created** (now DISABLED):
- ninja-publish-cam1.service - DISABLED
- ninja-publish-cam2.service - DISABLED
- ninja-publish-cam3.service - DISABLED

**Why They're Disabled**:
- P2P WebRTC doesn't work through FRP tunnels
- MediaMTX WHEP mode works better for remote access
- Simpler architecture with fewer failure points

**Current Solution**: MediaMTX WHEP (Working!)

Flow: Camera → GStreamer Ingest → MediaMTX → WHEP endpoint → VDO.ninja mixer (via &mediamtx=)

**Why This Works**:
- Server-based (no P2P)
- HTTP-based protocol (works through tunnels)
- MediaMTX handles WebRTC complexity
- Single hop architecture
        `,
        content: `
## When Raspberry.ninja Can Be Used

**Scenarios Where It Works**:

**1. Local Network**:
- All devices on same LAN
- No NAT traversal needed
- Direct P2P connections possible
- Use case: Local production

**2. ZeroTier/Tailscale VPN**:
- Virtual LAN between devices
- Appears as local network
- P2P works normally
- Use case: Distributed teams

**3. Public IP with Port Forwarding**:
- R58 has public IP
- UDP ports forwarded
- Direct internet access
- Use case: Fixed installations

**4. TURN Server Available**:
- Relay server for NAT traversal
- Adds latency and complexity
- Requires TURN infrastructure
- Use case: Enterprise deployments

## Why We Don't Use It (Currently)

**Our Constraints**:
- R58 behind NAT (no public IP)
- No router access (can't port forward)
- FRP tunnel (TCP-based)
- Need remote access without VPN

**Technical Limitations**:
- P2P requires direct connections
- TURN relay doesn't solve tunnel issue
- UDP doesn't work reliably through FRP
- Complex signaling through proxy

**Better Solution**: MediaMTX WHEP
- Server-based (no P2P)
- Works through FRP tunnel
- Lower latency
- Simpler architecture

## Configuration

**MediaMTX WHEP Mode** (Recommended for both local and remote):

URLs with &mediamtx= parameter:
- Mixer: https://app.itagenten.no/vdo/mixer.html?mediamtx=app.itagenten.no
- Director: https://app.itagenten.no/vdo/?director=r58studio&mediamtx=app.itagenten.no

**Local Access**:
- Mixer: https://localhost:8443/mixer.html?mediamtx=localhost:8889
- Director: https://localhost:8443/?director=r58studio&mediamtx=localhost:8889

**DO NOT USE** raspberry.ninja P2P publishers - they have been disabled because P2P WebRTC
doesn't work through FRP tunnels. Use MediaMTX WHEP mode instead.

## Lessons Learned

**What We Discovered**:
1. P2P WebRTC doesn't work through HTTP tunnels
2. Version matters: v9.0.0 has better features than older versions
3. raspberry.ninja is great for local/VPN scenarios
4. Server-based WHEP is better for tunneled remote access

**Documentation**:
- See VDO_NINJA_FINAL_CONCLUSION.md for full analysis
- See RASPBERRY_NINJA_DEPLOYMENT.md for setup details
        `,
        keyPoints: [
            'raspberry.ninja v9.0.0 installed and running',
            'P2P architecture doesn\'t work through FRP tunnel',
            'Works great on local network or with VPN',
            'We use MediaMTX WHEP instead for remote access'
        ],
        tags: ['raspberry.ninja', 'publisher', 'p2p', 'webrtc', 'limitations']
    },
    
    'version-issues': {
        title: 'Version Issues & Lessons',
        simple: `
**A lot of our early problems were caused by using outdated software!**

**Old versions we started with**:
- MediaMTX v1.5.1 (very old, missing features)
- VDO.ninja v25 (no WHEP support)

**After updating**:
- MediaMTX v1.15.5 (10 versions newer!)
- VDO.ninja v28 (WHEP support added)

**Result**: Most problems disappeared after updating!

**Lesson**: Always check you're using current versions, especially for rapidly-evolving projects like MediaMTX.
        `,
        technical: `
**Critical Version Dependencies**:

**MediaMTX**:
- **v1.5.1** (initial): Missing TCP WebRTC, outdated WHEP, bugs
- **v1.15.5+** (current): TCP WebRTC, stable WHEP, 10+ versions of fixes
- **Impact**: 80% of early WebRTC issues were version-related

**VDO.ninja**:
- **v25** (initial): No native WHEP support
- **v28+** (current): WHEP support, better stability
- **Impact**: Enabled server-based mixing through tunnels

**raspberry.ninja**:
- **main branch** (initial): Unstable, limited features
- **v9.0.0** (current): Stable, better WebRTC handling
- **Impact**: More reliable local network operation

**Why Versions Mattered**:
1. **TCP WebRTC**: Added in MediaMTX v1.15.5
2. **WHEP Protocol**: Matured in MediaMTX v1.15+
3. **Bug Fixes**: 10+ versions of stability improvements
4. **Feature Additions**: WHIP/WHEP support evolved significantly
        `,
        content: `
## Version Timeline

**December 18, 2025**: Initial deployment
- MediaMTX v1.5.1
- VDO.ninja v25
- Many WebRTC failures

**December 22, 2025**: Software updates
- Updated MediaMTX to v1.15.5
- Updated VDO.ninja to v28
- Updated raspberry.ninja to v9.0.0

**December 23-25, 2025**: Testing and refinement
- Discovered TCP WebRTC feature
- Configured WHEP integration
- Achieved remote streaming

**Result**: Version updates solved 80% of problems

## Specific Issues Caused by Old Versions

**MediaMTX v1.5.1 Issues**:
- ❌ No webrtcLocalTCPAddress support
- ❌ Unstable WHEP implementation
- ❌ CORS handling bugs
- ❌ WebRTC negotiation failures
- ❌ Memory leaks in long-running streams

**After v1.15.5 Update**:
- ✅ TCP WebRTC works
- ✅ Stable WHEP endpoints
- ✅ Proper CORS headers
- ✅ Reliable WebRTC
- ✅ Stable 24/7 operation

**VDO.ninja v25 Issues**:
- ❌ No native WHEP support
- ❌ Had to use P2P (doesn't work through tunnels)
- ❌ Complex signaling workarounds

**After v28 Update**:
- ✅ Native WHEP support
- ✅ Server-based mixing
- ✅ Works through tunnels
- ✅ Simpler integration

## How to Check Versions

**MediaMTX**:
- SSH to R58 and run: /usr/local/bin/mediamtx --version

**VDO.ninja**:
- SSH to R58: cd /opt/vdo.ninja && git log --oneline -1

**GStreamer**:
- SSH to R58 and run: gst-launch-1.0 --version

## Update Recommendations

**Always Use Latest Stable**:
- MediaMTX: Check https://github.com/bluenviron/mediamtx/releases
- VDO.ninja: Check https://github.com/steveseguin/vdo.ninja/releases
- GStreamer: Use Debian package (1.22.9 is current)

**Update Process**:
See update_r58_software.sh script for automated updates

**Testing After Updates**:
1. Verify services start
2. Test WHEP endpoints
3. Check camera streams
4. Test mixer functionality
5. Monitor logs for errors

## Key Takeaway

**Version matters!** 

For rapidly-evolving projects like MediaMTX and VDO.ninja:
- Check releases frequently
- Read changelogs for new features
- Test updates in development first
- Keep production systems current

**Our experience**: Updating from v1.5.1 to v1.15.5 (10 versions) solved most WebRTC issues immediately.
        `,
        keyPoints: [
            'MediaMTX v1.5.1 → v1.15.5 solved 80% of issues',
            'VDO.ninja v28+ required for WHEP support',
            'Always use latest stable versions',
            'Version updates more important than configuration tweaks'
        ],
        tags: ['versions', 'updates', 'mediamtx', 'vdo.ninja', 'lessons']
    },
    
    'hardware-specs': {
        title: 'R58 Hardware Specifications',
        simple: `
**Mekotronics R58 4x4 3S** - Professional video capture device

**Key Specs**:
- **Processor**: 8-core ARM (Rockchip RK3588)
- **Memory**: 8GB RAM
- **Video Inputs**: 4x HDMI (up to 4K@60fps each)
- **Special Features**: Hardware video encoding chips
- **Size**: Compact (approximately 6" x 6" x 2")
- **Power**: 20-28W (very efficient!)

**Operating System**: Custom Debian 12 built by Mekotronics
        `,
        technical: `
**Mekotronics R58 4x4 3S**

**SoC**: Rockchip RK3588S
- 8-core ARM CPU (4x Cortex-A76 @ 2.4GHz + 4x Cortex-A55 @ 1.8GHz)
- Mali-G610 MP4 GPU
- 6 TOPS NPU (Neural Processing Unit)
- MPP (Media Process Platform) hardware encoders/decoders

**Memory**: 8GB LPDDR4X

**Video Capture**:
- 1x rk_hdmirx (native HDMI RX controller) → /dev/video60
- 3x LT6911UXE HDMI-to-MIPI bridges → /dev/video0, /dev/video11, /dev/video22
- All inputs support up to 4K@60fps

**Hardware Encoders**:
- mpph264enc: H.264 encoding (up to 4K@60fps)
- mpph265enc: H.265 encoding (up to 4K@60fps)
- Multiple simultaneous encode sessions supported
- RGA: Hardware scaling and format conversion

**Operating System**:
- **Base**: Debian GNU/Linux 12 (bookworm)
- **Kernel**: 6.1.99 (custom Mekotronics build)
- **Build Info**: root@blueberry Fri Oct 24 18:38:55 CST 2025
- **Custom**: Includes Rockchip drivers and optimizations

**GStreamer**:
- **Version**: 1.22.9 (Debian package)
- **Custom Plugins**: Rockchip MPP encoders
- **RGA Support**: Hardware acceleration plugins
- **Source**: Debian repository (not custom build)

**Storage**:
- eMMC (system)
- SD card slot (recordings)
- USB 3.0 (external storage)

**Network**:
- Gigabit Ethernet
- Optional: Wi-Fi (if module installed)

**Power**:
- 12V DC input
- 20-28W typical consumption
- 30W peak

**Physical**:
- Compact form factor
- Fanless design (passive cooling)
- Industrial-grade construction
        `,
        content: `
## Verified Specifications (Dec 26, 2025)

**System Information**:
- Hostname: linaro-alip
- OS: Debian GNU/Linux 12 (bookworm)
- Kernel: 6.1.99 (Mekotronics custom build)
- Architecture: aarch64 (ARM 64-bit)
- Memory: 7.7GB total, 5.2GB available

**Build Information**:
- BUILD_INFO: root@blueberry Fri Oct 24 18:38:45 CST 2025
- RK_BUILD_INFO: root@blueberry Fri Oct 24 18:38:55 CST 2025

**This confirms**: Custom Debian build from Mekotronics with Rockchip optimizations.

## HDMI Capture Architecture

**Hybrid Capture System**:

**Port N60** (/dev/video60):
- Native RK3588 HDMI RX controller
- Device: rk_hdmirx (fdee0000.hdmirx-controller)
- Format: NV16 (4:2:2)
- Best performance (direct hardware)

**Ports N0, N11, N21** (/dev/video0, /dev/video11, /dev/video22):
- LT6911UXE HDMI-to-MIPI bridge chips
- Devices: rkcif-mipi-lvds (platform drivers)
- Format: UYVY/NV16 (requires initialization)
- I2C addresses: 2-002b, 4-002b, 7-002b

**Why This Design?**:
- RK3588 has only 1 native HDMI RX
- LT6911UXE bridges add 3 more inputs
- All 4 inputs support 4K@60fps
- Cost-effective solution

## Performance Characteristics

**CPU Usage** (8-core RK3588):
- Idle: ~5-10%
- 1 camera (hardware encode): ~10-15%
- 4 cameras (hardware encode): ~20-30%
- 4 cameras + mixer: ~40-50%

**Memory Usage**:
- Base system: ~2.5GB
- Per camera pipeline: ~50MB
- Mixer active: +100MB
- Total with 4 cameras + mixer: ~3GB

**Encoding Performance**:
- H.264: 4x 1080p@30fps simultaneous
- H.265: 4x 1080p@30fps simultaneous
- 4K: 2x 4K@30fps simultaneous
- Hardware acceleration critical

**Network**:
- 4x 1080p@4Mbps = 16 Mbps upload
- Gigabit Ethernet easily handles
- FRP tunnel adds ~20ms latency

**Storage**:
- Recording: ~6-8 MB/s per 1080p@30fps stream
- 4 cameras: ~24-32 MB/s
- SD card sufficient for short recordings
- SSD recommended for 24/7 operation

## Thermal Performance

**Operating Temperatures**:
- Idle: ~40-50°C
- 4 cameras active: ~60-70°C
- Passive cooling sufficient
- No throttling observed

**Recommendations**:
- Ensure adequate ventilation
- Avoid enclosed spaces
- Monitor temperature in hot environments
- Optional: Add fan for 24/7 operation

## Expansion Capabilities

**USB Ports**:
- USB 3.0 for external storage
- USB capture devices (additional cameras)
- USB audio interfaces

**PCIe**:
- M.2 slot available
- NVMe SSD for fast storage
- Potential for expansion cards

**GPIO/I2C/SPI**:
- Available for custom integrations
- Sensor connections
- Control interfaces
        `,
        keyPoints: [
            'Mekotronics R58 4x4 3S with RK3588 SoC',
            'Custom Debian 12 OS from Mekotronics',
            'GStreamer 1.22.9 (standard Debian, not custom)',
            '4x HDMI via 1 native + 3 LT6911UXE bridges'
        ],
        tags: ['hardware', 'specifications', 'r58', 'rk3588', 'mekotronics']
    }
});

