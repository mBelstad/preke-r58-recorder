# Preke Studio - Bug Fixes & Improvements

**Date**: 2025-12-19  
**Version**: 1.0.1 (Proposed)  
**Priority**: Critical Bugs + High Priority Improvements

---

## Critical Bug Fixes

### Fix #1: Ensure Window Creation on Launch

**File**: `/tmp/preke-studio-extracted/preke-studio.js`  
**Lines**: Add after line 381

```javascript
// Add this function to ensure window is always created
function ensureWindowCreated(mainWindow, args) {
  if (!mainWindow || mainWindow.isDestroyed()) {
    console.error('Main window not created! Creating now...');
    // This should be called from main.js
    return null;
  }
  return mainWindow;
}

// Update initPrekeStudio to validate window
function initPrekeStudio(window) {
  if (!window) {
    console.error('initPrekeStudio called with null window!');
    return false;
  }
  mainWindow = window;
  setupIpcHandlers();
  return true;
}
```

**File**: `/tmp/preke-studio-extracted/main.js` (needs modification)  
**Add after window creation**:

```javascript
// After creating mainWindow, check if we should show launcher
const prekeStudio = require('./preke-studio.js');

// Parse command line args
const args = parseArgs(); // existing function

if (prekeStudio.shouldShowLauncher(args)) {
  // Show Preke Studio launcher
  mainWindow.loadFile(prekeStudio.getLauncherPath());
  prekeStudio.initPrekeStudio(mainWindow);
} else {
  // Show regular Electron Capture with URL
  mainWindow.loadURL(args.url);
}
```

---

### Fix #2: Consistent Protocol Handling

**File**: `/tmp/preke-studio-extracted/preke-studio.js`  
**Lines**: 313-345

**Replace**:
```javascript
function getTabUrl(tabName) {
  if (!connectionConfig) {
    console.error('getTabUrl called without connectionConfig!');
    return 'about:blank';
  }
  
  const isLocal = connectionConfig.connectionType === 'local';
  const host = connectionConfig.host;
  const room = connectionConfig.roomId || 'r58studio';

  let url;
  switch(tabName) {
    case 'recorder':
      // Use HTTPS for recorder too, with fallback to HTTP
      url = isLocal 
        ? `https://${host}:5000/`  // Try HTTPS first
        : 'https://recorder.itagenten.no/';
      break;
    case 'mixer':
      url = getMixerUrl(currentMixerView);
      break;
    case 'conference':
      url = isLocal
        ? `https://${host}:8443/?push=${room}`
        : `https://vdo.itagenten.no/?push=${room}`;
      break;
    default:
      url = 'about:blank';
  }
  
  console.log(`getTabUrl(${tabName}) -> ${url}`);
  return url;
}
```

**Add certificate handling in main.js**:
```javascript
// Add to main.js after app.whenReady()
const { app, session } = require('electron');

app.whenReady().then(() => {
  // Allow self-signed certificates for local R58 devices
  session.defaultSession.setCertificateVerifyProc((request, callback) => {
    const { hostname } = new URL(request.url);
    
    // Allow self-signed certs for local IPs
    if (hostname.match(/^192\.168\.\d+\.\d+$/) || 
        hostname.match(/^10\.\d+\.\d+\.\d+$/) ||
        hostname === 'localhost' ||
        hostname === '127.0.0.1') {
      callback(0); // Accept
    } else {
      callback(-3); // Use default verification
    }
  });
});
```

---

### Fix #3: Error Handling for Missing Dependencies

**File**: `/tmp/preke-studio-extracted/preke-studio.js`  
**Lines**: 7-36

**Replace**:
```javascript
// Try to load optional dependencies with better error handling
let Store, Bonjour;
let storeAvailable = false;
let bonjourAvailable = false;

try {
  Store = require('electron-store');
  storeAvailable = true;
  console.log('✓ electron-store loaded successfully');
} catch (e) {
  console.warn('⚠️ electron-store not available - saved connections disabled');
  console.warn('Install with: npm install electron-store');
}

try {
  const BonjourService = require('bonjour-service');
  Bonjour = new BonjourService.Bonjour();
  bonjourAvailable = true;
  console.log('✓ bonjour-service loaded successfully');
} catch (e) {
  console.warn('⚠️ bonjour-service not available - device discovery disabled');
  console.warn('Install with: npm install bonjour-service');
}

