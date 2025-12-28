# R58 Fleet Management

This document describes the self-hosted fleet management system for R58 devices.

## Overview

The fleet management system provides:
- **Device registry** for tracking all R58 devices
- **Real-time status** via heartbeats
- **Remote commands** for updates, restarts, and diagnostics
- **Support bundle collection** for troubleshooting
- **Multi-tenant access** with role-based permissions

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Fleet Management Server                      │
│                    (Self-hosted, PostgreSQL)                     │
├─────────────────────────────────────────────────────────────────┤
│  API Endpoints          │  Background Workers                   │
│  - /devices             │  - Heartbeat monitor                  │
│  - /commands            │  - Alert dispatcher                   │
│  - /releases            │  - Bundle processor                   │
│  - /users               │  - Metrics aggregator                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS + mTLS
                              │
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  R58 Device  │  │  R58 Device  │  │  R58 Device  │
│  Agent       │  │  Agent       │  │  Agent       │
└──────────────┘  └──────────────┘  └──────────────┘
```

## Quick Start

### 1. Start Fleet Server

```bash
cd fleet/

# Install dependencies
pip install -r requirements.txt

# Set up database
createdb fleet
psql fleet < migrations/001_initial.sql

# Configure
cp .env.example .env
# Edit .env with your settings

# Run server
uvicorn fleet.main:app --host 0.0.0.0 --port 8180
```

### 2. Register a Device

```bash
curl -X POST https://fleet.r58.itagenten.no/api/v1/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "r58-studio-001",
    "name": "Studio Main",
    "platform": "linux",
    "arch": "arm64"
  }'
```

Response:
```json
{
  "device_id": "r58-studio-001",
  "token": "abc123...your-device-token...xyz789",
  "fleet_url": "https://fleet.r58.itagenten.no"
}
```

**Important:** Save the token securely. It's only shown once.

### 3. Configure Device Agent

On the R58 device, create `/opt/r58-app/shared/config/fleet.conf`:

```bash
FLEET_ENABLED=true
FLEET_URL=https://fleet.r58.itagenten.no
DEVICE_ID=r58-studio-001
DEVICE_TOKEN=abc123...your-device-token...xyz789
HEARTBEAT_INTERVAL=60
COMMAND_POLL_INTERVAL=30
```

### 4. Start Device Agent

```bash
# Start the agent
sudo systemctl enable r58-fleet-agent
sudo systemctl start r58-fleet-agent

# Check status
sudo systemctl status r58-fleet-agent
journalctl -u r58-fleet-agent -f
```

## API Reference

### Authentication

**Users:** Bearer JWT token in Authorization header
**Devices:** X-Device-Token header

### Device Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /devices/register | Register new device |
| GET | /devices | List all devices |
| GET | /devices/{id} | Get device details |
| PATCH | /devices/{id} | Update device |
| DELETE | /devices/{id} | Decommission device |

### Heartbeat Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /devices/{id}/heartbeat | Send heartbeat |
| GET | /devices/{id}/heartbeats | Get history |
| GET | /devices/{id}/metrics | Get aggregated metrics |

### Command Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /devices/{id}/commands | Queue command |
| GET | /devices/{id}/commands | List device commands |
| PATCH | /commands/{id} | Update command status |
| POST | /commands/{id}/cancel | Cancel command |

### Release Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /releases/latest | Get latest release |
| GET | /releases | List all releases |
| POST | /releases | Upload new release |
| POST | /releases/{v}/publish | Publish release |

## Command Types

### Update

Trigger a software update on the device:

```json
{
  "type": "update",
  "payload": {
    "version": "1.1.0",
    "force": false
  },
  "priority": 1
}
```

### Reboot

Reboot the device:

```json
{
  "type": "reboot",
  "payload": {
    "delay_seconds": 60
  }
}
```

### Restart Service

Restart a systemd service:

```json
{
  "type": "restart_service",
  "payload": {
    "service": "r58-api"
  }
}
```

### Support Bundle

Request a support bundle:

```json
{
  "type": "bundle",
  "payload": {
    "include_logs": true,
    "include_config": true,
    "include_recordings": false
  }
}
```

### Config Update

Update device configuration:

```json
{
  "type": "config",
  "payload": {
    "changes": {
      "HEARTBEAT_INTERVAL": "30"
    }
  }
}
```

## Heartbeat Protocol

Devices send heartbeats every 60 seconds:

```json
POST /api/v1/devices/{device_id}/heartbeat
{
  "ts": "2025-12-28T10:00:00Z",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "metrics": {
    "cpu_percent": 15.2,
    "mem_percent": 45.0,
    "disk_free_gb": 2.8,
    "temperature_c": 52.0
  },
  "status": {
    "recording_active": false,
    "mixer_active": true,
    "active_inputs": ["cam1", "cam2"],
    "degradation_level": 0
  },
  "errors": []
}
```

Response:
```json
{
  "ack": true,
  "commands_pending": 2,
  "target_version": "1.1.0",
  "server_time": "2025-12-28T10:00:01Z"
}
```

## User Roles

| Role | Devices | Commands | Users | Releases |
|------|---------|----------|-------|----------|
| viewer | read | read | - | - |
| operator | read, update | read, create | - | - |
| admin | full | full | full | upload |

## Database Schema

Key tables:
- `organizations` - Multi-tenant organizations
- `users` - User accounts with roles
- `devices` - Registered devices
- `heartbeats` - Time-series metrics (partitioned)
- `commands` - Remote command queue
- `releases` - Software releases
- `support_bundles` - Collected bundles
- `audit_log` - All actions logged

## Deployment

### Docker Compose

```yaml
version: '3.8'
services:
  fleet:
    build: ./fleet
    ports:
      - "8180:8180"
    environment:
      - FLEET_DATABASE_URL=postgresql://fleet:secret@db:5432/fleet
      - FLEET_JWT_SECRET=your-secret-here
    depends_on:
      - db
  
  db:
    image: postgres:16
    environment:
      - POSTGRES_USER=fleet
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=fleet
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

### Reverse Proxy (Traefik)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.fleet.rule=Host(`fleet.r58.itagenten.no`)"
  - "traefik.http.routers.fleet.tls=true"
  - "traefik.http.routers.fleet.tls.certresolver=letsencrypt"
```

## Security

### Device Authentication

- Each device has a unique 64-character token
- Token is hashed (SHA256) in database
- Tokens can be rotated via API

### Transport Security

- All communication over HTTPS
- Optional mTLS for high-security deployments
- Tokens never logged or exposed in responses

### Best Practices

1. Use strong JWT secrets in production
2. Enable rate limiting
3. Rotate device tokens periodically
4. Monitor audit logs for suspicious activity
5. Use separate database credentials per environment

## Troubleshooting

### Device not appearing in dashboard

1. Check agent is running: `systemctl status r58-fleet-agent`
2. Check config: `cat /opt/r58-app/shared/config/fleet.conf`
3. Check logs: `journalctl -u r58-fleet-agent -f`
4. Test connectivity: `curl -I https://fleet.r58.itagenten.no/health`

### Commands not executing

1. Check command status in dashboard
2. Verify device is online and polling
3. Check agent logs for errors
4. Ensure command hasn't expired

### High database disk usage

1. Heartbeats table grows quickly - partitions are auto-managed
2. Run cleanup: `SELECT mark_devices_offline(); SELECT expire_old_commands();`
3. Adjust retention period for heartbeats

