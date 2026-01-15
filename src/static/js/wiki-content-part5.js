// R58 Documentation Wiki - Content Database (Part 5)
// System Services, Directory Structure, Fleet Management, Legacy Components, WordPress Integration

// Extend the wikiContent object
Object.assign(wikiContent, {
    // ========================================
    // WORDPRESS INTEGRATION
    // ========================================
    
    'wordpress-integration': {
        title: 'WordPress & JetAppointments Integration',
        simple: `
The R58 can connect to your WordPress website to manage bookings and client projects.

**What it does**:
- Fetches bookings from JetAppointments
- Shows client list from WordPress
- Creates recording folders based on client/project
- Displays calendar for walk-in bookings

This makes it easy to organize recordings by client and automatically set up folders.
        `,
        technical: `
**Integration Status** (Verified Jan 15, 2026):
- ✅ WordPress REST API connection active
- ✅ JetAppointments booking sync working
- ✅ Client CPT integration functional
- ✅ Calendar kiosk view operational

**Technical Stack**:
- WordPress REST API with Application Passwords
- JetEngine for Custom Post Types (CPT)
- JetAppointments for booking management
- Python httpx client with retry logic
        `,
        content: `
## Configuration

### WordPress Setup

1. **Generate Application Password** in WordPress:
   - Go to Users → Profile
   - Scroll to "Application Passwords"
   - Enter name: "R58 Device"
   - Click "Add New Application Password"
   - Copy the generated password

2. **Add to config.yml** on R58:

\`\`\`yaml
wordpress:
  enabled: true
  url: 'https://preke.no'
  username: 'your-username'
  app_password: 'xxxx xxxx xxxx xxxx xxxx xxxx'
\`\`\`

3. **Restart Service**:

\`\`\`bash
sudo systemctl restart preke-recorder
\`\`\`

### Verify Connection

Check WordPress status:
\`\`\`bash
curl http://localhost:8000/api/v1/wordpress/status | jq
\`\`\`

Should show:
\`\`\`json
{
  "enabled": true,
  "connected": true,
  "wordpress_url": "https://preke.no"
}
\`\`\`

## Features

### Booking Management

**List Today's Bookings**:
\`\`\`bash
curl http://localhost:8000/api/v1/wordpress/appointments/today
\`\`\`

**Activate a Booking**:
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/wordpress/appointments/123/activate
\`\`\`

This creates:
- Recording folder: \`/data/recordings/clients/{client-slug}/{project-slug}/{booking-id}/\`
- Access token for customer portal
- WordPress Recording CPT entry

### Client & Project Management

**List Clients**:
\`\`\`bash
curl http://localhost:8000/api/v1/wordpress/clients
\`\`\`

**Create Project**:
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/wordpress/projects \\
  -H "Content-Type: application/json" \\
  -d '{"client_id": 5, "name": "Q1 Campaign", "type": "podcast"}'
\`\`\`

### Calendar Kiosk

The calendar view shows today's schedule with 30-minute slots:

**Get Today's Calendar**:
\`\`\`bash
curl http://localhost:8000/api/v1/wordpress/calendar/today
\`\`\`

**Create Walk-in Booking**:
\`\`\`bash
curl -X POST http://localhost:8000/api/v1/wordpress/calendar/book \\
  -H "Content-Type: application/json" \\
  -d '{
    "slot_start": "14:00",
    "slot_end": "15:00",
    "customer_name": "Jane Smith",
    "customer_email": "jane@example.com",
    "recording_type": "podcast"
  }'
\`\`\`

## Data Model

### Hierarchy

\`\`\`
Client (CPT)
  └─ Video Project (CPT)
      └─ Recording (CPT)
          └─ Recording Files (Media)
\`\`\`

### Custom Post Types

1. **client** - Client companies
   - Fields: name, slug, logo, contact info
   - Has many: video_project

2. **video_project** - Projects per client
   - Fields: name, slug, client_id, description
   - Has many: recordings

3. **recordings** - Individual recordings
   - Fields: title, project_id, booking_id, files
   - Belongs to: video_project

### JetAppointments

Bookings link to Clients (not projects directly):
- Booking → Client → Default Project → Recording

## Folder Structure

When a booking is activated, recordings are saved to:

\`\`\`
/data/recordings/clients/{client-slug}/{project-slug}/{booking-id}/
\`\`\`

Example:
\`\`\`
/data/recordings/clients/acme-corp/q1-campaign/123/
  ├── cam0_20260115_140530.mov
  ├── cam2_20260115_140530.mov
  └── cam3_20260115_140530.mov
\`\`\`

## API Endpoints

See full documentation: [docs/API.md](../docs/API.md)

### WordPress Status
- \`GET /api/v1/wordpress/status\` - Connection status

### Appointments
- \`GET /api/v1/wordpress/appointments\` - List bookings
- \`GET /api/v1/wordpress/appointments/today\` - Today's bookings
- \`GET /api/v1/wordpress/appointments/{id}\` - Get booking details
- \`POST /api/v1/wordpress/appointments/{id}/activate\` - Activate booking
- \`GET /api/v1/wordpress/booking/current\` - Get active booking

### Clients & Projects
- \`GET /api/v1/wordpress/clients\` - List all clients
- \`GET /api/v1/wordpress/clients/{id}/projects\` - Client's projects
- \`POST /api/v1/wordpress/projects\` - Create new project

### Calendar
- \`GET /api/v1/wordpress/calendar/today\` - Today's schedule
- \`POST /api/v1/wordpress/calendar/book\` - Create walk-in booking

### Customer Portal
- \`GET /api/v1/wordpress/customer/{token}/status\` - Portal status
- \`POST /api/v1/wordpress/customer/{token}/recording/start\` - Start recording
- \`POST /api/v1/wordpress/customer/{token}/recording/stop\` - Stop recording

## Troubleshooting

### Connection Issues

**403 Forbidden Error**:
- Whitelist R58 IP in WordPress WAF
- Check Application Password is valid
- Verify username is correct

**Authentication Failed**:
- Regenerate Application Password
- Update config.yml with new password
- Restart preke-recorder service

**No Bookings Showing**:
- Check JetAppointments is installed
- Verify bookings exist in WordPress
- Check date range in API call

### Testing Connection

Test authentication directly:
\`\`\`bash
curl -u 'username:app-password' \\
  https://preke.no/wp-json/wp/v2/users/me
\`\`\`

Should return user info, not 401/403 error.
        `,
        keyPoints: [
            'WordPress integration uses Application Passwords for secure API access',
            'Bookings automatically create organized folder structures',
            'Calendar kiosk allows walk-in bookings without WordPress login',
            'Full API documentation available in docs/API.md'
        ],
        tags: ['wordpress', 'integration', 'booking', 'jetappointments', 'api']
    },
    
    // ========================================
    // SYSTEM SERVICES
    // ========================================
    
    'system-services': {
        title: 'All System Services',
        simple: `
The R58 runs 11 different services that work together to provide all functionality.

**Main Services**:
- preke-recorder - The main application
- mediamtx - Streaming server
- vdo-ninja - Live mixer signaling

**Support Services**:
- frp - Remote access tunnel
- fleet-agent - Remote management
- admin-api - Legacy device control

All services start automatically when the R58 boots up.
        `,
        technical: `
**Complete Service List** (Verified Dec 26, 2025):

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| preke-recorder.service | 8000 | Main FastAPI application | Active |
| mediamtx.service | 8889, 8554, 9997 | Streaming server (WHEP) | Active |
| frpc.service | - | FRP client (tunnel) | Active |
| frp-ssh-tunnel.service | - | SSH tunnel for FRP | Active |
| vdo-ninja.service | 8443 | VDO.ninja signaling | Active |
| vdo-webapp.service | 8444 | VDO.ninja web app | Active |
| r58-admin-api.service | 8088 | Legacy admin API | Active |
| r58-fleet-agent.service | - | Fleet management | Active |

**DISABLED Services** (don't use):
- ninja-publish-cam1/2/3 - P2P publishers (don't work through tunnels)

**Service Dependencies**:
- mediamtx must start before preke-recorder
- frp-ssh-tunnel must start before frpc
        `,
        content: `
## Service Management

### Check Service Status

Check all services:
\`\`\`bash
systemctl status preke-recorder mediamtx frpc vdo-ninja
\`\`\`

Check specific service:
\`\`\`bash
systemctl status preke-recorder
\`\`\`

### Restart Services

Restart main application:
\`\`\`bash
sudo systemctl restart preke-recorder
\`\`\`

Restart streaming server:
\`\`\`bash
sudo systemctl restart mediamtx
\`\`\`

Restart VDO.ninja services:
\`\`\`bash
sudo systemctl restart vdo-ninja vdo-webapp
\`\`\`

### View Logs

Real-time logs:
\`\`\`bash
sudo journalctl -u preke-recorder -f
\`\`\`

Last 100 lines:
\`\`\`bash
sudo journalctl -u mediamtx -n 100
\`\`\`

### Service Files Location

All service files are in:
\`\`\`
/etc/systemd/system/
\`\`\`

## Service Details

### preke-recorder.service

**Purpose**: Main FastAPI application providing web UI and API

**Key Features**:
- Recording management
- Mixer control
- Scene management
- Graphics rendering
- API endpoints

**Configuration**:
- WorkingDirectory: /opt/preke-r58-recorder
- User: root
- Port: 8000
- Environment: Cloudflare TURN credentials

**Dependencies**: network.target

### mediamtx.service

**Purpose**: Multi-protocol streaming server

**Protocols Supported**:
- WebRTC (WHIP/WHEP)
- RTSP
- RTMP
- HLS
- SRT

**Configuration**:
- WorkingDirectory: /opt/mediamtx
- Config: /opt/mediamtx/mediamtx.yml
- User: root
- Ports: 8889 (WebRTC), 8554 (RTSP), 9997 (API)

### frpc.service + frp-ssh-tunnel.service

**Purpose**: Remote access via FRP tunnel

**How It Works**:
1. frp-ssh-tunnel creates SSH tunnel to VPS
2. frpc connects through tunnel to FRP server
3. FRP server exposes R58 services publicly

**Configuration**:
- frpc config: /opt/frp/frpc.toml
- SSH key: /root/.ssh/id_ed25519_frp
- VPS: 65.109.32.111:7000

**Exposed Services**:
- SSH (10022)
- API (18000)
- MediaMTX (18889)
- VDO.ninja (18443)
- WebRTC UDP (18189)

### vdo-ninja.service

**Purpose**: Custom VDO.ninja signaling server

**Important**: This is OUR CUSTOM CODE, not standard VDO.ninja!

**Custom Features**:
- Room normalization (all rooms become r58studio)
- Publisher tracking (r58-cam1/2/3)
- WebSocket signaling
- Serves VDO.ninja web app

**Configuration**:
- Code: /opt/vdo-signaling/vdo-server.js
- User: linaro
- Port: 8443 (HTTPS/WSS)
- SSL: Self-signed cert

### vdo-webapp.service

**Purpose**: Serve VDO.ninja web application

**Configuration**:
- Directory: /opt/vdo.ninja
- User: linaro
- Port: 8444
- Server: Python http.server

### ninja-publish-cam1/2/3.service (DEPRECATED - DISABLED)

**Purpose**: (Was) Publish camera feeds to VDO.ninja via P2P WebRTC

**Status**: DISABLED - P2P WebRTC doesn't work through FRP tunnels.
Use MediaMTX WHEP mode instead (VDO.ninja with &mediamtx= parameter).

**Technology**: raspberry.ninja v9.0.0

**Configuration**:
- Script: /opt/raspberry_ninja/publish.py
- User: linaro
- Cameras: /dev/video60, /dev/video11, /dev/video22
- Stream IDs: r58-cam1, r58-cam2, r58-cam3
- Bitrate: 8000 kbps
- Resolution: 1920x1080@30fps
- Codec: H.264

### r58-admin-api.service

**Purpose**: Legacy Mekotronics admin API

**Features**:
- Device detection (list /dev/video*)
- Encoder detection (mpph264enc, v4l2h264enc)
- Stream control (RTMP/SRT)
- Systemd service management

**Configuration**:
- Code: /opt/r58/admin_api/main.py
- User: root
- Port: 8088 (local only, not exposed)
- Environment: /etc/r58/.env

**Note**: This is legacy code from Mekotronics. The main preke-recorder application provides similar functionality. Consider whether this is still needed.

### r58-fleet-agent.service

**Purpose**: Remote fleet management

**Features**:
- Reports device status (CPU, memory, disk)
- Executes remote commands
- Software update handling
- WebSocket connection to fleet API

**Configuration**:
- Code: /opt/r58-fleet-agent/fleet_agent.py
- User: root
- Fleet API: wss://fleet.r58.itagenten.no/ws
- Heartbeat: Every 10 seconds
- Logs: /var/log/r58-fleet-agent/

**Security Note**: This service can execute remote commands. Ensure fleet API access is properly secured.

## Disabled Services

These services are installed but not running:

- cloudflared.service - Old Cloudflare tunnel (replaced by FRP)
- ninja-publish-cam0/1/2/3.service - P2P publishers (replaced by MediaMTX WHEP)
- ninja-receive-guest1/2.service - Guest receivers (old approach)
- ninja-rtmp-restream.service - RTMP test
- ninja-rtmp-test.service - RTMP test
- ninja-rtsp-restream.service - RTSP test
- ninja-pipeline-test.service - Pipeline test

**Note**: ninja-publish services were disabled because P2P WebRTC doesn't work 
through FRP tunnels. Use MediaMTX WHEP mode instead (&mediamtx= parameter).
- r58-opencast-agent.service - Opencast integration (unused)

These can be removed if not needed.
        `,
        keyPoints: [
            '11 active services work together',
            'All services auto-start on boot',
            'Use systemctl to manage services',
            'Logs available via journalctl'
        ],
        tags: ['services', 'systemd', 'management', 'configuration']
    },

    'directory-structure': {
        title: 'Directory Structure',
        simple: `
All R58 code and configuration lives in /opt/ directory.

**Main Directories**:
- /opt/preke-r58-recorder - Our main application
- /opt/vdo.ninja - VDO.ninja web app
- /opt/vdo-signaling - Our custom signaling server
- /opt/raspberry_ninja - Camera publishers
- /opt/mediamtx - Streaming server config
- /opt/frp - Remote access tunnel

Everything else is either legacy code or support files.
        `,
        technical: `
**Complete /opt/ Directory Map**:

| Directory | Type | Purpose | Git Repo |
|-----------|------|---------|----------|
| /opt/preke-r58-recorder | Custom | Main application | Yes |
| /opt/vdo.ninja | Third-party | VDO.ninja web app v28+ | Yes |
| /opt/vdo-signaling | Custom | Signaling server | Yes |
| /opt/raspberry_ninja | Third-party | Publishers v9.0.0 | Yes |
| /opt/mediamtx | Config | MediaMTX config files | No |
| /opt/frp | Binary | FRP client + config | No |
| /opt/r58 | Legacy | Mekotronics code | No |
| /opt/r58-fleet-agent | Custom | Fleet agent | No |
| /opt/fleet-agent | Legacy | Old fleet agent? | No |

**Which Are Ours vs Third-Party**:

Our Custom Code:
- /opt/preke-r58-recorder
- /opt/vdo-signaling
- /opt/r58-fleet-agent

Third-Party:
- /opt/vdo.ninja (VDO.ninja project)
- /opt/raspberry_ninja (raspberry.ninja project)
- /opt/frp (FRP project)

Legacy/Vendor:
- /opt/r58 (Mekotronics)
- /opt/fleet-agent (old?)
        `,
        content: `
## Main Application

### /opt/preke-r58-recorder

**Purpose**: Main FastAPI application

**Structure**:
\`\`\`
preke-r58-recorder/
├── src/                    # Source code
│   ├── main.py            # FastAPI app
│   ├── recorder.py        # Recording logic
│   ├── mixer/             # Mixer plugin
│   ├── graphics/          # Graphics rendering
│   ├── camera_control/    # Camera control
│   └── static/            # Web UI
├── config.yml             # Main configuration
├── venv/                  # Python virtual environment
├── scripts/               # Helper scripts
└── deployment/            # Deployment configs
\`\`\`

**Git Status**: Tracked, branch feature/remote-access-v2

**Local Modifications**:
- config.yml (1 line changed)
- Untracked: src/ninja/, scenes/, presentations/

## VDO.ninja Stack

### /opt/vdo.ninja

**Purpose**: VDO.ninja web application (v28+)

**Source**: https://github.com/steveseguin/vdo.ninja

**Version**: Git commit fa3df7a1

**Contents**: HTML/CSS/JS for VDO.ninja mixer interface

**Served By**: vdo-webapp.service on port 8444

### /opt/vdo-signaling

**Purpose**: CUSTOM signaling server for VDO.ninja

**Important**: This is OUR CODE, not standard VDO.ninja!

**Structure**:
\`\`\`
vdo-signaling/
├── vdo-server.js          # Our custom signaling logic
├── package.json           # Node.js dependencies
├── cert.pem               # Self-signed SSL cert
├── key.pem                # SSL private key
└── node_modules/          # Dependencies
\`\`\`

**Custom Features**:
- Room normalization (all rooms → r58studio)
- Publisher tracking (r58-cam1/2/3)
- Automatic viewer notification

**Dependencies**:
- express
- ws (WebSocket)
- cors

### /opt/raspberry_ninja

**Purpose**: WebRTC publishers for cameras

**Source**: https://github.com/steveseguin/raspberry_ninja

**Version**: 9.0.0 (Git commit 29ce989)

**Key File**: publish.py (597KB Python script)

**Features**:
- GStreamer-based WebRTC
- V4L2 device capture
- Hardware encoding support
- P2P WebRTC publishing

## Streaming & Tunnel

### /opt/mediamtx

**Purpose**: MediaMTX configuration

**Contents**:
- mediamtx.yml - Main config file

**Binary Location**: /usr/local/bin/mediamtx

**Key Configuration**:
- WebRTC on port 8889
- RTSP on port 8554
- API on port 9997
- ICE configuration for NAT
- Path definitions (cam0-3, guests, etc.)

### /opt/frp

**Purpose**: FRP client for remote access

**Contents**:
- frpc - FRP client binary
- frpc.toml - Configuration file

**Configuration Highlights**:
- 8 proxy definitions
- SSH, API, MediaMTX, VDO.ninja
- Connects via SSH tunnel to VPS

## Legacy Components

### /opt/r58

**Purpose**: Original Mekotronics code

**Structure**:
\`\`\`
r58/
├── admin_api/             # Admin API (FastAPI)
├── opencast_agent/        # Opencast integration
├── config/                # Configuration
├── scripts/               # Helper scripts
├── ui/                    # Web UI
└── .venv/                 # Python venv
\`\`\`

**Status**: Legacy code, admin_api still running

**Note**: Consider whether this is still needed. Main preke-recorder provides similar functionality.

### /opt/r58-fleet-agent

**Purpose**: Fleet management agent (CURRENT VERSION)

**Contents**:
- fleet_agent.py - WebSocket client for fleet API

**Improvements over /opt/fleet-agent**:
- 10-second heartbeat (vs 30-second)
- Log rotation (10MB, keeps 3 files)
- Quieter logging (debug messages reduced)
- Better error handling

**Status**: Active, connects to wss://fleet.r58.itagenten.no/ws

**Logs**: /var/log/r58-fleet-agent/fleet-agent.log

### /opt/fleet-agent

**Purpose**: OLDER version of fleet agent

**Contents**:
- fleet_agent.py (older version of r58-fleet-agent)

**Differences from /opt/r58-fleet-agent**:
- 30-second heartbeat (vs 10-second)
- Basic logging (no rotation)
- More verbose logging

**Status**: Obsolete - newer version at /opt/r58-fleet-agent is in use

**Note**: This is a backup/older copy. The active service uses /opt/r58-fleet-agent/

## Configuration Files

### System-Wide

- /etc/r58/.env - R58 environment variables
- /etc/systemd/system/*.service - Service definitions

### Application-Specific

- /opt/preke-r58-recorder/config.yml
- /opt/mediamtx/mediamtx.yml
- /opt/frp/frpc.toml
- /opt/vdo-signaling/vdo-server.js

### SSL Certificates

- /opt/vdo-signaling/cert.pem - Self-signed for local HTTPS
- /opt/vdo-signaling/key.pem - Private key

## Data Directories

- /opt/preke-r58-recorder/data/ - Runtime data
- /opt/preke-r58-recorder/data/sessions/ - Session data
- /opt/preke-r58-recorder/recordings/ - Recorded videos
- /opt/preke-r58-recorder/presentations/ - Presentation files
- /opt/preke-r58-recorder/scenes/ - Scene configurations

## Logs

- /var/log/frpc.log - FRP client logs
- /var/log/r58-fleet-agent/ - Fleet agent logs
- journalctl -u <service> - Systemd service logs
        `,
        keyPoints: [
            'All code in /opt/ directory',
            'Custom code: preke-recorder, vdo-signaling, fleet-agent',
            'Third-party: vdo.ninja, raspberry_ninja, frp',
            'Legacy: /opt/r58 (Mekotronics)'
        ],
        tags: ['directory', 'structure', 'filesystem', 'organization']
    },

    'fleet-management': {
        title: 'Fleet Management',
        simple: `
The R58 has a fleet management agent that connects to a central server.

**What it does**:
- Reports device status (CPU, memory, disk)
- Allows remote commands
- Enables software updates
- Sends heartbeat every 10 seconds

**Security**: The agent can execute commands remotely, so ensure the fleet API is secured.
        `,
        technical: `
**r58-fleet-agent.service**

**Purpose**: Remote fleet management and monitoring

**Architecture**:
\`\`\`
R58 Device                    Fleet API Server
    │                              │
    │  WebSocket (WSS)             │
    ├──────────────────────────────>│
    │  Heartbeat (every 10s)       │
    │  Device metrics              │
    │                              │
    │<─────────────────────────────┤
    │  Commands (execute, update)  │
\`\`\`

**Configuration**:
- Code: /opt/r58-fleet-agent/fleet_agent.py
- Fleet API: wss://fleet.r58.itagenten.no/ws
- Device ID: From DEVICE_ID env var
- Heartbeat: 10 seconds
- Reconnect: 5 seconds delay

**Environment Variables**:
- FLEET_API_URL - Fleet API WebSocket URL
- DEVICE_ID - Unique device identifier
- HEARTBEAT_INTERVAL - Seconds between heartbeats
- PROJECT_DIR - Path to preke-r58-recorder
        `,
        content: `
## Features

### Device Monitoring

The agent reports:
- CPU usage (per core and total)
- Memory usage (used/total)
- Disk usage (used/total)
- Network interfaces
- Running services
- System uptime

### Remote Commands

The fleet API can send commands:
- Execute shell commands
- Update software (git pull + restart)
- Restart services
- Check service status
- Get system info

### Software Updates

Update process:
1. Fleet API sends update command
2. Agent runs: cd /opt/preke-r58-recorder && git pull
3. Agent restarts preke-recorder service
4. Agent reports update status

### Logging

Logs are written to:
- /var/log/r58-fleet-agent/fleet-agent.log
- Rotated at 10MB (keeps 3 old files)
- Also logs to systemd journal

## Security Considerations

**Risk**: Agent can execute arbitrary commands

**Mitigations**:
- WebSocket connection uses WSS (encrypted)
- Fleet API should require authentication
- Commands are logged
- Agent runs as root (necessary for service management)

**Recommendations**:
1. Ensure fleet API has strong authentication
2. Use VPN or firewall to restrict fleet API access
3. Monitor agent logs for suspicious commands
4. Consider disabling if not needed

## Managing Fleet Agent

### Check Status

\`\`\`bash
sudo systemctl status r58-fleet-agent
\`\`\`

### View Logs

\`\`\`bash
sudo journalctl -u r58-fleet-agent -f
\`\`\`

Or:

\`\`\`bash
tail -f /var/log/r58-fleet-agent/fleet-agent.log
\`\`\`

### Restart Agent

\`\`\`bash
sudo systemctl restart r58-fleet-agent
\`\`\`

### Disable Agent

If you don't need fleet management:

\`\`\`bash
sudo systemctl stop r58-fleet-agent
sudo systemctl disable r58-fleet-agent
\`\`\`

### Configure Agent

Edit service file:

\`\`\`bash
sudo nano /etc/systemd/system/r58-fleet-agent.service
\`\`\`

Add environment variables:

\`\`\`ini
[Service]
Environment="DEVICE_ID=my-r58-device"
Environment="FLEET_API_URL=wss://fleet.example.com/ws"
Environment="HEARTBEAT_INTERVAL=30"
\`\`\`

Reload and restart:

\`\`\`bash
sudo systemctl daemon-reload
sudo systemctl restart r58-fleet-agent
\`\`\`

## Fleet API Integration

If you're building a fleet management system:

### WebSocket Protocol

Agent sends heartbeat:
\`\`\`json
{
  "type": "heartbeat",
  "device_id": "r58-001",
  "timestamp": "2025-12-26T12:00:00Z",
  "metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "disk_percent": 38.5,
    "uptime_seconds": 86400
  }
}
\`\`\`

Server sends command:
\`\`\`json
{
  "type": "execute",
  "command": "systemctl restart preke-recorder"
}
\`\`\`

Agent responds:
\`\`\`json
{
  "type": "result",
  "success": true,
  "output": "Service restarted successfully"
}
\`\`\`

## Troubleshooting

### Agent Not Connecting

Check fleet API URL:
\`\`\`bash
grep FLEET_API_URL /etc/systemd/system/r58-fleet-agent.service
\`\`\`

Test WebSocket connection:
\`\`\`bash
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  https://fleet.r58.itagenten.no/ws
\`\`\`

### High CPU Usage

Check heartbeat interval:
\`\`\`bash
grep HEARTBEAT_INTERVAL /etc/systemd/system/r58-fleet-agent.service
\`\`\`

Consider increasing to 30 or 60 seconds.

### Logs Filling Disk

Logs are rotated at 10MB (3 files max = 40MB total).

If logs are too large, check for:
- Frequent reconnections
- Error messages repeating
- Excessive command execution

## Alternative: Disable Fleet Management

If you don't need central management:

1. Stop and disable service
2. Remove from startup
3. Optionally remove code

\`\`\`bash
sudo systemctl stop r58-fleet-agent
sudo systemctl disable r58-fleet-agent
sudo rm /etc/systemd/system/r58-fleet-agent.service
sudo systemctl daemon-reload
\`\`\`

The R58 will continue to work normally without fleet management.
        `,
        keyPoints: [
            'Fleet agent connects to central management server',
            'Reports device metrics every 10 seconds',
            'Can execute remote commands and updates',
            'Can be disabled if not needed'
        ],
        tags: ['fleet', 'management', 'monitoring', 'remote']
    },

    'legacy-components': {
        title: 'Legacy Components',
        simple: `
The R58 has some legacy code from Mekotronics (the hardware manufacturer).

**Legacy Services**:
- r58-admin-api - Old admin interface
- r58-opencast-agent - Opencast integration (disabled)

**Legacy Code**:
- /opt/r58 - Original Mekotronics code

These are not part of the main preke-recorder system but may still be running.
        `,
        technical: `
**Legacy Mekotronics Code**

When we received the R58 hardware, it came with pre-installed software from Mekotronics. We built the preke-recorder system on top of this, but some legacy components remain.

**What's Legacy**:
- /opt/r58/ directory
- r58-admin-api.service
- r58-opencast-agent.service (disabled)

**What's Current**:
- /opt/preke-r58-recorder/ (our main application)
- All services we've documented

**Why Legacy Code Remains**:
- Some functionality may still be useful
- Removing it requires careful testing
- admin-api provides device detection
        `,
        content: `
## /opt/r58 Directory

**Source**: Mekotronics (hardware vendor)

**Structure**:
\`\`\`
r58/
├── admin_api/             # Admin API (still running)
│   ├── main.py           # FastAPI application
│   └── requirements.txt
├── opencast_agent/        # Opencast integration (unused)
├── config/                # Configuration files
├── scripts/               # Helper scripts
├── ui/                    # Web UI (unused)
├── systemd/               # Service files
├── docker-compose.yml     # Docker setup (unused)
└── .venv/                 # Python virtual environment
\`\`\`

## r58-admin-api.service

**Status**: Running on port 8088 (local only)

**Purpose**: Device management API

**Endpoints**:

GET /status - Service status
\`\`\`json
{
  "rtmp": {"0": "active", "1": "inactive", ...},
  "srt": {"0": "active", "1": "inactive", ...}
}
\`\`\`

GET /devices - List video devices
\`\`\`json
{
  "video": ["/dev/video0", "/dev/video1", ...]
}
\`\`\`

GET /encoders - Check available encoders
\`\`\`json
{
  "v4l2h264enc": true,
  "mpph264enc": true
}
\`\`\`

**Configuration**:
- Port: 8088 (from /etc/r58/.env)
- User: root
- WorkingDirectory: /opt/r58

**Should You Use It?**

Probably not. The main preke-recorder application provides:
- Better device detection
- More features
- Active development
- Better documentation

**Can You Remove It?**

Yes, but test first:
1. Stop service: sudo systemctl stop r58-admin-api
2. Test preke-recorder still works
3. If OK, disable: sudo systemctl disable r58-admin-api

## r58-opencast-agent.service

**Status**: Disabled (not running)

**Purpose**: Integration with Opencast video platform

**Why Disabled**: We don't use Opencast

**Can You Remove It?**

Yes:
\`\`\`bash
sudo rm /etc/systemd/system/r58-opencast-agent.service
sudo systemctl daemon-reload
\`\`\`

## Disabled Ninja Services

These were created during development but are now DEPRECATED:

- ninja-publish-cam0/1/2/3.service - P2P publishers (don't work through tunnels)
- ninja-receive-guest1.service - Guest receiver (old approach)
- ninja-receive-guest2.service - Guest receiver (old approach)
- ninja-rtmp-restream.service - RTMP test
- ninja-rtmp-test.service - RTMP test
- ninja-rtsp-restream.service - RTSP test

**DO NOT re-enable** ninja-publish services. Use MediaMTX WHEP mode instead.
- ninja-pipeline-test.service - Pipeline test

**Status**: All disabled

**Can You Remove Them?**

Yes:
\`\`\`bash
sudo rm /etc/systemd/system/ninja-*.service
sudo systemctl daemon-reload
\`\`\`

## cloudflared.service

**Purpose**: Old Cloudflare tunnel

**Status**: Disabled (replaced by FRP)

**History**: We initially tried Cloudflare Tunnel for remote access, but it didn't work well with WebRTC. We switched to FRP tunnel which works perfectly.

**Can You Remove It?**

Yes:
\`\`\`bash
sudo systemctl disable cloudflared
sudo rm /etc/systemd/system/cloudflared.service
sudo apt remove cloudflared  # If installed via apt
\`\`\`

## Cleanup Recommendations

**Safe to Remove**:
1. r58-opencast-agent.service
2. All ninja-*.service (disabled ones)
3. cloudflared.service
4. /opt/fleet-agent (if duplicate)

**Test Before Removing**:
1. r58-admin-api.service (stop and test first)
2. /opt/r58 directory (may have useful scripts)

**Keep**:
1. All active services
2. /opt/preke-r58-recorder
3. /opt/vdo.ninja, /opt/vdo-signaling
4. /opt/raspberry_ninja
5. /opt/mediamtx, /opt/frp

## Migration Path

If you want to fully migrate away from legacy code:

### Phase 1: Verify
1. Document what r58-admin-api provides
2. Verify preke-recorder has equivalent features
3. Test without r58-admin-api running

### Phase 2: Disable
1. Stop r58-admin-api service
2. Monitor for issues
3. Keep for 1-2 weeks as backup

### Phase 3: Remove
1. Disable service permanently
2. Archive /opt/r58 directory
3. Remove service file
4. Clean up systemd

### Commands

\`\`\`bash
# Phase 1: Test
sudo systemctl stop r58-admin-api
# ... test everything ...

# Phase 2: Disable
sudo systemctl disable r58-admin-api

# Phase 3: Remove (after testing period)
sudo rm /etc/systemd/system/r58-admin-api.service
sudo mv /opt/r58 /opt/r58.backup
sudo systemctl daemon-reload
\`\`\`

## Why We Keep Some Legacy Code

**Reasons**:
1. Device detection code is useful
2. Some scripts may be referenced
3. Safe to keep if not causing issues
4. Can remove later after thorough testing

**Not Reasons**:
- ❌ "Might need it someday" (document instead)
- ❌ "Too scared to remove" (test first)
- ❌ "Don't know what it does" (find out!)
        `,
        keyPoints: [
            'Legacy code from Mekotronics hardware vendor',
            'r58-admin-api still running but may not be needed',
            '9 disabled services can be removed',
            'Test before removing legacy components'
        ],
        tags: ['legacy', 'cleanup', 'mekotronics', 'maintenance']
    }
});

