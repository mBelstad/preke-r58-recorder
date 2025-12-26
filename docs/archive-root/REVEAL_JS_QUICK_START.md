# Reveal.js Video Source - Quick Start

**Get presentations as video in 3 steps!**

---

## Prerequisites

### On R58 Device

1. **Install wpesrc** (if not already installed):
   ```bash
   sudo apt install gstreamer1.0-plugins-bad-apps libwpewebkit-1.0-3
   ```

2. **Verify installation**:
   ```bash
   gst-inspect-1.0 wpesrc
   ```

3. **Restart services**:
   ```bash
   sudo systemctl restart mediamtx preke-recorder
   ```

---

## Quick Start (3 Steps)

### Step 1: Start Reveal.js Source

```bash
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=demo"
```

**What this does**: Starts rendering Reveal.js presentation to video stream at `rtsp://localhost:8554/slides`

### Step 2: Start Mixer with Presentation Scene

```bash
# Start mixer
curl -X POST http://recorder.itagenten.no/api/mixer/start

# Load presentation scene
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_focus"}'
```

### Step 3: View Program Output

```bash
# Play mixer output
ffplay rtsp://recorder.itagenten.no:8554/mixer_program

# Or open in browser
open http://recorder.itagenten.no/switcher
```

**Done!** Your presentation is now a video source in the mixer.

---

## Available Scenes

### Full-Screen Presentation
```bash
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_focus"}'
```

### Presentation with Speaker (70/30 Split)
```bash
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_speaker"}'
```

### Presentation with Picture-in-Picture
```bash
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_pip"}'
```

---

## Common Tasks

### Check Status

```bash
curl http://recorder.itagenten.no/api/reveal/status
```

### Stop Reveal.js Source

```bash
curl -X POST http://recorder.itagenten.no/api/reveal/stop
```

### Switch to Camera Scene

```bash
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "cam1_full"}'
```

### Stop Mixer

```bash
curl -X POST http://recorder.itagenten.no/api/mixer/stop
```

---

## Troubleshooting

### Reveal.js Won't Start

**Check renderer availability**:
```bash
curl http://recorder.itagenten.no/api/reveal/status
```

If `renderer: null`, install wpesrc:
```bash
ssh linaro@r58.itagenten.no
sudo apt install gstreamer1.0-plugins-bad-apps libwpewebkit-1.0-3
sudo systemctl restart preke-recorder
```

### Stream Not Available in Mixer

**Check if Reveal.js is running**:
```bash
curl http://recorder.itagenten.no/api/reveal/status
```

State should be "running"

**Check MediaMTX**:
```bash
curl http://127.0.0.1:9997/v3/paths/get/slides
```

Should show `sourceReady: true`

### Presentation Not Visible

**Check mixer status**:
```bash
curl http://recorder.itagenten.no/api/mixer/status
```

Verify:
- `state: "PLAYING"`
- `current_scene: "presentation_focus"` (or other presentation scene)

**Check logs**:
```bash
ssh linaro@r58.itagenten.no
sudo journalctl -u preke-recorder -f | grep -i "reveal\|slides"
```

---

## Advanced Usage

### Custom Presentation URL

```bash
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=custom&url=http://localhost:8000/graphics?presentation=my_pres"
```

### Enable Overlay Mode (Experimental)

```bash
# Start with camera scene
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "cam1_full"}'

# Enable slides overlay (alpha = 0.8 for transparency)
curl -X POST "http://recorder.itagenten.no/api/mixer/overlay/slides?alpha=0.8"
```

**Note**: Overlay feature requires pipeline rebuild (not yet dynamic)

---

## Performance

**Expected metrics with wpesrc + mpph265enc**:

- CPU Usage: ~5-10% (hardware encoding)
- Memory: ~200-300MB
- Latency: 100-300ms (wpesrc → MediaMTX → Mixer)
- Resolution: 1920x1080 @ 30fps
- Bitrate: 4 Mbps

---

## API Reference

### Start Reveal.js

```
POST /api/reveal/start?presentation_id={id}&url={url}
```

Parameters:
- `presentation_id` (required): Unique identifier
- `url` (optional): URL to render (defaults to `/graphics?presentation={id}`)

### Stop Reveal.js

```
POST /api/reveal/stop
```

### Get Status

```
GET /api/reveal/status
```

### Navigate Slides (Placeholder)

```
POST /api/reveal/navigate/{direction}
```

Directions: `next`, `prev`, `first`, `last`

**Note**: Not yet implemented

### Go to Slide (Placeholder)

```
POST /api/reveal/goto/{slide}
```

**Note**: Not yet implemented

---

## Files Reference

| File | Purpose |
|------|---------|
| `REVEAL_JS_VIDEO_SOURCE_IMPLEMENTATION.md` | Complete implementation guide |
| `REVEAL_JS_TESTING_CHECKLIST.md` | Comprehensive testing checklist |
| `REVEAL_JS_BUGS_FIXED.md` | This file - bugs and fixes |
| `REVEAL_JS_QUICK_START.md` | Quick start guide |
| `test_reveal_deployment.sh` | Automated deployment tests |

---

## Next Steps

1. **Deploy to R58**: `./deploy.sh`
2. **Run tests**: `./test_reveal_deployment.sh` (on R58)
3. **Test manually**: Follow this quick start guide
4. **Report issues**: Check logs and document any problems

---

**Status**: ✅ Ready for deployment and testing
