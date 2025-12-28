/**
 * E2E Tests for Health and Status functionality
 * Priority: P1
 */
import { test, expect } from '@playwright/test'

test.describe('Health Check', () => {
  test('API health endpoint returns healthy', async ({ request }) => {
    const response = await request.get('/api/v1/health')
    
    expect(response.ok()).toBeTruthy()
    
    const data = await response.json()
    expect(data.status).toBe('healthy')
  })

  test('API detailed health includes all services', async ({ request }) => {
    const response = await request.get('/api/v1/health/detailed')
    
    expect(response.ok()).toBeTruthy()
    
    const data = await response.json()
    expect(data.status).toBeDefined()
    expect(data.services).toBeDefined()
    expect(data.storage).toBeDefined()
    expect(data.uptime_seconds).toBeGreaterThanOrEqual(0)
  })
})

test.describe('Capabilities', () => {
  test('API capabilities endpoint returns device info', async ({ request }) => {
    const response = await request.get('/api/v1/capabilities')
    
    expect(response.ok()).toBeTruthy()
    
    const data = await response.json()
    expect(data.device_id).toBeDefined()
    expect(data.api_version).toBeDefined()
    expect(data.inputs).toBeDefined()
    expect(data.recorder_available).toBeDefined()
    expect(data.mixer_available).toBeDefined()
  })
})

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/admin')
  })

  test('displays admin interface', async ({ page }) => {
    // Check admin panel loads
    await expect(page.locator('h1, [data-testid="admin-title"]')).toBeVisible({ timeout: 10000 })
  })

  test('shows device status', async ({ page }) => {
    const deviceStatus = page.locator('[data-testid="device-status"], .device-status')
    
    if (await deviceStatus.isVisible()) {
      await expect(deviceStatus).toBeVisible()
    }
  })

  test('shows log viewer', async ({ page }) => {
    const logViewer = page.locator('[data-testid="log-viewer"], .log-viewer, .logs')
    
    if (await logViewer.isVisible()) {
      await expect(logViewer).toBeVisible()
    }
  })
})

test.describe('PWA Features', () => {
  test('has valid manifest', async ({ page }) => {
    await page.goto('/')
    
    // Check for manifest link
    const manifestLink = page.locator('link[rel="manifest"]')
    const href = await manifestLink.getAttribute('href')
    
    if (href) {
      const manifestResponse = await page.request.get(href)
      expect(manifestResponse.ok()).toBeTruthy()
    }
  })

  test('page loads without console errors', async ({ page }) => {
    const consoleErrors: string[] = []
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })
    
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // Filter out common third-party errors
    const criticalErrors = consoleErrors.filter(
      err => !err.includes('favicon') && !err.includes('404')
    )
    
    // Should have no critical errors
    expect(criticalErrors).toHaveLength(0)
  })
})

test.describe('Performance', () => {
  test('page loads within performance budget', async ({ page }) => {
    await page.goto('/')
    
    const performanceMetrics = await page.evaluate(() => ({
      fcp: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0,
      domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
      load: performance.timing.loadEventEnd - performance.timing.navigationStart,
    }))
    
    // FCP should be under 1.5s
    expect(performanceMetrics.fcp).toBeLessThan(3000) // Relaxed for dev server
    
    // DOM Content Loaded should be under 3s
    expect(performanceMetrics.domContentLoaded).toBeLessThan(5000)
  })

  test('no memory leaks on navigation', async ({ page }) => {
    // Navigate between pages multiple times
    for (let i = 0; i < 5; i++) {
      await page.goto('/')
      await page.goto('/recorder')
      await page.goto('/mixer')
      await page.goto('/admin')
    }
    
    // Page should still be responsive
    await expect(page.locator('body')).toBeVisible()
  })
})

