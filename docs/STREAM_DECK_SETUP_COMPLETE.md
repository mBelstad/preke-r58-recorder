# Stream Deck Setup Guide

Complete guide for setting up Stream Deck with R58 camera controls via Bitfocus Companion.

## Two Setup Options

### Option 1: Companion on R58 Device (Recommended for Standalone Setup)

Companion runs directly on the R58 device. Stream Deck connects to Companion via USB or network.

**Pros:**
- ✅ No separate PC required
- ✅ Stream Deck can connect directly via USB
- ✅ All-in-one solution
- ✅ Works offline (no PC needed)

**Cons:**
- ⚠️ Requires Companion installation on device
- ⚠️ Slightly more setup initially

### Option 2: Companion on PC (Recommended for Multi-Device Setup)

Companion runs on a Windows/Mac/Linux PC. Stream Deck connects to PC. PC connects to R58 API.

**Pros:**
- ✅ Easier to manage Companion UI on PC
- ✅ Can control multiple R58 devices
- ✅ Better for complex setups
- ✅ No installation needed on R58 device

**Cons:**
- ⚠️ Requires PC to be running
- ⚠️ PC and R58 must be on same network

---

## Option 1: Companion on R58 Device

### Step 1: Install Companion on R58

```bash
# SSH to R58 device
./connect-r58-frp.sh

# Run installation script
cd /opt/preke-r58-recorder
sudo bash scripts/install-companion.sh
```

The script will:
- Install Companion from GitHub
- Build Companion
- Create systemd service
- Start Companion automatically

### Step 2: Access Companion Web UI

**From R58 device (local):**
```
http://localhost:8080
```

**From PC (via FRP tunnel):**
```
https://app.itagenten.no:8080
```

**From PC (local network):**
```
http://<r58-device-ip>:8080
```

**Note:** Companion uses port 8080 to avoid conflict with R58 API (port 8000)

### Step 3: Connect Stream Deck

1. **USB Connection (Recommended):**
   - Connect Stream Deck to R58 device via USB
   - Companion will automatically detect it
   - Stream Deck appears in Companion's device list

2. **Network Connection:**
   - Enable network mode in Stream Deck settings
   - Add Stream Deck in Companion: Settings → Devices → Add Device
   - Enter Stream Deck's IP address

### Step 4: Configure Companion

1. **Add HTTP Instance:**
   - Go to Instances → Add Instance
   - Search for "HTTP" and add it
   - Configure:
     - **Base URL**: `https://app.itagenten.no` (or `http://localhost:8000` for local)
     - **Default Method**: `PUT`
     - **Default Headers**: `Content-Type: application/json`

2. **Add Camera Control Buttons:**
   - See [COMPANION_PROFESSIONAL_SETUP.md](./COMPANION_PROFESSIONAL_SETUP.md) for button configurations
   - Example: Focus Auto button
     - Action: HTTP Request
     - Method: `PUT`
     - URL: `/api/v1/cameras/Sony FX30/settings/focus`
     - Body: `{"mode":"auto"}`

---

## Option 2: Companion on PC

### Step 1: Install Companion on PC

**Windows:**
1. Download from: https://bitfocus.io/companion/download/builds
2. Run installer
3. Launch Companion

**macOS:**
1. Download from: https://bitfocus.io/companion/download/builds
2. Open DMG and drag to Applications
3. Launch Companion

**Linux:**
```bash
# Install Node.js 20+ first
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Clone and build Companion
git clone https://github.com/bitfocus/companion.git
cd companion
npm install
npm run build
node dist/companion.js
```

### Step 2: Connect Stream Deck to PC

1. **USB Connection:**
   - Connect Stream Deck to PC via USB
   - Companion will automatically detect it

2. **Network Connection:**
   - Enable network mode in Stream Deck settings
   - Add Stream Deck in Companion: Settings → Devices → Add Device

### Step 3: Configure Companion

1. **Add HTTP Instance:**
   - Go to Instances → Add Instance
   - Search for "HTTP" and add it
   - Configure:
     - **Base URL**: `https://app.itagenten.no` (R58 API URL)
     - **Default Method**: `PUT`
     - **Default Headers**: `Content-Type: application/json`

2. **Test Connection:**
   - Create a test button:
     - Action: HTTP Request
     - Method: `GET`
     - URL: `/api/v1/cameras/`
   - Press button - should return list of cameras

3. **Add Camera Control Buttons:**
   - See [COMPANION_PROFESSIONAL_SETUP.md](./COMPANION_PROFESSIONAL_SETUP.md) for configurations

---

## Stream Deck Button Layouts

### Recommended Layout for Production

#### Page 1: Camera Selection
- **Button 1**: Switch to Sony FX30
- **Button 2**: Switch to BMD Studio 4K Pro
- **Button 3**: Switch to OBSbot PTZ

#### Page 2: Focus Controls
- **Button 1**: Focus Auto
- **Button 2**: Focus Manual 50%
- **Button 3**: Focus Manual 75%
- **Button 4**: Focus Manual 100%

#### Page 3: Exposure Controls
- **Button 1**: ISO 400
- **Button 2**: ISO 800
- **Button 3**: ISO 1600
- **Button 4**: ISO 3200
- **Button 5**: Shutter 1/60
- **Button 6**: Shutter 1/125
- **Button 7**: Shutter 1/250

