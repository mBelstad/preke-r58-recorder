# Path Forward - DaVinci Resolve Integration

## Current Status

✅ **Fixed & Ready:**
- Electron app code (all components rebuilt)
- Timeline placement (all clips at frame 0)
- File selection (all cameras from session)
- Auto-refresh functionality (every 10 seconds)
- Configuration file (MOV format)

⚠️ **Needs Deployment:**
- Updated `config.yml` to R58 device
- Service restart to apply config

---

## Immediate Next Steps (Priority Order)

### Step 1: Deploy Configuration to R58 ⚠️ CRITICAL

The R58 device needs the updated `config.yml` with MOV format:

```bash
# Option A: Use deploy script (recommended)
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./deploy.sh

# Option B: Manual deployment
./connect-r58-frp.sh
# Then on R58:
cd /opt/preke-r58-recorder  # or /home/linaro/preke-r58-recorder
git pull
sudo systemctl restart preke-recorder.service
```

**Verify deployment:**
```bash
# Check config was updated
./connect-r58-frp.sh 'grep -A 5 "recording:" /opt/preke-r58-recorder/config.yml'

# Check service is running
./connect-r58-frp.sh 'sudo systemctl status preke-recorder.service'
```

---

### Step 2: Re-Test Growing Files Workflow 🧪

**Test Procedure:**

1. **Start Recording on R58**
   - Use Electron app or web UI
   - Start recording session with multiple cameras

2. **Verify Files Are MOV Format**
   ```bash
   # Check file extension on R58
   ./connect-r58-frp.sh 'ls -lh /data/recordings/cam0/ | tail -3'
   # Should show .mov files
   ```

3. **Open DaVinci Resolve**
   - Click "Open Project" in Electron app
   - Project should open automatically

4. **Create Multicam Timeline**
   - Click "Create Multicam" in Electron app
   - Verify all cameras added at frame 0 on separate tracks

5. **Test Growing Files**
   - Wait 30+ seconds while recording
   - Check if clip duration updates automatically (auto-refresh every 10s)
   - Or click "Refresh Clips" button manually
   - Verify files show as "growing" with live indicator

6. **Test Timeline Playback**
   - Play timeline while recording
   - Verify you can scrub to end and see new frames
   - Check that "offline" sections don't appear

---

### Step 3: Validate All Fixes ✅

**Checklist:**

- [ ] All 3 cameras appear in timeline (not just 1)
- [ ] All clips start at frame 0 (not sequential)
- [ ] Files are .mov format (not .mkv)
- [ ] Files show as "growing" in DaVinci
- [ ] Auto-refresh updates duration every 10 seconds
- [ ] Manual refresh button works
- [ ] Timeline playback works while recording

---

## If Growing Files Still Don't Work

### Option A: Verify MOV Format Settings

Check that files are actually MOV with proper moov atom:

```bash
# On Mac, check file format
file ~/r58-recordings/cam0/*.mov | head -1

# Check with ffprobe
ffprobe ~/r58-recordings/cam0/recording_*.mov 2>&1 | grep -i "format\|duration"
```

### Option B: Test on Local LAN

As planned, test on local gigabit LAN to rule out network latency:

1. Connect R58 and Mac to same local network
2. Remount SMB share (may use different IP)
3. Re-test growing files workflow
4. Compare results with Tailscale/internet connection

### Option C: Investigate DaVinci Settings

1. **Check DaVinci Preferences:**
   - System > Decode Options > "Automatically refresh growing files in the media pool"
   - Should be enabled

2. **Add SMB Mount to Media Storage:**
   - Preferences > Media Storage
   - Add `~/r58-recordings` as a media location
   - This helps DaVinci monitor the folder

3. **Try Bin Refresh:**
   - Right-click bin containing clips
   - Look for "Refresh Folder" or "Resync" option
   - Test if this updates clip duration

---

## Future Optimizations

### Short Term (If Current Solution Works)

1. **Fine-tune Auto-Refresh Interval**
   - Current: 10 seconds
   - Test: 5 seconds (more responsive) vs 15 seconds (less overhead)
   - Make configurable in UI

2. **Add Visual Feedback**
   - Show "Refreshing..." indicator in UI
   - Display last refresh time
   - Show clip count being refreshed

3. **Error Handling**
   - Better error messages if refresh fails
   - Retry logic for transient failures
   - Log refresh history

### Medium Term (If Growing Files Work)

1. **Smart Refresh**
   - Only refresh when file size changes
   - Skip refresh if no new data
   - Reduce unnecessary API calls

2. **Timeline Sync**
   - Auto-update timeline when clips refresh
   - Maintain playback position
   - Update thumbnails

3. **Multi-Project Support**
   - Handle multiple projects open
   - Refresh clips in all active projects
   - Project-specific settings

### Long Term (Advanced Features)

1. **Proxy Workflow**
   - Generate low-res proxies for faster editing
   - Auto-replace with full-res on export
   - Optimize for slow networks

2. **Collaborative Editing**
   - Multiple editors on same project
   - Real-time clip updates
   - Conflict resolution

3. **Custom Resolve Plugin** (If Needed)
   - Native growing file support
   - Better performance than scripting API
   - Custom UI integration

---

## Decision Points

### After Re-Testing:

**If Growing Files Work:**
- ✅ Success! Proceed with optimizations
- Document the working configuration
- Share learnings with team

**If Growing Files Don't Work:**
- Investigate DaVinci's growing file requirements
- Test alternative approaches:
  - Local proxy sync (Option C from plan)
  - NFS instead of SMB
  - Custom Resolve plugin
- Consider if manual refresh is acceptable

**If Performance Issues:**
- Optimize refresh frequency
- Implement smart refresh (only when needed)
- Consider proxy workflow for slow networks

---

## Success Criteria

The solution is successful when:

1. ✅ All cameras appear in timeline correctly
2. ✅ Clips placed at frame 0 on separate tracks
3. ✅ Files recognized as growing (or refresh works reliably)
4. ✅ Timeline playback works while recording
5. ✅ Auto-refresh updates duration automatically
6. ✅ Works over both LAN and Tailscale/internet

---

## Quick Reference

**Deploy Config:**
```bash
./deploy.sh
```

**Check Service:**
```bash
./connect-r58-frp.sh 'sudo systemctl status preke-recorder.service'
```

**View Logs:**
```bash
./connect-r58-frp.sh 'sudo journalctl -u preke-recorder -n 50 -f'
```

**Rebuild Electron App:**
```bash
cd packages/desktop
npm run test:build-all
```

**Test Growing Files:**
1. Start recording
2. Open project in DaVinci
3. Create multicam timeline
4. Wait 30+ seconds
5. Verify duration updates (auto or manual refresh)

---

## Questions to Answer

After re-testing, we'll know:

1. ✅ Does MOV format work for growing files?
2. ✅ Is auto-refresh sufficient, or need manual?
3. ✅ Does it work over slow internet, or only LAN?
4. ✅ Is 10-second refresh interval optimal?
5. ✅ Are there any DaVinci-specific requirements we're missing?

---

**Next Action:** Deploy config.yml to R58 and re-test! 🚀