// State
let connectionConfig = null;
let tabViews = {};
let currentTab = null;
let currentMixerView = 'director';
let mainWindow = null;

// Profile storage with fallback
let store = null;
let inMemoryProfiles = []; // Fallback when electron-store unavailable

if (Store && storeAvailable) {
  try {
    store = new Store({
      name: 'preke-studio-profiles',
      defaults: {
        profiles: []
      }
    });
    console.log('✓ Profile storage initialized');
  } catch (e) {
    console.error('Failed to initialize electron-store:', e);
    storeAvailable = false;
  }
}
```

**Update saved connections handlers**:
```javascript
// Update get-saved-connections handler (line ~140)
ipcMain.on('get-saved-connections', (event) => {
  if (store && storeAvailable) {
    const profiles = store.get('profiles', []);
    event.sender.send('saved-connections', profiles);
  } else {
    // Use in-memory fallback
    event.sender.send('saved-connections', inMemoryProfiles);
    // Also send warning to UI
    event.sender.send('feature-unavailable', {
      feature: 'saved-connections',
      reason: 'electron-store not available'
    });
  }
});

// Update save-connection handler (line ~145)
ipcMain.on('save-connection', (event, config) => {
  if (store && storeAvailable) {
    const profiles = store.get('profiles', []);
    const existingIndex = profiles.findIndex(p => 
      p.connectionType === config.connectionType && 
      p.host === config.host && 
      p.roomId === config.roomId
    );
    
    if (existingIndex >= 0) {
      profiles[existingIndex] = config;
    } else {
      profiles.push(config);
    }
    
    store.set('profiles', profiles);
    console.log('✓ Connection saved to disk');
  } else {
    // Use in-memory fallback
    const existingIndex = inMemoryProfiles.findIndex(p => 
      p.connectionType === config.connectionType && 
      p.host === config.host && 
      p.roomId === config.roomId
    );
    
    if (existingIndex >= 0) {
      inMemoryProfiles[existingIndex] = config;
    } else {
      inMemoryProfiles.push(config);
    }
    console.log('⚠️ Connection saved to memory only (will be lost on restart)');
  }
});
```

**Update device discovery**:
```javascript
function discoverDevices(event) {
  if (!Bonjour || !bonjourAvailable) {
    // Send error message to UI
    event.sender.send('discovery-error', {
      message: 'Device discovery unavailable',
      reason: 'bonjour-service not installed',
      solution: 'Enter IP address manually'
    });
    
    // Send completion immediately
    setTimeout(() => {
      event.sender.send('discovery-complete');
    }, 500);
    return;
  }

  const browser = Bonjour.find({ type: 'http' });
  let timeout = null;
  let foundDevices = 0;

  browser.on('up', (service) => {
    const name = (service.name || '').toLowerCase();
    if (name.includes('r58') || name.includes('preke') || name.includes('recorder')) {
      foundDevices++;
      event.sender.send('device-found', {
        name: service.name,
        host: service.host,
        port: service.port || 5000,
        addresses: service.addresses || []
      });
    }
  });

  timeout = setTimeout(() => {
    browser.stop();
    console.log(`✓ Device discovery complete - found ${foundDevices} device(s)`);
    event.sender.send('discovery-complete');
  }, 5000);
}
```

---

## High Priority Improvements

### Improvement #1: Input Validation

**File**: `/tmp/preke-studio-extracted/launcher.js`  
**Add before line 188 (connect function)**:

```javascript
// Input validation functions
function validateIPAddress(ip) {
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
  if (!ipPattern.test(ip)) {
    return { valid: false, error: 'Invalid IP address format' };
  }
  
  const parts = ip.split('.');
  for (let part of parts) {
    const num = parseInt(part, 10);
    if (num < 0 || num > 255) {
      return { valid: false, error: 'IP address octets must be 0-255' };
    }
  }
  
  return { valid: true };
}

function validateRoomId(roomId) {
  if (!roomId || roomId.trim().length === 0) {
    return { valid: false, error: 'Room ID cannot be empty' };
  }
  
  if (roomId.length > 50) {
    return { valid: false, error: 'Room ID too long (max 50 characters)' };
  }
  
  // Allow alphanumeric, dash, underscore
  const roomPattern = /^[a-zA-Z0-9_-]+$/;
  if (!roomPattern.test(roomId)) {
    return { valid: false, error: 'Room ID can only contain letters, numbers, dash, and underscore' };
  }
  
  return { valid: true };
}

