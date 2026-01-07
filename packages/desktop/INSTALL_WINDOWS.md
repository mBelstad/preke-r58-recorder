# Installing Preke Studio on Windows

This guide will help you install Preke Studio on your Windows computer.

## System Requirements

- **Windows**: Windows 10 (version 1809) or later, Windows 11
- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 200MB for application files
- **Network**: Internet connection required for connecting to R58 devices
- **Architecture**: 64-bit (x64) only

## Installation Steps

### Step 1: Download the Installer

1. Download `Preke Studio Setup {version}.exe` from the releases page
2. The file will typically be in your Downloads folder
3. File size is approximately 150-200MB

### Step 2: Run the Installer

1. **Locate the installer**
   - Open File Explorer
   - Navigate to your Downloads folder
   - Find `Preke Studio Setup {version}.exe`

2. **Launch the installer**
   - Double-click the installer file
   - If Windows SmartScreen appears, click "More info" then "Run anyway"
     - This is normal for unsigned builds or new publishers

3. **User Account Control (UAC)**
   - Windows may ask for administrator permission
   - Click "Yes" to allow the installation

### Step 3: Installation Wizard

1. **Welcome Screen**
   - Click "Next" to begin installation

2. **License Agreement** (if shown)
   - Read the license terms
   - Select "I accept the agreement"
   - Click "Next"

3. **Choose Installation Location**
   - Default location: `C:\Program Files\Preke Studio`
   - Click "Browse" to choose a different location if desired
   - Click "Next"

4. **Select Additional Tasks**
   - ☑ Create a desktop shortcut (recommended)
   - ☑ Create a Start Menu shortcut (recommended)
   - Click "Next"

5. **Ready to Install**
   - Review your selections
   - Click "Install" to begin installation

6. **Installation Progress**
   - Wait for the installation to complete
   - This typically takes 1-2 minutes

7. **Installation Complete**
   - ☑ Launch Preke Studio (optional)
   - Click "Finish"

### Step 4: First Launch

1. **Launch Preke Studio**
   - From the installer (if you checked the box)
   - Or from Desktop shortcut
   - Or from Start Menu → Preke Studio

2. **Windows Defender / Antivirus** (if prompted)
   - Some antivirus software may flag new applications
   - Click "Allow" or "Run anyway" if prompted
   - Preke Studio is safe to use

3. **Firewall Permission** (if prompted)
   - Windows Firewall may ask for network access
   - Click "Allow access" to enable device connections

## First Launch Setup

1. **Add your first R58 device**
   - Click "Add Device" or "Device Setup"
   - Enter your device URL (e.g., `https://r58-api.itagenten.no`)
   - Click "Connect" to test the connection

2. **Verify connection**
   - The app should connect to your R58 device
   - You'll see the device status and controls

## Troubleshooting

### Installer Won't Run

**Problem**: Double-clicking the installer does nothing or shows an error.

**Solutions**:
1. **Check Windows version**:
   - Settings → System → About
   - Requires Windows 10 (1809+) or Windows 11

2. **Run as Administrator**:
   - Right-click the installer
   - Select "Run as administrator"
   - Click "Yes" in UAC prompt

3. **Check file integrity**:
   - Re-download the installer
   - Verify the file size matches the expected size

4. **Disable antivirus temporarily**:
   - Some antivirus software blocks installers
   - Temporarily disable, install, then re-enable

### SmartScreen Warning

**Problem**: "Windows protected your PC" or "Unknown publisher" warning.

**Solutions**:
1. **For unsigned builds** (development/testing):
   - Click "More info"
   - Click "Run anyway"
   - This is safe for unsigned installers

2. **For signed builds**:
   - Should not appear if properly signed
   - If it does, the certificate may not be trusted yet
   - Click "More info" → "Run anyway"

### Installation Fails

**Problem**: Installer shows an error or fails partway through.

**Solutions**:
1. **Check disk space**:
   - Ensure at least 500MB free space
   - Free up space if needed

2. **Close other applications**:
   - Close all running programs
   - Try installation again

3. **Check permissions**:
   - Ensure you have administrator rights
   - Right-click → Run as administrator

4. **Check Windows Installer service**:
   ```powershell
   # Run in PowerShell as Administrator
   Get-Service msiserver
   # If stopped, start it:
   Start-Service msiserver
   ```

5. **View installation logs**:
   - Check `%TEMP%` folder for installer logs
   - Look for files starting with "Preke Studio"

### App Won't Launch After Installation

**Problem**: App doesn't start or crashes immediately.

**Solutions**:
1. **Check Event Viewer**:
   - Press Win+X → Event Viewer
   - Windows Logs → Application
   - Look for Preke Studio errors

2. **Check application logs**:
   ```
   %APPDATA%\R58 Studio\logs\main.log
   ```

