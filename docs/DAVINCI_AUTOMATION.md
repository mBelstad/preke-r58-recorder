# DaVinci Resolve Automation Setup Guide

This guide explains how to set up automatic project creation and media import in DaVinci Resolve when recording sessions start on the R58 device.

## Overview

The DaVinci Resolve automation system automatically:
- Creates DaVinci Resolve projects when recording sessions start
- Imports media files organized by camera into bins
- Sets up multi-camera timelines
- Handles incremental file imports (edit-while-record)

## Architecture

```
R58 Device → Webhook → Editing PC → DaVinci Resolve Automation Service → DaVinci Resolve
```

- **R58 Device**: Sends webhook when recording starts (minimal overhead)
- **Editing PC**: Runs automation service that receives webhooks
- **DaVinci Resolve**: Project created, media imported automatically

## Prerequisites

### On R58 Device
- Recording system configured and working
- Network connectivity to editing PC(s)

### On Editing PC (Mac or Windows)
- DaVinci Resolve Studio installed (Scripting API requires Studio version)
- Python 3.6.8 or later
- Network connectivity to R58 device

## Installation

### Step 1: Install Python Dependencies

On your editing PC, install required packages:

```bash
pip install flask httpx watchdog
```

### Step 2: Configure R58 Device

Edit `config.yml` on the R58 device:

```yaml
davinci_automation:
  enabled: true  # Enable automation
  webhook_urls:
    - "http://mac-editing-pc:8080/webhook/session-start"
    - "http://windows-editing-pc:8080/webhook/session-start"
  project_templates:
    default: "standard_template"
    multicam: "multicam_template"
  auto_import: true
  create_multicam_timeline: true
  auto_sync: true
  sync_method: "timecode"  # timecode, audio, or manual
```

Replace `mac-editing-pc` and `windows-editing-pc` with the actual IP addresses or hostnames of your editing computers.

### Step 3: Start Automation Service

On each editing PC, start the automation service:

```bash
cd /path/to/preke-r58-recorder
python scripts/davinci-automation-service.py
```

The service will:
- Listen on port 8080 for webhooks
- Connect to DaVinci Resolve (must be running)
- Automatically create projects and import media

### Step 4: Run as Background Service (Optional)

#### macOS (using launchd)

Create `~/Library/LaunchAgents/com.preke.davinci-automation.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.preke.davinci-automation</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/preke-r58-recorder/scripts/davinci-automation-service.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load the service:
```bash
launchctl load ~/Library/LaunchAgents/com.preke.davinci-automation.plist
```

#### Windows (using Task Scheduler or NSSM)

Create a scheduled task or use NSSM (Non-Sucking Service Manager) to run the Python script as a Windows service.

## Usage

### Starting a Recording Session

1. Start recording on R58 device (via web interface or API)
2. R58 automatically sends webhook to editing PC(s)
3. Automation service receives webhook
4. DaVinci Resolve project is created automatically
5. Media files are imported into camera-specific bins
6. Multi-camera timeline is created (if configured)

### File Organization

Media is organized in bins by camera:
```
Project: session_20250108_143022
├── cam0/
│   └── recording_20250108_143022.mkv
├── cam1/
│   └── recording_20250108_143022.mkv
├── cam2/
│   └── recording_20250108_143022.mkv
└── cam3/
    └── recording_20250108_143022.mkv
