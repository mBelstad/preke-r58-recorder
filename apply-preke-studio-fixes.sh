#!/bin/bash
# Apply bug fixes to Preke Studio app
# Run this script to fix critical bugs in the Preke Studio Mac app

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================"
echo "Preke Studio Bug Fix Installer"
echo "======================================"
echo ""

# Check if app exists
APP_PATH="/Applications/Preke Studio.app"
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}✗${NC} Preke Studio app not found at $APP_PATH"
    exit 1
fi
echo -e "${GREEN}✓${NC} Found Preke Studio app"

# Check if npx is available
if ! command -v npx &> /dev/null; then
    echo -e "${RED}✗${NC} npx not found. Please install Node.js first."
    exit 1
fi
echo -e "${GREEN}✓${NC} npx available"

# Create backup
BACKUP_PATH="$HOME/preke-studio-backup-$(date +%Y%m%d-%H%M%S).asar"
echo ""
echo "Creating backup..."
cp "$APP_PATH/Contents/Resources/app.asar" "$BACKUP_PATH"
echo -e "${GREEN}✓${NC} Backup created: $BACKUP_PATH"

# Extract app
WORK_DIR="$HOME/preke-studio-fixed"
echo ""
echo "Extracting app source..."
rm -rf "$WORK_DIR"
npx asar extract "$APP_PATH/Contents/Resources/app.asar" "$WORK_DIR"
echo -e "${GREEN}✓${NC} Source extracted to $WORK_DIR"

# Apply fixes
echo ""
echo "Applying bug fixes..."

# Fix #1: Better error handling for dependencies
echo "  • Fix #1: Error handling for dependencies..."
cat > "$WORK_DIR/preke-studio-fixed.js" << 'EOF'
// Preke Studio - Bug fixes applied
const { ipcMain, BrowserView, BrowserWindow } = require('electron');
const path = require('path');
const fs = require('fs');

// Try to load optional dependencies with better error handling
let Store, Bonjour;
let storeAvailable = false;
let bonjourAvailable = false;

try {
  Store = require('electron-store');
  storeAvailable = true;
  console.log('✓ electron-store loaded');
} catch (e) {
  console.warn('⚠️  electron-store not available - saved connections disabled');
}

try {
  const BonjourService = require('bonjour-service');
  Bonjour = new BonjourService.Bonjour();
  bonjourAvailable = true;
  console.log('✓ bonjour-service loaded');
} catch (e) {
  console.warn('⚠️  bonjour-service not available - device discovery disabled');
}

// State
let connectionConfig = null;
let tabViews = {};
let currentTab = null;
let currentMixerView = 'director';
let mainWindow = null;

// Profile storage with fallback
let store = null;
let inMemoryProfiles = [];

if (Store && storeAvailable) {
  try {
    store = new Store({
      name: 'preke-studio-profiles',
      defaults: { profiles: [] }
    });
    console.log('✓ Profile storage initialized');
  } catch (e) {
    console.error('Failed to initialize electron-store:', e);
    storeAvailable = false;
  }
}

function initPrekeStudio(window) {
  if (!window) {
    console.error('initPrekeStudio called with null window!');
    return false;
  }
  mainWindow = window;
  setupIpcHandlers();
  return true;
}

