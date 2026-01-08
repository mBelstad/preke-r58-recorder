# R58 Debug Runbook

> **Version:** 1.0.0  
> **Last Updated:** January 5, 2026  
> **Audience:** Operators, Developers, Support

This runbook provides step-by-step procedures for diagnosing and resolving common issues with the R58 recording system.

---

## Quick Diagnostics

### One-Command System Check

```bash
# Run the diagnostics script (creates timestamped archive)
./scripts/collect-diagnostics.sh

# Or manually check everything:
curl -s http://localhost:8000/api/v1/health/detailed | jq
```

### Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `GET /api/v1/health` | Basic health | `{"status": "healthy"}` |
| `GET /api/v1/health/detailed` | Full health with services | All services "healthy" |
| `GET /api/v1/capabilities` | Device info | Device ID, inputs, features |
| `GET /api/v1/recorder/status` | Recording state | Current mode and session |
| `GET /api/v1/alerts` | Active alerts | List of warnings/errors |
| `GET /api/v1/degradation` | System load level | NORMAL, WARN, DEGRADE, CRITICAL |

---

## Log Management

### Log Locations

| Service | Log Location | Rotation |
|---------|-------------|----------|
| preke-recorder | `journalctl -u preke-recorder` | systemd (7 days) |
| mediamtx | `journalctl -u mediamtx` | systemd (7 days) |
| vdo-ninja | `journalctl -u vdo-ninja` | systemd (7 days) |
| frpc | `journalctl -u frpc` | systemd (7 days) |
| Application logs | `/var/log/r58/*.log` | logrotate (7 days) |

### Log Rotation Configuration

**Systemd journald** (automatic):
```bash
# View current settings
journalctl --disk-usage

# Configuration in /etc/systemd/journald.conf
SystemMaxUse=500M      # Max disk usage
SystemMaxFileSize=50M  # Max per file
MaxRetentionSec=7day   # Keep 7 days
```

**Application logs** (logrotate):
```bash
# Configuration installed at /etc/logrotate.d/r58
# Rotates daily, keeps 7 days, compresses old logs

# Test rotation (dry run)
sudo logrotate -d /etc/logrotate.d/r58

# Force rotation
sudo logrotate -f /etc/logrotate.d/r58
```

### Viewing Logs

```bash
# Recent logs (last 50 lines)
sudo journalctl -u preke-recorder -n 50

# Follow logs in real-time
sudo journalctl -u preke-recorder -f

# Logs from specific time
sudo journalctl -u preke-recorder --since "2026-01-05 10:00"

# Logs with specific priority (errors only)
sudo journalctl -u preke-recorder -p err

# Export logs to file
sudo journalctl -u preke-recorder --since today > /tmp/preke-logs.txt
```

### Clearing Old Logs

```bash
# Clear logs older than 3 days
sudo journalctl --vacuum-time=3d

# Limit journal size to 100MB
sudo journalctl --vacuum-size=100M

# Verify disk usage after cleanup
journalctl --disk-usage
```

---

## Common Issues and Resolutions

### Issue 1: API Not Responding

**Symptoms:**
- `curl http://localhost:8000/api/v1/health` times out or connection refused
- Web UI shows "Disconnected"

**Diagnosis:**
```bash
# Check if service is running
sudo systemctl status r58-api

# Check if port is in use
sudo lsof -i :8000

# View recent logs
sudo journalctl -u r58-api -n 50
```

**Common Causes & Fixes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| Service crashed | Status shows "failed" | `sudo systemctl restart r58-api` |
| Port conflict | Another process on :8000 | Kill conflicting process |
| Python error | Import error in logs | Check dependencies: `pip install -e packages/backend` |
| Pipeline socket missing | "Connection refused" in logs | `sudo systemctl restart r58-pipeline` |

**Recovery:**
```bash
sudo systemctl restart r58-pipeline r58-api
curl http://localhost:8000/api/v1/health
```

---

### Issue 2: No Video Preview

**Symptoms:**
- Black video in browser
- WHEP requests fail
- "Connection refused" errors

**Diagnosis:**
```bash
# Check MediaMTX
sudo systemctl status mediamtx
curl http://localhost:9997/v3/paths/list | jq

# Check if streams are ready
curl http://localhost:9997/v3/paths/list | jq '.items[] | {name, ready, readers}'

# Check if video devices exist
v4l2-ctl --list-devices
```

**Common Causes & Fixes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| MediaMTX not running | Status "failed" | `sudo systemctl restart mediamtx` |
| No active paths | Empty items list | Check pipeline: `sudo systemctl status r58-pipeline` |
| Camera not connected | Device not listed | Connect HDMI cable |
| Pipeline stalled | Path exists but not ready | Restart pipeline |

