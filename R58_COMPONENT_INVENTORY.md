# R58 Complete Component Inventory
**Generated**: December 26, 2025  
**Status**: Verified via SSH

---

## Active Services (11 Running)

| Service | Status | Port | Purpose | Documented |
|---------|--------|------|---------|------------|
| **preke-recorder.service** | ✅ Active | 8000 | Main FastAPI application | ✅ Yes (wiki) |
| **mediamtx.service** | ✅ Active | 8889, 8554, 9997 | Streaming server (WHEP/RTSP/API) | ✅ Yes (wiki) |
| **frpc.service** | ✅ Active | - | FRP client (tunnel to VPS) | ✅ Yes (wiki) |
| **frp-ssh-tunnel.service** | ✅ Active | - | SSH tunnel for FRP control | ⚠️ Partial |
| **vdo-ninja.service** | ✅ Active | 8443 | VDO.ninja signaling server | ✅ Just added |
| **vdo-webapp.service** | ✅ Active | 8444 | VDO.ninja web app (HTTP server) | ✅ Just added |
| **ninja-publish-cam1.service** | ✅ Active | - | raspberry.ninja publisher (cam1) | ✅ Just added |
| **ninja-publish-cam2.service** | ✅ Active | - | raspberry.ninja publisher (cam2) | ✅ Just added |
| **ninja-publish-cam3.service** | ✅ Active | - | raspberry.ninja publisher (cam3) | ✅ Just added |
| **r58-admin-api.service** | ✅ Active | 8088 | Admin API (legacy Mekotronics) | ❌ NO |
| **r58-fleet-agent.service** | ✅ Active | - | Fleet management agent | ❌ NO |

---

## Disabled/Unused Services (Not Running)

| Service | Status | Purpose | Action Needed |
|---------|--------|---------|---------------|
| **cloudflared.service** | ❌ Disabled | Old Cloudflare tunnel | 🗑️ Can be removed |
| **ninja-publish-cam0.service** | ❌ Disabled | Publisher for cam0 (unused) | 🗑️ Can be removed |
| **ninja-receive-guest1.service** | ❌ Disabled | Guest receiver (old approach) | 🗑️ Can be removed |
| **ninja-receive-guest2.service** | ❌ Disabled | Guest receiver (old approach) | 🗑️ Can be removed |
| **ninja-rtmp-restream.service** | ❌ Disabled | RTMP restream test | 🗑️ Can be removed |
| **ninja-rtmp-test.service** | ❌ Disabled | RTMP test | 🗑️ Can be removed |
| **ninja-rtsp-restream.service** | ❌ Disabled | RTSP restream test | 🗑️ Can be removed |
| **ninja-pipeline-test.service** | ❌ Disabled | Pipeline test | 🗑️ Can be removed |
| **r58-opencast-agent.service** | ❌ Disabled | Opencast integration (unused) | 🗑️ Can be removed |

---

## Code Directories (/opt/)

| Directory | Size | Purpose | Documented | Notes |
|-----------|------|---------|------------|-------|
| **/opt/preke-r58-recorder** | 21 subdirs | Main application (FastAPI) | ✅ Yes | Active development, git tracked |
| **/opt/mediamtx** | Config only | MediaMTX config (mediamtx.yml) | ⚠️ Partial | Config documented, not directory |
| **/opt/frp** | Binary + config | FRP client binary + frpc.toml | ⚠️ Partial | Config documented |
| **/opt/vdo.ninja** | 15 subdirs | VDO.ninja web app (v28+) | ✅ Just added | Git repo, commit fa3df7a1 |
| **/opt/vdo-signaling** | Node.js app | **CUSTOM signaling server** | ❌ NO | **CRITICAL - Our custom code!** |
| **/opt/raspberry_ninja** | 13 subdirs | raspberry.ninja publisher (v9.0.0) | ⚠️ Partial | Git repo, commit 29ce989 |
| **/opt/r58** | 11 subdirs | **Legacy Mekotronics code** | ❌ NO | Contains admin_api, opencast_agent |
| **/opt/r58-fleet-agent** | Python script | **Fleet management agent** | ❌ NO | **CRITICAL - Active service!** |
| **/opt/fleet-agent** | Python script | Duplicate/old fleet agent? | ❌ NO | May be obsolete |

---

## Configuration Files

| File | Purpose | Documented | Notes |
|------|---------|------------|-------|
| `/opt/mediamtx/mediamtx.yml` | MediaMTX config | ⚠️ Partial | WebRTC, RTSP, paths config |
| `/opt/frp/frpc.toml` | FRP client config | ⚠️ Partial | 8 proxy definitions |
| `/opt/preke-r58-recorder/config.yml` | Main app config | ✅ Yes | Local modifications exist |
| `/etc/r58/.env` | R58 environment vars | ❌ NO | Used by admin-api |
| `/opt/vdo-signaling/vdo-server.js` | **Custom signaling logic** | ❌ NO | Room normalization, publisher tracking |
| `/opt/vdo-signaling/cert.pem` | SSL cert (self-signed) | ❌ NO | For local HTTPS |
| `/opt/vdo-signaling/key.pem` | SSL key | ❌ NO | For local HTTPS |

---

## Network Ports Summary