function setupIpcHandlers() {
  // Device discovery
  ipcMain.on('discover-devices', (event) => {
    discoverDevices(event);
  });

  // Connection handling
  ipcMain.on('connect', (event, config) => {
    connectionConfig = config;
    console.log('Connecting with config:', config);
    if (mainWindow) {
      mainWindow.loadFile(path.join(__dirname, 'app.html'));
    }
  });

  // Get connection config
  ipcMain.on('get-connection-config', (event) => {
    event.sender.send('connection-config', connectionConfig);
  });

  // Tab switching
  ipcMain.on('switch-tab', (event, data) => {
    const tabName = typeof data === 'string' ? data : data.tab;
    if (data.view) {
      currentMixerView = data.view;
    }
    switchTab(tabName, event.sender);
  });

  // Mixer view switching
  ipcMain.on('switch-mixer-view', (event, view) => {
    currentMixerView = view;
    if (tabViews['mixer'] && mainWindow) {
      const url = getMixerUrl(view);
      console.log(`Switching mixer to ${view} view: ${url}`);
      
      const loadTimeout = setTimeout(() => {
        console.log('Mixer view load timeout');
        if (mainWindow && mainWindow.webContents) {
          mainWindow.webContents.send('tab-loaded');
        }
      }, 30000); // Increased to 30 seconds
      
      tabViews['mixer'].webContents.loadURL(url);
      
      tabViews['mixer'].webContents.once('did-finish-load', () => {
        clearTimeout(loadTimeout);
        console.log('Mixer view loaded successfully');
        injectMixerStyles(tabViews['mixer']);
        if (mainWindow && mainWindow.webContents) {
          mainWindow.webContents.send('tab-loaded');
        }
      });
      
      tabViews['mixer'].webContents.once('did-fail-load', (event, errorCode, errorDescription) => {
        clearTimeout(loadTimeout);
        console.error(`Mixer view failed to load: ${errorDescription}`);
        if (mainWindow && mainWindow.webContents) {
          mainWindow.webContents.send('tab-error', errorDescription);
        }
      });
    }
  });

  // Settings
  ipcMain.on('open-settings', () => {
    if (mainWindow) {
      Object.values(tabViews).forEach(view => {
        if (view && mainWindow.getBrowserViews().includes(view)) {
          mainWindow.removeBrowserView(view);
        }
      });
      tabViews = {};
      currentTab = null;
      mainWindow.loadFile(path.join(__dirname, 'launcher.html'));
    }
  });

  // Close app
  ipcMain.on('close-app', () => {
    if (mainWindow) {
      mainWindow.close();
    }
  });

  // Saved connections with fallback
  ipcMain.on('get-saved-connections', (event) => {
    if (store && storeAvailable) {
      const profiles = store.get('profiles', []);
      event.sender.send('saved-connections', profiles);
    } else {
      event.sender.send('saved-connections', inMemoryProfiles);
      event.sender.send('feature-unavailable', {
        feature: 'saved-connections',
        reason: 'electron-store not available'
      });
    }
  });

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
      console.log('⚠️  Connection saved to memory only');
    }
  });
}

function discoverDevices(event) {
  if (!Bonjour || !bonjourAvailable) {
    event.sender.send('discovery-error', {
      message: 'Device discovery unavailable',
      reason: 'bonjour-service not installed',
      solution: 'Enter IP address manually'
    });
    
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

function switchTab(tabName, sender) {
  if (!mainWindow || !connectionConfig) {
    console.error('switchTab called without mainWindow or connectionConfig!');
    return;
  }

  console.log(`Switching to tab: ${tabName}`);

  const bounds = mainWindow.getBounds();
  const toolbarHeight = 50;
  const subToolbarHeight = tabName === 'mixer' ? 36 : 0;
  const statusbarHeight = 30;
  const totalHeaderHeight = toolbarHeight + subToolbarHeight;
  const contentHeight = bounds.height - totalHeaderHeight - statusbarHeight;

  if (currentTab && tabViews[currentTab]) {
    tabViews[currentTab].setBounds({ x: 0, y: 0, width: 0, height: 0 });
  }

  if (!tabViews[tabName]) {
    const view = new BrowserView({
      webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false
      }
    });
    
    mainWindow.addBrowserView(view);
    tabViews[tabName] = view;

    const url = getTabUrl(tabName);
    console.log(`Loading tab ${tabName}: ${url}`);
    
    view.webContents.loadURL(url);
    
    view.webContents.on('did-finish-load', () => {
      if (tabName === 'mixer') {
        injectMixerStyles(view);
      }
      sender.send('tab-loaded');
    });

    view.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
      sender.send('tab-error', errorDescription);
    });
  } else {
    sender.send('tab-loaded');
  }

  tabViews[tabName].setBounds({
    x: 0,
    y: totalHeaderHeight,
    width: bounds.width,
    height: contentHeight
  });

  currentTab = tabName;

  mainWindow.removeAllListeners('resize');
  mainWindow.on('resize', () => {
    if (currentTab && tabViews[currentTab]) {
      const newBounds = mainWindow.getBounds();
      const currentSubToolbar = currentTab === 'mixer' ? 36 : 0;
      const newTotalHeader = toolbarHeight + currentSubToolbar;
      const newContentHeight = newBounds.height - newTotalHeader - statusbarHeight;
      tabViews[currentTab].setBounds({
        x: 0,
        y: newTotalHeader,
        width: newBounds.width,
        height: newContentHeight
      });
    }
  });
}

