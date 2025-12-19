# Project Handoff - December 17, 2025

## Project Overview
Multi-camera video recording system for Mekotronics R58 4x4 3S (RK3588). Records from 4 HDMI inputs, provides live preview via web interface, streams to MediaMTX.

## Current Branch
`always-on-ingest`

## System Status

| Camera | Device | Resolution | Status |
|--------|--------|------------|--------|
| cam0 | /dev/video0 | - | No signal (no HDMI connected) |
| cam1 | /dev/video60 | 1920x1080 | Working |
| cam2 | /dev/video11 | 3840x2160 | Streaming but frozen in browser (hardware issue) |
| cam3 | /dev/video22 | 1920x1080 | Working |

## Work Completed Today

### 1. HLS Optimization (Complete)
- Added Stream Mode selector (Low Latency / Balanced / Stable)
- Made "Stable" mode extremely aggressive (30-90s buffers) for bad connections
- Added freeze detection with auto-recovery
- Added stream synchronization (±1s drift tolerance)
- Tuned MediaMTX HLS settings

### 2. 4K Encoding Optimization (Complete)
- Optimized encoder for cam2 (4K source): ultrafast preset, 6 threads
- Reduced CPU load for 4K→1080p scaling
- **Result**: Backend works, but cam2 still frozen in browser (likely camera hardware issue)

### 3. Documentation Created
- `SESSION_SUMMARY_DEC17.md` - Full session details
- `STABLE_MODE_IMPROVEMENTS.md` - Buffer/freeze improvements
- `CAM2_4K_FIX.md` - 4K investigation report
- `HLS_OPTIMIZATION_TEST_RESULTS.md` - Test results

## Next Task: Recording Quality + Library Page

### Plan Location
`.cursor/plans/recording_ef9b6b8b.plan.md` (or `~/.cursor/plans/`)

### Tasks
1. **Fix recording quality** - Add `faststart=true` to mp4mux in `src/pipelines.py`
2. **Add API endpoint** - `/api/recordings` returning grouped recordings by session
3. **Create library.html** - Simple page to browse and play recordings
4. **Add navigation** - Link from main page to library
5. **Test playback** - Verify recordings play in browser

### Key Files
- `src/pipelines.py` - Recording pipeline (line ~600)
- `src/main.py` - API endpoints (existing `/recordings/{cam_id}` at line 632)
- `src/static/index.html` - Main page (for navigation link)
- `src/static/library.html` - New file to create

### Recording Details
- **Location**: `/mnt/sdcard/recordings/camX/recording_YYYYMMDD_HHMMSS.mp4`
- **Format**: H.264 in MP4 container
- **Bitrate**: 5000 kbps (configured)
- **Issue**: Missing `faststart` flag for browser playback

## Remote Access
- **Web GUI**: https://recorder.itagenten.no
- **SSH**: `ssh linaro@r58.itagenten.no` (use SSH keys - see SECURITY_FIX.md)

## Key Technical Notes
1. Recording subscribes to MediaMTX RTSP streams (not direct V4L2)
2. Ingest always streams H.264 regardless of codec config
3. cam2 outputs native 4K but streams scaled to 1080p
4. rkcif devices require initialization via subdev before use

## Reference Files
- `.cursor/project-summary.md` - Full project documentation
- `config.yml` - Camera configuration
- `mediamtx.yml` - MediaMTX streaming config