```

### Edit-While-Record

The automation service watches for new files and automatically imports them as they appear. You can start editing while recording is still in progress.

## Webhook Endpoints

The automation service provides these endpoints:

### POST /webhook/session-start

Triggered when a recording session starts.

**Payload:**
```json
{
  "event": "session_start",
  "session_id": "session_20250108_143022",
  "start_time": "2025-01-08T14:30:22",
  "cameras": {
    "cam0": {"status": "recording", "file": "/path/to/cam0.mkv"},
    "cam1": {"status": "recording", "file": "/path/to/cam1.mkv"}
  },
  "file_paths": {
    "cam0": "/path/to/cam0.mkv",
    "cam1": "/path/to/cam1.mkv"
  }
}
```

### POST /webhook/session-stop

Triggered when a recording session stops.

**Payload:**
```json
{
  "event": "session_stop",
  "session_id": "session_20250108_143022",
  "end_time": "2025-01-08T15:45:00",
  "cameras": {
    "cam0": {"status": "completed"},
    "cam1": {"status": "completed"}
  }
}
```

### POST /webhook/file-added

Triggered when a new file is detected (for incremental imports).

**Payload:**
```json
{
  "event": "file_added",
  "session_id": "session_20250108_143022",
  "cam_id": "cam0",
  "file_path": "/path/to/new_file.mkv"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "davinci_connected": true,
  "active_sessions": 1
}
```

## Troubleshooting

### DaVinci Resolve Not Connected

**Error:** "Failed to connect to DaVinci Resolve"

**Solution:**
- Ensure DaVinci Resolve Studio is running
- Check that Scripting API is available at the expected path
- Verify DaVinci Resolve Studio (not free version) is installed

### Webhook Not Received

**Issue:** Automation service doesn't receive webhooks

**Solutions:**
1. Check firewall settings on editing PC (port 8080 must be open)
2. Verify webhook URL in `config.yml` is correct
3. Check network connectivity between R58 and editing PC
4. Review R58 logs for webhook delivery errors

### Files Not Importing

**Issue:** Media files not appearing in DaVinci Resolve

**Solutions:**
1. Verify file paths are accessible from editing PC
2. Check file permissions
3. Ensure files are in MKV format (DaVinci Resolve compatible)
4. Review automation service logs for import errors

### Project Not Created

**Issue:** Project creation fails

**Solutions:**
1. Check DaVinci Resolve is running
2. Verify project name doesn't conflict with existing project
3. Check DaVinci Resolve database permissions
4. Review automation service logs

## Advanced Configuration

### Custom Templates

Create project templates in DaVinci Resolve and reference them in `config.yml`:

```yaml
davinci_automation:
  project_templates:
    default: "my_custom_template"
    multicam: "my_multicam_template"
```

Templates should be saved as projects in your DaVinci Resolve database.

### Multiple Editing PCs

You can configure multiple webhook URLs to send automation to multiple editing PCs:

```yaml
davinci_automation:
  webhook_urls:
    - "http://editor1:8080/webhook/session-start"
    - "http://editor2:8080/webhook/session-start"
    - "http://editor3:8080/webhook/session-start"
```

Each PC will receive the webhook and create its own project.

### Sync Methods

Configure camera synchronization method:

- **timecode**: Sync by embedded timecode (requires cameras with timecode)
- **audio**: Sync by audio waveform analysis
- **manual**: No automatic sync, manual setup required

## Scripts Reference

Individual scripts can be run manually for testing:

### create_session_project.py

Create a project manually:

```bash
python scripts/davinci-scripts/create_session_project.py session_20250108_143022
```

### import_media.py

Import media files manually:

```bash
python scripts/davinci-scripts/import_media.py session_20250108_143022 cam0:/path/to/cam0.mkv cam1:/path/to/cam1.mkv
```

### setup_multicam_timeline.py

Create multi-camera timeline:

```bash
python scripts/davinci-scripts/setup_multicam_timeline.py session_20250108_143022 multicam_timeline cam0 cam1 cam2
```

## Limitations

1. **DaVinci Resolve Studio Required**: Scripting API only available in Studio version
2. **DaVinci Must Be Running**: Automation service requires DaVinci Resolve to be running
3. **Network Access**: Editing PC must be accessible from R58 device
4. **File Paths**: Files must be accessible from editing PC (use network shares)
5. **Multi-Cam Sync**: Full automatic sync requires advanced implementation (currently manual)

## Future Enhancements

Planned improvements:
- Full automatic multi-camera synchronization
- Template system with project settings
- Proxy generation automation
- Quality control checks
- Collaboration server integration
- Advanced timeline setup

## Support

For issues or questions:
1. Check automation service logs
2. Review R58 device logs for webhook delivery
3. Verify DaVinci Resolve Scripting API connectivity
4. Test individual scripts manually

## See Also

- [DaVinci Resolve Scripting API Documentation](https://wiki.dvresolve.com/developer-docs/scripting-api)
- [Live Editing Workflow Plan](../.cursor/plans/live_video_editing_workflow_ed60cd47.plan.md)
- [Smart Session-Based Automation Plan](../.cursor/plans/smart_session-based_automation_for_davinci_resolve_1329b9d8.plan.md)
