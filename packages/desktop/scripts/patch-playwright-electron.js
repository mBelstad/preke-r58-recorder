#!/usr/bin/env node
/**
 * Patches playwright-core for Electron 33+ compatibility.
 * 
 * Note: The circuit-electron MCP server has compatibility issues with 
 * Playwright's Electron loader on Electron 33+. We use the test-helper.js
 * script for testing instead, which launches the app manually.
 * 
 * This patch is kept for potential future circuit-electron compatibility.
 */

const fs = require('fs');
const path = require('path');

const electronJsPath = path.join(
  __dirname, 
  '../node_modules/playwright-core/lib/server/electron/electron.js'
);

console.log('🔧 Checking Playwright patches for Electron 33+ compatibility...\n');

if (!fs.existsSync(electronJsPath)) {
  console.log('⚠️  playwright-core not found, skipping patches');
  console.log('   This is normal if you\'re not using circuit-electron.');
  process.exit(0);
}

let content = fs.readFileSync(electronJsPath, 'utf8');
let patched = false;

// Patch: Fix argument order (flags after app path for Electron 33+)
// Original: ["--inspect=0", "--remote-debugging-port=0", ...options.args || []]
// Patched:  [...options.args || [], "--remote-debugging-port=9222"]
const originalPattern = 'let electronArguments = ["--inspect=0", "--remote-debugging-port=0", ...options.args || []];';
const patchedPattern = 'let electronArguments = [...options.args || [], "--remote-debugging-port=9222"];';

if (content.includes(patchedPattern)) {
  console.log('✓  Already patched: electron.js (argument order)');
} else if (content.includes(originalPattern)) {
  content = content.replace(originalPattern, patchedPattern);
  fs.writeFileSync(electronJsPath, content);
  console.log('✅ Patched: electron.js (fixed argument order for Electron 33+)');
  patched = true;
} else {
  console.log('⚠️  Could not find pattern to patch in electron.js');
  console.log('   This may indicate a different playwright-core version.');
}

if (patched) {
  console.log('\n✨ Patches applied.');
} else {
  console.log('\n✨ No patches needed.');
}

console.log(`
📝 Note: For testing Preke Studio in Cursor, use the test helper:

   npm run test:launch     # Start app with debugging
   npm run test:logs       # View logs
   npm run test:cdp        # Show CDP info for browser tools
   npm run test:stop       # Stop the app
`);
