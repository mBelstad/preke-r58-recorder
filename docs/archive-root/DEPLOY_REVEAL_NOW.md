# Deploy Reveal.js Video Source - Ready Now! 🚀

**Status**: ✅ Code complete, tested locally, ready for deployment  
**Date**: December 19, 2025

---

## 🎯 Current Status

### ✅ Local Implementation Complete
- All code written and validated
- 4 bugs fixed
- Syntax checked
- Documentation complete
- Browser test page created

### ⚠️ Not Yet Deployed to R58
- API test shows: `{"detail":"Not Found"}` for `/api/reveal/status`
- This is expected - the new code is not on R58 yet
- Need to deploy to make it work

---

## 🚀 Deploy Now (3 Commands)

### Step 1: Deploy Code
```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./deploy.sh r58.itagenten.no linaro
```

This will:
- Push code to git
- SSH to R58
- Pull latest code
- Restart service

### Step 2: Verify Deployment
```bash
# Wait 10 seconds for service to restart
sleep 10

# Test API endpoint
curl http://recorder.itagenten.no/api/reveal/status
```

Expected output:
```json
{
  "state": "idle",
  "presentation_id": null,
  "url": null,
  "renderer": "wpe",
  "resolution": "1920x1080",
  "framerate": 30,
  "bitrate": 4000,
  "mediamtx_path": "slides",
  "stream_url": null
}
```

### Step 3: Run Deployment Tests
```bash
ssh linaro@r58.itagenten.no "cd /opt/preke-r58-recorder && ./test_reveal_deployment.sh"
```

---

## 📋 What Will Be Deployed

### New Files (3)
1. `src/reveal_source.py` - RevealSourceManager (393 lines)
2. `scenes/presentation_speaker.json` - Scene template
3. `scenes/presentation_pip.json` - Scene template

### Modified Files (8)
1. `src/config.py` - Added RevealConfig
2. `config.yml` - Added reveal section
3. `mediamtx.yml` - Added slides paths
4. `src/mixer/core.py` - Added slides handling
5. `src/graphics/__init__.py` - Added reveal param
6. `src/graphics/renderer.py` - Connected manager
7. `src/main.py` - Added API endpoints
8. `scenes/presentation_focus.json` - Updated for slides

### Test Files (3)
1. `test_reveal_browser.html` - Browser test page
2. `test_reveal_deployment.sh` - Deployment tests
3. `test_reveal_integration.py` - Integration tests

---

## 🧪 After Deployment - Test It!

### Quick Test (Browser)
1. Open: `test_reveal_browser.html` (already open)
2. Click "Run All Tests"
3. Should see: ✓ All tests pass

### Manual Test (API)
```bash
# Start Reveal.js
curl -X POST "http://recorder.itagenten.no/api/reveal/start?presentation_id=demo"

# Check status
curl http://recorder.itagenten.no/api/reveal/status

# Start mixer
curl -X POST http://recorder.itagenten.no/api/mixer/start

# Load presentation scene
curl -X POST "http://recorder.itagenten.no/api/mixer/set_scene" \
  -H "Content-Type: application/json" \
  -d '{"scene_id": "presentation_focus"}'
```

---

## ⚠️ Pre-Deployment Checklist

- [x] Code written and tested
- [x] Bugs fixed
- [x] Documentation complete
- [x] Test scripts created
- [ ] **Deploy to R58** ← YOU ARE HERE
- [ ] Verify wpesrc available
- [ ] Run deployment tests
- [ ] Test in browser

---

## 🔍 Troubleshooting

### If Deployment Fails

**Check SSH access:**
```bash
ssh linaro@r58.itagenten.no "hostname"
```

**Check service status:**
```bash
ssh linaro@r58.itagenten.no "sudo systemctl status preke-recorder"
```

**View logs:**
```bash
ssh linaro@r58.itagenten.no "sudo journalctl -u preke-recorder -n 50"
```

### If wpesrc Not Available

```bash
ssh linaro@r58.itagenten.no
sudo apt install gstreamer1.0-plugins-bad-apps libwpewebkit-1.0-3
sudo systemctl restart preke-recorder
```

---

## 📊 Expected Results After Deployment

### API Endpoints Should Work
- ✅ `/api/reveal/status` - Returns status JSON
- ✅ `/api/reveal/start` - Starts Reveal.js
- ✅ `/api/reveal/stop` - Stops Reveal.js
- ✅ `/api/mixer/status` - Shows overlay fields

### Scenes Should Include Slides
- ✅ `presentation_focus` - Full screen slides
- ✅ `presentation_speaker` - Slides + speaker
- ✅ `presentation_pip` - Slides + PiP

### MediaMTX Should Have Slides Path
- ✅ `rtsp://recorder.itagenten.no:8554/slides`
- ✅ `http://recorder.itagenten.no:8888/slides/index.m3u8`

---

## 🎉 Ready to Deploy!

**Run this now:**
```bash
cd "/Users/mariusbelstad/R58 app/preke-r58-recorder"
./deploy.sh r58.itagenten.no linaro
```

Then test with the browser test page!

---

## 📚 Documentation Reference

After deployment, refer to:
- **REVEAL_JS_QUICK_START.md** - User guide
- **REVEAL_JS_TESTING_CHECKLIST.md** - Testing guide
- **REVEAL_JS_BUGS_FIXED.md** - Bug analysis
- **REVEAL_JS_IMPLEMENTATION_COMPLETE.md** - Full summary

---

**Status**: Ready to deploy! Run `./deploy.sh` now! 🚀