| Port | Service | Protocol | Exposed via FRP | Public URL |
|------|---------|----------|-----------------|------------|
| 8000 | preke-recorder | HTTP | ✅ → 18000 | r58-api.itagenten.no |
| 8088 | r58-admin-api | HTTP | ❌ | Local only |
| 8443 | vdo-ninja | HTTPS/WSS | ✅ → 18443 | r58-vdo.itagenten.no |
| 8444 | vdo-webapp | HTTP | ✅ → 18444 | - |
| 8554 | MediaMTX RTSP | RTSP | ❌ | Local only |
| 8889 | MediaMTX WebRTC | HTTP/WS | ✅ → 18889 | r58-mediamtx.itagenten.no |
| 8189 | MediaMTX WebRTC | UDP | ✅ → 18189 | - |
| 8190 | MediaMTX WebRTC | TCP | ✅ → 8190 | - |
| 9997 | MediaMTX API | HTTP | ✅ → 19997 | - |
| 1935 | MediaMTX RTMP | RTMP | ❌ | Local only |
| 22 | SSH | SSH | ✅ → 10022 | 65.109.32.111:10022 |

---

## Critical Undocumented Components

### 1. **r58-admin-api** (ACTIVE SERVICE)
- **Location**: `/opt/r58/admin_api/main.py`
- **Port**: 8088
- **Purpose**: Legacy Mekotronics admin API
- **Features**:
  - Stream control (RTMP/SRT)
  - Device detection (/dev/video*)
  - Encoder detection (v4l2h264enc, mpph264enc)
  - Systemd service management
- **Status**: Running but not exposed publicly
- **Documentation**: ❌ NONE

### 2. **r58-fleet-agent** (ACTIVE SERVICE)
- **Location**: `/opt/r58-fleet-agent/fleet_agent.py`
- **Purpose**: Fleet management WebSocket agent
- **Features**:
  - Connects to `wss://fleet.r58.itagenten.no/ws`
  - Reports device status (CPU, memory, disk)
  - Executes remote commands
  - Software update handling
  - 10-second heartbeat interval
- **Status**: Running and connecting to fleet API
- **Documentation**: ❌ NONE

### 3. **vdo-signaling** (CUSTOM CODE!)
- **Location**: `/opt/vdo-signaling/vdo-server.js`
- **Purpose**: Custom VDO.ninja signaling server
- **Features**:
  - Room normalization (all rooms → "r58studio")
  - Publisher tracking (r58-cam1/2/3)
  - WebSocket signaling
  - Serves VDO.ninja web app
- **Status**: Running on port 8443
- **Documentation**: ❌ NONE - **THIS IS CRITICAL!**

### 4. **raspberry.ninja** (PARTIALLY DOCUMENTED)
- **Location**: `/opt/raspberry_ninja/publish.py`
- **Version**: 9.0.0
- **Purpose**: WebRTC publisher for V4L2 devices
- **Features**:
  - GStreamer-based WebRTC publishing
  - Connects to VDO.ninja signaling
  - Hardware encoding support
  - 597KB Python script (complex!)
- **Status**: 3 instances running (cam1/2/3)
- **Documentation**: ⚠️ Mentioned but not detailed

---

## Local File Modifications (Not in Git)

On R58 device in `/opt/preke-r58-recorder`:

**Modified Files**:
- `config.yml` - 1 line changed
- `reveal.js` - submodule modified

**Untracked Files/Directories**:
- `data/sessions/` - Runtime session data
- `presentations/` - Presentation files
- `scenes/*.json` - Scene configurations
- `src/ninja/` - Ninja integration code (untracked!)
- `src.backup.*` - Multiple backup directories
- `*.backup.*` - Various backup files
- Test HTML files (camera_viewer, ninja_*, etc.)

**Action Needed**: 
- ⚠️ Review `src/ninja/` - may contain important code
- 🗑️ Clean up backup files and test files

---

## Version Information

| Component | Version | Source |
|-----------|---------|--------|
| **raspberry.ninja** | 9.0.0 | /opt/raspberry_ninja/VERSION |
| **VDO.ninja** | v28+ | Git commit fa3df7a1 |
| **MediaMTX** | v1.15.5+ | Verified in docs |
| **GStreamer** | 1.22.9 | Standard Debian + Rockchip plugins |
| **Python** | 3.11+ | preke-recorder venv |
| **Node.js** | System | For vdo-signaling |

---

## Documentation Gaps Summary

### Critical Gaps (Active Services)
1. ❌ **r58-admin-api** - Running service, no docs
2. ❌ **r58-fleet-agent** - Running service, no docs
3. ❌ **vdo-signaling** - Custom code, no docs
4. ⚠️ **raspberry.ninja** - Mentioned but not detailed

### Important Gaps (Configs)
5. ❌ `/etc/r58/.env` - Environment configuration
6. ⚠️ MediaMTX full config - Only partially documented
7. ⚠️ FRP full config - Only partially documented
8. ❌ SSL certificates (vdo-signaling)

### Minor Gaps (Legacy/Unused)
9. ❌ `/opt/r58` - Legacy Mekotronics code
10. ❌ `/opt/fleet-agent` - Duplicate or old?

---

## Cleanup Opportunities

### High Priority Removals
1. 🗑️ **cloudflared.service** - Replaced by FRP
2. 🗑️ **8 disabled ninja services** - Test/old services
3. 🗑️ **r58-opencast-agent.service** - Unused
4. 🗑️ Backup files in preke-r58-recorder (src.backup.*, *.backup.*)
5. 🗑️ Test HTML files (ninja_*.html, test_*.html)

### Medium Priority
6. 🔍 **Review `/opt/fleet-agent`** - May be duplicate
7. 🔍 **Review `src/ninja/`** - Untracked code
8. 🗑️ ~290 archived markdown files in docs/

### Low Priority
9. 🔍 **Review `/opt/r58`** - Legacy code, may have useful parts
10. 🧹 Clean up untracked files in preke-r58-recorder

---

## Next Steps

1. ✅ **Complete** - Deep exploration done
2. ⏭️ **Next** - Gap analysis against wiki
3. ⏭️ **Then** - Update wiki with missing components
4. ⏭️ **Then** - Create cleanup proposal for user
5. ⏭️ **Finally** - Add prevention checklist



