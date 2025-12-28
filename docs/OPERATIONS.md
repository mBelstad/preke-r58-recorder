# Operations Guide

> Deployment, services, monitoring, and maintenance for R58 devices.

## Table of Contents

1. [Deployment](#deployment)
2. [Services Management](#services-management)
3. [Logs & Monitoring](#logs--monitoring)
4. [Upgrades](#upgrades)
5. [Rollback](#rollback)
6. [Backup & Recovery](#backup--recovery)
7. [Troubleshooting](#troubleshooting)

---

## Deployment

### Prerequisites

- R58 device with Debian-based OS
- SSH access configured
- Git installed on device
- Python 3.9+ and Node.js 20+ installed

### Initial Setup (First-Time)

```bash
# 1. SSH to R58 device
./connect-r58-frp.sh

# 2. Create directory structure
sudo mkdir -p /opt/r58 /var/lib/r58 /opt/r58/recordings
sudo chown -R $USER:$USER /opt/r58 /var/lib/r58

# 3. Clone repository
cd /opt/r58
git clone https://github.com/your-org/preke-r58-recorder.git .

# 4. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -e packages/backend

# 5. Setup frontend
cd packages/frontend
npm ci
npm run build

# 6. Create environment file
sudo mkdir -p /etc/r58
sudo tee /etc/r58/r58.env << 'EOF'
R58_JWT_SECRET=generate-a-secure-secret-here
R58_DEVICE_ID=r58-production-001
R58_DEBUG=false
R58_VDONINJA_ENABLED=true
R58_FLEET_ENABLED=false
EOF

# 7. Install systemd services
sudo cp services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable r58-api r58-pipeline mediamtx

# 8. Start services
sudo systemctl start mediamtx
sudo systemctl start r58-pipeline
sudo systemctl start r58-api
```

### Automated Deployment

From your development machine:

```bash
# Simple deploy script
./deploy-simple.sh

# Or manually:
./connect-r58-frp.sh << 'EOF'
cd /opt/r58
git pull origin main
source venv/bin/activate
pip install -e packages/backend
cd packages/frontend && npm ci && npm run build
sudo systemctl restart r58-api r58-pipeline
EOF
```

### Docker Deployment

```bash
# Build images
docker build -f docker/Dockerfile.api -t r58-api:latest packages/backend
docker build -f docker/Dockerfile.frontend -t r58-frontend:latest packages/frontend

# Run with docker-compose
docker compose -f docker/docker-compose.production.yml up -d
```

---

## Services Management

### Service Overview

| Service | Purpose | Port | User |
|---------|---------|------|------|
| `r58-api` | Control API (FastAPI) | 8000 | r58 |
| `r58-pipeline` | Pipeline Manager (GStreamer) | Unix socket | r58 |
| `mediamtx` | WebRTC/WHEP streams | 8889, 8554, 9997 | root |

### Common Commands

```bash
# Check status
sudo systemctl status r58-api r58-pipeline mediamtx

# Start/stop/restart
sudo systemctl start r58-api
sudo systemctl stop r58-api
sudo systemctl restart r58-api

# Enable/disable on boot
sudo systemctl enable r58-api
sudo systemctl disable r58-api

# View service file
sudo systemctl cat r58-api
```

### Service Configuration

**r58-api.service**
```ini
[Unit]
Description=R58 Control API
After=network.target r58-pipeline.service
Wants=r58-pipeline.service

[Service]
Type=simple
User=r58
Group=r58
WorkingDirectory=/opt/r58
ExecStart=/opt/r58/venv/bin/uvicorn r58_api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=R58_JWT_SECRET=change-this
Environment=PYTHONPATH=/opt/r58/packages/backend

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/r58 /opt/r58/recordings

[Install]
WantedBy=multi-user.target
```

### Modifying Service Configuration

```bash
# Edit service file
sudo systemctl edit r58-api --full

# Or create override
sudo systemctl edit r58-api
# Add overrides, e.g.:
# [Service]
# Environment="R58_DEBUG=true"

# Reload after changes
sudo systemctl daemon-reload
sudo systemctl restart r58-api
```

---

## Logs & Monitoring

### Viewing Logs

```bash
# Real-time logs
sudo journalctl -u r58-api -f
sudo journalctl -u r58-pipeline -f
sudo journalctl -u mediamtx -f

# Last 100 lines
sudo journalctl -u r58-api -n 100

# Logs from last hour
sudo journalctl -u r58-api --since "1 hour ago"

# Logs from specific time
sudo journalctl -u r58-api --since "2024-12-28 10:00" --until "2024-12-28 12:00"

# All services together
sudo journalctl -u r58-api -u r58-pipeline -u mediamtx -f

# Export to file
sudo journalctl -u r58-api --since today > api-logs.txt
```

### Log Levels

Set via environment variable:

```bash
# In /etc/r58/r58.env
R58_DEBUG=true  # Enables debug logging
```

Or temporarily:

```bash
sudo systemctl stop r58-api
R58_DEBUG=true /opt/r58/venv/bin/uvicorn r58_api.main:app --host 0.0.0.0 --port 8000
```

### Health Monitoring

```bash
# Simple health check
curl http://localhost:8000/api/v1/health

# Detailed health with service status
curl http://localhost:8000/api/v1/health/detailed | jq

# Metrics snapshot
curl http://localhost:8000/api/v1/metrics | jq
```

### Setting Up Alerts

Example with systemd:

```bash
# Create health check timer
sudo tee /etc/systemd/system/r58-health-check.service << 'EOF'
[Unit]
Description=R58 Health Check

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'curl -sf http://localhost:8000/api/v1/health || systemctl restart r58-api'
EOF

sudo tee /etc/systemd/system/r58-health-check.timer << 'EOF'
[Unit]
Description=R58 Health Check Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

sudo systemctl enable --now r58-health-check.timer
```

---

## Upgrades

### Standard Upgrade Procedure

```bash
# 1. Check current version
curl http://localhost:8000/api/v1/health | jq .version

# 2. Create backup
./scripts/backup.sh

# 3. Pull latest code
cd /opt/r58
git fetch origin
git checkout main
git pull

# 4. Update backend dependencies
source venv/bin/activate
pip install -e packages/backend

# 5. Update frontend
cd packages/frontend
npm ci
npm run build

# 6. Restart services
sudo systemctl restart r58-api r58-pipeline

# 7. Verify
curl http://localhost:8000/api/v1/health
./scripts/smoke-test.sh
```

### Blue-Green Deployment (Advanced)

```bash
# 1. Deploy to alternate port
R58_API_PORT=8001 /opt/r58/venv/bin/uvicorn r58_api.main:app --port 8001 &

# 2. Test new version
curl http://localhost:8001/api/v1/health

# 3. Switch traffic (update nginx/load balancer)

# 4. Stop old version
sudo systemctl stop r58-api

# 5. Update systemd to use new version
sudo systemctl start r58-api
```

### Database Migrations

```bash
# Check for pending migrations
cd packages/backend
python -c "from r58_api.db.database import init_db; init_db()"

# Backup database before migration
cp /var/lib/r58/r58.db /var/lib/r58/r58.db.backup
```

---

## Rollback

### Quick Rollback

```bash
# 1. Find previous commit
git log --oneline -10

# 2. Rollback to specific commit
git checkout abc1234

# 3. Reinstall and restart
source venv/bin/activate
pip install -e packages/backend
cd packages/frontend && npm ci && npm run build
sudo systemctl restart r58-api r58-pipeline
```

### Rollback with Backup

```bash
# 1. Restore from backup
./scripts/restore.sh /path/to/backup.tar.gz

# 2. Restart services
sudo systemctl restart r58-api r58-pipeline mediamtx
```

### Emergency Rollback

If services won't start:

```bash
# 1. Check logs for error
sudo journalctl -u r58-api -n 50

# 2. Restore previous known-good version
cd /opt/r58
git reflog  # Find last working commit
git checkout HEAD@{1}

# 3. Restart
sudo systemctl restart r58-api
```

---

## Backup & Recovery

### What to Backup

| Path | Description | Frequency |
|------|-------------|-----------|
| `/var/lib/r58/r58.db` | Database (sessions, users) | Daily |
| `/etc/r58/r58.env` | Configuration | On change |
| `/opt/r58/recordings/` | Recording files | Per policy |
| `/var/lib/r58/pipeline_state.json` | Pipeline state | Before upgrade |

### Backup Script

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/opt/r58/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/r58-backup-$TIMESTAMP.tar.gz"

mkdir -p "$BACKUP_DIR"

tar -czf "$BACKUP_FILE" \
  /var/lib/r58/r58.db \
  /etc/r58/r58.env \
  /var/lib/r58/pipeline_state.json \
  2>/dev/null

echo "Backup created: $BACKUP_FILE"

# Keep only last 7 backups
ls -t "$BACKUP_DIR"/r58-backup-*.tar.gz | tail -n +8 | xargs -r rm
```

### Restore Script

```bash
#!/bin/bash
# scripts/restore.sh

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: restore.sh <backup-file>"
  exit 1
fi

# Stop services
sudo systemctl stop r58-api r58-pipeline

# Restore
tar -xzf "$BACKUP_FILE" -C /

# Start services
sudo systemctl start r58-pipeline r58-api

echo "Restored from: $BACKUP_FILE"
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check status and logs
sudo systemctl status r58-api
sudo journalctl -u r58-api -n 50

# Common issues:
# 1. Port in use
sudo lsof -i :8000

# 2. Permission denied
sudo chown -R r58:r58 /opt/r58 /var/lib/r58

# 3. Python import error
source /opt/r58/venv/bin/activate
python -c "from r58_api.main import app"

# 4. Missing environment file
cat /etc/r58/r58.env
```

### Recording Not Working

```bash
# Check pipeline manager
sudo systemctl status r58-pipeline
sudo journalctl -u r58-pipeline -n 50

# Check IPC socket
ls -la /run/r58/pipeline.sock

# Check for stuck recordings
cat /var/lib/r58/pipeline_state.json

# Reset pipeline state (caution!)
sudo systemctl stop r58-pipeline
rm /var/lib/r58/pipeline_state.json
sudo systemctl start r58-pipeline
```

### WebRTC/WHEP Not Working

```bash
# Check MediaMTX
sudo systemctl status mediamtx
curl http://localhost:9997/v3/paths/list

# Check if streams are active
curl http://localhost:8889/cam1/whep -v

# Restart MediaMTX
sudo systemctl restart mediamtx
```

### High CPU/Memory

```bash
# Check resource usage
htop
ps aux | grep python

# Check for runaway recordings
ls -la /opt/r58/recordings/

# Check disk space
df -h /opt/r58/recordings

# Force garbage collection (if API is running)
curl -X POST http://localhost:8000/api/v1/debug/gc
```

### Network Issues

```bash
# Check if API is listening
ss -tlnp | grep 8000

# Check firewall
sudo ufw status

# Test from another machine
curl http://r58.local:8000/api/v1/health
```

---

## Quick Reference

### Service Commands

```bash
sudo systemctl status r58-api        # Check status
sudo systemctl restart r58-api       # Restart
sudo journalctl -u r58-api -f        # Follow logs
```

### Health Checks

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/detailed | jq
```

### Emergency Contacts

- **On-call**: [Team Contact]
- **Escalation**: [Manager Contact]
- **Vendor Support**: [Hardware Vendor]

