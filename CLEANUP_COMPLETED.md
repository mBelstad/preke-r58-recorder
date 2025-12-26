# R58 Cleanup - COMPLETED
**Date**: December 26, 2025

---

## What Was Cleaned

### Services Removed (7)
| Service | Reason |
|---------|--------|
| cloudflared.service | Replaced by FRP |
| ninja-receive-guest1.service | Old guest approach, unused |
| ninja-receive-guest2.service | Old guest approach, unused |
| ninja-rtmp-restream.service | Test service |
| ninja-rtmp-test.service | Test service |
| ninja-rtsp-restream.service | Test service |
| ninja-pipeline-test.service | Test service |

### Services KEPT (per user request)
| Service | Reason |
|---------|--------|
| ninja-publish-cam0.service | User requested to keep |
| r58-opencast-agent.service | User requested to keep |

### Files Removed from R58
**Junk Files** (8):
- ._config.yml, ._mediamtx.yml (macOS metadata)
- =1.6.0, =10.0.0, =12.0 (failed pip installs)
- src/._config.py, src/._main.py, src/._reveal_source.py

**Backup Files** (5+):
- config.yml.backup.*
- src/config.py.backup.*
- src/main.py.backup.*
- src/static/switcher.html.backup.*
- src.backup.20251218_150555/ (entire directory)
- src.backup.20251218_200645/ (entire directory)

**Test HTML Files** (6):
- camera_viewer.html
- ninja_hls_viewer.html
- ninja_join.html
- ninja_pipeline_test.html
- ninja_view.html
- test_vdo_simple.html

### Documentation Archived
- ~290 markdown files from docs/archive*, docs/archive-root/, docs/archive-dec26/
- Archived to: docs/archived-docs-dec26-2025.tar.gz (700KB)

---

## What Was NOT Cleaned (For Later Review)

### src/ninja/ Directory
**Status**: Kept for user decision  
**Contents**: Custom WebRTC plugin (publisher, subscriber, signaling, room)  
**Decision Needed**: Commit to git or remove?

### /opt/fleet-agent Directory
**Status**: Kept, documented as older version  
**Action**: Wiki updated to explain difference vs /opt/r58-fleet-agent

### /opt/r58 Directory
**Status**: Kept (contains running service code)  
**Reason**: r58-admin-api.service uses this

### r58-admin-api.service
**Status**: Kept (running service)  
**Reason**: Provides device detection, may be useful

### scenes/ Directory
**Status**: IMPORTANT - Not touched!  
**Contents**: 22 mixer scene presets (quad, pip, interview, etc.)

---

## Pending TODOs (For Later)

- [ ] Service Consolidation
- [ ] Configuration Consolidation
- [ ] Log Rotation verification

---

## Space Saved

**On R58 Device**:
- ~100 backup/test files removed
- 7 service files removed

**Local Repository**:
- ~290 markdown files archived (712KB tarball)

---

## Remaining Cleanup Tasks

1. **src/ninja/** - User decision: commit or remove?
2. **Test without r58-admin-api** - If redundant, can stop later
3. **Consider removing /opt/fleet-agent** - It's obsolete copy

---

## Research Summary

### src/ninja/ Directory
Custom WebRTC plugin we developed as alternative to raspberry.ninja:
- publisher.py - Publish cameras via WebRTC
- subscriber.py - Receive guests via WebRTC
- signaling.py - WebSocket signaling server
- room.py - Participant management

**Created**: Dec 18, 2025  
**Status**: Experimental, untracked in git  
**Decision**: Commit to preserve, or remove if fully replaced by raspberry.ninja?

### Untracked Files Explained
- macOS metadata (._*) - JUNK, removed
- Failed pip output (=*) - JUNK, removed
- scenes/*.json - IMPORTANT runtime data, kept

### /opt/r58 Directory (Mekotronics)
Original vendor code with:
- admin_api/ (running service)
- scripts/ (useful shell scripts)
- ui/ (touch panel)
- opencast_agent/ (unused)

### r58-admin-api vs preke-recorder
| Feature | r58-admin-api | preke-recorder |
|---------|---------------|----------------|
| Device detection | ✅ | ✅ |
| Encoder detection | ✅ | ✅ |
| Stream control | RTMP/SRT only | WebRTC/WHEP |
| Recording | Basic | Full-featured |
| Mixer | ❌ | ✅ |
| Port | 8088 (local) | 8000 (exposed) |

### /opt/fleet-agent vs /opt/r58-fleet-agent
| Feature | fleet-agent | r58-fleet-agent |
|---------|-------------|-----------------|
| Heartbeat | 30 seconds | 10 seconds |
| Logging | Basic | Rotating (10MB) |
| Verbosity | High | Low |
| Status | OLD | CURRENT |

---

## Verification

Services remaining:
```
ninja-publish-cam0.service (disabled, kept)
ninja-publish-cam1.service (active)
ninja-publish-cam2.service (active)
ninja-publish-cam3.service (active)
r58-opencast-agent.service (disabled, kept)
```

All other ninja-* and cloudflared services removed.

---

**Cleanup Status**: ✅ COMPLETE  
**Date**: December 26, 2025

