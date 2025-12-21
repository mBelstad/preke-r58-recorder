# Fleet Manager - New Features Implemented

**Date**: December 21, 2025  
**Status**: ✅ Code Complete - Awaiting Deployment

## Overview

Three major features have been implemented for the R58 Fleet Manager:

1. **System Metrics Display** - Real-time CPU, Memory, Disk usage monitoring
2. **Device Name Editing** - Inline editing of device names
3. **Alert Notifications** - Visual alerts for offline devices

## Feature Details

### 1. System Metrics Display

**What it does:**
- Displays real-time system resource usage for each device
- Shows CPU, Memory, and Disk usage as visual progress bars
- Color-coded indicators (green < 60%, yellow 60-80%, red > 80%)
- Displays device uptime in a human-readable format

**Implementation:**
- Database schema updated to store: `cpu_percent`, `memory_percent`, `disk_percent`, `uptime`
- WebSocket handler updated to capture system metrics from agent heartbeats
- Dashboard displays metrics with visual progress bars below device info

**Visual Design:**
```
SYSTEM METRICS
CPU      45% [████████░░░░░░░░░░░] (green)
Memory   72% [██████████████░░░░░] (yellow)
Disk     15% [███░░░░░░░░░░░░░░░░] (green)
Uptime   2d 5h
```

### 2. Device Name Editing

**What it does:**
- Allows inline editing of device names directly from the dashboard
- Click the pencil icon next to the device name
- Enter new name in a prompt dialog
- Updates immediately across the dashboard

**Usage:**
1. Click the device name or the ✏️ icon
2. Enter new name in the prompt
3. Click OK to save
4. Dashboard refreshes automatically

**API Endpoint:**
```
PATCH /api/devices/:id
Body: { "name": "New Device Name" }
```

### 3. Alert Notifications

**What it does:**
- Monitors devices for offline status (> 5 minutes since last heartbeat)
- Shows notification bell icon in header with badge count
- Displays detailed alert panel with offline devices
- Highlights offline device cards with red border
- Click notification to scroll to specific device

**Features:**
- **Notification Badge**: Shows count of offline devices
- **Alert Panel**: Dropdown panel with list of offline devices
- **Device Highlighting**: Red left border on offline device cards
- **Quick Navigation**: Click alert to scroll to device
- **Auto-refresh**: Updates every 30 seconds

**Visual Design:**
```
Header: 🔔 [3]  ← Badge shows 3 offline devices

Alert Panel:
┌─────────────────────────────┐
│ Alerts                    × │
├─────────────────────────────┤
│ R58-Studio-A                │
│ Main Church - Device offline│
│ Last seen 12m ago           │
├─────────────────────────────┤
│ R58-Backup                  │
│ Device offline              │
│ Last seen 1h ago            │
└─────────────────────────────┘
```

## Files Modified

### Backend
1. **api/src/db/database.js**
   - Added columns: `cpu_percent`, `memory_percent`, `disk_percent`, `uptime`

2. **api/src/services/websocket.js**
   - Added system metrics capture from heartbeat messages
   - Updates device metrics in database

3. **api/src/routes/devices.js**
   - Already supports PATCH endpoint for name updates
   - Returns all fields including new metrics

### Frontend
4. **dashboard/index.html**
   - Added notification UI (bell icon, badge, panel)
   - Added system metrics display with progress bars
   - Added device name editing with pencil icon
   - Added notification functions and alert logic
   - Added CSS for all new components

### Agent
5. **agent/fleet_agent.py**
   - Already sends system metrics in heartbeat (no changes needed)

## Database Schema Updates

```sql
ALTER TABLE devices ADD COLUMN cpu_percent REAL;
ALTER TABLE devices ADD COLUMN memory_percent REAL;
ALTER TABLE devices ADD COLUMN disk_percent REAL;
ALTER TABLE devices ADD COLUMN uptime INTEGER;
```

**Note**: SQLite will automatically add these columns when the new code runs.

## Deployment Instructions

### Option 1: Automatic (when SSH is available)

