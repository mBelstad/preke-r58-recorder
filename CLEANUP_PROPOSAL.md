# R58 Cleanup and Optimization Proposal
**Generated**: December 26, 2025  
**Status**: FOR USER REVIEW - DO NOT EXECUTE WITHOUT APPROVAL

---

## Executive Summary

After comprehensive audit, we identified:
- **9 disabled services** that can be removed
- **Multiple backup files** cluttering the codebase
- **Untracked code** that should be reviewed
- **Legacy components** that may be obsolete
- **~290 archived markdown files** that could be consolidated

**Estimated Cleanup Impact**:
- Disk space saved: ~50-100MB
- Reduced confusion: High
- Risk: Low (all items are disabled/unused)

---

## Priority 1: Safe Removals (Low Risk)

### 1.1 Disabled Services (9 services)

These services are installed but not running and can be safely removed:

#### cloudflared.service
**Status**: Disabled  
**Reason**: Replaced by FRP tunnel  
**Last Used**: Before Dec 4, 2025

**Remove**:
```bash
sudo systemctl disable cloudflared
sudo rm /etc/systemd/system/cloudflared.service
sudo apt remove cloudflared  # If installed
sudo systemctl daemon-reload
```

**Risk**: ✅ None - FRP is working perfectly

---

#### ninja-publish-cam0.service
**Status**: Disabled  
**Reason**: Camera 0 not in use (using cam1/2/3)

**Remove**:
```bash
sudo rm /etc/systemd/system/ninja-publish-cam0.service
sudo systemctl daemon-reload
```

**Risk**: ✅ None - cam0 not configured

---

#### ninja-receive-guest1.service & ninja-receive-guest2.service
**Status**: Disabled  
**Reason**: Old approach for guest receiving (replaced by WHIP)

**Remove**:
```bash
sudo rm /etc/systemd/system/ninja-receive-guest{1,2}.service
sudo systemctl daemon-reload
```

**Risk**: ✅ None - WHIP/WHEP approach is working

---

#### ninja-rtmp-restream.service
**Status**: Disabled  
**Reason**: RTMP test service

**Remove**:
```bash
sudo rm /etc/systemd/system/ninja-rtmp-restream.service
sudo systemctl daemon-reload
```

**Risk**: ✅ None - test service

---

#### ninja-rtmp-test.service
**Status**: Disabled  
**Reason**: RTMP test service

**Remove**:
```bash
sudo rm /etc/systemd/system/ninja-rtmp-test.service
sudo systemctl daemon-reload
```

**Risk**: ✅ None - test service

---

#### ninja-rtsp-restream.service
**Status**: Disabled  
**Reason**: RTSP test service

**Remove**:
```bash
sudo rm /etc/systemd/system/ninja-rtsp-restream.service
sudo systemctl daemon-reload
```

**Risk**: ✅ None - test service

---

#### ninja-pipeline-test.service
**Status**: Disabled  
**Reason**: Pipeline test service

**Remove**:
```bash
sudo rm /etc/systemd/system/ninja-pipeline-test.service
sudo systemctl daemon-reload
```

**Risk**: ✅ None - test service

---

#### r58-opencast-agent.service
**Status**: Disabled  
**Reason**: Opencast integration not used

**Remove**:
```bash
sudo rm /etc/systemd/system/r58-opencast-agent.service
sudo systemctl daemon-reload
```

**Risk**: ✅ None - Opencast not in use

---

### 1.2 Backup Files in preke-r58-recorder

**Location**: `/opt/preke-r58-recorder/`

**Files to Remove**:
```
config.yml.backup.20251218_200817
src.backup.20251218_150555/
src.backup.20251218_200645/
src/config.py.backup.20251218_200736
src/main.py.backup.20251218_200736
src/main.py.backup.20251218_211233
src/static/switcher.html.backup.20251218_151529
```

**Remove**:
```bash
cd /opt/preke-r58-recorder
rm -rf *.backup.* src.backup.* src/*.backup.* src/static/*.backup.*
```

**Risk**: ✅ Low - all code is in git

---

### 1.3 Test HTML Files

**Location**: `/opt/preke-r58-recorder/src/static/`

**Files to Remove**:
```
camera_viewer.html
ninja_hls_viewer.html
ninja_join.html
ninja_pipeline_test.html
ninja_view.html
test_vdo_simple.html
```

