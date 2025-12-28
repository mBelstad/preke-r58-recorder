# User Guide

> How to use the R58 Recorder and Mixer for professional video production.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Recorder Mode](#recorder-mode)
3. [Mixer Mode](#mixer-mode)
4. [Library & Playback](#library--playback)
5. [Troubleshooting](#troubleshooting)
6. [Best Practices](#best-practices)

---

## Getting Started

### Accessing the R58 Interface

1. **Local Access** (same network):
   - Open browser to `http://r58.local:8000` or `http://<device-ip>:8000`
   
2. **Remote Access**:
   - Contact your administrator for remote access URL

3. **Installing as PWA** (recommended):
   - Click "Install" in browser menu (Chrome/Edge)
   - Or use "Add to Home Screen" (Safari/mobile)

### Interface Overview

```
┌─────────────────────────────────────────────────────────┐
│  R58 Studio                          [Status] [Admin]  │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  [Home]  │                                              │
│          │              Main Content Area               │
│[Recorder]│                                              │
│          │         (Changes based on mode)              │
│ [Mixer]  │                                              │
│          │                                              │
│[Library] │                                              │
│          │                                              │
├──────────┴──────────────────────────────────────────────┤
│  cam1: ● | cam2: ● | cam3: ○ | Storage: 234GB free     │
└─────────────────────────────────────────────────────────┘
```

### Status Indicators

| Icon | Meaning |
|------|---------|
| ● (green) | Signal detected, input active |
| ○ (gray) | No signal |
| ● (red) | Recording active |
| ⚠ (yellow) | Warning (low storage, etc.) |

---

## Recorder Mode

### Quick Start Recording

1. **Connect HDMI sources** to R58 input ports
2. **Navigate** to Recorder tab
3. **Verify** green signal indicators for connected inputs
4. **Click** "Start Recording"
5. **Monitor** the duration timer and file sizes
6. **Click** "Stop Recording" when done

### Understanding the Recorder Interface

```
┌─────────────────────────────────────────────────────────┐
│ Recorder                                                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │  CAM 1  │ │  CAM 2  │ │  CAM 3  │ │  CAM 4  │       │
│  │ [VIDEO] │ │ [VIDEO] │ │   NO    │ │   NO    │       │
│  │ 1080p30 │ │ 1080p30 │ │ SIGNAL  │ │ SIGNAL  │       │
│  │ ●Active │ │ ●Active │ │ ○       │ │ ○       │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                         │
│  Duration: 00:15:32        Total: 2.4 GB               │
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │            ■ STOP RECORDING                   │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Recording Options

| Option | Description | Default |
|--------|-------------|---------|
| Session Name | Optional name for the recording | Auto-generated |
| Input Selection | Which inputs to record | All with signal |
| Codec | H.264 or H.265 (device dependent) | H.264 |
| Resolution | Recording resolution | Source resolution |

### During Recording

- **Duration Timer**: Shows elapsed recording time
- **Bytes Counter**: Shows file size per input
- **Signal Status**: Monitor for signal loss
- **Storage Warning**: Appears when disk space is low

### Stopping a Recording

1. Click "Stop Recording" button
2. Wait for finalization (may take a few seconds for long recordings)
3. Files appear in Library automatically

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Start/Stop recording |
| R | Start recording |
| S | Stop recording |
| 1-4 | Toggle input selection |

---

## Mixer Mode

### Overview

The Mixer uses VDO.ninja for live video switching and composition.

```
┌─────────────────────────────────────────────────────────┐
│ Mixer                                                   │
├─────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────┐ │
│  │                                                   │ │
│  │              VDO.ninja Mixer                      │ │
│  │                                                   │ │
│  │    ┌─────────────┐  ┌─────────────┐              │ │
│  │    │   Camera 1  │  │   Camera 2  │              │ │
│  │    └─────────────┘  └─────────────┘              │ │
│  │                                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  Sources: [CAM1] [CAM2] [+Add]    Scene: [Grid] [Solo] │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Adding Sources

1. **HDMI Inputs**: Automatically available as sources
2. **Remote Guests**: Share invite link for browser-based guests
3. **Screen Share**: Add computer screens to the mix

### Switching Scenes

| Scene | Description |
|-------|-------------|
| Grid | Show all sources in grid layout |
| Solo | Full-screen single source |
| PiP | Picture-in-picture layout |
| Custom | User-defined layouts |

### Audio Control

- **Volume Sliders**: Adjust individual source volumes
- **Mute Buttons**: Quickly mute/unmute sources
- **Audio Meter**: Monitor audio levels

### Recording the Mix

You can record while mixing:

1. Start the mixer and compose your scene
2. Navigate to Recorder tab
3. The program output is available as a recording source
4. Start recording as normal

---

## Library & Playback

### Accessing Recordings

1. Navigate to **Library** tab
2. Browse recordings by date or session name
3. Click to preview or download

### File Organization

```
/opt/r58/recordings/
├── 2024-12-28/
│   ├── session-abc123/
│   │   ├── cam1_20241228_100000.mp4
│   │   ├── cam2_20241228_100000.mp4
│   │   └── metadata.json
│   └── session-def456/
│       └── ...
└── 2024-12-27/
    └── ...
```

### Downloading Files

1. **Single File**: Click download icon next to file
2. **Session Bundle**: Download all files from a session as ZIP
3. **Bulk Export**: Use USB export for large transfers

### Managing Storage

- View storage usage in status bar
- Delete old recordings from Library
- Configure auto-cleanup rules in Settings

---

## Troubleshooting

### No Video Signal

**Symptoms**: Gray box, "No Signal" indicator

**Solutions**:
1. Check HDMI cable connection
2. Verify source device is outputting video
3. Try a different HDMI port
4. Restart source device
5. Check port mapping in Settings

### Recording Won't Start

**Symptoms**: Start button unresponsive, error message

**Solutions**:
1. Check storage space (need >1GB free)
2. Verify at least one input has signal
3. Check for stuck recordings in status
4. Restart R58 services if needed

```bash
# On R58 device
sudo systemctl restart r58-api r58-pipeline
```

### VDO.ninja Won't Load

**Symptoms**: Black iframe, loading spinner

**Solutions**:
1. Refresh the page
2. Check VDO.ninja service status
3. Verify network connectivity
4. Check browser console for errors

### WebSocket Disconnects

**Symptoms**: "Reconnecting" message, stale data

**Solutions**:
1. Check network stability
2. Wait for automatic reconnection
3. Refresh page if reconnection fails
4. Check API service status

### Choppy Video Preview

**Symptoms**: Stuttering, frame drops

**Solutions**:
1. Check network bandwidth
2. Reduce number of active previews
3. Use lower-latency preview mode
4. Check CPU/GPU utilization

### Recording Files Corrupted

**Symptoms**: File won't play, incomplete file

**Solutions**:
1. Check if recording stopped properly
2. Try recovering with ffmpeg:
```bash
ffmpeg -i corrupted.mp4 -c copy recovered.mp4
```
3. Check disk space wasn't exhausted
4. Review logs for encoder errors

---

## Best Practices

### Before Recording

- [ ] Verify all inputs have stable signal
- [ ] Check available storage space
- [ ] Test preview streams work
- [ ] Confirm recording settings

### During Recording

- [ ] Monitor duration and file sizes
- [ ] Watch for signal loss warnings
- [ ] Don't disconnect sources mid-recording
- [ ] Avoid other heavy operations on device

### After Recording

- [ ] Verify files in Library
- [ ] Spot-check playback quality
- [ ] Backup important recordings
- [ ] Clean up test recordings

### For Live Events

1. **Pre-show**
   - Arrive early for setup
   - Test all sources and connections
   - Do a test recording
   - Verify network connectivity

2. **During Show**
   - Have backup recording running
   - Monitor storage levels
   - Keep source devices charged

3. **Post-show**
   - Don't power off until files are verified
   - Download backups immediately
   - Document any issues

### Storage Management

- Keep at least 10% disk space free
- Archive old recordings regularly
- Use external storage for long-term backup
- Enable storage warnings in Settings

### Network Tips

- Use wired Ethernet when possible
- Avoid WiFi for critical productions
- Reserve bandwidth for R58 device
- Test remote access before events

---

## Quick Reference

### Recording Workflow

```
1. Connect sources → 2. Check signals → 3. Start recording →
4. Monitor status → 5. Stop recording → 6. Verify files
```

### Mixer Workflow

```
1. Add sources → 2. Arrange layout → 3. Set audio levels →
4. Switch scenes → 5. (Optional) Record output
```

### Emergency Procedures

**Recording Stuck**:
```bash
curl -X POST http://localhost:8000/api/v1/recorder/stop
```

**Force Restart Services**:
```bash
sudo systemctl restart r58-api r58-pipeline
```

**Check System Health**:
```bash
curl http://localhost:8000/api/v1/health/detailed | jq
```

