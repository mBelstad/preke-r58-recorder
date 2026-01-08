# DaVinci Resolve Automation - Testing Instructions

## Quick Start Testing Guide

### Prerequisites Checklist

**On R58 Device:**
- ✅ Code deployed (completed)
- ⬜ DaVinci automation enabled in config
- ⬜ Webhook URLs configured

**On Editing PC (Mac/Windows):**
- ⬜ DaVinci Resolve Studio installed and running
- ⬜ Python 3.6.8+ installed
- ⬜ Dependencies installed (`pip install flask httpx watchdog`)
- ⬜ Automation service running
- ⬜ Network connectivity to R58

---

## Step 1: Configure R58 Device

### 1.1 Edit Configuration

SSH to R58 and edit the config file:

```bash
./connect-r58-frp.sh
cd /opt/preke-r58-recorder
nano config.yml
```

### 1.2 Enable DaVinci Automation

Find the `davinci_automation` section and update it:

```yaml
davinci_automation:
  enabled: true  # Change from false to true
  webhook_urls:
    - "http://YOUR_EDITING_PC_IP:8080/webhook/session-start"
    # Add more editing PCs if needed
  project_templates:
    default: "standard_template"
    multicam: "multicam_template"
  auto_import: true
  create_multicam_timeline: true
  auto_sync: true
  sync_method: "timecode"
```

**Important:** Replace `YOUR_EDITING_PC_IP` with the actual IP address of your editing PC.

### 1.3 Restart Service

After saving config, restart the recorder service:

```bash
sudo systemctl restart preke-recorder
```

### 1.4 Verify Configuration

Check that the service started correctly:

```bash
sudo systemctl status preke-recorder
```

---

## Step 2: Set Up Editing PC

### 2.1 Install Python Dependencies

On your editing PC (Mac or Windows):

```bash
pip install flask httpx watchdog
```

### 2.2 Verify DaVinci Resolve Scripting API

**macOS:**
```bash
ls "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
```

**Windows:**
```powershell
dir "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
```

If the directory doesn't exist, ensure DaVinci Resolve Studio (not free version) is installed.

### 2.3 Start DaVinci Resolve

**Important:** DaVinci Resolve Studio must be running before starting the automation service.

### 2.4 Start Automation Service

Navigate to the project directory and start the service:

```bash
cd /path/to/preke-r58-recorder
python scripts/davinci-automation-service.py
```

You should see:
```
DaVinci Resolve Automation Service starting...
Webhook endpoints:
  POST /webhook/session-start
  POST /webhook/session-stop
  POST /webhook/file-added
  GET  /health
 * Running on http://0.0.0.0:8080
```

### 2.5 Test Health Endpoint

In another terminal, test the health endpoint:

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "davinci_connected": true,
  "active_sessions": 0
}
```

If `davinci_connected` is `false`, ensure DaVinci Resolve Studio is running.

---

## Step 3: Test Webhook Delivery

### 3.1 Test from R58

SSH to R58 and test webhook delivery manually:

```bash
./connect-r58-frp.sh
curl -X POST http://YOUR_EDITING_PC_IP:8080/webhook/session-start \
  -H "Content-Type: application/json" \
  -d '{
    "event": "session_start",
    "session_id": "test_session_001",
    "start_time": "2025-01-08T22:00:00",
    "cameras": {
      "cam0": {"status": "recording", "file": "/mnt/sdcard/recordings/cam0/test.mkv"}
    },
    "file_paths": {
      "cam0": "/mnt/sdcard/recordings/cam0/test.mkv"
    }
  }'
