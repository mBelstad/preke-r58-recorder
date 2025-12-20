# MSE Streaming - Quick Start Guide

## What is MSE?

Media Source Extensions (MSE) is a new streaming protocol added to the R58 recorder that provides:
- **Lower latency**: 500ms-2s (vs 2-10s for HLS)
- **H.265 support**: Native HEVC playback on Safari and Chrome
- **Works remotely**: Through Cloudflare Tunnel (unlike WebRTC)
- **Better quality**: No transcoding needed for most browsers

## Quick Test (5 minutes)

### Step 1: Restart the Server
The new MSE endpoint needs the server to restart:

```bash
# Stop current server (Ctrl+C if running)
# Then restart:
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
source venv/bin/activate
python -m src.main
```

### Step 2: Test the Standalone Page
1. Open browser: `https://recorder.itagenten.no/static/mse_test.html`
2. Select "Camera 0" (or any camera with active signal)
3. Leave codec on "Auto"
4. Click **"Start Stream"**
5. ✅ Video should appear within 1-2 seconds

**What to check:**
- Browser Codec Support shows ✓ for H.265 (Safari/Chrome) or H.264 (Firefox)
- Latency shown in stats (should be < 2000ms)
- Video plays smoothly
- Console log shows "MSE WebSocket connected"

### Step 3: Test in Multiview
1. Open: `https://recorder.itagenten.no/`
2. Find **"Stream Protocol"** dropdown in right sidebar
3. Select **"MSE (H.265, Low Latency)"**
4. ✅ All camera streams should restart with MSE

**What to check:**
- Videos reload and play within 2 seconds
- Protocol hint shows "MSE over WebSocket..."
- No black flickering
- Console shows "Auto-selecting MSE for camX"

### Step 4: Test Auto Mode
1. In multiview, select **"Auto (Best Available)"**
2. ✅ Should automatically use MSE for remote access

**Expected behavior:**
- Remote access → MSE (H.265 or H.264)
- Local access → WebRTC
- Fallback → HLS if MSE not supported

## Troubleshooting

### "Not Found" Error
**Problem**: Server hasn't been restarted
**Solution**: Restart the FastAPI server (see Step 1)

### Video Not Playing
**Problem**: No camera signal or wrong stream path
**Solution**: 
- Check camera is connected: `http://localhost:8554/cam0`
- Try different camera in dropdown
- Check console for errors

### "Codec not supported"
**Problem**: Very old browser
**Solution**: 
- Update browser to latest version
- Or select "HLS (Universal)" protocol

### High Latency (>3s)
**Problem**: Network issues or server overload
**Solution**:
- Check network connection
- Try "HLS" protocol for more stable buffering
- Check FFmpeg process isn't stuck

### WebSocket Connection Failed
**Problem**: Firewall or proxy blocking WebSocket
**Solution**:
- Check Cloudflare Tunnel is running
- Verify WSS connections allowed
- Try HLS as fallback

## Browser Compatibility

| Browser | Best Protocol | H.265 MSE | Expected Latency |
|---------|---------------|-----------|------------------|
| Safari (Mac/iOS) | MSE | ✅ Yes | 500ms-1s |
| Chrome (all) | MSE | ✅ Yes* | 500ms-1s |
| Edge (Windows) | MSE | ✅ Yes* | 500ms-1s |
| Firefox (all) | MSE | ⚠️ H.264 | 1-2s |

*Hardware-dependent, but widely available

## Console Commands (Debug)

Open browser console (F12) and try:

```javascript
// Check current protocol
console.log('Protocol:', streamProtocol);

// Check if remote
console.log('Is Remote:', IS_REMOTE);

// Check H.265 support
console.log('H.265:', MediaSource.isTypeSupported('video/mp4; codecs="hev1.1.6.L120.90"'));

// Check active MSE connections
console.log('MSE Connections:', Object.keys(mseConnections));

// Force protocol change
changeStreamProtocol('mse');
```

## Performance Comparison

Test the same camera with different protocols:

1. Select **"HLS"** → Note latency and quality
2. Select **"MSE"** → Compare latency and quality
3. Select **"Auto"** → See which is chosen

**Expected results:**
- MSE latency: 500-2000ms
- HLS latency: 2000-10000ms
- MSE quality: Better (native H.265)
- HLS quality: Good (transcoded H.264)

## API Testing

Test the WebSocket endpoint directly:

```javascript
// In browser console
const ws = new WebSocket('wss://recorder.itagenten.no/ws/mse/cam0');
ws.binaryType = 'arraybuffer';

ws.onopen = () => console.log('Connected!');
ws.onmessage = (e) => {
    if (typeof e.data === 'string') {
        console.log('Message:', e.data);
    } else {
        console.log('Chunk:', e.data.byteLength, 'bytes');
    }
};
```

## Next Steps

Once basic testing works:

1. **Test all cameras**: Verify MSE works for cam0-3
2. **Test mixer output**: Try `mixer_program` stream
3. **Test reconnection**: Disconnect/reconnect network
4. **Test protocol switching**: Switch between protocols while streaming
5. **Test on mobile**: Safari iOS should have excellent H.265 support

## Getting Help

If issues persist:

1. Check `MSE_IMPLEMENTATION_COMPLETE.md` for detailed architecture
2. Check browser console for errors
3. Check server logs for FFmpeg errors
4. Verify MediaMTX is serving RTSP: `ffplay rtsp://localhost:8554/cam0`

## Success Criteria

✅ MSE test page loads and plays video
✅ Multiview can switch to MSE protocol
✅ Auto mode selects MSE for remote access
✅ Latency is < 2 seconds
✅ H.265 detected on Safari/Chrome
✅ H.264 fallback works on Firefox
✅ No console errors during playback

**Status**: Ready for testing after server restart
**Date**: December 20, 2025
