# R58 Testing Tools Guide

> **Version:** 1.0.0  
> **Last Updated:** January 5, 2026  
> **Status:** Production Reference

This document describes all testing tools available for the R58 recording system and how to use them effectively.

---

## Overview

The R58 system has three complementary testing approaches:

| Tool | Purpose | Target | When to Use |
|------|---------|--------|-------------|
| **Desktop Test Helper** | Interactive Electron app testing | Preke Studio (macOS) | UI development, debugging |
| **Playwright E2E** | Automated frontend testing | Vue webapp | CI/CD, regression testing |
| **Smoke Test Script** | Device health verification | R58 hardware | Pre-release, deployment |

---

## 1. Desktop Test Helper (Electron)

### Location

- Script: `packages/desktop/scripts/test-helper.js`
- Documentation: `packages/desktop/TESTING.md`

### Purpose

The Desktop Test Helper provides easy debugging and testing for the Preke Studio Electron app during development. It launches the app with Chrome DevTools Protocol (CDP) enabled, allowing Cursor's browser tools to interact with the app.

### Quick Start

```bash
cd packages/desktop
npm run test:launch    # Start app with debugging
npm run test:logs      # View recent logs
npm run test:stop      # Stop the app
```

### All Commands

| Command | Description |
|---------|-------------|
| `npm run test:launch` | Launch app with CDP debugging on port 9222 |
| `npm run test:stop` | Stop the running app |
| `npm run test:restart` | Stop and relaunch |
| `npm run test:build` | Rebuild main process and restart |
| `npm run test:status` | Check app and CDP status |
| `npm run test:logs` | Show last 50 log lines |
| `npm run test:logs:follow` | Follow logs in real-time |
| `npm run test:logs:clear` | Clear the log file |
| `npm run test:cdp` | Show CDP endpoints |
| `npm run test:devtools` | Open DevTools in browser |
| `npm run test:screenshot` | Capture screen to screenshots/ |

### Using with Cursor Browser Tools

After running `npm run test:launch`, you can use Cursor's browser tools:

```
1. Navigate to CDP interface:
   browser_navigate to http://localhost:9222

2. Take a snapshot to see elements:
   browser_snapshot

3. Interact with elements:
   browser_click, browser_type, browser_evaluate
```

### Log File Location

- **macOS:** `~/Library/Logs/preke-studio/main.log`
- **View:** `npm run test:logs`
- **Follow:** `npm run test:logs:follow`

### Reading Logs from Renderer

```typescript
const { logs, path } = await window.electronAPI.getRecentLogs(100);
console.log(logs);
```

### What "Pass" Means

A successful test session shows:

1. App launches without errors
2. CDP is available at `http://localhost:9222`
3. No critical errors in console (`npm run test:logs`)
4. UI renders correctly (verify via screenshot or browser tools)

### Troubleshooting

```bash
# App won't start
npm run test:stop        # Ensure old instance stopped
npm run test:logs        # Check for errors
npm run test:launch      # Try again

# CDP not available
lsof -i :9222            # Check what's using port
npm run test:restart     # Restart the app

# Build errors
npm run build:main       # Build manually to see errors
npm run test:logs        # Check runtime errors
```

---

## 2. Playwright E2E (Frontend)

### Location

- Tests: `packages/frontend/e2e/`
- Config: `packages/frontend/playwright.config.ts`

### Purpose

Playwright E2E tests verify the Vue webapp functionality automatically. These tests run in a headless browser and check critical user flows.

### Test Files

| File | Priority | Tests |
|------|----------|-------|
| `health.spec.ts` | P1 | API health, capabilities, admin panel, PWA |
| `recorder.spec.ts` | P0 | Recording start/stop, UI elements, navigation |
| `mixer.spec.ts` | P0 | VDO.ninja embed, scenes, sources, Go Live |

### Quick Start

```bash
cd packages/frontend

# Install Playwright browsers (first time only)
npx playwright install

# Run all E2E tests
npm run test:e2e

# Run specific test file
npx playwright test e2e/health.spec.ts

# Run with UI mode (interactive)
npx playwright test --ui

# Run with headed browser (visible)
npx playwright test --headed
```

### Configuration

The Playwright config (`playwright.config.ts`) specifies:

- **Base URL:** `http://localhost:5173` (Vite dev server)
- **Browsers:** Chromium, Mobile Chrome
- **Retries:** 2 on CI, 0 locally
- **Timeouts:** 30s per test, 5s per expect
- **Artifacts:** Screenshots on failure, traces on retry

### Running Against Different Environments

```bash
# Local dev server (default)
npm run test:e2e

# Against staging
VITE_API_URL=https://r58-api.itagenten.no npm run test:e2e

# Against production R58
VITE_API_URL=http://192.168.1.24:8000 npm run test:e2e
```

### What "Pass" Means

All tests pass (green checkmarks) with:

1. No assertion failures
2. No timeout errors
3. No console errors during tests
4. Screenshots captured only on failures

### Test Output

```
Running 25 tests using 4 workers

  ✓  health.spec.ts:8:3 › Health Check › API health endpoint returns healthy (1.2s)
  ✓  health.spec.ts:17:3 › Health Check › API detailed health includes all services (0.8s)
  ✓  recorder.spec.ts:13:3 › Recorder › displays recorder interface (2.1s)
  ...

  25 passed (45s)
```

### Viewing Reports

```bash
# HTML report (opens automatically on failure)
npx playwright show-report

# JUnit XML (for CI)
# Located at: e2e-results.xml
```

