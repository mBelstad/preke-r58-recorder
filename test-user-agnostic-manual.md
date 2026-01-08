# Manual Testing Guide - User-Agnostic App

## Test Results

### ✅ Automated Tests
- [x] No hardcoded URLs in source code
- [x] FRP URL fetched dynamically from device config
- [x] WHEP URL builder uses device URL dynamically
- [x] VDO.ninja host is configurable

### Manual Testing Checklist

#### Test 1: Fresh App Start (No Device)
**Status:** ⏳ Pending manual verification

**Steps:**
1. Clear device store: Delete `~/Library/Application Support/preke-studio-devices/config.json` (macOS) or equivalent
2. Launch app: `cd packages/desktop && npm run test:launch`
3. Open DevTools: Cmd+Option+I (macOS) or Ctrl+Shift+I (Windows/Linux)
4. Go to Network tab
5. Check for any requests to:
   - `r58-api.itagenten.no`
   - `192.168.1.24`
   - `100.98.37.53`
6. Verify app shows "No device connected" or similar empty state

**Expected Result:** 
- ✅ No network requests to hardcoded URLs
- ✅ App shows empty state gracefully
- ✅ No errors in console

**Actual Result:** _[To be filled]_

---

#### Test 2: Device Discovery (LAN)
**Status:** ⏳ Pending manual verification

**Steps:**
1. Ensure R58 device is on same network
2. In app, go to Settings > Devices
3. Click "Scan Network" or wait for auto-discovery
4. Verify device appears with its actual IP (not hardcoded)

**Expected Result:**
- ✅ Device discovered with correct IP
- ✅ Can connect to discovered device

**Actual Result:** _[To be filled]_

---

#### Test 3: Device Discovery (Tailscale)
**Status:** ⏳ Pending manual verification

**Steps:**
1. Ensure Tailscale is running
2. Ensure R58 device is online in Tailscale
3. In app, go to Settings > Devices
4. Verify Tailscale device appears with Tailscale IP (100.x.x.x)

**Expected Result:**
- ✅ Tailscale device discovered automatically
- ✅ Can connect via Tailscale IP

**Actual Result:** _[To be filled]_

---

#### Test 4: Manual Device Add
**Status:** ⏳ Pending manual verification

**Steps:**
1. In app, go to Settings > Devices
2. Click "Add Device Manually"
3. Enter a test URL: `http://192.168.1.100:8000` (or any test URL)
4. Save device
5. Set as active device
6. Check Network tab - verify all requests go to the test URL

**Expected Result:**
- ✅ Device added successfully
- ✅ All API requests use the test URL
- ✅ No fallback to hardcoded URLs

**Actual Result:** _[To be filled]_

---

#### Test 5: WHEP Connections
**Status:** ⏳ Pending manual verification

**Steps:**
1. Connect to a device (via discovery or manual)
2. Navigate to Recorder or Studio view
3. Check browser console for WHEP connection logs
4. Verify WHEP URLs use the device's URL (not hardcoded)
5. Check connection type detection (P2P vs Relay)

**Expected Result:**
- ✅ WHEP URLs built from device URL
- ✅ Connection type correctly detected (P2P for Tailscale/LAN, Relay for FRP)
- ✅ Video streams work correctly

**Actual Result:** _[To be filled]_

---

#### Test 6: FRP Fallback (Conditional)
**Status:** ⏳ Pending manual verification

**Prerequisites:** Device must support `/api/config` endpoint with `frp_url` field

**Steps:**
1. Connect to device that has FRP configured
2. Disconnect device (unplug network or stop service)
3. Wait for connection failures
4. Check if FRP fallback activates
5. Verify FRP URL comes from device config (not hardcoded)

**Alternative Test (Device without FRP):**
1. Connect to device without FRP configuration
2. Disconnect device
3. Verify app shows "Device unreachable" (not connecting to hardcoded FRP URL)

**Expected Result:**
- ✅ FRP fallback only works if device provides FRP URL
- ✅ No connection attempts to hardcoded FRP URL
- ✅ Graceful error handling when FRP not available

**Actual Result:** _[To be filled]_

---

#### Test 7: VDO.ninja Integration
**Status:** ⏳ Pending manual verification

**Steps:**
1. Connect to a device
2. Navigate to Mixer view
3. Check iframe source in DevTools
4. Verify VDO.ninja URL uses configured host (or default `vdo.itagenten.no`)
5. Verify no hardcoded VDO.ninja URLs

**Expected Result:**
- ✅ Mixer iframe loads from configured VDO.ninja host
- ✅ No hardcoded VDO.ninja URLs in code
- ✅ Mixer functionality works correctly

**Actual Result:** _[To be filled]_

---

## Code Verification

### Files Verified:
- ✅ `packages/frontend/src/lib/api.ts` - No hardcoded FRP URL
- ✅ `packages/frontend/src/lib/whepConnectionManager.ts` - Dynamic IP detection
- ✅ `packages/frontend/src/lib/vdoninja.ts` - Configurable VDO.ninja host
- ✅ `packages/desktop/src/main/window.ts` - No hardcoded IPs in CSP

### Remaining Hardcoded References:
- ⚠️ `packages/frontend/src/views/StyleGuideV2View.vue` - Demo/example data only (not functional)

---

## Summary

**Automated Tests:** ✅ All passed

**Manual Tests:** ⏳ Pending user verification

**Next Steps:**
1. Run manual tests above
2. Fill in "Actual Result" for each test
3. Document any issues found
4. Fix any bugs discovered
5. Re-test until all pass
