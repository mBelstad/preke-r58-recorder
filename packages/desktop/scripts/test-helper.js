#!/usr/bin/env node
/**
 * Preke Studio Test Helper
 * 
 * Provides easy testing, debugging, and log access for Cursor vibe-coding.
 * 
 * Commands:
 *   launch     - Launch app with debugging
 *   stop       - Stop the app
 *   restart    - Stop and relaunch the app
 *   status     - Check app status
 *   logs       - Show recent logs (add -f to follow)
 *   logs:clear - Clear log file
 *   cdp        - Show CDP info for browser tools
 *   screenshot - Take a screenshot of the app
 *   build      - Rebuild main process and restart
 *   devtools   - Open DevTools in browser
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
const SCREENSHOT_DIR = path.join(DESKTOP_DIR, 'screenshots');

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
async function launchApp(quiet = false) {
  if (!quiet) logHeader('Launching ' + APP_NAME);
  
  if (await isAppRunning()) {
    log('⚠️  App is already running. Use "restart" to restart.', 'yellow');
    const cdpInfo = await getCDPInfo();
    if (cdpInfo) {
      log(`\n✅ CDP available at http://localhost:${CDP_PORT}`, 'green');
    }
    return true;
  }
  
  if (!quiet) log('Starting Electron with remote debugging...', 'cyan');
  
  const electronPath = path.join(DESKTOP_DIR, 'node_modules/.bin/electron');
  const child = spawn(electronPath, ['.', `--remote-debugging-port=${CDP_PORT}`], {
    cwd: DESKTOP_DIR,
    detached: true,
    stdio: 'ignore',
  });
  
  child.unref();
  
  // Poll for app to start
  if (!quiet) log('Waiting for app...', 'gray');
  
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
  
  if (!quiet) {
    console.log('');
    if (running && cdpInfo) {
      log('✅ App launched successfully!', 'green');
      log(`\n📡 CDP: http://localhost:${CDP_PORT}`, 'cyan');
      log(`📄 Logs: ${LOG_FILE}`, 'cyan');
      
      log('\n📱 Pages:', 'bright');
      cdpInfo.forEach((page, i) => {
        log(`   ${i + 1}. ${page.title || 'Untitled'}`, 'reset');
      });
    } else if (running) {
      log('⚠️  App running but CDP not available', 'yellow');
    } else {
      log('❌ App failed to start', 'red');
      return false;
    }
  }
  
  return running && cdpInfo;
}

// Stop the app
async function stopApp(quiet = false) {
  if (!quiet) logHeader('Stopping ' + APP_NAME);
  
  if (!(await isAppRunning())) {
    if (!quiet) log('⚠️  App is not running', 'yellow');
    return true;
  }
  
  try {
    execSync('pkill -x Electron', { stdio: 'pipe' });
    await new Promise(r => setTimeout(r, 1000));
    
    if (await isAppRunning()) {
      execSync('pkill -9 -x Electron', { stdio: 'pipe' });
      await new Promise(r => setTimeout(r, 500));
    }
    
    if (!quiet) log('✅ App stopped', 'green');
    return true;
  } catch (e) {
    if (!quiet) log('❌ Error stopping app: ' + e.message, 'red');
    return false;
  }
}

// Restart the app
async function restartApp() {
  logHeader('Restarting ' + APP_NAME);
  
  await stopApp(true);
  await new Promise(r => setTimeout(r, 500));
  
  const success = await launchApp(true);
  
  if (success) {
    log('✅ App restarted successfully!', 'green');
    log(`\n📡 CDP: http://localhost:${CDP_PORT}`, 'cyan');
  } else {
    log('❌ Failed to restart app', 'red');
  }
}

// Show logs
async function showLogs(follow = false) {
  logHeader('Preke Studio Logs');
  
  if (!fs.existsSync(LOG_FILE)) {
    log('❌ Log file not found: ' + LOG_FILE, 'red');
    return;
  }
  
  log(`📄 ${LOG_FILE}`, 'cyan');
  console.log('');
  
  if (follow) {
    log('Following logs (Ctrl+C to stop)...', 'gray');
    console.log('');
    
    const tail = spawn('tail', ['-f', '-n', '50', LOG_FILE], { stdio: 'inherit' });
    tail.on('close', () => process.exit(0));
  } else {
    try {
      const content = fs.readFileSync(LOG_FILE, 'utf8');
      const lines = content.trim().split('\n');
      const lastLines = lines.slice(-50);
      
      lastLines.forEach(line => {
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

// Clear logs
async function clearLogs() {
  logHeader('Clearing Logs');
  
  if (!fs.existsSync(LOG_FILE)) {
    log('⚠️  Log file does not exist', 'yellow');
    return;
  }
  
  try {
    fs.writeFileSync(LOG_FILE, '');
    log('✅ Log file cleared', 'green');
  } catch (e) {
    log('❌ Error clearing logs: ' + e.message, 'red');
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
    cdpInfo.forEach((page) => {
      log(`   ${page.title || 'Untitled'}`, 'reset');
    });
  }
  
  if (fs.existsSync(LOG_FILE)) {
    const stats = fs.statSync(LOG_FILE);
    const mtime = stats.mtime.toLocaleString();
    const size = (stats.size / 1024).toFixed(1) + ' KB';
    log(`\n📄 Log: ${size}, modified ${mtime}`, 'gray');
  }
}

// Show CDP info
async function showCDPInfo() {
  logHeader('CDP Info');
  
  const cdpInfo = await getCDPInfo();
  
  if (!cdpInfo) {
    log('❌ CDP not available. Launch the app first.', 'red');
    log('\n   npm run test:launch', 'gray');
    return;
  }
  
  log(`Endpoint: http://localhost:${CDP_PORT}`, 'cyan');
  log(`JSON API: http://localhost:${CDP_PORT}/json`, 'cyan');
  
  log('\n📱 Pages:', 'bright');
  cdpInfo.forEach((page) => {
    console.log('');
    log(`  ${page.title || 'Untitled'}`, 'bright');
    log(`  Type: ${page.type}`, 'gray');
    log(`  WS: ${page.webSocketDebuggerUrl}`, 'cyan');
  });
  
  log('\n🔧 Browser tools usage:', 'bright');
  log('   Navigate to http://localhost:9222 to see pages', 'gray');
  log('   Use browser_snapshot to inspect the app', 'gray');
}

// Take screenshot
async function takeScreenshot() {
  logHeader('Screenshot');
  
  if (!(await isAppRunning())) {
    log('❌ App is not running', 'red');
    return;
  }
  
  // Create screenshots directory if needed
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }
  
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filename = `screenshot-${timestamp}.png`;
  const filepath = path.join(SCREENSHOT_DIR, filename);
  
  try {
    // Use screencapture on macOS
    execSync(`screencapture -x "${filepath}"`, { stdio: 'pipe' });
    log(`✅ Screenshot saved: ${filepath}`, 'green');
    log(`\n📁 Screenshots directory: ${SCREENSHOT_DIR}`, 'cyan');
  } catch (e) {
    log('❌ Failed to take screenshot: ' + e.message, 'red');
  }
}

// Build and restart
async function buildAndRestart() {
  logHeader('Build & Restart');
  
  log('Building main process...', 'cyan');
  
  try {
    execSync('npm run build:main', { cwd: DESKTOP_DIR, stdio: 'inherit' });
    log('\n✅ Build complete', 'green');
  } catch (e) {
    log('\n❌ Build failed', 'red');
    return;
  }
  
  await restartApp();
}

// Open DevTools in browser
async function openDevTools() {
  logHeader('Open DevTools');
  
  const cdpInfo = await getCDPInfo();
  
  if (!cdpInfo) {
    log('❌ App not running. Launch first.', 'red');
    return;
  }
  
  // Find main page (not DevTools)
  const mainPage = cdpInfo.find(p => !p.url.includes('devtools://'));
  
  if (mainPage && mainPage.devtoolsFrontendUrl) {
    log('Opening DevTools in browser...', 'cyan');
    try {
      execSync(`open "${mainPage.devtoolsFrontendUrl}"`, { stdio: 'pipe' });
      log('✅ DevTools opened in browser', 'green');
    } catch (e) {
      log('❌ Failed to open browser: ' + e.message, 'red');
      log(`\nManual URL: ${mainPage.devtoolsFrontendUrl}`, 'gray');
    }
  } else {
    log('⚠️  Could not find DevTools URL', 'yellow');
    log(`\nTry: http://localhost:${CDP_PORT}`, 'gray');
  }
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
      
    case 'stop':
    case 'kill':
      await stopApp();
      break;
      
    case 'restart':
      await restartApp();
      break;
      
    case 'status':
      await showStatus();
      break;
      
    case 'logs':
    case 'log':
      await showLogs(args.includes('-f') || args.includes('--follow'));
      break;
      
    case 'logs:clear':
    case 'clear':
      await clearLogs();
      break;
      
    case 'cdp':
    case 'debug':
      await showCDPInfo();
      break;
      
    case 'screenshot':
    case 'snap':
      await takeScreenshot();
      break;
      
    case 'build':
      await buildAndRestart();
      break;
      
    case 'devtools':
    case 'open':
      await openDevTools();
      break;
      
    case 'help':
    case '--help':
    case '-h':
      console.log(`
${colors.bright}Preke Studio Test Helper${colors.reset}

${colors.bright}App Control:${colors.reset}
  launch      Start the app with CDP debugging
  stop        Stop the app
  restart     Stop and relaunch
  build       Rebuild main process and restart

${colors.bright}Debugging:${colors.reset}
  status      Show app and CDP status
  logs        Show recent logs (add -f to follow)
  logs:clear  Clear the log file
  cdp         Show CDP endpoints
  devtools    Open DevTools in browser
  screenshot  Capture screen to screenshots/

${colors.bright}Examples:${colors.reset}
  npm run test:launch
  npm run test:logs -- -f
  npm run test:build
`);
      break;
      
    default:
      log(`Unknown command: ${command}`, 'red');
      log('Use "help" to see available commands', 'gray');
      process.exit(1);
  }
}

main().catch(e => {
  log('Error: ' + e.message, 'red');
  process.exit(1);
});
