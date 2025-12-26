# R58 Documentation Gap Analysis
**Generated**: December 26, 2025  
**Based on**: Component Inventory + Wiki Content Review

---

## Executive Summary

**Critical Finding**: 3 active services and 1 custom codebase are completely undocumented:
1. ❌ **r58-admin-api** (running service, port 8088)
2. ❌ **r58-fleet-agent** (running service, WebSocket client)
3. ❌ **vdo-signaling** (custom Node.js code, port 8443)
4. ⚠️ **raspberry.ninja** (mentioned but not detailed)

This is similar to how VDO.ninja was initially missed - these are **production components** that users need to understand.

---

## Gap Categories

### 🔴 Critical Gaps (Active Production Services)

#### 1. r58-admin-api Service
**Status**: ❌ COMPLETELY UNDOCUMENTED  
**Severity**: HIGH  
**Impact**: Users don't know this service exists

**What's Missing**:
- Service purpose and functionality
- API endpoints (/status, /devices, /encoders)
- Port (8088) and access method
- Relationship to main preke-recorder
- Why it exists (legacy Mekotronics code)
- Whether it's still needed

**Current State**:
- Running on port 8088
- Located at `/opt/r58/admin_api/main.py`
- FastAPI application
- Provides device/encoder detection
- Stream control (RTMP/SRT)
- **Not mentioned anywhere in wiki**

#### 2. r58-fleet-agent Service
**Status**: ❌ COMPLETELY UNDOCUMENTED  
**Severity**: HIGH  
**Impact**: Users don't know fleet management exists

**What's Missing**:
- Service purpose (fleet management)
- WebSocket connection to fleet.r58.itagenten.no
- Capabilities (remote commands, updates, monitoring)
- Security implications
- Configuration options
- How to disable if not needed

**Current State**:
- Running and active
- Located at `/opt/r58-fleet-agent/fleet_agent.py`
- Connects to `wss://fleet.r58.itagenten.no/ws`
- Reports device metrics every 10 seconds
- Can execute remote commands
- **Not mentioned anywhere in wiki**

#### 3. vdo-signaling Custom Code
**Status**: ❌ COMPLETELY UNDOCUMENTED  
**Severity**: CRITICAL  
**Impact**: Users don't know we have custom signaling logic

**What's Missing**:
- That this is **OUR CUSTOM CODE**, not standard VDO.ninja
- Custom room normalization logic
- Publisher tracking features
- Why we needed custom signaling
- How it differs from standard VDO.ninja server
- Configuration and customization options

**Current State**:
- Custom Node.js application at `/opt/vdo-signaling/vdo-server.js`
- Normalizes all rooms to "r58studio"
- Tracks r58-cam1/2/3 publishers
- Serves VDO.ninja web app
- **Wiki mentions "VDO.ninja signaling" but not that it's custom**

---

### 🟡 Important Gaps (Partial Documentation)

#### 4. raspberry.ninja Details
**Status**: ⚠️ MENTIONED BUT NOT DETAILED  
**Severity**: MEDIUM  
**Impact**: Users know it exists but not how it works

**What's Missing**:
- Version (9.0.0)
- How it works (GStreamer + WebRTC)
- Configuration options
- The 597KB publish.py script details
- Hardware encoding support
- Connection to vdo-signaling
- Service file details

**Current State**:
- Wiki mentions it exists
- Wiki explains limitations (P2P issues)
- **Missing**: Technical details, version, configuration

#### 5. MediaMTX Configuration
**Status**: ⚠️ PARTIALLY DOCUMENTED  
**Severity**: MEDIUM  
**Impact**: Users don't see full configuration

**What's Missing**:
- Complete mediamtx.yml content
- All path definitions (cam0-3, guests, speakers, etc.)
- ICE configuration details
- STUN server setup
- Port mappings explanation

**Current State**:
- Wiki mentions MediaMTX extensively
- **Missing**: Full config file documentation

#### 6. FRP Configuration
**Status**: ⚠️ PARTIALLY DOCUMENTED  
**Severity**: MEDIUM  
**Impact**: Users don't see all proxied services

**What's Missing**:
- Complete frpc.toml content
- All 8 proxy definitions
- Authentication token (redacted)
- SSH tunnel relationship

**Current State**:
- Wiki explains FRP concept
- **Missing**: Complete configuration details

---

### 🟢 Minor Gaps (Legacy/Unused)

#### 7. /opt/r58 Directory
**Status**: ❌ NOT DOCUMENTED  
**Severity**: LOW  
**Impact**: Users don't know about legacy code

**What's Missing**:
- That this is legacy Mekotronics code
- What's in it (admin_api, opencast_agent)
- Whether it's still needed
- Relationship to current system

#### 8. Disabled Services
**Status**: ❌ NOT DOCUMENTED  
**Severity**: LOW  
**Impact**: Users don't know what can be removed

**What's Missing**:
- List of 9 disabled services
- Why they're disabled
- Whether they can be removed
- What they were used for

