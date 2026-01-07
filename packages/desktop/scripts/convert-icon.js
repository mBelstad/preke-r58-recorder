#!/usr/bin/env node
/**
 * Icon Conversion Script
 * Converts icon.png to Windows .ico and macOS .icns formats
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const RESOURCES_DIR = path.join(__dirname, '..', 'resources');
const ICON_PNG = path.join(RESOURCES_DIR, 'icon.png');
const ICON_ICO = path.join(RESOURCES_DIR, 'icon.ico');
const ICON_ICNS = path.join(RESOURCES_DIR, 'icon.icns');

function checkCommand(command) {
  try {
    execSync(`which ${command}`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function convertToIco() {
  if (fs.existsSync(ICON_ICO)) {
    console.log('✓ icon.ico already exists');
    return;
  }

  if (!fs.existsSync(ICON_PNG)) {
    console.error('✗ icon.png not found at', ICON_PNG);
    process.exit(1);
  }

  console.log('Converting icon.png to icon.ico...');

  // Try ImageMagick first (most common)
  if (checkCommand('convert') || checkCommand('magick')) {
    try {
      const cmd = checkCommand('magick') ? 'magick' : 'convert';
      execSync(
        `${cmd} "${ICON_PNG}" -define icon:auto-resize=256,128,64,48,32,16 "${ICON_ICO}"`,
        { stdio: 'inherit' }
      );
      console.log('✓ Created icon.ico using ImageMagick');
      return;
    } catch (error) {
      console.warn('ImageMagick conversion failed, trying alternatives...');
    }
  }

  // Try sips on macOS
  if (process.platform === 'darwin' && checkCommand('sips')) {
    try {
      // sips can't directly create .ico, but we can create a temp PNG and use iconutil
      console.log('Note: sips cannot create .ico directly. Please install ImageMagick or use online converter.');
      console.log('Alternatively, electron-builder will handle icon conversion automatically.');
      return;
    } catch (error) {
      console.warn('sips conversion failed');
    }
  }

  // Fallback: provide instructions
  console.log('\n⚠ Could not automatically convert icon.png to icon.ico');
  console.log('Options:');
  console.log('1. Install ImageMagick: brew install imagemagick (macOS) or choco install imagemagick (Windows)');
  console.log('2. Use online converter: https://convertio.co/png-ico/');
  console.log('3. electron-builder will attempt to convert automatically during build');
  console.log('\nThe build will continue, but Windows installer may use default icon.');
}

function convertToIcns() {
  if (fs.existsSync(ICON_ICNS)) {
    console.log('✓ icon.icns already exists');
    return;
  }

  if (!fs.existsSync(ICON_PNG)) {
    console.error('✗ icon.png not found at', ICON_PNG);
    process.exit(1);
  }

  if (process.platform !== 'darwin') {
    console.log('⚠ icon.icns conversion requires macOS (iconutil)');
    console.log('Skipping .icns generation. electron-builder will handle this on macOS.');
    return;
  }

  if (!checkCommand('iconutil')) {
    console.error('✗ iconutil not found (should be available on macOS)');
    return;
  }

  console.log('Converting icon.png to icon.icns...');

  const ICONSET_DIR = path.join(RESOURCES_DIR, 'icon.iconset');
  const sizes = [
    { size: 16, scale: 1 },
    { size: 16, scale: 2 },
    { size: 32, scale: 1 },
    { size: 32, scale: 2 },
    { size: 128, scale: 1 },
    { size: 128, scale: 2 },
    { size: 256, scale: 1 },
    { size: 256, scale: 2 },
    { size: 512, scale: 1 },
    { size: 512, scale: 2 },
  ];

  // Clean up old iconset if exists
  if (fs.existsSync(ICONSET_DIR)) {
    fs.rmSync(ICONSET_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(ICONSET_DIR, { recursive: true });

  try {
    // Generate all required sizes
    for (const { size, scale } of sizes) {
      const actualSize = size * scale;
      const filename = scale === 2 ? `icon_${size}x${size}@2x.png` : `icon_${size}x${size}.png`;
      const outputPath = path.join(ICONSET_DIR, filename);

      execSync(
        `sips -z ${actualSize} ${actualSize} "${ICON_PNG}" --out "${outputPath}"`,
        { stdio: 'ignore' }
      );
    }

    // Convert iconset to icns
    execSync(`iconutil -c icns "${ICONSET_DIR}" -o "${ICON_ICNS}"`, {
      stdio: 'inherit',
    });

    // Clean up iconset
    fs.rmSync(ICONSET_DIR, { recursive: true, force: true });

    console.log('✓ Created icon.icns');
  } catch (error) {
    console.error('✗ Failed to create icon.icns:', error.message);
    // Clean up on error
    if (fs.existsSync(ICONSET_DIR)) {
      fs.rmSync(ICONSET_DIR, { recursive: true, force: true });
    }
  }
}

// Main execution
console.log('Icon Conversion Script\n');
console.log('Checking icon files...\n');

convertToIco();
console.log('');
convertToIcns();

console.log('\n✓ Icon conversion complete!');