#### Page 4: PTZ Controls (OBSbot/Sony)
- **Button 1**: PTZ Preset 1
- **Button 2**: PTZ Preset 2
- **Button 3**: PTZ Preset 3
- **Button 4**: PTZ Center
- **Button 5**: PTZ Left
- **Button 6**: PTZ Right
- **Button 7**: PTZ Up
- **Button 8**: PTZ Down

#### Page 5: White Balance
- **Button 1**: WB Auto
- **Button 2**: WB 3200K
- **Button 3**: WB 5600K
- **Button 4**: WB 6500K

---

## Testing Your Setup

### Test 1: API Connectivity

**From PC:**
```bash
curl https://app.itagenten.no/api/v1/cameras/
```

Should return list of cameras: `["Sony FX30", "BMD Studio 4K Pro", ...]`

### Test 2: Camera Status

**From PC:**
```bash
curl https://app.itagenten.no/api/v1/cameras/Sony%20FX30/status
```

Should return camera status with connection info.

### Test 3: Control Test

**From PC:**
```bash
curl -X PUT https://app.itagenten.no/api/v1/cameras/Sony%20FX30/settings/focus \
  -H "Content-Type: application/json" \
  -d '{"mode":"auto"}'
```

Should return: `{"success":true,"camera":"Sony FX30","parameter":"focus"}`

### Test 4: Stream Deck Button

1. Create a test button in Companion
2. Configure HTTP request to set focus auto
3. Press button on Stream Deck
4. Verify camera responds

---

## Troubleshooting

### Stream Deck Not Detected

**If Companion on R58:**
1. Check USB connection: `lsusb | grep Stream`
2. Check Companion logs: `sudo journalctl -u companion -n 50`
3. Restart Companion: `sudo systemctl restart companion`

**If Companion on PC:**
1. Check USB connection in Device Manager (Windows) or System Information (Mac)
2. Try different USB port
3. Restart Companion application

### Companion Can't Connect to R58 API

1. **Check API is accessible:**
   ```bash
   curl https://app.itagenten.no/api/v1/cameras/
   ```

2. **Check firewall:**
   - R58 device should allow HTTPS (443) and HTTP (8000)
   - PC should allow outbound HTTPS

3. **Verify base URL in Companion:**
   - Should be: `https://app.itagenten.no`
   - Or local: `http://<r58-ip>:8000` (if on same network)

### Camera Not Responding

1. **Check camera is enabled:**
   ```bash
   # On R58 device
   grep -A 5 "Sony FX30" /opt/preke-r58-recorder/config.yml
   # Should show: enabled: true
   ```

2. **Check camera connection:**
   ```bash
   curl http://localhost:8000/api/v1/cameras/Sony%20FX30/status
   ```

3. **Restart R58 service:**
   ```bash
   sudo systemctl restart preke-recorder
   ```

### Companion Web UI Not Accessible

**If Companion on R58:**
1. Check service status: `sudo systemctl status companion`
2. Check port 8000 is not in use: `sudo ss -tlnp | grep 8000`
3. Check logs: `sudo journalctl -u companion -n 100`

**If Companion on PC:**
1. Check Companion is running
2. Check firewall allows port 8000 (default) or configured port
3. Try accessing: `http://localhost:8000` (or configured port)

---

## Advanced Configuration

### Using Variables in Companion

Companion supports variables for dynamic camera names:

```
/api/v1/cameras/$(internal:custom_var_camera_name)/settings/focus
```

### Feedback in Companion

Configure feedback to show camera status:

1. In button configuration, add feedback
2. Use HTTP GET to `/api/v1/cameras/{camera_name}/status`
3. Parse response to show connection status

### Multiple Stream Decks

Companion supports multiple Stream Decks:
- Connect additional Stream Decks via USB or network
- Each Stream Deck can have different button layouts
- All Stream Decks control the same R58 cameras

---

## Security Considerations

1. **HTTPS Only:** Always use `https://app.itagenten.no` for production
2. **API Authentication:** Consider adding API keys if exposing publicly
3. **Network Isolation:** Keep R58 device on isolated network if possible
4. **Firewall Rules:** Only allow necessary ports (443, 8000)

---

## Support

- **Companion Documentation:** https://github.com/bitfocus/companion
- **R58 API Documentation:** `/docs/API.md`
- **Camera Setup:** `/docs/CAMERA_PLUGINS_SUMMARY.md`
- **Companion Setup:** `/docs/COMPANION_PROFESSIONAL_SETUP.md`

---

## Quick Reference

### Companion Service Commands (R58 Device)

```bash
# Start Companion
sudo systemctl start companion

# Stop Companion
sudo systemctl stop companion

# Restart Companion
sudo systemctl restart companion

# Check status
sudo systemctl status companion

# View logs
sudo journalctl -u companion -f

# Enable on boot
sudo systemctl enable companion
```

### API Endpoints Quick Reference

```
GET  /api/v1/cameras/                              # List cameras
GET  /api/v1/cameras/{name}/status                 # Camera status
PUT  /api/v1/cameras/{name}/settings/focus         # Set focus
PUT  /api/v1/cameras/{name}/settings/whiteBalance  # Set WB
PUT  /api/v1/cameras/{name}/settings/iso           # Set ISO
PUT  /api/v1/cameras/{name}/settings/ptz           # Move PTZ
PUT  /api/v1/cameras/{name}/settings/ptz/preset/1  # Recall preset
```
