# R58 System Services Documentation

This document describes all systemd services running on an R58 device, including their purpose, configuration, and troubleshooting.

## Core Services

### r58-api.service
**Status:** Active (Primary)
**Port:** 8000
**Purpose:** Main REST/WebSocket API for controlling the R58 device.

**Features:**
- FastAPI-based control plane
- Recording start/stop/status
- WebSocket real-time events
- VDO.ninja URL generation
- Device capabilities
- Health monitoring

**Service File:** `/etc/systemd/system/r58-api.service`

```ini
[Unit]
Description=R58 Control API
After=network.target r58-pipeline.service

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/preke-r58-recorder/packages/backend
ExecStart=/opt/preke-r58-recorder/venv/bin/uvicorn r58_api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Logs:** `journalctl -u r58-api -f`

---

### r58-pipeline.service
**Status:** Active (Primary)
**Socket:** `/run/r58/pipeline.sock`
**Purpose:** GStreamer pipeline manager for video capture and recording.

**Features:**
- Preview pipelines (WHEP streams to MediaMTX)
- Recording pipelines (MKV output)
- Watchdog for stall detection
- Event queue for WebSocket notifications

**Service File:** `/etc/systemd/system/r58-pipeline.service`

```ini
[Unit]
Description=R58 Pipeline Manager
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/preke-r58-recorder/packages/backend
ExecStart=/opt/preke-r58-recorder/venv/bin/python -m pipeline_manager
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**IPC Commands:**
- `status` - Get current mode
- `recording.start` - Start recording
- `recording.stop` - Stop recording
- `preview.start` - Start preview pipeline
- `preview.stop` - Stop preview pipeline
- `events.poll` - Get pending async events

**Logs:** `journalctl -u r58-pipeline -f`

---

### r58-mediamtx.service
**Status:** Active (Primary)
**Ports:** 8554 (RTSP), 8889 (WHEP), 8888 (HLS)
**Purpose:** Media streaming server for WebRTC/RTSP/HLS output.

**Features:**
- WHIP input from GStreamer pipelines
- WHEP output for browser previews
- RTSP output for local network access
- HLS output for compatibility

**Configuration:** `/opt/preke-r58-recorder/mediamtx.yml`

**Logs:** `journalctl -u r58-mediamtx -f`

---

## VDO.ninja Services

### vdo-signaling.service
**Status:** Active (Critical)
**Port:** 8443
**Purpose:** Custom WebSocket signaling server for VDO.ninja WebRTC.

**Description:**
This is a **custom implementation** of the VDO.ninja signaling server that runs locally on the R58. It handles WebRTC peer connection signaling between VDO.ninja participants.

**Features:**
- WebRTC signaling (offer/answer/ICE)
- Room management
- Peer tracking
- SSL/TLS support (self-signed cert)

**Configuration:**
- Location: `/opt/vdo-ninja/signaling-server/`
- SSL Cert: `/opt/vdo-ninja/certs/`
- Config: `/opt/vdo-ninja/config.json`

**Service File:** `/etc/systemd/system/vdo-signaling.service`

```ini
[Unit]
Description=VDO.ninja Signaling Server
After=network.target

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/vdo-ninja/signaling-server
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=5
Environment=PORT=8443
Environment=SSL_CERT=/opt/vdo-ninja/certs/cert.pem
Environment=SSL_KEY=/opt/vdo-ninja/certs/key.pem

[Install]
WantedBy=multi-user.target
```

**Logs:** `journalctl -u vdo-signaling -f`

**Troubleshooting:**
- If WebRTC connections fail, check SSL certificates are valid
- Verify port 8443 is open in firewall
- Check signaling server is binding to correct interface

---

### vdo-webapp.service
**Status:** Active
**Port:** 8080
**Purpose:** Serves the VDO.ninja web application locally.

**Description:**
Local copy of VDO.ninja web app configured to use the local signaling server.

**Service File:** `/etc/systemd/system/vdo-webapp.service`

```ini
[Unit]
Description=VDO.ninja Web App
After=network.target

[Service]
Type=simple
User=linaro
WorkingDirectory=/opt/vdo-ninja/webapp
ExecStart=/usr/bin/python3 -m http.server 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Remote Access Services

### frpc.service
**Status:** Active (Remote Access)
**Port:** N/A (outbound connection)
**Purpose:** FRP (Fast Reverse Proxy) client for remote access.

**Description:**
Establishes secure tunnel to FRP server for remote SSH and HTTP access.

**Configuration:** `/etc/frp/frpc.ini`

```ini
[common]
server_addr = 65.109.32.111
server_port = 7000
token = <secure_token>

[ssh]
type = tcp
local_ip = 127.0.0.1
local_port = 22
remote_port = 10022

