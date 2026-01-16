# Companion Quick Start Guide

Get Stream Deck working with R58 camera controls in 5 minutes.

## Choose Your Setup

### 🖥️ Option A: Companion on PC (Easiest)

**Best for:** Most users, easier setup

1. **Install Companion on your PC:**
   - Download: https://bitfocus.io/companion/download/builds
   - Install and launch Companion

2. **Connect Stream Deck to PC:**
   - Plug Stream Deck into PC via USB
   - Companion will detect it automatically

3. **Add HTTP Instance in Companion:**
   - Instances → Add Instance → Search "HTTP"
   - Base URL: `https://app.itagenten.no`
   - Method: `PUT`
   - Headers: `Content-Type: application/json`

4. **Create Your First Button:**
   - Add button → HTTP Request
   - Method: `PUT`
   - URL: `/api/v1/cameras/Sony FX30/settings/focus`
   - Body: `{"mode":"auto"}`
   - Press button → Camera should respond!

**Done!** Your Stream Deck now controls cameras.

---

### 📱 Option B: Companion on R58 Device (Standalone)

**Best for:** No PC required, all-in-one solution

1. **Install Companion on R58:**
   ```bash
   ./connect-r58-frp.sh
   cd /opt/preke-r58-recorder
   sudo bash scripts/install-companion.sh
   ```

2. **Access Companion Web UI:**
   - Open: `https://app.itagenten.no:8080`
   - Or local: `http://<device-ip>:8080`

3. **Connect Stream Deck:**
   - **USB:** Plug Stream Deck into R58 device
   - **Network:** Enable network mode in Stream Deck, add in Companion

4. **Configure as above** (same HTTP instance setup)

**Done!** Stream Deck works directly with R58 device.

---

## Quick Button Examples

### Focus Auto
- Method: `PUT`
- URL: `/api/v1/cameras/Sony FX30/settings/focus`
- Body: `{"mode":"auto"}`

### ISO 400
- Method: `PUT`
- URL: `/api/v1/cameras/Sony FX30/settings/iso`
- Body: `{"value":400}`

### PTZ Preset 1
- Method: `PUT`
- URL: `/api/v1/cameras/OBSbot PTZ/settings/ptz/preset/1`
- Body: `{}`

### PTZ Move
- Method: `PUT`
- URL: `/api/v1/cameras/OBSbot PTZ/settings/ptz`
- Body: `{"pan":0.5,"tilt":-0.3,"zoom":0.2}`

---

## Troubleshooting

**Can't connect to API?**
```bash
curl https://app.itagenten.no/api/v1/cameras/
```
Should return: `["Sony FX30", ...]`

**Stream Deck not detected?**
- Check USB connection
- Restart Companion
- Check Companion logs

**Camera not responding?**
- Check camera is enabled in `config.yml`
- Restart R58 service: `sudo systemctl restart preke-recorder`
- Test API: `curl https://app.itagenten.no/api/v1/cameras/{camera}/status`

---

## Full Documentation

- **Complete Setup:** [STREAM_DECK_SETUP_COMPLETE.md](./STREAM_DECK_SETUP_COMPLETE.md)
- **Button Configurations:** [COMPANION_PROFESSIONAL_SETUP.md](./COMPANION_PROFESSIONAL_SETUP.md)
- **Camera Support:** [CAMERA_PLUGINS_SUMMARY.md](./CAMERA_PLUGINS_SUMMARY.md)

---

## Need Help?

1. Run test script: `bash scripts/test-companion-setup.sh`
2. Check Companion logs
3. Verify API is accessible
4. See full docs for detailed troubleshooting