---

## Comparison: Wiki vs Reality

### Services in Wiki ✅
- preke-recorder.service ✅
- mediamtx.service ✅
- frpc.service ✅
- vdo-ninja.service ✅ (just added)
- vdo-webapp.service ✅ (just added)
- ninja-publish-cam1/2/3.service ✅ (just added)

### Services NOT in Wiki ❌
- r58-admin-api.service ❌
- r58-fleet-agent.service ❌
- frp-ssh-tunnel.service ❌ (mentioned but not detailed)

### Code Directories in Wiki ✅
- /opt/preke-r58-recorder ✅
- /opt/vdo.ninja ✅ (just added)
- /opt/raspberry_ninja ⚠️ (mentioned, not detailed)

### Code Directories NOT in Wiki ❌
- /opt/vdo-signaling ❌ (CRITICAL - custom code!)
- /opt/r58 ❌
- /opt/r58-fleet-agent ❌
- /opt/mediamtx ⚠️ (config mentioned, not directory)
- /opt/frp ⚠️ (config mentioned, not directory)

---

## Impact Assessment

### User Confusion Risk: HIGH

**Scenario 1**: User SSHs to R58 and sees:
```bash
$ ps aux | grep python
root      ... /opt/r58-fleet-agent/fleet_agent.py
root      ... /opt/r58/.venv/bin/uvicorn admin_api.main:app
```

**Problem**: "What are these? Are they supposed to be running? Can I stop them?"  
**Current Answer**: Wiki doesn't mention them at all.

### Scenario 2**: User checks ports:
```bash
$ ss -tlnp | grep LISTEN
*:8088  ... admin_api
```

**Problem**: "What's on port 8088? Is it exposed? Is it secure?"  
**Current Answer**: Wiki doesn't document this port.

### Scenario 3**: Developer explores code:
```bash
$ ls /opt/
r58  r58-fleet-agent  vdo-signaling  ...
```

**Problem**: "What are these directories? Which ones are ours? Which are third-party?"  
**Current Answer**: Wiki doesn't explain the directory structure.

---

## Lessons from VDO.ninja Incident

**What Happened**:
- VDO.ninja was running in production
- Wiki didn't mention it at all
- User discovered it and asked: "Dont we have vdo.ninja running locally?"
- We had to add it retroactively

**Why It Happened**:
- Focus on main application (preke-recorder)
- Assumed "obvious" services didn't need documentation
- No systematic audit of all running services

**How to Prevent**:
1. ✅ Complete inventory (done)
2. ✅ Gap analysis (this document)
3. ⏭️ Update wiki with ALL components
4. ⏭️ Add documentation checklist
5. ⏭️ Regular audits

---

## Priority for Wiki Updates

### Must Add (Critical)
1. **r58-admin-api** - New wiki section
2. **r58-fleet-agent** - New wiki section
3. **vdo-signaling** - Update existing VDO.ninja section to clarify it's custom
4. **raspberry.ninja details** - Expand existing section

### Should Add (Important)
5. **Complete MediaMTX config** - Add config file section
6. **Complete FRP config** - Add config file section
7. **frp-ssh-tunnel** - Add to FRP section
8. **Directory structure** - Add /opt/ directory map

### Nice to Have (Minor)
9. **Legacy /opt/r58** - Add to "History & Decisions"
10. **Disabled services** - Add to troubleshooting
11. **Cleanup opportunities** - Add maintenance section

---

## Recommended Wiki Sections to Add

### 1. "System Services" Section
- All 11 active services
- Purpose of each
- Ports and access
- Dependencies
- How to restart/check status

### 2. "Directory Structure" Section
- /opt/ directory map
- What's in each directory
- Which are custom vs third-party
- Which are git repos

### 3. "Fleet Management" Section
- What r58-fleet-agent does
- How to configure
- Security considerations
- How to disable if not needed

### 4. "Legacy Components" Section
- /opt/r58 (Mekotronics code)
- r58-admin-api (why it exists)
- Disabled services (what they were)

### 5. "Configuration Files" Section
- Complete mediamtx.yml
- Complete frpc.toml
- /etc/r58/.env
- SSL certificates

---

## Next Actions

1. ✅ **Completed**: Component inventory
2. ✅ **Completed**: Gap analysis (this document)
3. ⏭️ **Next**: Update wiki with all missing components
4. ⏭️ **Then**: Create cleanup proposal
5. ⏭️ **Finally**: Add documentation checklist

---

## Success Criteria

**Wiki is complete when**:
- ✅ All 11 active services documented
- ✅ All /opt/ directories explained
- ✅ All configuration files detailed
- ✅ Custom code (vdo-signaling) clearly marked
- ✅ Legacy components explained
- ✅ User can understand entire system from wiki alone

**Prevention is successful when**:
- ✅ Documentation checklist exists
- ✅ New services trigger documentation update
- ✅ Regular audits scheduled
- ✅ No more "surprise" discoveries like VDO.ninja