**Recovery:**
```bash
sudo systemctl restart mediamtx r58-pipeline
sleep 3
curl http://localhost:9997/v3/paths/list | jq '.items[] | .name'
```

---

### Issue 3: Recording Won't Start

**Symptoms:**
- Start button does nothing
- API returns 500 or 507 error
- Recording status stays "idle"

**Diagnosis:**
```bash
# Check disk space (needs >2GB)
df -h /opt/preke-r58-recorder/recordings

# Check recorder status
curl http://localhost:8000/api/v1/recorder/status | jq

# Check pipeline health
curl http://localhost:8000/api/v1/health/detailed | jq '.services[] | select(.name=="pipeline_manager")'

# Try starting via API
curl -X POST http://localhost:8000/api/v1/recorder/start \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["cam2"]}'
```

**Common Causes & Fixes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| Disk full | 507 error, < 2GB free | Free up space or change recording path |
| Already recording | 409 Conflict | Stop current recording first |
| Pipeline unhealthy | pipeline_manager "unhealthy" | `sudo systemctl restart r58-pipeline` |
| No cameras | Empty inputs in capabilities | Connect HDMI sources |

**Recovery:**
```bash
# Free disk space
ls -lah /opt/preke-r58-recorder/recordings/
rm -f /opt/preke-r58-recorder/recordings/old_recording.mp4

# Restart and try again
sudo systemctl restart r58-pipeline r58-api
curl -X POST http://localhost:8000/api/v1/recorder/start \
  -H "Content-Type: application/json" \
  -d '{"inputs": ["cam2"]}'
```

---

### Issue 4: Recording Stalled

**Symptoms:**
- Duration timer running but bytes not increasing
- File size not growing
- Watchdog alerts in logs

**Diagnosis:**
```bash
# Check recording metrics
curl http://localhost:8000/api/v1/recorder/status | jq

# Watch bytes counter (should increase)
watch -n 1 'curl -s http://localhost:8000/api/v1/recorder/status | jq .bytes_written'

# Check for stall alerts
curl http://localhost:8000/api/v1/alerts | jq '.alerts[] | select(.source=="PIPELINE")'

# Check file is growing
ls -la /opt/preke-r58-recorder/recordings/*.mp4 | tail -1
sleep 5
ls -la /opt/preke-r58-recorder/recordings/*.mp4 | tail -1
```

**Common Causes & Fixes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| Encoder stall | Bytes frozen | Stop and restart recording |
| Disk I/O issue | System slow, high iowait | Check `iostat`, reduce bitrate |
| Camera disconnect | No signal | Reconnect HDMI |
| VPU overload | Multiple 4K streams | Reduce resolution or camera count |

**Recovery:**
```bash
# Force stop recording
curl -X POST http://localhost:8000/api/v1/recorder/stop

# Check if file is valid
ffprobe /opt/preke-r58-recorder/recordings/latest.mp4 2>&1 | head -20

# Restart pipeline
sudo systemctl restart r58-pipeline
```

---

### Issue 5: WebSocket Disconnects

**Symptoms:**
- UI shows stale data
- "Disconnected" indicator
- Events not updating

**Diagnosis:**
```bash
# Check WebSocket connections
curl http://localhost:8000/api/v1/ws/stats 2>/dev/null || echo "No WS stats endpoint"

# Check API logs for WS errors
sudo journalctl -u r58-api -n 100 | grep -i websocket

# Test WebSocket manually
websocat ws://localhost:8000/api/v1/ws 2>/dev/null || echo "websocat not installed"
```

**Common Causes & Fixes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| Network flap | Temporary disconnect | Auto-reconnect should handle |
| Server overload | High latency | Check CPU, reduce load |
| Proxy timeout | Nginx/Traefik timeout | Increase timeout settings |
| Client bug | Console errors | Refresh browser |

**Recovery:**
```bash
# Refresh client (browser)
# Or restart API
sudo systemctl restart r58-api
```

---

### Issue 6: Remote Access Not Working

**Symptoms:**
- Cannot SSH via `./connect-r58-frp.sh`
- Public URLs timeout
- VPS shows FRP disconnected

**Diagnosis:**
```bash
# On local machine - test VPS connectivity
nc -zv 65.109.32.111 10022
nc -zv 65.109.32.111 7000

# Test public endpoint
curl -v https://app.itagenten.no/api/v1/health

# On VPS (if accessible)
./connect-coolify-vps.sh "docker ps | grep frp"
```