### Writing New Tests

```typescript
import { test, expect } from '@playwright/test'

test.describe('My Feature', () => {
  test('does something', async ({ page }) => {
    await page.goto('/my-page')
    
    // Check element is visible
    await expect(page.getByText('Hello')).toBeVisible()
    
    // Click button
    await page.getByRole('button', { name: 'Submit' }).click()
    
    // Assert result
    await expect(page.getByTestId('result')).toHaveText('Success')
  })
})
```

---

## 3. Smoke Test Script (R58 Device)

### Location

- Script: `scripts/smoke-test.sh`
- Checklist: `docs/SMOKE_TEST_CHECKLIST.md`

### Purpose

The smoke test script runs on the R58 device to verify system health before releases or after deployments. It checks services, API endpoints, disk space, and optionally runs a recording cycle.

### Quick Start

```bash
# SSH to R58
./connect-r58-frp.sh

# Run basic smoke test
cd /opt/preke-r58-recorder
./scripts/smoke-test.sh

# Run with recording test (requires camera)
./scripts/smoke-test.sh --with-recording

# Verbose output
./scripts/smoke-test.sh --verbose
```

### What It Tests

| Category | Tests |
|----------|-------|
| **Service Health** | r58-api, r58-pipeline, mediamtx running |
| **API Endpoints** | /health, /health/detailed, /capabilities, /recorder/status |
| **Device Capabilities** | recorder_available, api_version |
| **Storage** | Disk space > 10GB |
| **Recording Cycle** | Start, wait, stop, verify file (optional) |

### Sample Output

```
========================================
R58 Smoke Test
========================================
Date: Mon Jan  5 10:30:00 UTC 2026
Host: r58-production

=== 1. Service Health ===
✓ Service r58-api is running
✓ Service r58-pipeline is running
✓ Service mediamtx is running

=== 2. API Endpoints ===
✓ GET /api/v1/health returns 200
✓ GET /api/v1/health.status == healthy
✓ GET /api/v1/health/detailed returns 200
✓ GET /api/v1/capabilities returns 200
✓ GET /api/v1/recorder/status returns 200

=== 3. Device Capabilities ===
✓ GET /api/v1/capabilities.recorder_available == true
✓ GET /api/v1/capabilities.api_version == 2.0.0

=== 4. Storage ===
✓ Disk space: 85GB available (minimum 10GB)

=== 5. Recording Cycle ===
  Skipped (use --with-recording to enable)

========================================
SUMMARY
========================================
Passed:   10
Failed:   0
Warnings: 0

All tests passed!
```

### What "Pass" Means

1. All services are running (green checkmarks)
2. API endpoints return expected responses
3. Disk space is sufficient
4. Recording cycle completes without errors (if enabled)
5. Exit code is 0

### Recording Cycle Test

When run with `--with-recording`:

1. Starts recording on cam2
2. Waits 5 seconds
3. Checks recording status is "recording"
4. Stops recording
5. Verifies recording file was created
6. Cleans up test file

### Running Remotely

```bash
# From development machine
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && ./scripts/smoke-test.sh"

# With recording test
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && ./scripts/smoke-test.sh --with-recording"
```

---

## Test Workflow

### Pre-Release Testing

```bash
# 1. Run Playwright E2E locally
cd packages/frontend
npm run test:e2e

# 2. Test Electron app
cd packages/desktop
npm run test:launch
npm run test:logs  # Check for errors

# 3. Deploy to R58
./deploy-simple.sh

# 4. Run smoke test on R58
./connect-r58-frp.sh "cd /opt/preke-r58-recorder && ./scripts/smoke-test.sh --with-recording"

# 5. Manual verification
# Open https://r58-api.itagenten.no/static/studio.html
# Test recording manually
```

### CI/CD Integration

```yaml
# Example GitHub Actions
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node
      uses: actions/setup-node@v4
      with:
        node-version: 20
    
    - name: Install dependencies
      run: |
        cd packages/frontend
        npm ci
        npx playwright install --with-deps
    
    - name: Run E2E tests
      run: |
        cd packages/frontend
        npm run test:e2e
    
    - name: Upload report
      uses: actions/upload-artifact@v4
      if: failure()
      with:
        name: playwright-report
        path: packages/frontend/playwright-report/
```

---

## Troubleshooting

### Playwright Tests Failing

```bash
# Debug mode
npx playwright test --debug

# Trace viewer
npx playwright test --trace on
npx playwright show-trace trace.zip

# Screenshot comparison
# Check playwright-report/ for visual diffs
```

### Smoke Test Failing

```bash
# Check individual services
sudo systemctl status r58-api r58-pipeline mediamtx

# View logs
sudo journalctl -u r58-api -n 50

# Test API manually
curl http://localhost:8000/api/v1/health | jq
```

### Desktop App Not Launching

```bash
# Check port 9222
lsof -i :9222

# Kill existing Electron
pkill -9 Electron

# Rebuild
npm run build:main
npm run test:launch
```

---

## Related Documentation

- [docs/SMOKE_TEST_CHECKLIST.md](../SMOKE_TEST_CHECKLIST.md) - Manual checklist
- [docs/testing/test-matrix.md](test-matrix.md) - Complete test cases
- [docs/ops/debug-runbook.md](../ops/debug-runbook.md) - Troubleshooting
- [packages/desktop/TESTING.md](../../packages/desktop/TESTING.md) - Electron testing details