3. **Reinstall**:
   - Uninstall completely (see Uninstallation below)
   - Restart computer
   - Install again

4. **Check .NET Framework** (if required):
   - Windows 10/11 should have this by default
   - If missing, download from Microsoft

### Cannot Connect to R58 Device

**Problem**: App launches but cannot connect to devices.

**Solutions**:
1. **Verify device URL**:
   - Must include protocol: `https://` or `http://`
   - Check for typos in the URL

2. **Test device in browser**:
   - Open: `https://your-device/api/v1/health`
   - Should return JSON response

3. **Check Windows Firewall**:
   - Settings → Privacy & Security → Windows Security → Firewall
   - Ensure Preke Studio is allowed

4. **Check network connectivity**:
   - Verify internet connection
   - Test with: `ping your-device-url`

5. **For self-signed certificates**:
   - Ensure you've added the device in Device Setup
   - The app will handle certificate trust for configured devices

### Antivirus Blocks the App

**Problem**: Antivirus software quarantines or blocks Preke Studio.

**Solutions**:
1. **Add exception**:
   - Open your antivirus software
   - Add Preke Studio to exceptions/whitelist
   - Location: `C:\Program Files\Preke Studio`

2. **Temporarily disable** (for testing):
   - Disable real-time protection temporarily
   - Launch the app
   - Re-enable protection
   - Add permanent exception

### Missing Desktop Shortcut

**Problem**: No shortcut created on desktop.

**Solutions**:
1. **Create manually**:
   - Navigate to: `C:\Program Files\Preke Studio`
   - Right-click `Preke Studio.exe`
   - Send to → Desktop (create shortcut)

2. **Reinstall with shortcut option**:
   - Uninstall current version
   - Reinstall and check "Create desktop shortcut"

## Uninstallation

### Standard Method

1. **Quit Preke Studio** (if running)
   - Close the application window
   - Check system tray for running instance

2. **Open Settings**
   - Press Win+I
   - Go to Apps → Apps & features
   - Or: Control Panel → Programs → Uninstall a program

3. **Uninstall Preke Studio**
   - Find "Preke Studio" in the list
   - Click it, then click "Uninstall"
   - Follow the uninstaller prompts
   - Click "Finish" when done

### Alternative Method (Control Panel)

1. **Open Control Panel**
   - Press Win+R, type `appwiz.cpl`, press Enter

2. **Find Preke Studio**
   - Scroll to find "Preke Studio"
   - Double-click or right-click → Uninstall

3. **Follow prompts**
   - Confirm uninstallation
   - Wait for completion

### Complete Removal

To remove all traces (including user data):

1. **Uninstall via Settings** (as above)

2. **Delete user data** (optional):
   ```
   %APPDATA%\R58 Studio
   %LOCALAPPDATA%\R58 Studio
   ```

3. **Delete registry entries** (advanced):
   - Press Win+R, type `regedit`
   - Navigate to: `HKEY_CURRENT_USER\Software\no.itagenten.prekestudio`
   - Delete the key (if exists)
   - **Warning**: Only do this if you're comfortable with Registry Editor

### Command Line Uninstallation

```powershell
# Find the uninstaller
$uninstaller = Get-ChildItem "C:\Program Files\Preke Studio\Uninstall Preke Studio.exe"

# Run uninstaller silently
& $uninstaller /S
```

## Updating the Application

1. **Download the new version**
   - Download the latest installer from releases

2. **Run the new installer**
   - The installer will detect the existing installation
   - Choose to update/replace the existing version

3. **Your settings are preserved**
   - Device configurations are stored in AppData
   - No need to reconfigure devices after update

## Code Signing

### Signed Builds

If you downloaded a signed build:
- No SmartScreen warnings (after first use)
- Publisher name shows in installer
- Automatically trusted by Windows

### Unsigned Builds

Development or test builds may be unsigned:
- Will show SmartScreen warnings
- Requires "Run anyway" on first install
- Safe to use after approval

## Getting Help

If you encounter issues not covered here:

1. **Check the logs**:
   ```
   %APPDATA%\R58 Studio\logs\main.log
   ```

2. **Export support bundle**:
   - Help menu → Export Support Bundle...
   - Share the ZIP file with support

3. **Check Event Viewer**:
   - Win+X → Event Viewer
   - Windows Logs → Application
   - Look for Preke Studio errors

4. **Contact support**:
   - Email: support@itagenten.no
   - Include:
     - Support bundle ZIP
     - Error messages
     - Windows version
     - Steps to reproduce

## Additional Resources

- [Main README](../README.md) - General information
- [Development Guide](README.md) - Building from source
- [Troubleshooting Guide](README.md#troubleshooting) - More detailed troubleshooting

