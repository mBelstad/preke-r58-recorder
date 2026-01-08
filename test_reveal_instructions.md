# Testing Reveal.js on R58 Device

Since you're connected via Tailscale, test reveal.js using these steps:

## Quick Test (Browser)

1. Open your browser
2. Navigate to: `http://100.98.37.53:8000/reveal.js/reveal.js`
   - Or: `http://linaro-alip.tailab6fd7.ts.net:8000/reveal.js/reveal.js`
3. You should see the reveal.js JavaScript code

## Test Files

Test these URLs in your browser:
- `http://100.98.37.53:8000/reveal.js/reveal.js` (main library)
- `http://100.98.37.53:8000/reveal.js/reveal.css` (stylesheet)
- `http://100.98.37.53:8000/reveal.js/theme/black.css` (black theme)

## Interactive Test Page

Open `test_reveal_device.html` in your browser and:
1. Enter your device URL (e.g., `http://100.98.37.53:8000`)
2. Click "Test Connection" to verify device is reachable
3. Click "Test Reveal.js Files" to verify all files are accessible
4. Click "Load Reveal.js Presentation" to see a working presentation

## Command Line Test

```bash
# Test health endpoint
curl http://100.98.37.53:8000/health

# Test reveal.js file
curl -I http://100.98.37.53:8000/reveal.js/reveal.js

# Check file size
curl -s http://100.98.37.53:8000/reveal.js/reveal.js | wc -c
```

Expected: reveal.js should be ~114KB

## If Connection Fails

1. Verify Tailscale is running: `tailscale status`
2. Ping the device: `tailscale ping linaro-alip`
3. Check if device is online: Look for `100.98.37.53` in `tailscale status`
4. Try HTTPS instead of HTTP (if device uses SSL)
