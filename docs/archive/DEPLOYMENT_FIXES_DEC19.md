# Deployment Guide - December 19, 2025 Fixes
**7 Improvements Ready for Deployment**

---

## Changes Summary

### Code Changes
- 8 files modified
- 260 insertions, 73 deletions
- All changes backward compatible
- No breaking changes

### Files Modified
1. `src/config.py` - Added camera enabled flag
2. `src/ingest.py` - Skip disabled cameras properly
3. `src/main.py` - FastAPI lifespan migration
4. `src/gst_utils.py` - Better error messages
5. `src/static/index.html` - Fixed camera status display
6. `src/static/switcher.html` - Enhanced HLS fallback
7. `src/static/library.html` - Improved thumbnails
8. `src/static/guest_join.html` - Better device detection

---

## Improvements Included

### 1. Camera Status Display Fix
**Impact**: Users see accurate camera status  
**Change**: Frontend now uses correct API endpoint  
**Benefit**: No more confusion about camera state

### 2. Remote Switcher Video
**Impact**: Switcher works remotely via Cloudflare Tunnel  
**Change**: Enhanced HLS fallback for remote access  
**Benefit**: Can use switcher from anywhere

### 3. Library Thumbnails
**Impact**: Faster library browsing  
**Change**: Better timeout and error handling  
**Benefit**: Clear feedback when thumbnails load slowly

### 4. Guest Device Detection
**Impact**: Better guest experience  
**Change**: Comprehensive error handling  
**Benefit**: Clear error messages for permission issues

### 5. Disabled Camera Support
**Impact**: Cleaner system with unused cameras  
**Change**: Added enabled flag to camera config  
**Benefit**: No more errors from disconnected cameras

### 6. FastAPI Modernization
**Impact**: No deprecation warnings  
**Change**: Migrated to lifespan context manager  
**Benefit**: Future-proof code, cleaner startup

### 7. macOS Development
**Impact**: Easier local development  
**Change**: Helpful GStreamer installation guide  
**Benefit**: New developers can set up faster

---

## Deployment Steps

### Option 1: Quick Deploy (Recommended)
```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./deploy.sh r58.itagenten.no linaro
```

### Option 2: Manual Deploy
```bash
# 1. SSH to R58
ssh linaro@r58.itagenten.no

# 2. Navigate to app directory
cd /home/rock/preke-r58-recorder

# 3. Pull latest changes
git pull origin feature/webrtc-switcher-preview

# 4. Restart service
sudo systemctl restart preke-recorder

# 5. Check status
sudo systemctl status preke-recorder
```

---

## Testing After Deployment

### 1. Verify Service Started
```bash
ssh linaro@r58.itagenten.no
sudo systemctl status preke-recorder
# Should show "active (running)"
```

### 2. Check for Warnings
```bash
ssh linaro@r58.itagenten.no
sudo journalctl -u preke-recorder -n 50 | grep -i "deprecation\|warning"
# Should see NO deprecation warnings
```

### 3. Test Camera Status
```bash
curl https://recorder.itagenten.no/api/ingest/status
# cam0 should show "idle" (disabled)
# cam1, cam2, cam3 should show "streaming"
```

### 4. Test Switcher
- Open: https://recorder.itagenten.no/switcher
- Should see video in compact inputs (HLS)
- Program output should show video when mixer running

### 5. Test Library
- Open: https://recorder.itagenten.no/library
- Thumbnails should load or show clear error
- No indefinite "Loading..." state

### 6. Test Guest Join
- Open: https://recorder.itagenten.no/guest_join
- Should see camera/mic dropdowns populate
- If permission denied, should show clear error

---

## Rollback Plan (If Needed)

### If Issues Occur
```bash
# SSH to R58
ssh linaro@r58.itagenten.no

# Stop service
sudo systemctl stop preke-recorder

# Revert to previous commit
cd /home/rock/preke-r58-recorder
git log --oneline -5  # Find previous commit
git reset --hard <previous-commit-hash>

# Restart service
sudo systemctl start preke-recorder
```

---

## Risk Assessment

### Low Risk Changes ✅
- Frontend JavaScript updates (no backend impact)
- Error message improvements (better UX)
- Config field addition (backward compatible)

### Medium Risk Changes ⚠️
- FastAPI lifespan migration (well-tested pattern)
- Ingest manager logic (adds check, doesn't remove)

### High Risk Changes ❌
- None

**Overall Risk**: **LOW** - All changes improve stability

---

## Expected Behavior After Deployment

### What Should Change
1. ✅ CAM 2 status shows correctly in multiview
2. ✅ Switcher shows video remotely (via HLS)
3. ✅ Library thumbnails load with timeout
4. ✅ Guest join shows clear permission errors
5. ✅ cam0 shows "idle" instead of "error"
6. ✅ No deprecation warnings in logs
7. ✅ Helpful GStreamer errors on macOS

### What Should Stay the Same
- ✅ Recording functionality unchanged
- ✅ Mixer behavior unchanged
- ✅ API responses unchanged
- ✅ Performance unchanged
- ✅ All existing features work

---

## Monitoring After Deployment

### First 5 Minutes
- Check service status
- Verify no errors in logs
- Test multiview loads
- Test switcher loads

### First Hour
- Monitor for any crashes
- Check recording still works
- Verify mixer stability
- Test scene switching

### First 24 Hours
- Monitor disk space
- Check for memory leaks
- Verify long-running stability
- Test all features

---

## Documentation Updated

### New Documents
- ✅ `COMPREHENSIVE_TEST_RESULTS.md` - Full test report
- ✅ `TEST_SUMMARY_DEC19.md` - Executive summary
- ✅ `DEPLOYMENT_FIXES_DEC19.md` - This document

### Existing Documents
- All existing documentation remains valid
- No breaking changes to APIs or features

---

## Support

### If You Need Help
1. Check logs: `sudo journalctl -u preke-recorder -f`
2. Check status: `curl https://recorder.itagenten.no/health`
3. Review: `COMPREHENSIVE_TEST_RESULTS.md`
4. Rollback: Use git reset (see above)

### Common Issues

#### Issue: Service won't start
```bash
# Check detailed logs
sudo journalctl -u preke-recorder -n 100

# Verify Python syntax
cd /home/rock/preke-r58-recorder
python3 -m py_compile src/main.py
```

#### Issue: Cameras not streaming
```bash
# Check ingest status
curl https://recorder.itagenten.no/api/ingest/status

# Verify MediaMTX running
sudo systemctl status mediamtx
```

---

## Conclusion

**All 7 improvements are ready for deployment.**

- ✅ Thoroughly tested
- ✅ Low risk
- ✅ Backward compatible
- ✅ Improves stability
- ✅ Better user experience

**Recommendation**: Deploy now and monitor for 24 hours.

---

**Deployment Status**: ✅ READY  
**Risk Level**: LOW  
**Expected Downtime**: <30 seconds (service restart)
