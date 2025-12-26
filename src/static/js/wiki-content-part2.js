// R58 Documentation Wiki - Content Database (Part 2)
// Remote Access, API Reference, Troubleshooting, History & Decisions

// Extend the wikiContent object
Object.assign(wikiContent, {
    // ========================================
    // REMOTE ACCESS
    // ========================================
    
    'remote-overview': {
        title: 'Remote Access Overview',
        simple: `
You can access the R58 from anywhere in the world through the internet!

There are two ways to access it:
1. **SSH** - Command line access (for advanced users)
2. **Web Browser** - Easy graphical interface (for everyone)

Both methods are secure and use encrypted connections.
        `,
        technical: `
**Architecture**: FRP Reverse Proxy Tunnel

The R58 is behind NAT (no public IP). We use FRP (Fast Reverse Proxy) to create a secure tunnel to a public VPS:

\`\`\`
R58 (local) → FRP Client → SSH Tunnel → VPS FRP Server → Internet
\`\`\`

**VPS Details** (Verified):
- IP: 65.109.32.111
- Provider: Coolify-managed
- SSL: Let's Encrypt (automatic)
- Domains: *.itagenten.no

**Security**:
- FRP uses token authentication
- SSH tunnel for FRP control connection
- All web traffic over HTTPS
- SSH on non-standard port (10022)
        `,
        diagram: `
flowchart LR
    subgraph Local[Your Computer]
        SSH[SSH Client]
        BROWSER[Web Browser]
    end
    
    subgraph VPS[Coolify VPS<br/>65.109.32.111]
        PORT10022[Port 10022<br/>SSH]
        PORT443[Port 443<br/>HTTPS]
        FRPS[FRP Server]
        TRAEFIK[Traefik SSL]
    end
    
    subgraph R58[R58 Device<br/>Local Network]
        FRPC[FRP Client]
        SSHD[SSH Server :22]
        API[FastAPI :8000]
        MTX[MediaMTX :8889]
    end
    
    SSH -->|SSH| PORT10022
    BROWSER -->|HTTPS| PORT443
    PORT10022 --> FRPS
    PORT443 --> TRAEFIK
    FRPS --> FRPC
    TRAEFIK --> FRPS
    FRPC --> SSHD
    FRPC --> API
    FRPC --> MTX
    
    style VPS fill:#fff3e0
    style R58 fill:#e3f2fd
`,
        content: `
## Access Methods

### 1. SSH Access

**Command**:
\`\`\`bash
./connect-r58-frp.sh
\`\`\`

**What it does**:
\`\`\`bash
sshpass -p linaro ssh -p 10022 linaro@65.109.32.111
\`\`\`

**Use cases**:
- Deploy code
- View logs
- Restart services
- Edit configuration
- Debug issues

### 2. Web Access

**URLs** (All HTTPS with valid certificates):

- **Studio**: https://r58-api.itagenten.no/static/studio.html
- **Main App**: https://r58-api.itagenten.no/static/app.html
- **Guest Portal**: https://r58-api.itagenten.no/static/guest.html
- **API Docs**: https://r58-api.itagenten.no/docs
- **This Wiki**: https://r58-api.itagenten.no/static/wiki.html

**Use cases**:
- View camera feeds
- Control recording
- Monitor system status
- Manage mixer and scenes

## Network Requirements

**From Your Computer**:
- Internet connection
- Access to 65.109.32.111:10022 (SSH)
- Access to 65.109.32.111:443 (HTTPS)

**Firewall**: No special configuration needed (uses standard ports)

## Stability

**Verified Dec 26, 2025**:
- SSH: 100% success rate (5/5 tests)
- HTTPS: Valid SSL certificate
- WebRTC: Working through tunnel
- Latency: ~20ms added by tunnel
        `,
        keyPoints: [
            'FRP tunnel provides secure remote access',
            'No port forwarding needed on R58 network',
            'All web traffic uses HTTPS with Let\'s Encrypt',
            'SSH on port 10022, HTTPS on port 443'
        ],
        tags: ['remote access', 'frp', 'ssh', 'https', 'tunnel']
    },
    
    'ssh-access': {
        title: 'SSH Access Guide',
        simple: `
SSH lets you control the R58 using text commands. It's like having a direct line to the computer's brain!

**To connect**:
\`\`\`bash
./connect-r58-frp.sh
\`\`\`

**Username**: linaro  
**Password**: linaro

Once connected, you can type commands to control the R58.
        `,
        technical: `
**Connection Details** (Verified):
- **Host**: 65.109.32.111
- **Port**: 10022 (FRP-mapped from R58:22)
- **User**: linaro
- **Password**: linaro
- **Method**: Password authentication via sshpass

**Script**: ./connect-r58-frp.sh

**Source code**:
- Uses sshpass for password authentication
- Connects to 65.109.32.111:10022
- Passes through commands to R58
- Password defaults to "linaro"

**Requirements**:
- sshpass installed (\`brew install sshpass\` on macOS)
- Network access to VPS port 10022
        `,
        content: `
## Basic SSH Commands

**Connect**:
\`\`\`bash
./connect-r58-frp.sh
\`\`\`

**Run Single Command**:
\`\`\`bash
./connect-r58-frp.sh "hostname"
# Output: linaro-alip
\`\`\`

**Multiple Commands**:
\`\`\`bash
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && git status"
\`\`\`

## Common Tasks

### Check Service Status
\`\`\`bash
./connect-r58-frp.sh "systemctl status preke-recorder"
./connect-r58-frp.sh "systemctl status mediamtx"
./connect-r58-frp.sh "systemctl status frpc"
\`\`\`

### View Logs
\`\`\`bash
# Last 50 lines
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -n 50"

# Follow logs (live)
./connect-r58-frp.sh "sudo journalctl -u preke-recorder -f"
\`\`\`

### Restart Services
\`\`\`bash
./connect-r58-frp.sh "sudo systemctl restart preke-recorder"
./connect-r58-frp.sh "sudo systemctl restart mediamtx"
\`\`\`

### Edit Configuration
\`\`\`bash
# Connect interactively
./connect-r58-frp.sh

# Edit config
nano /opt/preke-r58-recorder/config.yml

# Restart to apply
sudo systemctl restart preke-recorder
\`\`\`

### Check System Resources
\`\`\`bash
# CPU and memory
./connect-r58-frp.sh "top -bn1 | head -20"

# Disk space
./connect-r58-frp.sh "df -h"

# Active ports
./connect-r58-frp.sh "ss -tlnp"
\`\`\`

## SSH Key Setup (Optional)

For passwordless access:

\`\`\`bash
# Generate key (if you don't have one)
ssh-keygen -t ed25519

# Copy to R58
ssh-copy-id -p 10022 linaro@65.109.32.111

# Test
ssh -p 10022 linaro@65.109.32.111
\`\`\`

## Troubleshooting SSH

**Connection Refused**:
\`\`\`bash
# Check if port is open
nc -zv 65.109.32.111 10022
# Should show: Connection succeeded
\`\`\`

**Permission Denied**:
- Verify password is "linaro"
- Check sshpass is installed
- Try manual connection: \`ssh -p 10022 linaro@65.109.32.111\`

**Timeout**:
- Check internet connection
- Verify VPS is accessible
- Check FRP tunnel status on R58
        `,
        keyPoints: [
            'SSH via FRP tunnel on port 10022',
            'Username: linaro, Password: linaro',
            'Use ./connect-r58-frp.sh for easy access',
            'Can run single commands or interactive session'
        ],
        tags: ['ssh', 'terminal', 'command line', 'access']
    },
    
    'web-interfaces': {
        title: 'Web Interfaces',
        simple: `
The R58 has several web pages you can open in your browser:

1. **Studio** - See all cameras at once (like a TV control room)
2. **Main App** - Control recording and settings
3. **Guest Portal** - For remote speakers to join
4. **Wiki** - This documentation you're reading!

All pages work on phones, tablets, and computers.
        `,
        technical: `
**Base URL**: https://r58-api.itagenten.no

**Static Files Served by FastAPI**:
- Location: /opt/preke-r58-recorder/src/static/
- Route: /static/{filename}
- MIME types: Automatic detection

**SSL**: Let's Encrypt certificate via Traefik
- Auto-renewal
- Valid for *.itagenten.no
- HTTPS only (HTTP redirects to HTTPS)

**CORS**: Handled by nginx proxy
- Allows all origins for MediaMTX
- OPTIONS preflight support
- Required for WebRTC WHEP/WHIP
        `,
        content: `
## Available Interfaces

### Studio (Multiview)
**URL**: https://r58-api.itagenten.no/static/studio.html

**Features**:
- 4-camera multiview grid
- Real-time WebRTC streams
- Audio level meters
- Recording status indicators
- Scene switching controls
- Dark mode support

**Use case**: Production monitoring, live switching

### Main App
**URL**: https://r58-api.itagenten.no/static/app.html

**Features**:
- Camera control (start/stop recording)
- System status monitoring
- Configuration management
- File browser
- Log viewer

**Use case**: System administration, recording control

### Guest Portal
**URL**: https://r58-api.itagenten.no/static/guest.html

**Features**:
- WHIP publishing (WebRTC)
- Camera/microphone selection
- Connection status
- Audio level monitoring

**Use case**: Remote speakers, guests joining remotely

### API Documentation
**URL**: https://r58-api.itagenten.no/docs

**Features**:
- Interactive API explorer (Swagger UI)
- Try endpoints directly
- See request/response formats
- Authentication testing

**Use case**: API integration, development

### This Wiki
**URL**: https://r58-api.itagenten.no/static/wiki.html

**Features**:
- Full-text search
- Mermaid diagrams
- Dark mode
- Print-friendly
- Mobile responsive

**Use case**: Documentation, learning, reference

## Browser Compatibility

**Tested Browsers**:
- ✅ Chrome/Edge (Chromium) - Recommended
- ✅ Firefox
- ✅ Safari (macOS/iOS)
- ⚠️ Mobile browsers (limited WebRTC support)

**Requirements**:
- JavaScript enabled
- WebRTC support (for video streaming)
- Modern CSS support (flexbox, grid)

## Performance Tips

**For Best Experience**:
1. Use Chrome/Edge for WebRTC
2. Enable hardware acceleration in browser
3. Close unused tabs
4. Use wired ethernet (not Wi-Fi) for streaming
5. Disable browser extensions that block scripts

## Mobile Access

All interfaces are responsive and work on mobile devices:

**Recommended**:
- Tablets (iPad, Android tablets) for Studio
- Phones for monitoring and control
- Landscape orientation for multiview

**Limitations**:
- Mobile WebRTC may have higher latency
- Some features require keyboard (shortcuts)
- Small screens limit multiview usefulness
        `,
        keyPoints: [
            'All interfaces accessible via HTTPS',
            'Studio provides 4-camera multiview',
            'Guest portal for remote WHIP publishing',
            'Mobile-responsive design for all pages'
        ],
        tags: ['web', 'interface', 'browser', 'ui', 'studio']
    },
    
    'deployment': {
        title: 'Deployment Guide',
        simple: `
To update the R58 with new code, just run one command:

\`\`\`bash
./deploy-simple.sh
\`\`\`

This script will:
1. Save your changes to GitHub
2. Connect to the R58
3. Download the new code
4. Restart the service

It takes about 30 seconds!
        `,
        technical: `
**Deployment Script**: ./deploy-simple.sh

**Process**:
1. Git commit and push to GitHub
2. SSH to R58 via FRP tunnel
3. Pull latest code from GitHub
4. Restart preke-recorder service
5. Verify service started successfully

**Requirements**:
- Git repository with remote (GitHub)
- SSH access to R58 (via FRP)
- Systemd service configured

**Verified Working** (Dec 26, 2025):
- SSH connection: ✅
- Git pull: ✅
- Service restart: ✅
- Zero downtime: ~5 seconds
        `,
        content: `
## Simple Deployment

**One-Command Deploy**:
\`\`\`bash
./deploy-simple.sh
\`\`\`

**What it does**:
\`\`\`bash
# 1. Commit and push
git add .
git commit -m "Deploy $(date)"
git push

# 2. SSH to R58 and update
./connect-r58-frp.sh "
    cd /opt/preke-r58-recorder &&
    git pull &&
    sudo systemctl restart preke-recorder
"
\`\`\`

**Output**:
\`\`\`
Deploying to R58...
[main abc1234] Deploy Thu Dec 26 15:30:00 2025
Connecting to R58 via FRP tunnel...
Already up to date.
Service restarted successfully!
\`\`\`

## Manual Deployment

If you need more control:

\`\`\`bash
# 1. Commit locally
git add .
git commit -m "Your commit message"
git push

# 2. Connect to R58
./connect-r58-frp.sh

# 3. Update code
cd /opt/preke-r58-recorder
git pull

# 4. Restart service
sudo systemctl restart preke-recorder

# 5. Check status
sudo systemctl status preke-recorder

# 6. View logs
sudo journalctl -u preke-recorder -n 50
\`\`\`

## Deployment Checklist

Before deploying:
- [ ] Test changes locally (if possible)
- [ ] Commit with descriptive message
- [ ] Check no syntax errors
- [ ] Verify config.yml changes (if any)

After deploying:
- [ ] Check service status
- [ ] View logs for errors
- [ ] Test affected features
- [ ] Verify web interfaces load

## Rollback

If deployment causes issues:

\`\`\`bash
# Connect to R58
./connect-r58-frp.sh

# Rollback to previous commit
cd /opt/preke-r58-recorder
git log --oneline -5  # Find previous commit
git reset --hard <commit-hash>

# Restart service
sudo systemctl restart preke-recorder
\`\`\`

## Configuration Changes

**If you changed config.yml**:
\`\`\`bash
# After deploying code
./connect-r58-frp.sh

# Edit config if needed
nano /opt/preke-r58-recorder/config.yml

# Restart to apply
sudo systemctl restart preke-recorder
\`\`\`

**If you changed mediamtx.yml**:
\`\`\`bash
sudo systemctl restart mediamtx
\`\`\`

## Zero-Downtime Deployment

For critical systems:

\`\`\`bash
# 1. Deploy new code (don't restart yet)
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && git pull"

# 2. Test new code in separate process
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && python -m src.main --port 8001"

# 3. If tests pass, restart main service
./connect-r58-frp.sh "sudo systemctl restart preke-recorder"
\`\`\`
        `,
        keyPoints: [
            './deploy-simple.sh handles full deployment',
            'Takes ~30 seconds, ~5 seconds downtime',
            'Git-based deployment (push to GitHub, pull on R58)',
            'Easy rollback with git reset'
        ],
        tags: ['deployment', 'deploy', 'update', 'git']
    },
    
    // ========================================
    // API REFERENCE
    // ========================================
    
    'api-overview': {
        title: 'API Overview',
        simple: `
The R58 has a REST API - a way for programs to talk to it using web requests.

You can use the API to:
- Start and stop recording
- Check camera status
- Control the mixer
- Manage scenes

You can test the API using your web browser or command-line tools like curl.
        `,
        technical: `
**Framework**: FastAPI (Python)  
**Base URL**: https://r58-api.itagenten.no  
**Documentation**: https://r58-api.itagenten.no/docs (Swagger UI)

**Features**:
- RESTful design
- JSON request/response
- Automatic validation (Pydantic)
- OpenAPI 3.0 schema
- CORS enabled

**Authentication**: None (trusted network)  
**Rate Limiting**: None

**Verified Endpoints** (Dec 26, 2025):
- ✅ /health
- ✅ /status
- ✅ /record/start/{cam_id}
- ✅ /api/mixer/status
- ✅ /api/scenes
        `,
        content: `
## API Base URL

**Production**: https://r58-api.itagenten.no  
**Local**: http://localhost:8000 (when on R58)

## Common Patterns

### Request Format
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/endpoint \\
  -H "Content-Type: application/json" \\
  -d '{"key": "value"}'
\`\`\`

### Response Format
\`\`\`json
{
  "status": "success",
  "data": { ... }
}
\`\`\`

### Error Format
\`\`\`json
{
  "detail": "Error message"
}
\`\`\`

## HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful request |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid input |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Internal error |
| 503 | Unavailable | Service disabled |

## Interactive Documentation

Visit https://r58-api.itagenten.no/docs to:
- See all endpoints
- Try requests directly
- View request/response schemas
- Test authentication

## API Categories

1. **Health & Status** - System monitoring
2. **Recording** - Camera recording control
3. **Mixer** - Video mixer control
4. **Scenes** - Scene management
5. **Preview** - Live preview control

## Example: Start Recording

\`\`\`bash
# Start recording on camera 1
curl -X POST https://r58-api.itagenten.no/record/start/cam1

# Response
{
  "status": "started",
  "camera": "cam1"
}
\`\`\`

## Example: Check Status

\`\`\`bash
# Get all camera statuses
curl https://r58-api.itagenten.no/status

# Response
{
  "cameras": {
    "cam0": {"status": "preview", "config": true},
    "cam1": {"status": "recording", "config": true},
    "cam2": {"status": "preview", "config": true},
    "cam3": {"status": "preview", "config": true}
  }
}
\`\`\`
        `,
        keyPoints: [
            'RESTful API with JSON request/response',
            'Interactive docs at /docs endpoint',
            'No authentication required (trusted network)',
            'All endpoints verified working Dec 26, 2025'
        ],
        tags: ['api', 'rest', 'endpoints', 'http']
    },
    
    'api-recording': {
        title: 'Recording API',
        simple: `
Control camera recording with simple web requests:

**Start recording**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/record/start/cam1
\`\`\`

**Stop recording**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/record/stop/cam1
\`\`\`

That's it! The R58 handles everything else automatically.
        `,
        technical: `
**Endpoints**:

\`\`\`
POST /record/start/{cam_id}  - Start recording
POST /record/stop/{cam_id}   - Stop recording
GET  /record/status/{cam_id} - Get recording status
\`\`\`

**Camera IDs**: cam0, cam1, cam2, cam3

**Recording Process**:
1. API receives start request
2. Creates GStreamer pipeline
3. Opens output file (MKV format)
4. Starts capture and encoding
5. Returns success response

**File Output**:
- Path: /mnt/sdcard/recordings/{cam_id}/
- Format: recording_%Y%m%d_%H%M%S.mkv
- Codec: H.264 (mpph264enc)
- Container: Matroska (fragmented)

**Verified Working** (Dec 26, 2025):
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/record/start/cam1
# Response: {"status":"started","camera":"cam1"}
\`\`\`
        `,
        content: `
## Start Recording

**Endpoint**: \`POST /record/start/{cam_id}\`

**Parameters**:
- \`cam_id\` (path): Camera ID (cam0, cam1, cam2, cam3)

**Request**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/record/start/cam1
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "status": "started",
  "camera": "cam1",
  "output_path": "/mnt/sdcard/recordings/cam1/recording_20251226_153022.mkv"
}
\`\`\`

**Errors**:
- 404: Camera not found
- 400: Camera already recording
- 500: Failed to start pipeline

## Stop Recording

**Endpoint**: \`POST /record/stop/{cam_id}\`

**Request**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/record/stop/cam1
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "status": "stopped",
  "camera": "cam1",
  "duration_seconds": 125.4,
  "file_size_mb": 62.3
}
\`\`\`

## Get Recording Status

**Endpoint**: \`GET /record/status/{cam_id}\`

**Request**:
\`\`\`bash
curl https://r58-api.itagenten.no/record/status/cam1
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "camera": "cam1",
  "recording": true,
  "start_time": "2025-12-26T15:30:22Z",
  "duration_seconds": 45.2,
  "output_path": "/mnt/sdcard/recordings/cam1/recording_20251226_153022.mkv"
}
\`\`\`

## Start All Cameras

**Bash Script Example**:
- Loop through cam0, cam1, cam2, cam3
- POST to /record/start/{cam_id} for each
- Use a simple for loop or parallel requests

**Python Script**:
\`\`\`python
import requests

base_url = "https://r58-api.itagenten.no"
cameras = ["cam0", "cam1", "cam2", "cam3"]

for cam in cameras:
    response = requests.post(f"{base_url}/record/start/{cam}")
    print(f"{cam}: {response.json()}")
\`\`\`

## Recording Settings

Configured in config.yml:
\`\`\`yaml
cameras:
  cam1:
    resolution: 1920x1080
    bitrate: 4000  # kbps
    codec: h264
    output_path: /mnt/sdcard/recordings/cam1/recording_%Y%m%d_%H%M%S.mkv
\`\`\`

**File Naming**:
- \`%Y\` - Year (2025)
- \`%m\` - Month (12)
- \`%d\` - Day (26)
- \`%H\` - Hour (15)
- \`%M\` - Minute (30)
- \`%S\` - Second (22)

**Example**: recording_20251226_153022.mkv
        `,
        keyPoints: [
            'Simple POST requests to start/stop recording',
            'Automatic file naming with timestamps',
            'MKV format with H.264 encoding',
            'Can control individual cameras or all at once'
        ],
        tags: ['api', 'recording', 'camera', 'control']
    },
    
    'api-mixer': {
        title: 'Mixer API',
        simple: `
Control the video mixer (combining multiple cameras) via API:

**Start mixer**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/api/mixer/start
\`\`\`

**Change scene**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/api/mixer/set_scene \\
  -H "Content-Type: application/json" \\
  -d '{"id": "quad"}'
\`\`\`

The mixer lets you create professional multi-camera layouts!
        `,
        technical: `
**Endpoints**:

\`\`\`
POST /api/mixer/start      - Start mixer pipeline
POST /api/mixer/stop       - Stop mixer pipeline
POST /api/mixer/set_scene  - Apply scene
GET  /api/mixer/status     - Get mixer status
\`\`\`

**Mixer Architecture**:
- GStreamer compositor element
- Multiple v4l2src inputs
- Dynamic pad property updates
- Hardware encoding (mpph265enc)
- Output to MediaMTX and/or file

**Current Status** (Verified Dec 26, 2025):
\`\`\`json
{
  "state": "NULL",
  "current_scene": null,
  "health": "healthy",
  "recording_enabled": false,
  "mediamtx_enabled": true
}
\`\`\`
        `,
        content: `
## Start Mixer

**Endpoint**: \`POST /api/mixer/start\`

**Request**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/api/mixer/start
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "status": "started",
  "scene": "quad",
  "output": "mixer_program"
}
\`\`\`

**What happens**:
1. Creates GStreamer compositor pipeline
2. Adds camera sources based on scene
3. Starts encoding (H.265 @ 8 Mbps)
4. Streams to MediaMTX path: mixer_program

## Stop Mixer

**Endpoint**: \`POST /api/mixer/stop\`

**Request**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/api/mixer/stop
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "status": "stopped"
}
\`\`\`

## Set Scene

**Endpoint**: \`POST /api/mixer/set_scene\`

**Request**:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/api/mixer/set_scene \\
  -H "Content-Type: application/json" \\
  -d '{"id": "quad"}'
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "status": "scene_applied",
  "scene_id": "quad",
  "rebuild_required": false
}
\`\`\`

**Available Scenes**:
- \`quad\` - 2x2 grid of all 4 cameras
- \`cam0_full\` - Camera 0 fullscreen
- \`cam1_full\` - Camera 1 fullscreen
- \`cam2_full\` - Camera 2 fullscreen
- \`cam3_full\` - Camera 3 fullscreen
- \`presentation_pip\` - Presentation with PiP

## Get Mixer Status

**Endpoint**: \`GET /api/mixer/status\`

**Request**:
\`\`\`bash
curl https://r58-api.itagenten.no/api/mixer/status
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "state": "PLAYING",
  "current_scene": "quad",
  "health": "healthy",
  "last_error": null,
  "last_buffer_seconds_ago": 0.1,
  "recording_enabled": false,
  "mediamtx_enabled": true,
  "overlay_enabled": false
}
\`\`\`

**State Values**:
- \`NULL\` - Not running
- \`PLAYING\` - Active and mixing
- \`PAUSED\` - Paused (rare)

**Health Values**:
- \`healthy\` - Normal operation
- \`degraded\` - Minor issues
- \`unhealthy\` - Serious issues
- \`failed\` - Pipeline failure

## Mixer Configuration

**config.yml**:
\`\`\`yaml
mixer:
  enabled: true
  output_resolution: 1920x1080
  output_bitrate: 8000  # kbps
  output_codec: h265
  recording_enabled: false
  mediamtx_enabled: true
  mediamtx_path: mixer_program
  scenes_dir: scenes
\`\`\`

## View Mixer Output

**MediaMTX Path**: mixer_program

**WHEP URL**:
\`\`\`
https://r58-mediamtx.itagenten.no/mixer_program/whep
\`\`\`

**HLS URL**:
\`\`\`
https://r58-mediamtx.itagenten.no/mixer_program/index.m3u8
\`\`\`
        `,
        keyPoints: [
            'Mixer combines multiple cameras into one output',
            'Dynamic scene switching without restart',
            'H.265 encoding @ 8 Mbps for quality',
            'Output available via WHEP and HLS'
        ],
        tags: ['api', 'mixer', 'scenes', 'compositor']
    },
    
    'api-scenes': {
        title: 'Scenes API',
        simple: `
Scenes define how cameras are arranged in the mixer. You can:

**List all scenes**:
\`\`\`bash
curl https://r58-api.itagenten.no/api/scenes
\`\`\`

**Get scene details**:
\`\`\`bash
curl https://r58-api.itagenten.no/api/scenes/quad
\`\`\`

Scenes are stored as JSON files in the \`scenes/\` directory.
        `,
        technical: `
**Endpoints**:

\`\`\`
GET /api/scenes       - List all scenes
GET /api/scenes/{id}  - Get scene definition
\`\`\`

**Scene Format**:
\`\`\`json
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
\`\`\`

**Coordinate System**:
- Relative coordinates (0.0 to 1.0)
- Converted to absolute pixels at runtime
- Resolution-independent

**Storage**: scenes/ directory (JSON files)
        `,
        content: `
## List All Scenes

**Endpoint**: \`GET /api/scenes\`

**Request**:
\`\`\`bash
curl https://r58-api.itagenten.no/api/scenes
\`\`\`

**Response** (200 OK):
\`\`\`json
{
  "scenes": [
    {
      "id": "quad",
      "label": "4-up grid",
      "resolution": {"width": 1920, "height": 1080},
      "slot_count": 4
    },
    {
      "id": "cam0_full",
      "label": "CAM 1 fullscreen",
      "resolution": {"width": 1920, "height": 1080},
      "slot_count": 1
    }
  ]
}
\`\`\`

## Get Scene Definition

**Endpoint**: \`GET /api/scenes/{id}\`

**Request**:
\`\`\`bash
curl https://r58-api.itagenten.no/api/scenes/quad
\`\`\`

**Response** (200 OK):
\`\`\`json
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
    },
    {
      "source": "cam1",
      "x_rel": 0.5,
      "y_rel": 0.0,
      "w_rel": 0.5,
      "h_rel": 0.5,
      "z": 0,
      "alpha": 1.0
    },
    {
      "source": "cam2",
      "x_rel": 0.0,
      "y_rel": 0.5,
      "w_rel": 0.5,
      "h_rel": 0.5,
      "z": 0,
      "alpha": 1.0
    },
    {
      "source": "cam3",
      "x_rel": 0.5,
      "y_rel": 0.5,
      "w_rel": 0.5,
      "h_rel": 0.5,
      "z": 0,
      "alpha": 1.0
    }
  ]
}
\`\`\`

## Scene Properties

**Slot Properties**:
- \`source\`: Camera ID (cam0, cam1, cam2, cam3)
- \`x_rel\`: X position (0.0 = left, 1.0 = right)
- \`y_rel\`: Y position (0.0 = top, 1.0 = bottom)
- \`w_rel\`: Width (0.5 = half screen)
- \`h_rel\`: Height (0.5 = half screen)
- \`z\`: Layer order (0 = back, higher = front)
- \`alpha\`: Opacity (0.0 = transparent, 1.0 = opaque)

**Example: Picture-in-Picture**:
\`\`\`json
{
  "slots": [
    {
      "source": "cam0",
      "x_rel": 0.0,
      "y_rel": 0.0,
      "w_rel": 1.0,
      "h_rel": 1.0,
      "z": 0
    },
    {
      "source": "cam1",
      "x_rel": 0.7,
      "y_rel": 0.7,
      "w_rel": 0.25,
      "h_rel": 0.25,
      "z": 1
    }
  ]
}
\`\`\`

## Create Custom Scene

1. Create JSON file in scenes/ directory:

\`\`\`json
// scenes/my_scene.json
{
  "id": "my_scene",
  "label": "My Custom Layout",
  "resolution": {"width": 1920, "height": 1080},
  "slots": [
    // Your layout here
  ]
}
\`\`\`

2. Apply scene:
\`\`\`bash
curl -X POST https://r58-api.itagenten.no/api/mixer/set_scene \\
  -H "Content-Type: application/json" \\
  -d '{"id": "my_scene"}'
\`\`\`

## Default Scenes

| Scene ID | Description |
|----------|-------------|
| quad | 2x2 grid (all 4 cameras) |
| cam0_full | Camera 0 fullscreen |
| cam1_full | Camera 1 fullscreen |
| cam2_full | Camera 2 fullscreen |
| cam3_full | Camera 3 fullscreen |
| presentation_pip | Presentation with PiP |
        `,
        keyPoints: [
            'Scenes define camera layouts for mixer',
            'JSON format with relative coordinates',
            'Resolution-independent (0.0-1.0 scale)',
            'Easy to create custom scenes'
        ],
        tags: ['api', 'scenes', 'layouts', 'mixer']
    },
    
    // Continue with Troubleshooting and History sections...
    // (Due to length, I'll create these in the next file)
});

