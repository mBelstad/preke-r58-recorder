# Installing Preke Studio on macOS

This guide will help you install Preke Studio on your Mac.

## System Requirements

- **macOS**: 10.15 (Catalina) or later
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 200MB for application files
- **Network**: Internet connection required for connecting to R58 devices

## Installation Methods

### Method 1: DMG Installer (Recommended)

1. **Download the installer**
   - Download `Preke Studio-{version}-universal.dmg` from the releases page
   - The file will be in your Downloads folder

2. **Open the DMG file**
   - Double-click the DMG file to mount it
   - A window will open showing the Preke Studio app icon and an Applications folder shortcut

3. **Install the application**
   - Drag the Preke Studio app icon to the Applications folder
   - Alternatively, you can drag it to any location you prefer

4. **Launch Preke Studio**
   - Open Finder and navigate to Applications (or your chosen location)
   - Double-click Preke Studio to launch
   - On first launch, you may see a security warning

5. **Handle Gatekeeper warning (if unsigned build)**
   - If you see "Preke Studio cannot be opened because it is from an unidentified developer":
     - Right-click (or Control-click) the app icon
     - Select "Open" from the context menu
     - Click "Open" in the security dialog
   - After the first launch, macOS will remember your choice

### Method 2: Direct Download (Unpackaged)

1. **Download the directory build**
   - Download `Preke Studio-{version}-mac-universal.zip` (if available)
   - Extract the ZIP file
   - Move the `Preke Studio.app` to your Applications folder

2. **Launch the application**
   - Double-click Preke Studio.app to launch
   - Follow the Gatekeeper steps above if needed

## First Launch Setup

1. **Grant network permissions** (if prompted)
   - macOS may ask for network access permission
   - Click "Allow" to enable device connections

2. **Add your first R58 device**
   - Click "Add Device" or "Device Setup"
   - Enter your device URL (e.g., `https://r58-api.itagenten.no`)
   - Click "Connect" to test the connection

## Troubleshooting

### App Won't Open After Installation

**Problem**: Double-clicking does nothing or shows an error.

**Solutions**:
1. Check macOS version: System Preferences → About This Mac
   - Requires macOS 10.15 or later
2. Try right-click → Open (bypasses Gatekeeper)
3. Check Console.app for error messages:
   - Open Console.app
   - Look for "Preke Studio" or "Electron" errors

### Gatekeeper Blocks the App

**Problem**: "Preke Studio cannot be opened because it is from an unidentified developer"

**Solutions**:
1. **Right-click method** (recommended):
   - Right-click the app → Open → Open in dialog
2. **System Preferences method**:
   - System Preferences → Security & Privacy → General
   - Click "Open Anyway" next to the blocked app message
3. **Command line method**:
   ```bash
   sudo xattr -rd com.apple.quarantine "/Applications/Preke Studio.app"
   ```

### App Crashes on Launch

**Problem**: App opens then immediately closes.

**Solutions**:
1. Check logs:
   ```bash
   tail -f ~/Library/Logs/R58\ Studio/main.log
   ```
2. Delete corrupted config (if needed):
   ```bash
   rm ~/Library/Application\ Support/R58\ Studio/r58-devices.json
   ```
3. Reinstall the application

### Cannot Connect to R58 Device

**Problem**: App launches but cannot connect to devices.

**Solutions**:
1. Verify device URL is correct (include `https://` or `http://`)
2. Test device in browser: `https://your-device/api/v1/health`
3. Check network connectivity
4. Verify firewall isn't blocking connections
5. For self-signed certificates, ensure you've added the device in Device Setup

### App Icon Missing or Incorrect

**Problem**: App shows generic Electron icon.

**Solutions**:
1. Clear icon cache:
   ```bash
   sudo rm -rf /Library/Caches/com.apple.iconservices.store
   killall Finder
   ```
2. Rebuild icon cache:
   ```bash
   touch /Applications/Preke\ Studio.app
   killall Finder
   ```

## Uninstallation

### Standard Method

1. **Quit Preke Studio** (if running)
   - Preke Studio menu → Quit Preke Studio
   - Or press Cmd+Q

2. **Delete the application**
   - Open Finder → Applications
   - Drag Preke Studio.app to Trash
   - Empty Trash

3. **Remove user data** (optional)
   ```bash
   rm -rf ~/Library/Application\ Support/R58\ Studio
   rm -rf ~/Library/Logs/R58\ Studio
   ```

### Complete Removal

To remove all traces of the application:

```bash
# Application
rm -rf "/Applications/Preke Studio.app"

# User data
rm -rf ~/Library/Application\ Support/R58\ Studio
rm -rf ~/Library/Logs/R58\ Studio
rm -rf ~/Library/Preferences/no.itagenten.prekestudio.plist
rm -rf ~/Library/Caches/no.itagenten.prekestudio
```

## Code Signing and Notarization

### Signed Builds

If you downloaded a signed and notarized build:
- No Gatekeeper warnings
- Automatically trusted by macOS
- Can be distributed without warnings

### Unsigned Builds

Development or test builds may be unsigned:
- Will show Gatekeeper warnings
- Requires manual approval on first launch
- Safe to use after approval

## Updating the Application

1. **Download the new version**
   - Download the latest DMG from releases

2. **Replace the old version**
   - Drag the new Preke Studio.app to Applications
   - macOS will ask to replace the existing app
   - Click "Replace"

3. **Your settings are preserved**
   - Device configurations are stored separately
   - No need to reconfigure devices after update

## Getting Help

If you encounter issues not covered here:

1. **Check the logs**:
   ```bash
   cat ~/Library/Logs/R58\ Studio/main.log
   ```

2. **Export support bundle**:
   - Help menu → Export Support Bundle...
   - Share the ZIP file with support

3. **Contact support**:
   - Email: support@itagenten.no
   - Include the support bundle and error messages

## Additional Resources

- [Main README](../README.md) - General information
- [Development Guide](README.md) - Building from source
- [Troubleshooting Guide](README.md#troubleshooting) - More detailed troubleshooting