[web]
type = http
local_port = 8000
custom_domains = r58-api.itagenten.no
```

**Logs:** `journalctl -u frpc -f`

---

## Legacy Services (Consider Removal)

### r58-admin-api.service
**Status:** Active (Legacy)
**Port:** 8088
**Purpose:** Legacy admin API from Mekotronics.

**Description:**
This is the original admin API that came with the R58 hardware from Mekotronics. It provides basic device control functionality but has been largely superseded by the new r58-api service.

**Features (Legacy):**
- System info
- Network configuration
- Reboot/shutdown
- Update mechanism (old)

**Location:** `/opt/r58/admin-api/`

**Recommendation:**
This service should be tested for removal. The new r58-api provides all necessary functionality. To test:

1. Stop the service: `sudo systemctl stop r58-admin-api`
2. Monitor for 1 week to ensure nothing breaks
3. If no issues, disable: `sudo systemctl disable r58-admin-api`
4. Archive the code: `tar -czvf /opt/r58-admin-api-backup.tar.gz /opt/r58/`

---

### r58-fleet-agent.service
**Status:** Active (Fleet Management)
**Purpose:** Fleet management agent for centralized control.

**Description:**
Agent that connects to the central fleet management server for:
- Device registration
- Heartbeat reporting (CPU, memory, disk, temperature)
- Remote command execution
- Software updates
- Support bundle collection

**Configuration:** `/etc/r58/.env`

```env
FLEET_SERVER_URL=https://fleet.r58.itagenten.no
DEVICE_ID=<unique-device-id>
HEARTBEAT_INTERVAL=30
```

**Features:**
- Connects to fleet server via HTTPS
- Reports system metrics every 30 seconds
- Polls for pending commands
- Executes: restart, update, config-reload, bundle
- Sends software version and capabilities

**Service File:** `/etc/systemd/system/r58-fleet-agent.service`

```ini
[Unit]
Description=R58 Fleet Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/preke-r58-recorder/fleet
ExecStart=/opt/preke-r58-recorder/venv/bin/python -m fleet_agent
Restart=always
RestartSec=30
Environment=FLEET_CONFIG=/etc/r58/fleet.conf

[Install]
WantedBy=multi-user.target
```

**Logs:** `journalctl -u r58-fleet-agent -f`

**Heartbeat Protocol:**
```json
{
  "device_id": "r58-001",
  "timestamp": "2025-12-29T10:00:00Z",
  "version": "2.0.0",
  "status": "online",
  "metrics": {
    "cpu_percent": 25.5,
    "mem_percent": 45.2,
    "disk_free_gb": 120.5,
    "temperature_c": 42.0
  },
  "flags": {
    "recording": false,
    "mixer": false
  }
}
```

---

## Camera Publisher Services

### ninja-publish-cam2.service
**Status:** Active (if cam2 enabled)
**Purpose:** Publishes cam2 WHEP stream to VDO.ninja room.

**Configuration:** Managed by deployment scripts.

### ninja-publish-cam3.service
**Status:** Active (if cam3 enabled)
**Purpose:** Publishes cam3 WHEP stream to VDO.ninja room.

---

## Service Dependencies

```
┌─────────────────────┐
│   r58-pipeline      │──────┐
│   (GStreamer)       │      │
└─────────────────────┘      │ IPC
                             ▼
┌─────────────────────┐   ┌─────────────────────┐
│   r58-mediamtx      │◄──│     r58-api         │
│   (WHEP/RTSP)       │   │   (REST/WebSocket)  │
└─────────────────────┘   └─────────────────────┘
                                   │
                                   │ HTTP
                                   ▼
                         ┌─────────────────────┐
                         │   r58-fleet-agent   │
                         │   (Fleet Connect)   │
                         └─────────────────────┘
```

---

## Quick Reference

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| r58-api | 8000 | Active | Main API |
| r58-pipeline | socket | Active | GStreamer |
| r58-mediamtx | 8889 | Active | WHEP/RTSP |
| vdo-signaling | 8443 | Active | WebRTC signaling |
| vdo-webapp | 8080 | Active | VDO.ninja UI |
| frpc | N/A | Active | Remote access |
| r58-fleet-agent | N/A | Active | Fleet management |
| r58-admin-api | 8088 | Legacy | Consider removal |

---

## Troubleshooting

### All services down
```bash
# Check systemd status
sudo systemctl status r58-*.service vdo-*.service frpc.service

# Restart all core services
sudo systemctl restart r58-pipeline r58-api r58-mediamtx
```

### No video preview
```bash
# Check MediaMTX
curl http://localhost:8889/v3/config/paths/list

# Check pipeline status
sudo journalctl -u r58-pipeline -n 50

# Check if camera device exists
v4l2-ctl --list-devices
```

### WebSocket not connecting
```bash
# Test WebSocket endpoint
websocat ws://localhost:8000/api/v1/ws

# Check API logs
sudo journalctl -u r58-api -f
```

### VDO.ninja not working
```bash
# Check signaling server
sudo journalctl -u vdo-signaling -f

# Check SSL certificate
openssl s_client -connect localhost:8443

# Test signaling connection
curl -k https://localhost:8443/health
```