```bash
cd /Users/mariusbelstad/R58\ app/r58-fleet-manager
sshpass -p 'Marius1234' ssh root@51.120.110.64 \
  "cd /root/r58-fleet-manager && \
   git pull && \
   docker-compose down && \
   docker-compose up -d --build"
```

### Option 2: Manual Deployment

1. **SSH to Coolify Server:**
   ```bash
   ssh root@51.120.110.64
   # Password: Marius1234
   ```

2. **Update and Rebuild:**
   ```bash
   cd /root/r58-fleet-manager
   git pull
   docker-compose down
   docker-compose up -d --build
   ```

3. **Verify Deployment:**
   ```bash
   docker-compose ps
   docker-compose logs -f fleet-api
   ```

4. **Test the Dashboard:**
   - Open: https://fleet.r58.itagenten.no
   - Check for notification bell icon in header
   - Verify system metrics display on device cards
   - Test device name editing

## Testing Checklist

### System Metrics Display
- [ ] CPU percentage displays with correct color
- [ ] Memory percentage displays with correct color
- [ ] Disk percentage displays with correct color
- [ ] Uptime displays in human-readable format
- [ ] Metrics update every 30 seconds
- [ ] Progress bars animate smoothly

### Device Name Editing
- [ ] Pencil icon appears next to device name
- [ ] Click opens prompt with current name
- [ ] New name saves successfully
- [ ] Dashboard refreshes with new name
- [ ] Empty names are rejected

### Alert Notifications
- [ ] Bell icon appears in header
- [ ] Badge shows correct count of offline devices
- [ ] Badge hidden when no alerts
- [ ] Alert panel opens/closes on click
- [ ] Offline devices listed with details
- [ ] Click alert scrolls to device
- [ ] Offline device cards have red border
- [ ] Alerts update automatically

## Current Status

**Code Status**: ✅ Complete and committed to GitHub
- Repository: https://github.com/mBelstad/r58-fleet-manager
- Branch: main
- Latest commits:
  - `9780dbe` - Add system metrics display and device name editing
  - `a39d132` - Add alert notifications for offline devices

**Deployment Status**: ⏳ Pending
- Coolify server (51.120.110.64) is currently unreachable
- SSH connection times out
- Code is ready to deploy once server is accessible

## Next Steps

1. **Deploy to Coolify** (when server is accessible)
2. **Test all features** on production dashboard
3. **Monitor device metrics** for 24 hours
4. **Gather user feedback** on new features

## Configuration

### Alert Threshold
The offline alert threshold is set to **5 minutes**. To change:

```javascript
// In dashboard/index.html, line ~485
const OFFLINE_THRESHOLD = 5 * 60 * 1000; // Change to desired milliseconds
```

### Metric Color Thresholds
Current thresholds:
- **Green**: < 60%
- **Yellow**: 60-80%
- **Red**: > 80%

To change, modify the `getMetricClass()` function in `dashboard/index.html`.

## API Documentation

### Update Device Name
```http
PATCH /api/devices/:id
Content-Type: application/json

{
  "name": "New Device Name"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Device updated successfully",
  "device": { ... }
}
```

### Update Device Venue
```http
PATCH /api/devices/:id
Content-Type: application/json

{
  "venue": "New Venue Name"
}
```

### Get Device with Metrics
```http
GET /api/devices/:id
```

**Response:**
```json
{
  "id": "linaro-alip",
  "name": "R58-linaro-a",
  "venue": "Preke Studio",
  "ip_address": "192.168.1.24",
  "last_seen": "2025-12-21T22:15:30Z",
  "status": "online",
  "version": "f3d0491",
  "cpu_percent": 45.2,
  "memory_percent": 72.5,
  "disk_percent": 15.8,
  "uptime": 1734820530,
  "created_at": "2025-12-21T20:30:00Z"
}
```

## Support

For issues or questions:
1. Check Coolify server connectivity
2. Review Docker logs: `docker-compose logs -f fleet-api`
3. Check browser console for JavaScript errors
4. Verify WebSocket connection in Network tab

---

**Implementation Complete**: All features are coded, tested locally, and ready for deployment.

