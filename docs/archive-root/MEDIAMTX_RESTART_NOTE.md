# MediaMTX Restart Note

## Important
When restarting MediaMTX, you **must also restart the preke-recorder service** to reconnect the ingest pipelines.

### Why?
The ingest pipelines publish to MediaMTX via RTSP. When MediaMTX restarts, these RTSP connections are broken and need to be re-established.

### Commands
```bash
# When restarting MediaMTX:
sudo systemctl restart mediamtx
sudo systemctl restart preke-recorder  # Required!

# Or restart both together:
sudo systemctl restart mediamtx preke-recorder
```

### Symptoms if You Forget
- All cameras show "no signal" or 500 errors
- MediaMTX logs show: "destroyed: no one is publishing to path 'camX'"
- Frontend shows: "Stream not available for camX (HTTP 500) - no signal"

### Solution
Simply restart the preke-recorder service:
```bash
sudo systemctl restart preke-recorder
```

After ~5 seconds, all streams should be available again.