**Remove**:
```bash
cd /opt/preke-r58-recorder/src/static
rm camera_viewer.html ninja_*.html test_*.html
```

**Risk**: ✅ Low - test files only

---

### 1.4 Archived Documentation (~290 files)

**Locations**:
- `docs/archive/` (150 files)
- `docs/archive-root/` (141 files)

**Proposal**: Create single archive tarball and remove directories

**Commands**:
```bash
cd /Users/mariusbelstad/R58\ app/preke-r58-recorder/docs
tar -czf archived-docs-dec26-2025.tar.gz archive/ archive-root/ archive-dec26/
# Review tarball, then:
rm -rf archive/ archive-root/ archive-dec26/
```

**Keep**:
- `docs/CURRENT_ARCHITECTURE.md`
- `docs/CLOUDFLARE_HISTORY.md`
- Active documentation

**Risk**: ✅ Low - all archived, can extract if needed

---

## Priority 2: Review Before Removal (Medium Risk)

### 2.1 /opt/fleet-agent Directory

**Status**: Not running, possibly duplicate of r58-fleet-agent

**Action Required**: Verify it's a duplicate

**Commands**:
```bash
# Compare with r58-fleet-agent
diff /opt/fleet-agent/fleet_agent.py /opt/r58-fleet-agent/fleet_agent.py

# If identical or obsolete:
sudo mv /opt/fleet-agent /opt/fleet-agent.backup
# Test for 1 week, then remove
```

**Risk**: ⚠️ Medium - verify it's not used

---

### 2.2 src/ninja/ Directory

**Status**: Untracked code in main repository

**Action Required**: Review contents and decide to commit or remove

**Commands**:
```bash
cd /opt/preke-r58-recorder
ls -la src/ninja/
# Review files, then either:
git add src/ninja/  # If needed
# OR
rm -rf src/ninja/   # If obsolete
```

**Risk**: ⚠️ Medium - may contain important code

---

### 2.3 Untracked Files

**Files**:
```
._config.yml
._mediamtx.yml
=1.6.0
=10.0.0
=12.0
src/._config.py
src/._main.py
src/._reveal_source.py
static/r58_screenshot.png
```

**Action Required**: Review and remove if not needed

**Risk**: ⚠️ Low-Medium - mostly temp files

---

## Priority 3: Test Before Removal (Higher Risk)

### 3.1 r58-admin-api.service

**Status**: Running on port 8088

**Reason for Removal**: Legacy code, preke-recorder provides same functionality

**Testing Process**:
1. Stop service: `sudo systemctl stop r58-admin-api`
2. Test preke-recorder for 1 week
3. Verify device detection still works
4. If OK, disable: `sudo systemctl disable r58-admin-api`
5. After 1 month, remove: `sudo rm /etc/systemd/system/r58-admin-api.service`

**Risk**: ⚠️ High - currently running service

**Recommendation**: Test thoroughly before removing

---

### 3.2 /opt/r58 Directory

**Status**: Legacy Mekotronics code

**Contains**:
- admin_api/ (used by r58-admin-api.service)
- opencast_agent/ (unused)
- scripts/ (may have useful utilities)
- ui/ (unused)

**Action Required**: 
1. Review scripts/ directory for useful utilities
2. Document any useful scripts
3. After r58-admin-api is removed, archive entire directory

**Commands**:
```bash
# After r58-admin-api is removed:
sudo mv /opt/r58 /opt/r58.backup.20251226
# Keep for 1 month, then remove
```

**Risk**: ⚠️ High - contains running service code

---

## Priority 4: Optimization Opportunities

### 4.1 Service Consolidation

**Observation**: 3 separate ninja-publish services for 3 cameras

**Potential Optimization**: Single service with 3 instances

**Benefit**: Easier management, consistent configuration

**Risk**: ⚠️ Medium - requires testing

**Recommendation**: Consider for future refactoring

---

### 4.2 Configuration Consolidation

**Observation**: Multiple config files
- /opt/preke-r58-recorder/config.yml
- /opt/mediamtx/mediamtx.yml
- /opt/frp/frpc.toml
- /etc/r58/.env

**Potential Optimization**: Single configuration source

**Benefit**: Easier management

**Risk**: ⚠️ High - major refactoring

