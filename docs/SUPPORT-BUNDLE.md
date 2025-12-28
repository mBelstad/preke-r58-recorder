# Support Bundle Guide

> Understanding what data is collected, how to export it, and privacy considerations.

## Table of Contents

1. [What is a Support Bundle?](#what-is-a-support-bundle)
2. [Data Collected](#data-collected)
3. [How to Export](#how-to-export)
4. [Privacy Considerations](#privacy-considerations)
5. [Using the Bundle for Debugging](#using-the-bundle-for-debugging)

---

## What is a Support Bundle?

A support bundle is a diagnostic archive containing system information, logs, configuration, and metrics. It helps:

- **Diagnose issues** without direct device access
- **Reproduce problems** with accurate state information
- **Speed up support** by providing context upfront

**Bundle Contents Overview**:

```
support-bundle-20241228-103045.zip
├── system/
│   ├── info.json            # Device info, versions
│   ├── services.json        # Service status
│   └── resources.json       # CPU, memory, disk
├── logs/
│   ├── r58-api.log          # API server logs
│   ├── r58-pipeline.log     # Pipeline manager logs
│   └── mediamtx.log         # WebRTC server logs
├── config/
│   ├── settings.json        # App settings (sanitized)
│   └── capabilities.json    # Device capabilities
├── state/
│   ├── pipeline_state.json  # Current pipeline state
│   └── sessions.json        # Recent sessions (metadata only)
└── metrics/
    ├── current.json         # Current metrics snapshot
    └── history.json         # Recent metrics history
```

---

## Data Collected

### System Information

| Data | Description | Example |
|------|-------------|---------|
| Device ID | Unique device identifier | `r58-prod-001` |
| API Version | Software version | `2.0.0` |
| OS Version | Operating system | `Debian 12` |
| Uptime | Time since last restart | `4 days, 3:15:22` |
| Hostname | Network hostname | `r58.local` |

### Service Status

| Service | Information Collected |
|---------|----------------------|
| r58-api | Running state, restart count, memory usage |
| r58-pipeline | Active state, current mode |
| mediamtx | Stream status, connected clients |

### Resource Metrics

| Metric | Description |
|--------|-------------|
| CPU Usage | Current and average CPU utilization |
| Memory Usage | Used/total RAM |
| Disk Usage | Free space on recordings volume |
| Network | Interface status, IP addresses |
| Temperature | CPU/GPU temperature (if available) |

### Logs (Last 24 Hours)

| Log Source | Content |
|------------|---------|
| API Logs | HTTP requests, errors, WebSocket events |
| Pipeline Logs | Recording operations, encoder status |
| MediaMTX Logs | Stream connections, WHEP/WebRTC events |
| System Logs | Service starts/stops, kernel messages |

### Configuration (Sanitized)

| Setting | Included | Sanitized |
|---------|----------|-----------|
| Device ID | Yes | No |
| API Port | Yes | No |
| Enabled Inputs | Yes | No |
| JWT Secret | **No** | Removed |
| Passwords | **No** | Removed |
| API Keys | **No** | Removed |

### Session Metadata

| Data | Included | Example |
|------|----------|---------|
| Session ID | Yes | `abc123` |
| Start/End Time | Yes | Timestamps |
| Input Count | Yes | `2` |
| Duration | Yes | `3600s` |
| File Paths | Partial | Directory only |
| **File Contents** | **No** | Not included |

---

## How to Export

### Via Web Interface

1. Navigate to **Admin** > **Support**
2. Click **"Generate Support Bundle"**
3. Wait for generation (may take 30 seconds)
4. Download the ZIP file

### Via API

```bash
# Generate and download bundle
curl -o support-bundle.zip http://localhost:8000/api/v1/support/bundle

# Generate with custom time range
curl -o support-bundle.zip \
  "http://localhost:8000/api/v1/support/bundle?hours=48"
```

### Via Command Line (On Device)

```bash
# Quick bundle
./scripts/generate-support-bundle.sh

# With extended logs
./scripts/generate-support-bundle.sh --hours=72

# Output to specific location
./scripts/generate-support-bundle.sh -o /tmp/my-bundle.zip
```

### Bundle Generation Script

```bash
#!/bin/bash
# scripts/generate-support-bundle.sh

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BUNDLE_DIR="/tmp/support-bundle-$TIMESTAMP"
OUTPUT="${1:-support-bundle-$TIMESTAMP.zip}"

mkdir -p "$BUNDLE_DIR"/{system,logs,config,state,metrics}

# System info
echo '{"device_id": "'$R58_DEVICE_ID'", "version": "2.0.0", "timestamp": "'$(date -Is)'"}' \
  > "$BUNDLE_DIR/system/info.json"

# Service status
systemctl status r58-api r58-pipeline mediamtx --no-pager > "$BUNDLE_DIR/system/services.txt"

# Logs (last 24h)
journalctl -u r58-api --since "24 hours ago" --no-pager > "$BUNDLE_DIR/logs/r58-api.log"
journalctl -u r58-pipeline --since "24 hours ago" --no-pager > "$BUNDLE_DIR/logs/r58-pipeline.log"

# Config (sanitized)
curl -s http://localhost:8000/api/v1/capabilities > "$BUNDLE_DIR/config/capabilities.json"

# Current state
cp /var/lib/r58/pipeline_state.json "$BUNDLE_DIR/state/" 2>/dev/null

# Metrics
curl -s http://localhost:8000/api/v1/metrics > "$BUNDLE_DIR/metrics/current.json"

# Create ZIP
cd /tmp && zip -r "$OUTPUT" "support-bundle-$TIMESTAMP"

echo "Bundle created: $OUTPUT"
```

---

## Privacy Considerations

### What is NOT Included

| Data Type | Reason |
|-----------|--------|
| JWT Secret | Security sensitive |
| Passwords | Security sensitive |
| API Keys | Security sensitive |
| Recording Files | Privacy, file size |
| Video Content | Privacy |
| User Data | Privacy |
| Network Passwords | Security |

### Data Sanitization

The bundle generator automatically sanitizes:

```python
SANITIZED_FIELDS = [
    "jwt_secret",
    "password",
    "api_key",
    "secret",
    "token",
    "credential",
]

def sanitize_config(config: dict) -> dict:
    for key in config:
        if any(s in key.lower() for s in SANITIZED_FIELDS):
            config[key] = "[REDACTED]"
    return config
```

### Before Sharing

1. **Review the bundle** before sending to support
2. **Check logs** for any accidentally logged sensitive data
3. **Redact** any visible passwords or tokens
4. **Use secure transfer** (encrypted email, HTTPS upload)

### Data Retention

- Support bundles are **not stored permanently** on device
- Generated bundles are deleted after download
- Sent bundles are subject to support provider's retention policy

### GDPR/Privacy Compliance

- No personal data is collected in bundles
- Device IDs are pseudonymous
- Logs may contain IP addresses (operational necessity)
- Users can request bundle contents before sharing

---

## Using the Bundle for Debugging

### Analyzing Locally

```bash
# Extract bundle
unzip support-bundle-20241228.zip
cd support-bundle-20241228

# Check system info
cat system/info.json | jq

# Check service status
cat system/services.txt

# Search logs for errors
grep -i error logs/*.log

# Check resource usage
cat metrics/current.json | jq
```

### Common Log Patterns

**Recording Issues**:
```bash
grep -E "(start_recording|stop_recording|error)" logs/r58-pipeline.log
```

**API Errors**:
```bash
grep -E "(500|400|ERROR)" logs/r58-api.log
```

**WebSocket Issues**:
```bash
grep -E "(websocket|disconnect|reconnect)" logs/r58-api.log
```

**MediaMTX Issues**:
```bash
grep -E "(error|failed|timeout)" logs/mediamtx.log
```

### Key Files to Check

| Issue | Check |
|-------|-------|
| Recording stuck | `state/pipeline_state.json` |
| Service crashes | `logs/r58-*.log` |
| Out of storage | `metrics/current.json` |
| Network issues | `system/info.json` |

### Creating a Support Request

When reporting an issue, include:

1. **Bundle file** (attached or uploaded)
2. **Steps to reproduce** the issue
3. **Expected vs actual behavior**
4. **Time of occurrence** (for log correlation)
5. **Any error messages** shown in UI

Example:

```
Subject: Recording fails to start - Device r58-prod-001

## Issue
Recording fails to start with "Insufficient disk space" error even though 
100GB is available.

## Steps to Reproduce
1. Navigate to Recorder
2. Connect HDMI to cam1
3. Click Start Recording
4. See error message

## Time of Occurrence
2024-12-28 10:30:00 UTC

## Bundle
Attached: support-bundle-20241228-103045.zip
```

---

## API Reference

### GET /api/v1/support/bundle

Generate and download a support bundle.

**Parameters**:

| Name | Type | Default | Description |
|------|------|---------|-------------|
| hours | int | 24 | Hours of logs to include |
| include_metrics | bool | true | Include metrics history |
| include_sessions | bool | true | Include session metadata |

**Example**:

```bash
# Default bundle (24h)
curl -o bundle.zip http://localhost:8000/api/v1/support/bundle

# Extended logs (72h)
curl -o bundle.zip "http://localhost:8000/api/v1/support/bundle?hours=72"

# Minimal bundle (no metrics history)
curl -o bundle.zip "http://localhost:8000/api/v1/support/bundle?include_metrics=false"
```

**Response**: ZIP file download

---

## Quick Reference

### Generate Bundle

**Web**: Admin > Support > Generate Bundle

**CLI**: `curl -o bundle.zip http://localhost:8000/api/v1/support/bundle`

**Script**: `./scripts/generate-support-bundle.sh`

### Bundle Contents

- System info and service status
- Logs (last 24 hours)
- Configuration (sanitized)
- Metrics and state

### Privacy Checklist

- [ ] No passwords or secrets
- [ ] No video content
- [ ] No personal data
- [ ] Logs reviewed for sensitive info

