// Quick script to check device store state
const Store = require('electron-store');
const path = require('path');
const os = require('os');

const storePath = path.join(
  os.homedir(),
  'Library',
  'Application Support',
  'preke-studio-devices',
  'config.json'
);

console.log('Device store path:', storePath);
console.log('');

try {
  const store = new Store({
    name: 'preke-studio-devices',
    defaults: {
      devices: [],
      activeDeviceId: null
    }
  });
  
  const devices = store.get('devices', []);
  const activeDeviceId = store.get('activeDeviceId', null);
  
  console.log('Active Device ID:', activeDeviceId);
  console.log('Number of devices:', devices.length);
  console.log('');
  
  if (devices.length > 0) {
    console.log('Devices:');
    devices.forEach((device, i) => {
      console.log(`  ${i + 1}. ${device.name} (${device.url})`);
      if (device.id === activeDeviceId) {
        console.log('     ^ ACTIVE');
      }
    });
  } else {
    console.log('No devices configured (clean state)');
  }
} catch (error) {
  console.error('Error reading store:', error.message);
}