function getMixerUrl(view) {
  if (!connectionConfig) {
    console.error('getMixerUrl called without connectionConfig!');
    return 'about:blank';
  }
  
  const isLocal = connectionConfig.connectionType === 'local';
  const host = connectionConfig.host;
  const room = connectionConfig.roomId || 'r58studio';

  let url;
  if (view === 'director') {
    url = isLocal
      ? `https://${host}:8443/?director=${room}`
      : `https://vdo.itagenten.no/?director=${room}`;
  } else {
    url = isLocal
      ? `https://${host}:8443/mixer.html?room=${room}`
      : `https://vdo.itagenten.no/mixer.html?room=${room}`;
  }
  
  return url;
}

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
      // Use HTTPS for consistency
      url = isLocal 
        ? `https://${host}:5000/`
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
  
  return url;
}

function shouldShowLauncher(args) {
  if (!args.url) return true;
  if (args.url.includes('vdo.ninja/electron')) return true;
  return false;
}

function getLauncherPath() {
  return path.join(__dirname, 'launcher.html');
}

function injectMixerStyles(view) {
  try {
    const cssPath = path.join(__dirname, 'mixer-custom.css');
    const css = fs.readFileSync(cssPath, 'utf8');
    
    view.webContents.insertCSS(css)
      .then(() => {
        console.log('✓ Custom mixer styles injected');
      })
      .catch(err => {
        console.error('Failed to inject mixer styles:', err);
      });
  } catch (err) {
    console.error('Failed to read mixer-custom.css:', err);
  }
}

module.exports = {
  initPrekeStudio,
  shouldShowLauncher,
  getLauncherPath
};
EOF

# Backup original and replace
mv "$WORK_DIR/preke-studio.js" "$WORK_DIR/preke-studio.js.original"
mv "$WORK_DIR/preke-studio-fixed.js" "$WORK_DIR/preke-studio.js"
echo -e "${GREEN}  ✓${NC} Applied error handling fixes"

# Fix #2: Add input validation to launcher.js
echo "  • Fix #2: Adding input validation..."
cat >> "$WORK_DIR/launcher.js" << 'EOF'

// Input validation functions (added by bug fix)
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
  
  const roomPattern = /^[a-zA-Z0-9_-]+$/;
  if (!roomPattern.test(roomId)) {
    return { valid: false, error: 'Room ID can only contain letters, numbers, dash, and underscore' };
  }
  
  return { valid: true };
}

function sanitizeInput(input) {
  return input.trim().replace(/[<>'"]/g, '');
}

// Override original connect function with validation
const originalConnect = connect;
connect = function() {
  const connectionType = document.querySelector('input[name="connectionType"]:checked').value;
  let roomId = roomIdInput.value.trim() || 'r58studio';
  
  // Validate room ID
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

  console.log('Connecting with validated config:', config);

  if (saveConnectionCheckbox.checked && window.prekeApi) {
    window.prekeApi.saveConnection(config);
  }

  if (window.prekeApi) {
    window.prekeApi.connect(config);
  } else {
    console.error('prekeApi not available');
    alert('Error: App API not available. Please restart the app.');
  }
};
EOF
echo -e "${GREEN}  ✓${NC} Applied input validation"

# Rebuild ASAR
echo ""
echo "Rebuilding app..."
npx asar pack "$WORK_DIR" "$APP_PATH/Contents/Resources/app.asar"
echo -e "${GREEN}✓${NC} App rebuilt successfully"

# Create version file
echo "v1.0.1-bugfixes-$(date +%Y%m%d)" > "$WORK_DIR/VERSION"

echo ""
echo "======================================"
echo -e "${GREEN}Bug fixes applied successfully!${NC}"
echo "======================================"
echo ""
echo "Fixes applied:"
echo "  ✓ Better error handling for dependencies"
echo "  ✓ Input validation for IP and Room ID"
echo "  ✓ Increased timeout for tab loading (30s)"
echo "  ✓ HTTPS protocol for all connections"
echo "  ✓ In-memory fallback for saved connections"
echo ""
echo "Backup location: $BACKUP_PATH"
echo "Source location: $WORK_DIR"
echo ""
echo "To test the app:"
echo "  open -a '/Applications/Preke Studio.app'"
echo ""
echo "To restore from backup:"
echo "  cp '$BACKUP_PATH' '$APP_PATH/Contents/Resources/app.asar'"
echo ""
