#!/usr/bin/env node
/**
 * Preke Studio Test Helper
 * 
 * Provides easy testing, debugging, and log access for Cursor vibe-coding.
 * 
 * Usage:
 *   node scripts/test-helper.js launch    - Launch app with debugging
 *   node scripts/test-helper.js logs      - Show recent logs
 *   node scripts/test-helper.js logs -f   - Follow logs in real-time
 *   node scripts/test-helper.js status    - Check app status
 *   node scripts/test-helper.js stop      - Stop the app
 *   node scripts/test-helper.js cdp       - Show CDP info for browser tools
 */

const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const http = require('http');

const APP_NAME = 'Preke Studio';
const CDP_PORT = 9222;
const LOG_FILE = path.join(os.homedir(), 'Library/Logs/preke-studio/main.log');
const DESKTOP_DIR = path.dirname(__dirname);

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
};

function log(msg, color = 'reset') {
  console.log(`${colors[color]}${msg}${colors.reset}`);
}

function logHeader(msg) {
  log(`\n${colors.bright}${colors.blue}═══ ${msg} ═══${colors.reset}\n`);
}

// Check if app is running
async function isAppRunning() {
  try {
    const result = execSync('pgrep -x Electron', { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
    return result.trim().length > 0;
  } catch {
    return false;
  }
}

// Check CDP availability
async function getCDPInfo() {
  return new Promise((resolve) => {
    const req = http.get(`http://localhost:${CDP_PORT}/json`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          resolve(null);
        }
      });
    });
    req.on('error', () => resolve(null));
    req.setTimeout(2000, () => {
      req.destroy();
      resolve(null);
    });
  });
}

// Launch the app
async function launchApp() {
  logHeader('Launching ' + APP_NAME);
  
  if (await isAppRunning()) {
    log('⚠️  App is already running. Use "stop" first to restart.', 'yellow');
    const cdpInfo = await getCDPInfo();
    if (cdpInfo) {
      log(`\n✅ CDP available at http://localhost:${CDP_PORT}`, 'green');
      log('\n📱 Pages:', 'bright');
      cdpInfo.forEach((page) => {
        log(`   ${page.title || 'Untitled'}`, 'reset');
      });
    }
    return;
  }
  
  log('Starting Electron with remote debugging...', 'cyan');
  
  const electronPath = path.join(DESKTOP_DIR, 'node_modules/.bin/electron');
  const child = spawn(electronPath, ['.', `--remote-debugging-port=${CDP_PORT}`], {
    cwd: DESKTOP_DIR,
    detached: true,
    stdio: 'ignore', // Don't capture output to allow proper detachment
  });
  
  child.unref();
  
  // Poll for app to start
  log('Waiting for app...', 'gray');
  
  let attempts = 0;
  const maxAttempts = 20;
  let running = false;
  let cdpInfo = null;
  
  while (attempts < maxAttempts) {
    await new Promise(r => setTimeout(r, 250));
    running = await isAppRunning();
    if (running) {
      cdpInfo = await getCDPInfo();
      if (cdpInfo) break;
    }
    attempts++;
  }
  
  console.log('');
  if (running && cdpInfo) {
    log('✅ App launched successfully!', 'green');
    log(`\n📡 CDP Endpoint: http://localhost:${CDP_PORT}`, 'cyan');
    log(`📄 Log file: ${LOG_FILE}`, 'cyan');
    
    // Show pages
    log('\n📱 Available pages:', 'bright');
    cdpInfo.forEach((page, i) => {
      log(`   ${i + 1}. ${page.title || 'Untitled'}`, 'reset');
      log(`      ${page.url}`, 'gray');
    });
    
    log('\n🔧 Quick commands:', 'bright');
    log('   View logs:    npm run test:logs', 'gray');
    log('   Follow logs:  npm run test:logs:follow', 'gray');
    log('   Stop app:     npm run test:stop', 'gray');
    log('   CDP info:     npm run test:cdp', 'gray');
  } else if (running) {
    log('⚠️  App running but CDP not available yet', 'yellow');
    log('   Try: npm run test:status', 'gray');
  } else {
    log('❌ App failed to start', 'red');
    log('   Check logs: npm run test:logs', 'gray');
  }
}

// Show logs
async function showLogs(follow = false) {
  logHeader('Preke Studio Logs');
  
  if (!fs.existsSync(LOG_FILE)) {
    log('❌ Log file not found: ' + LOG_FILE, 'red');
    return;
  }
  
  log(`📄 Log file: ${LOG_FILE}`, 'cyan');
  console.log('');
  
  if (follow) {
    log('Following logs (Ctrl+C to stop)...', 'gray');
    console.log('');
    
    const tail = spawn('tail', ['-f', '-n', '50', LOG_FILE], { stdio: 'inherit' });
    tail.on('close', () => process.exit(0));
  } else {
    // Show last 50 lines
    try {
      const content = fs.readFileSync(LOG_FILE, 'utf8');
      const lines = content.trim().split('\n');
      const lastLines = lines.slice(-50);
      
      lastLines.forEach(line => {
        // Colorize log levels
        if (line.includes('[error]')) {
          log(line, 'red');
        } else if (line.includes('[warn]')) {
          log(line, 'yellow');
        } else if (line.includes('[info]')) {
          log(line, 'reset');
        } else {
          log(line, 'gray');
        }
      });
      
      console.log('');
      log(`Showing last ${lastLines.length} lines. Use "logs -f" to follow.`, 'gray');
    } catch (e) {
      log('Error reading logs: ' + e.message, 'red');
    }
  }
}

