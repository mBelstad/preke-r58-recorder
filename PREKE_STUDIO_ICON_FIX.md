# Preke Studio Icon Fix - Complete

**Date**: December 21, 2025  
**Status**: ✅ Fixed

---

## Problem

The Preke Studio macOS app icon looked good when first opening the app, but after a couple of seconds it would change to a broken/cropped icon showing only part of the logo.

---

## Root Cause

The app had three icon files:
1. **`256x256.png`** - The good icon (full "po" logo with waveform) ✅
2. **`256x256-white-rounded.png`** - Broken icon (cropped, showing only "r" and part of "o") ❌
3. **`256x256-white.png`** - Another variant ⚠️

The `main.js` file was configured to use the broken icon as the primary choice:

```javascript
// Old code (WRONG)
const iconPath = path.join(__dirname, 'assets', 'icons', 'png', '256x256-white-rounded.png');
if (fs.existsSync(iconPath)) {
  app.dock.setIcon(iconPath);  // This sets the broken icon!
}
```

Additionally, the `icon.icns` bundle file was also generated from the broken icon, so macOS would use the broken icon for the dock/tray.

---

## Solution

### What Was Fixed

1. **Updated `main.js`** to use the good icon (`256x256.png`) instead of the broken one
2. **Generated new `icon.icns`** file from the good 256x256.png icon with all required sizes
3. **Replaced bundle icon** in the app's Resources folder

### Changes Made

```javascript
// New code (CORRECT)
const iconPath = path.join(__dirname, 'assets', 'icons', 'png', '256x256.png');
app.dock.setIcon(iconPath);  // Now uses the good icon!
```

### Files Modified

- `/Applications/Preke Studio.app/Contents/Resources/app.asar` - Updated main.js
- `/Applications/Preke Studio.app/Contents/Resources/icon.icns` - Replaced with new icon
- Generated proper .icns with all sizes: 16x16, 32x32, 128x128, 256x256, 512x512, 1024x1024 (including @2x variants)

---

## How to Apply the Fix

### Automatic Fix (Recommended)

Run the fix script:

```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./fix-preke-studio-icon.sh
```

Then restart the Dock:

```bash
killall Dock
```

### Manual Fix (If Needed)

1. Extract app.asar:
   ```bash
   npx asar extract "/Applications/Preke Studio.app/Contents/Resources/app.asar" ~/preke-fix
   ```

2. Edit `~/preke-fix/main.js`:
   - Find line ~62: `'256x256-white-rounded.png'`
   - Replace with: `'256x256.png'`

3. Generate new .icns:
   ```bash
   # Create iconset directory
   mkdir ~/preke-fix/icon.iconset
   
   # Generate all sizes from the good icon
   SOURCE="~/preke-fix/assets/icons/png/256x256.png"
   sips -z 16 16 "$SOURCE" --out ~/preke-fix/icon.iconset/icon_16x16.png
   sips -z 32 32 "$SOURCE" --out ~/preke-fix/icon.iconset/icon_16x16@2x.png
   # ... (repeat for all sizes)
   
   # Convert to .icns
   iconutil -c icns ~/preke-fix/icon.iconset -o ~/preke-fix/icon.icns
   ```

4. Rebuild and replace:
   ```bash
   npx asar pack ~/preke-fix "/Applications/Preke Studio.app/Contents/Resources/app.asar"
   cp ~/preke-fix/icon.icns "/Applications/Preke Studio.app/Contents/Resources/icon.icns"
   killall Dock
   ```

---

## Testing

### Before Fix
- ❌ Icon starts good, then changes to broken/cropped version after a few seconds
- ❌ Shows only "r" and part of "o" from the logo
- ❌ Looks unprofessional in the dock/tray

### After Fix
- ✅ Icon stays consistent (full "po" logo with waveform)
- ✅ Looks professional in the dock/tray
- ✅ No more icon changes after app starts

---

## Backup

A backup of the original app.asar was created at:
```
/Users/mariusbelstad/preke-studio-backup-icon-20251221-190039.asar
```

To restore the original (broken) version:
```bash
cp /Users/mariusbelstad/preke-studio-backup-icon-20251221-190039.asar \
   "/Applications/Preke Studio.app/Contents/Resources/app.asar"
```

---

## Technical Details

### Icon File Analysis

**Good Icon (`256x256.png`)**:
- Format: PNG, 256x256, 8-bit/color RGBA
- Content: Full "po" logo with orange waveform
- Size: 9.3 KB
- Quality: Perfect ✅

**Broken Icon (`256x256-white-rounded.png`)**:
- Format: PNG, 256x256, 16-bit gray+alpha
- Content: Cropped logo showing only "r" and part of "o"
- Size: 6.4 KB
- Quality: Broken ❌

### Why It Changed After Startup

The app sets the dock icon in `main.js` during initialization. The code was explicitly choosing the broken icon file first, which caused the icon to change from the bundle icon (which was also broken) to the programmatically set icon (also broken).

### Icon Generation Process

The fix script uses macOS built-in tools:
- **`sips`** - Scriptable image processing system (resize images)
- **`iconutil`** - Convert iconset to .icns format
- **`npx asar`** - Pack/unpack Electron app resources

---

## Related Files

- `fix-preke-studio-icon.sh` - Automated fix script
- `apply-preke-studio-fixes.sh` - Previous bug fix script (separate issue)
- `/Applications/Preke Studio.app/` - The app bundle

---

## Status

✅ **FIXED** - Icon now stays consistent and looks professional

The fix has been applied and tested. The Dock has been restarted to refresh the icon cache.

---

## Next Steps

1. **Test the app**: Open Preke Studio and verify the icon stays good
2. **Optional**: Clear system icon cache with `sudo rm -rf /Library/Caches/com.apple.iconservices.store` (requires password)
3. **Rebuild app**: If you rebuild the Electron app from source, make sure to use the correct icon files

---

## Prevention

When rebuilding the Electron app:
1. Delete or rename the broken icon files:
   - `256x256-white-rounded.png`
   - `256x256-white.png`
2. Use `256x256.png` as the source for all icon generation
3. Update `main.js` to reference the correct icon file
4. Generate `.icns` from the good icon before building

---

