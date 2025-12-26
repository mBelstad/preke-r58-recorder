# Fleet Manager - Venue Name Feature

**Date**: December 21, 2025  
**Status**: ✅ Deployed and Working

---

## Feature: Edit Venue Names

You can now assign venue names to your R58 devices to help organize them by location.

---

## How to Use

### From the Dashboard

1. **Open Dashboard**: https://fleet.r58.itagenten.no

2. **Find the Venue Field**: In each device card, look for the "Venue" field

3. **Click to Edit**: Click on the venue field (you'll see a pencil icon ✏️)

4. **Enter Venue Name**: A prompt will appear asking for the venue name
   - Examples: "Main Church", "Studio A", "Youth Center", "Chapel B"

5. **Save**: Click OK to save the venue name

6. **See Update**: The dashboard will refresh and show the new venue name

---

## Example Venue Names

Here are some suggestions for organizing your R58 devices:

### By Church/Location
- "Main Church"
- "Chapel A"
- "Youth Center"
- "Community Hall"

### By Studio
- "Studio A"
- "Studio B"
- "Production Room"
- "Broadcast Center"

### By Event Type
- "Sunday Service"
- "Midweek Meeting"
- "Youth Events"
- "Special Events"

### By City/Region
- "Oslo Main"
- "Bergen Branch"
- "Trondheim Center"

---

## API Usage

You can also update venue names programmatically:

### Update Venue via API

```bash
curl -X PATCH https://fleet.r58.itagenten.no/api/devices/DEVICE_ID \
  -H "Content-Type: application/json" \
  -d '{"venue":"Church Name"}'
```

### Update Both Name and Venue

```bash
curl -X PATCH https://fleet.r58.itagenten.no/api/devices/DEVICE_ID \
  -H "Content-Type: application/json" \
  -d '{"name":"Custom Name", "venue":"Venue Name"}'
```

### Get Device Info

```bash
curl https://fleet.r58.itagenten.no/api/devices/DEVICE_ID
```

---

## Benefits

### Organization
- **Identify Devices**: Quickly see which device is at which location
- **Multiple Locations**: Manage devices across different churches/venues
- **Team Coordination**: Everyone knows which device is where

### Troubleshooting
- **Quick Identification**: "The device at Main Church is offline"
- **Targeted Support**: Know exactly which location needs help
- **Maintenance Planning**: Schedule updates by venue

### Reporting
- **Usage by Location**: See which venues are most active
- **Performance Tracking**: Compare devices by venue
- **Resource Allocation**: Plan equipment distribution

---

## Technical Details

### Database Field
- **Field**: `venue` (TEXT, nullable)
- **Stored in**: `devices` table
- **Default**: `null` (shows as "-" in dashboard)

### API Endpoint
- **Method**: `PATCH /api/devices/:id`
- **Body**: `{"venue": "Venue Name"}`
- **Response**: Updated device object

### Dashboard
- **Location**: Device info section
- **Interaction**: Click to edit
- **Validation**: None (can be empty or any text)
- **Update**: Immediate refresh after save

---

## Current Status

Your device is currently set to:
- **Device ID**: linaro-alip
- **Venue**: Test Church (set during testing)

You can change it to any name you want by clicking on it in the dashboard!

---

## Future Enhancements

Possible improvements for venue management:

1. **Venue Dropdown**: Pre-defined list of venues
2. **Venue Grouping**: Group devices by venue in dashboard
3. **Venue Filter**: Show only devices from specific venue
4. **Venue Statistics**: Summary per venue
5. **Bulk Update**: Set venue for multiple devices at once

---

## Example Workflow

### Managing 10 Churches

1. **Initial Setup**:
   - Install agent on each R58
   - Devices auto-register with default names

2. **Assign Venues**:
   - Open dashboard
   - Click venue field for each device
   - Enter church name

3. **Daily Monitoring**:
   - Open dashboard
   - See all 10 devices with their venues
   - Quickly identify which location has issues

4. **Maintenance**:
   - Filter by venue (future feature)
   - Update all devices at specific venue
   - Track uptime by location

---

**Status**: ✅ Feature deployed and ready to use!

**Try it now**: https://fleet.r58.itagenten.no

