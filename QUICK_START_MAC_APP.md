# Quick Start - Mac App

**Electron Capture for Preke R58 Recorder**

---

## Quick Launch Commands

### Director/Mixer Mode
```bash
./launch-director.sh
```
Full VDO.Ninja director interface for controlling mixer and viewing all cameras.

### Camera Views (for OBS)
```bash
./launch-cam0.sh    # Camera 0 (4K)
./launch-cam2.sh    # Camera 2 (1080p)
./launch-mixer.sh   # Mixer output
```
Clean, frameless windows perfect for OBS window capture.

### Stop App
```bash
killall elecap
```

---

## OBS Integration (3 Steps)

1. **Launch camera view**:
   ```bash
   ./launch-cam0.sh
   ```

2. **Add to OBS**:
   - Add Source → Window Capture
   - Select window: "elecap"
   - Capture Method: Window Capture (macOS 10.15+)

3. **Done!** Clean video feed with no browser UI to crop.

---

## Testing

Run automated test suite:
```bash
./test-mac-app.sh
```

---

## Troubleshooting

### App won't launch?
```bash
xattr -cr ~/Applications/elecap.app
```

### SSL warning?
Click "Advanced" → "Proceed to 192.168.1.25 (unsafe)" - this is expected for self-signed certificates.

### App already running?
```bash
killall elecap
sleep 1
./launch-director.sh
```

---

## More Info

See **MAC_APP_TEST_REPORT.md** for comprehensive testing details and advanced features.

---

**Status**: ✅ Fully functional and ready to use!