**Recommendation**: Document current state, consider for v2.0

---

### 4.3 Log Rotation

**Observation**: Multiple services writing logs

**Current State**:
- r58-fleet-agent: Has log rotation (10MB, 3 files)
- Others: Systemd journal only

**Recommendation**: Verify journald log rotation is configured

**Commands**:
```bash
# Check journal size
journalctl --disk-usage

# Configure if needed
sudo nano /etc/systemd/journald.conf
# Set: SystemMaxUse=500M
```

---

## Summary of Recommendations

### Execute Immediately (User Approval Required)

1. ✅ Remove 9 disabled services
2. ✅ Remove backup files
3. ✅ Remove test HTML files
4. ✅ Archive old documentation

**Commands Script**:
```bash
#!/bin/bash
# R58 Cleanup Script - Dec 26, 2025
# DO NOT RUN WITHOUT USER APPROVAL

set -e

echo "Removing disabled services..."
sudo rm /etc/systemd/system/cloudflared.service
sudo rm /etc/systemd/system/ninja-publish-cam0.service
sudo rm /etc/systemd/system/ninja-receive-guest{1,2}.service
sudo rm /etc/systemd/system/ninja-rtmp-{restream,test}.service
sudo rm /etc/systemd/system/ninja-rtsp-restream.service
sudo rm /etc/systemd/system/ninja-pipeline-test.service
sudo rm /etc/systemd/system/r58-opencast-agent.service
sudo systemctl daemon-reload

echo "Removing backup files..."
cd /opt/preke-r58-recorder
rm -rf *.backup.* src.backup.* src/*.backup.* src/static/*.backup.*

echo "Removing test files..."
cd /opt/preke-r58-recorder/src/static
rm -f camera_viewer.html ninja_*.html test_*.html

echo "Archiving old docs..."
cd /Users/mariusbelstad/R58\ app/preke-r58-recorder/docs
tar -czf archived-docs-dec26-2025.tar.gz archive/ archive-root/ archive-dec26/
rm -rf archive/ archive-root/ archive-dec26/

echo "Cleanup complete!"
echo "Disk space saved: $(du -sh archived-docs-dec26-2025.tar.gz)"
```

### Review and Decide

1. ⏳ Review `/opt/fleet-agent` - duplicate?
2. ⏳ Review `src/ninja/` - commit or remove?
3. ⏳ Review untracked files - keep or remove?

### Test Before Removal

1. ⏳ Test without r58-admin-api (1 week)
2. ⏳ Archive /opt/r58 after admin-api removed

### Future Optimization

1. 💡 Consider service consolidation
2. 💡 Consider configuration consolidation
3. 💡 Verify log rotation

---

## Rollback Plan

If anything breaks after cleanup:

### Restore Services
```bash
# Services are in git history
cd /Users/mariusbelstad/R58\ app/preke-r58-recorder
git checkout HEAD~1 -- deployment/systemd/
# Copy back to /etc/systemd/system/
```

### Restore Docs
```bash
cd /Users/mariusbelstad/R58\ app/preke-r58-recorder/docs
tar -xzf archived-docs-dec26-2025.tar.gz
```

### Restore Backup Files
```bash
# If needed, restore from git
cd /opt/preke-r58-recorder
git checkout HEAD -- config.yml src/
```

---

## Questions for User

Before proceeding, please confirm:

1. ✅ **Remove 9 disabled services?** (cloudflared, ninja-*, r58-opencast-agent)
2. ✅ **Remove backup files?** (*.backup.*, src.backup.*)
3. ✅ **Remove test HTML files?** (ninja_*.html, test_*.html)
4. ✅ **Archive old documentation?** (~290 markdown files → tarball)
5. ❓ **Review src/ninja/ directory?** (What's in there?)
6. ❓ **Test without r58-admin-api?** (Stop for 1 week, monitor)
7. ❓ **Remove /opt/fleet-agent?** (After verifying it's duplicate)

---

## Next Steps

After user approval:

1. Create cleanup script
2. Test on local copy first
3. Run on R58 device
4. Monitor for issues
5. Document changes
6. Update wiki if needed

---

**Status**: AWAITING USER APPROVAL  
**Risk Level**: LOW (for Priority 1 items)  
**Estimated Time**: 15 minutes  
**Reversible**: YES (all items can be restored)