**Common Causes & Fixes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| FRP client down | Service not running | Restart on R58: `sudo systemctl restart frpc` |
| FRP server down | VPS not responding | Restart on VPS: `docker restart frps` |
| Network issue | Connection refused | Check R58 internet connection |
| Token mismatch | Auth failed in logs | Verify `/etc/frp/frpc.toml` token |

**Recovery:**
```bash
# If you have local access to R58:
sudo systemctl restart frpc
sudo journalctl -u frpc -n 20

# If only VPS access:
./connect-coolify-vps.sh "docker restart frps"
```

---

### Issue 7: VDO.ninja Mixer Not Working

**Symptoms:**
- Mixer page blank or loading forever
- No cameras visible in mixer
- WebRTC connection failed

**Diagnosis:**
```bash
# Check VDO.ninja signaling
curl -k https://localhost:8443/ 2>/dev/null | head -5

# Check if service running
sudo systemctl status vdo-signaling

# Check SSL certificate
openssl s_client -connect localhost:8443 </dev/null 2>/dev/null | head -10

# Check WHEP sources for mixer
curl http://localhost:9997/v3/paths/list | jq '.items[] | .name'
```

**Common Causes & Fixes:**

| Cause | Evidence | Fix |
|-------|----------|-----|
| Signaling down | Service not running | `sudo systemctl restart vdo-signaling` |
| SSL cert issue | Certificate error | Regenerate self-signed cert |
| CORS blocking | Browser console errors | Check nginx CORS headers |
| No camera streams | Empty MediaMTX paths | Start preview pipelines |

---

## Log Locations

| Service | Log Command | Log File (if applicable) |
|---------|-------------|--------------------------|
| r58-api | `journalctl -u r58-api -f` | via journald |
| r58-pipeline | `journalctl -u r58-pipeline -f` | via journald |
| mediamtx | `journalctl -u mediamtx -f` | via journald |
| vdo-signaling | `journalctl -u vdo-signaling -f` | via journald |
| frpc | `journalctl -u frpc -f` | via journald |
| Preke Studio (Electron) | `npm run test:logs` | `~/Library/Logs/preke-studio/main.log` |

### Log Filtering

```bash
# Errors only
journalctl -u r58-api -p err -n 50

# Last hour
journalctl -u r58-api --since "1 hour ago"

# Multiple services
journalctl -u r58-api -u r58-pipeline -f

# Search for keyword
journalctl -u r58-api | grep -i "error\|fail\|exception"

# JSON formatted (if structured logging enabled)
journalctl -u r58-api -o json | jq
```

---

## Support Bundle

Generate a complete diagnostic package:

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/support/bundle -o support-bundle.zip
unzip -l support-bundle.zip

# Or via script
./scripts/collect-diagnostics.sh
```

**Bundle Contents:**
- `system_info.json` - Host, Python version, config
- `metrics.json` - CPU, memory, disk stats
- `health.json` - Service health status
- `logs/` - Recent logs for all services
- `config/` - Sanitized configuration files

---

## Emergency Procedures

### Emergency Stop All

```bash
# Stop all recording immediately
curl -X POST http://localhost:8000/api/v1/recorder/stop

# Stop all services
sudo systemctl stop r58-api r58-pipeline mediamtx

# Kill any stuck processes
sudo pkill -9 -f gstreamer
sudo pkill -9 -f uvicorn
```

### Full System Restart

```bash
# Graceful restart
sudo systemctl restart mediamtx
sleep 2
sudo systemctl restart r58-pipeline
sleep 2
sudo systemctl restart r58-api

# Verify
curl http://localhost:8000/api/v1/health/detailed | jq
```

### Recovery from Corrupted State

```bash
# Stop services
sudo systemctl stop r58-api r58-pipeline

# Clear state files
rm -f /var/lib/r58/pipeline_state.json

# Restart
sudo systemctl start r58-pipeline r58-api
```

---

## Escalation

If issues persist after following this runbook:

1. **Collect diagnostics:** `./scripts/collect-diagnostics.sh`
2. **Check alerts:** `curl http://localhost:8000/api/v1/alerts | jq`
3. **Review recent changes:** `git log --oneline -10`
4. **Document:** Note exact error messages and steps taken
5. **Escalate:** Contact development team with bundle + notes

---

## Related Documentation

- [docs/ops/system-map.md](system-map.md) - System architecture
- [docs/ops/triage-log.md](triage-log.md) - Known issues and decisions
- [docs/HARDENING.md](../HARDENING.md) - Stability features
- [docs/OPERATIONS.md](../OPERATIONS.md) - Deployment guide

