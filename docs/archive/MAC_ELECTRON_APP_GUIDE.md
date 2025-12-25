# VDO.Ninja Electron Capture - Mac App Guide

**Date**: December 18, 2025  
**Status**: ✅ Installed and Ready to Use

## Installation Complete

The Electron Capture app has been successfully installed:
- **Location**: `~/Applications/elecap.app`
- **Version**: 2.21.5 (universal - Intel & Apple Silicon)
- **Size**: ~190MB

## What is Electron Capture?

Electron Capture is a frameless, transparent Electron app designed for clean window capture in OBS. It provides:
- **Frameless window** - No browser chrome, perfect for OBS capture
- **Hardware acceleration** - Better performance than browser
- **Low CPU usage** - Optimized for streaming
- **All VDO.Ninja features** - Full compatibility

## Launching the App

### Method 1: Open with URL (Recommended)

Open Terminal and run:

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?director=r58studio"
```

Or for viewing a specific camera:

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1"
```

### Method 2: Double-click and Enter URL

1. Double-click `elecap.app` in Applications folder
2. Enter URL when prompted: `https://192.168.1.25:8443/?director=r58studio`

## Usage Examples

### Director/Mixer Mode

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?director=r58studio"
```

Use this for:
- Controlling the VDO.Ninja mixer
- Viewing all camera feeds
- Managing remote guests
- Building scenes

### View Single Camera

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1"
```

Use this for:
- Clean camera feed in OBS
- Individual camera monitoring
- Picture-in-picture setups

### Guest Mode

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?room=r58studio"
```

Use this for:
- Joining as a guest
- Sharing your camera/screen
- Testing guest functionality

### Remote Access (via Cloudflare Tunnel)

Once Cloudflare route is configured:

```bash
open -a ~/Applications/elecap.app --args --url="https://vdoninja.itagenten.no/?director=r58studio"
```

## OBS Integration

### Step 1: Launch Electron Capture

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1"
```

### Step 2: Add to OBS

1. Open OBS
2. Add Source → **Window Capture**
3. Select window: **elecap**
4. Enable: **Capture Method** → **Window Capture (macOS 10.15+)**

### Step 3: Crop/Position

- The window is frameless, so you get clean video
- No browser UI elements to crop out
- Resize and position as needed

## Advanced Features

### Transparency

The app supports transparency for overlays:

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1&transparent"
```

### Custom Window Size

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1" --width=1920 --height=1080
```

### Always on Top

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1" --ontop
```

### Disable Audio

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1&noaudio"
```

## VDO.Ninja URL Parameters

You can combine these with any Electron Capture launch:

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `&director=ROOM` | Director mode | `&director=r58studio` |
| `&view=STREAMID` | View specific stream | `&view=r58-cam1` |
| `&room=ROOM` | Join as guest | `&room=r58studio` |
| `&mediamtx=HOST:PORT` | Use MediaMTX backend | `&mediamtx=192.168.1.25:8889` |
| `&lanonly` | LAN-only mode | `&lanonly` |
| `&turn=SERVER` | TURN server | `&turn=turn:relay.metered.ca:443` |
| `&bitrate=KBPS` | Video bitrate | `&bitrate=5000` |
| `&noaudio` | Disable audio | `&noaudio` |
| `&transparent` | Transparent background | `&transparent` |

## Testing the App

### Test 1: Launch Director Mode

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?director=r58studio"
```

**Expected**:
- App window opens
- VDO.Ninja director interface loads
- You may need to accept SSL certificate warning
- If cam1 is streaming, you should see it

### Test 2: View Camera Feed

```bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?view=r58-cam1"
```

**Expected**:
- Clean video feed from cam1
- No browser UI elements
- Perfect for OBS capture

### Test 3: OBS Capture

1. Launch app with camera view
2. Open OBS
3. Add Window Capture source
4. Select elecap window
5. Verify clean video feed

## Troubleshooting

### "elecap.app is damaged and can't be opened"

This is a Gatekeeper warning. Fix it:

```bash
xattr -cr ~/Applications/elecap.app
```

Then try opening again.

### SSL Certificate Warning

When connecting to `https://192.168.1.25:8443`:
1. Click "Advanced"
2. Click "Proceed to 192.168.1.25 (unsafe)"
3. This is expected for self-signed certificates

### App Won't Launch

Check if it's quarantined:

```bash
xattr -l ~/Applications/elecap.app
```

Remove quarantine:

```bash
xattr -d com.apple.quarantine ~/Applications/elecap.app
```

### No Video in OBS

1. Verify app is running and showing video
2. In OBS, try different capture methods
3. Make sure window isn't minimized
4. Check OBS permissions in System Settings → Privacy & Security

### Black Screen

1. Check hardware acceleration: Preferences → Advanced
2. Try disabling GPU acceleration
3. Restart the app

## Performance Tips

1. **Close unused apps** - Free up system resources
2. **Use hardware acceleration** - Enable in app settings
3. **Lower bitrate if needed** - Add `&bitrate=3000` to URL
4. **Disable audio if not needed** - Add `&noaudio` to URL
5. **Use LAN access** - Faster than Cloudflare Tunnel

## Security Note

⚠️ **Important**: Electron Capture does not auto-update Chromium. For security:
- Only use with trusted VDO.Ninja instances (like your self-hosted R58)
- Don't use with untrusted remote peers
- Update the app regularly from GitHub releases

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Cmd+Q` | Quit app |
| `Cmd+W` | Close window |
| `Cmd+M` | Minimize window |
| `Cmd+F` | Toggle fullscreen |
| `F11` | Toggle fullscreen |

## Creating Launch Scripts

Create a script for quick launching:

```bash
cat > ~/launch-vdo-director.sh << 'EOF'
#!/bin/bash
open -a ~/Applications/elecap.app --args --url="https://192.168.1.25:8443/?director=r58studio"
EOF

chmod +x ~/launch-vdo-director.sh
```

Then launch with:

```bash
~/launch-vdo-director.sh
```

## Comparison: Browser vs Electron App

| Feature | Browser | Electron App |
|---------|---------|--------------|
| Window chrome | ✗ Yes (address bar, tabs) | ✅ No (frameless) |
| OBS capture | ⚠️ Need to crop | ✅ Clean capture |
| Performance | ⚠️ Good | ✅ Better |
| Hardware acceleration | ✅ Yes | ✅ Yes |
| Updates | ✅ Auto | ⚠️ Manual |
| Transparency | ⚠️ Limited | ✅ Full support |

## Next Steps

1. ✅ App installed at `~/Applications/elecap.app`
2. 📋 Test launching with director mode
3. 📋 Test OBS window capture
4. 📋 Create launch scripts for common URLs
5. 📋 Configure OBS scenes with camera feeds

## Resources

- **GitHub**: https://github.com/steveseguin/electroncapture
- **Documentation**: https://docs.vdo.ninja/steves-helper-apps/electron-capture
- **VDO.Ninja Docs**: https://docs.vdo.ninja
- **Latest Releases**: https://github.com/steveseguin/electroncapture/releases

---

**Installation completed successfully!** 🎉

You can now launch the Electron Capture app and connect to your self-hosted VDO.Ninja server for clean, frameless video capture in OBS.