function sanitizeInput(input) {
  return input.trim().replace(/[<>'"]/g, '');
}
```

**Update connect function (line 188)**:
```javascript
function connect() {
  const connectionType = document.querySelector('input[name="connectionType"]:checked').value;
  let roomId = roomIdInput.value.trim() || 'r58studio';
  
  // Validate and sanitize room ID
  const roomValidation = validateRoomId(roomId);
  if (!roomValidation.valid) {
    alert(`Invalid Room ID: ${roomValidation.error}`);
    return;
  }
  roomId = sanitizeInput(roomId);
  
  let host = '';
  
  if (connectionType === 'local') {
    if (manualIpInput.value.trim()) {
      host = manualIpInput.value.trim();
      
      // Validate IP address
      const ipValidation = validateIPAddress(host);
      if (!ipValidation.valid) {
        alert(`Invalid IP Address: ${ipValidation.error}`);
        return;
      }
      
      host = sanitizeInput(host);
    } else if (selectedDevice) {
      host = selectedDevice.host || selectedDevice.addresses[0];
    } else {
      alert('Please select a device or enter an IP address');
      return;
    }
  }

  const config = {
    connectionType,
    host,
    roomId,
    name: connectionType === 'local' ? `R58 @ ${host}` : 'Preke Cloud'
  };

  console.log('Connecting with config:', config);

  // Save connection if checkbox is checked
  if (saveConnectionCheckbox.checked && window.prekeApi) {
    window.prekeApi.saveConnection(config);
  }

  // Send connect message to main process
  if (window.prekeApi) {
    window.prekeApi.connect(config);
  } else {
    console.error('prekeApi not available');
    alert('Error: App API not available. Please restart the app.');
  }
}
```

---

### Improvement #2: Better Error Messages

**File**: `/tmp/preke-studio-extracted/launcher.js`  
**Add after setupIpcListeners (line 56)**:

```javascript
// Add error message handler
if (window.prekeApi) {
  window.prekeApi.onFeatureUnavailable((data) => {
    showWarningBanner(data.feature, data.reason);
  });
  
  window.prekeApi.onDiscoveryError((error) => {
    deviceList.innerHTML = `
      <div class="device-item error">
        <span class="error-icon">⚠️</span>
        <div>
          <div class="error-title">${error.message}</div>
          <div class="error-detail">${error.reason}</div>
          <div class="error-solution">💡 ${error.solution}</div>
        </div>
      </div>
    `;
  });
}

function showWarningBanner(feature, reason) {
  const banner = document.createElement('div');
  banner.className = 'warning-banner';
  banner.innerHTML = `
    <span class="warning-icon">⚠️</span>
    <span>${feature} unavailable: ${reason}</span>
    <button onclick="this.parentElement.remove()">×</button>
  `;
  document.body.insertBefore(banner, document.body.firstChild);
}
```

**Add to launcher.css**:
```css
.warning-banner {
  background: #ff9800;
  color: white;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.warning-banner button {
  margin-left: auto;
  background: none;
  border: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
  padding: 0 8px;
}

.device-item.error {
  background: #fff3cd;
  border-left: 4px solid #ff9800;
  padding: 16px;
}

.error-icon {
  font-size: 24px;
  margin-right: 12px;
}

.error-title {
  font-weight: 600;
  color: #856404;
  margin-bottom: 4px;
}

.error-detail {
  font-size: 13px;
  color: #856404;
  margin-bottom: 8px;
}

.error-solution {
  font-size: 12px;
  color: #856404;
  font-style: italic;
}
```

---

### Improvement #3: Increase Timeout & Add Retry

**File**: `/tmp/preke-studio-extracted/preke-studio.js`  
**Lines**: 84-112

**Replace**:
```javascript
// Set a timeout to hide loading overlay if page doesn't load
const loadTimeout = setTimeout(() => {
  console.log('Mixer view load timeout - showing retry option');
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('tab-timeout', {
      tab: 'mixer',
      view: view,
      timeout: 30000
    });
  }
}, 30000); // Increased to 30 seconds

tabViews['mixer'].webContents.loadURL(url);

let retryCount = 0;
const maxRetries = 2;

const handleLoadError = (event, errorCode, errorDescription) => {
  clearTimeout(loadTimeout);
  console.error(`Mixer view failed to load: ${errorDescription} (code: ${errorCode})`);
  
  if (retryCount < maxRetries && errorCode !== -3) { // -3 is user abort
    retryCount++;
    console.log(`Retrying... (attempt ${retryCount}/${maxRetries})`);
    setTimeout(() => {
      tabViews['mixer'].webContents.loadURL(url);
    }, 2000);
  } else {
    if (mainWindow && mainWindow.webContents) {
      mainWindow.webContents.send('tab-error', {
        message: errorDescription,
        code: errorCode,
        canRetry: true
      });
    }
  }
};

tabViews['mixer'].webContents.once('did-finish-load', () => {
  clearTimeout(loadTimeout);
  retryCount = 0; // Reset retry count on success
  console.log('Mixer view loaded successfully');
  injectMixerStyles(tabViews['mixer']);
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('tab-loaded');
  }
});

tabViews['mixer'].webContents.on('did-fail-load', handleLoadError);
```

---

### Improvement #4: Add Retry Button in UI

**File**: `/tmp/preke-studio-extracted/app.js`  
**Lines**: 43-51

**Replace**:
```javascript
window.prekeApi.onTabError((error) => {
  const errorData = typeof error === 'string' ? { message: error } : error;
  
  loadingOverlay.innerHTML = `
    <div style="text-align: center; color: var(--text-secondary); max-width: 400px; margin: 0 auto;">
      <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
      <p style="margin-bottom: 8px; font-weight: 600;">Failed to load</p>
      <p style="font-size: 14px; margin-bottom: 4px;">${errorData.message}</p>
      ${errorData.code ? `<p style="font-size: 12px; color: var(--text-tertiary);">Error code: ${errorData.code}</p>` : ''}
      <div style="margin-top: 24px; display: flex; gap: 12px; justify-content: center;">
        ${errorData.canRetry ? '<button onclick="retryCurrentTab()" class="btn-primary">Retry</button>' : ''}
        <button onclick="window.prekeApi.openSettings()" class="btn-secondary">Back to Launcher</button>
      </div>
    </div>
  `;
});

// Add retry function
window.retryCurrentTab = function() {
  loadingOverlay.innerHTML = `
    <div class="loading-spinner"></div>
    <p>Retrying...</p>
  `;
  switchTab(currentTab);
};
```

---

## Installation Instructions

### To Apply These Fixes:

1. **Extract the app source**:
```bash
npx asar extract "/Applications/Preke Studio.app/Contents/Resources/app.asar" ~/preke-studio-source
```

2. **Apply the fixes** to the files in `~/preke-studio-source/`

3. **Rebuild the ASAR**:
```bash
npx asar pack ~/preke-studio-source "/Applications/Preke Studio.app/Contents/Resources/app.asar"
```

4. **Test the app**:
```bash
open -a "/Applications/Preke Studio.app"
```

### Or Build from Source:

If you have the original source repository:

```bash
cd /path/to/preke-studio-app
# Apply fixes to source files
npm install
npm run build:darwin
```

---

## Testing Checklist

After applying fixes, test:

- [ ] App launches and window appears
- [ ] Launcher shows without errors
- [ ] Device discovery works (or shows helpful error)
- [ ] Manual IP entry validates correctly
- [ ] Room ID validates correctly
- [ ] Invalid inputs show clear error messages
- [ ] Connection to local R58 works
- [ ] Connection to cloud works
- [ ] All tabs load successfully
- [ ] Mixer view toggle works
- [ ] Retry button works on errors
- [ ] Saved connections work (or shows warning)
- [ ] Error messages are user-friendly

---

## Version History

**v1.0.0** (Current)
- Initial release
- Known bugs present

**v1.0.1** (Proposed)
- Fix: Window creation reliability
- Fix: Consistent HTTPS protocol
- Fix: Error handling for missing dependencies
- Improvement: Input validation
- Improvement: Better error messages
- Improvement: Increased timeouts and retry logic

---

**Created**: 2025-12-19  
**Status**: Ready for Implementation