// Show status
async function showStatus() {
  logHeader('App Status');
  
  const running = await isAppRunning();
  const cdpInfo = await getCDPInfo();
  
  log(`App Running:  ${running ? '✅ Yes' : '❌ No'}`, running ? 'green' : 'red');
  log(`CDP Active:   ${cdpInfo ? '✅ Yes' : '❌ No'}`, cdpInfo ? 'green' : 'red');
  log(`Log File:     ${fs.existsSync(LOG_FILE) ? '✅ Exists' : '⚠️ Not found'}`, fs.existsSync(LOG_FILE) ? 'green' : 'yellow');
  
  if (cdpInfo) {
    log(`\n📡 CDP: http://localhost:${CDP_PORT}`, 'cyan');
    log(`\n📱 Pages (${cdpInfo.length}):`, 'bright');
    cdpInfo.forEach((page, i) => {
      log(`   ${page.title || 'Untitled'}`, 'reset');
    });
  }
  
  if (fs.existsSync(LOG_FILE)) {
    const stats = fs.statSync(LOG_FILE);
    const mtime = stats.mtime.toLocaleString();
    log(`\n📄 Log last modified: ${mtime}`, 'gray');
  }
}

// Stop the app
async function stopApp() {
  logHeader('Stopping ' + APP_NAME);
  
  if (!(await isAppRunning())) {
    log('⚠️  App is not running', 'yellow');
    return;
  }
  
  try {
    execSync('pkill -x Electron', { stdio: 'inherit' });
    await new Promise(r => setTimeout(r, 1000));
    
    if (await isAppRunning()) {
      log('⚠️  App still running, force killing...', 'yellow');
      execSync('pkill -9 -x Electron', { stdio: 'inherit' });
    }
    
    log('✅ App stopped', 'green');
  } catch (e) {
    log('❌ Error stopping app: ' + e.message, 'red');
  }
}

// Show CDP info for browser tools
async function showCDPInfo() {
  logHeader('CDP Info for Browser Tools');
  
  const cdpInfo = await getCDPInfo();
  
  if (!cdpInfo) {
    log('❌ CDP not available. Launch the app first.', 'red');
    log('\n   node scripts/test-helper.js launch', 'gray');
    return;
  }
  
  log(`CDP Endpoint: http://localhost:${CDP_PORT}`, 'cyan');
  log(`WebSocket: ws://localhost:${CDP_PORT}/devtools/browser/...`, 'cyan');
  
  log('\n📱 Available pages:', 'bright');
  cdpInfo.forEach((page) => {
    console.log('');
    log(`Title: ${page.title}`, 'bright');
    log(`Type: ${page.type}`, 'gray');
    log(`URL: ${page.url}`, 'gray');
    log(`WS: ${page.webSocketDebuggerUrl}`, 'cyan');
  });
  
  log('\n🔧 Use in Cursor browser tools:', 'bright');
  log('   1. Navigate to http://localhost:9222', 'gray');
  log('   2. Use browser_snapshot to inspect the app', 'gray');
  log('   3. Use browser_click/type/etc to interact', 'gray');
}

// Main
async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'status';
  
  switch (command) {
    case 'launch':
    case 'start':
      await launchApp();
      break;
    case 'logs':
    case 'log':
      await showLogs(args.includes('-f') || args.includes('--follow'));
      break;
    case 'status':
      await showStatus();
      break;
    case 'stop':
    case 'kill':
      await stopApp();
      break;
    case 'cdp':
    case 'debug':
      await showCDPInfo();
      break;
    case 'help':
    case '--help':
    case '-h':
      console.log(`
${colors.bright}Preke Studio Test Helper${colors.reset}

Commands:
  launch    Launch the app with remote debugging enabled
  stop      Stop the app
  status    Check if app is running and CDP is available
  logs      Show recent logs (add -f to follow)
  cdp       Show CDP endpoints for browser tools integration
  help      Show this help message

Examples:
  node scripts/test-helper.js launch
  node scripts/test-helper.js logs -f
  node scripts/test-helper.js cdp
`);
      break;
    default:
      log(`Unknown command: ${command}`, 'red');
      log('Use "help" to see available commands', 'gray');
  }
}

main().catch(e => {
  log('Error: ' + e.message, 'red');
  process.exit(1);
});