```

Check the automation service logs on your editing PC - you should see the webhook received.

### 3.2 Verify Firewall

If webhook test fails, check firewall on editing PC:

**macOS:**
```bash
# Allow incoming connections on port 8080
sudo pfctl -f /etc/pf.conf
```

**Windows:**
```powershell
# Allow port 8080 in Windows Firewall
New-NetFirewallRule -DisplayName "DaVinci Automation" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow
```

---

## Step 4: Test Full Workflow

### 4.1 Start Recording Session

On R58, start a recording session:

**Via Web Interface:**
- Navigate to https://app.itagenten.no
- Go to Recorder view
- Click "Start Recording" for all cameras

**Via API:**
```bash
curl -X POST https://app.itagenten.no/api/trigger/start
```

### 4.2 Monitor Automation Service

On your editing PC, watch the automation service logs. You should see:

```
Received session_start webhook for session_20250108_143022
Created DaVinci Resolve project: session_20250108_143022
Created bin for cam0
Created bin for cam1
...
Imported /path/to/file.mkv to cam0 bin
Created timeline: session_20250108_143022_multicam
```

### 4.3 Check DaVinci Resolve

In DaVinci Resolve:
1. Open Project Manager
2. Look for a project named `session_YYYYMMDD_HHMMSS`
3. Open the project
4. Check Media Pool - you should see:
   - Bins for each camera (cam0, cam1, cam2, cam3)
   - Media files imported into appropriate bins
   - A timeline named `session_YYYYMMDD_HHMMSS_multicam`

---

## Step 5: Test Edit-While-Record

### 5.1 Start Recording

Start a recording session as in Step 4.1

### 5.2 Open Project in DaVinci

While recording is active:
1. Open the project in DaVinci Resolve
2. Check that files are visible in bins
3. Try scrubbing through recorded portions (should work)

### 5.3 Verify Incremental Import

The automation service watches for new files. As recording continues:
- New files should automatically appear in bins
- Timeline should update (if configured)

---

## Troubleshooting

### Issue: Webhook Not Received

**Symptoms:** Automation service doesn't receive webhooks

**Solutions:**
1. Check R58 logs: `sudo journalctl -u preke-recorder -f | grep webhook`
2. Verify webhook URL in config.yml is correct
3. Test network connectivity: `ping YOUR_EDITING_PC_IP`
4. Check firewall on editing PC
5. Verify automation service is running and listening on port 8080

### Issue: DaVinci Not Connected

**Symptoms:** `davinci_connected: false` in health check

**Solutions:**
1. Ensure DaVinci Resolve Studio (not free) is installed
2. Ensure DaVinci Resolve is running
3. Check Scripting API path is correct
4. Restart DaVinci Resolve
5. Restart automation service

### Issue: Project Not Created

**Symptoms:** Webhook received but no project in DaVinci

**Solutions:**
1. Check automation service logs for errors
2. Verify DaVinci Resolve database permissions
3. Check if project with same name already exists
4. Try creating project manually to test API access

### Issue: Files Not Importing

**Symptoms:** Project created but no media files

**Solutions:**
1. Verify file paths are accessible from editing PC
2. Check file permissions
3. Ensure files are in MKV format
4. Check automation service logs for import errors
5. Test file import manually using `scripts/davinci-scripts/import_media.py`

### Issue: Service Crashes

**Symptoms:** Automation service stops running

**Solutions:**
1. Check Python version (needs 3.6.8+)
2. Verify all dependencies installed
3. Check logs for error messages
4. Ensure DaVinci Resolve is running before starting service
5. Run service in foreground to see error output

---

## Manual Testing Scripts

You can test individual components manually:

### Test Project Creation

```bash
python scripts/davinci-scripts/create_session_project.py test_session_001
```

### Test Media Import

```bash
python scripts/davinci-scripts/import_media.py test_session_001 \
  cam0:/path/to/cam0.mkv \
  cam1:/path/to/cam1.mkv
```

### Test Timeline Creation

```bash
python scripts/davinci-scripts/setup_multicam_timeline.py \
  test_session_001 \
  multicam_timeline \
  cam0 cam1 cam2
```

---

## Expected Behavior

### When Recording Starts

1. ✅ R58 sends webhook to editing PC
2. ✅ Automation service receives webhook
3. ✅ DaVinci Resolve project created
4. ✅ Camera bins created
5. ✅ Media files imported
6. ✅ Multi-camera timeline created (if configured)

### During Recording

1. ✅ New files automatically detected
2. ✅ Files imported to appropriate bins
3. ✅ Timeline updates (if configured)

### When Recording Stops

1. ✅ R58 sends stop webhook
2. ✅ File watchers stopped
3. ✅ Session marked as complete

---

## Next Steps After Testing

Once testing is successful:

1. **Set up as background service** (see DAVINCI_AUTOMATION.md)
2. **Configure multiple editing PCs** if needed
3. **Set up project templates** for different recording types
4. **Customize sync methods** based on your cameras
5. **Test with real recording sessions**

---

## Support

If you encounter issues:

1. Check logs:
   - R58: `sudo journalctl -u preke-recorder -f`
   - Automation service: Check terminal output
   - DaVinci Resolve: Check Resolve logs

2. Review documentation:
   - `docs/DAVINCI_AUTOMATION.md` - Full setup guide
   - Plan files in `.cursor/plans/`

3. Test components individually using manual scripts

4. Verify network connectivity and firewall settings
