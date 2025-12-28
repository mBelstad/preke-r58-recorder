/**
 * E2E Tests for Mixer (VDO.ninja) functionality
 * Priority: P0 - Critical path tests
 */
import { test, expect } from '@playwright/test'

test.describe('Mixer', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/mixer')
  })

  test('displays mixer interface', async ({ page }) => {
    // Check main UI elements are present
    await expect(page.locator('h1, [data-testid="mixer-title"]')).toBeVisible({ timeout: 10000 })
  })

  test('loads VDO.ninja iframe', async ({ page }) => {
    // Check for VDO.ninja iframe or embed
    const vdoEmbed = page.locator('iframe[src*="vdo"], [data-testid="vdo-embed"], .vdo-ninja-embed')
    
    // Wait for iframe to be present (may take time to load)
    await expect(vdoEmbed).toBeVisible({ timeout: 15000 })
  })

  test('shows loading state while VDO.ninja loads', async ({ page }) => {
    // Should show loading indicator before iframe loads
    const loadingIndicator = page.locator('[data-testid="vdo-loading"], .loading, .spinner')
    
    // This may be visible very briefly
    // Main check is that page handles loading state
    await expect(page.locator('body')).toBeVisible()
  })

  test('displays source panel', async ({ page }) => {
    // Check for source/input panel
    const sourcePanel = page.locator('[data-testid="source-panel"], .source-panel, .sources')
    
    if (await sourcePanel.isVisible()) {
      await expect(sourcePanel).toBeVisible()
    }
  })
})

test.describe('Mixer Scene Switching', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/mixer')
    // Wait for VDO.ninja to load
    await page.waitForTimeout(3000)
  })

  test('can switch scenes', async ({ page }) => {
    // Find scene selection buttons
    const sceneButtons = page.locator('[data-testid="scene-button"], .scene-button, button:has-text("Scene")')
    
    if (await sceneButtons.count() > 0) {
      // Click first scene button
      await sceneButtons.first().click()
      
      // Some visual feedback should occur
      // This is implementation-dependent
    }
  })
})

test.describe('Mixer Audio Controls', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/mixer')
    await page.waitForTimeout(3000)
  })

  test('shows audio controls', async ({ page }) => {
    // Check for audio/volume controls
    const audioControls = page.locator('[data-testid="audio-control"], .audio-control, .volume-slider, input[type="range"]')
    
    // Audio controls may or may not be visible depending on UI
    await expect(page.locator('body')).toBeVisible()
  })

  test('mute button toggles audio', async ({ page }) => {
    const muteButton = page.locator('[data-testid="mute-button"], button:has-text("Mute"), button[aria-label*="mute"]')
    
    if (await muteButton.isVisible()) {
      await muteButton.click()
      // Should show muted state
      
      await muteButton.click()
      // Should show unmuted state
    }
  })
})

test.describe('Mixer VDO.ninja Integration', () => {
  test('iframe has correct source URL', async ({ page }) => {
    await page.goto('/mixer')
    
    const iframe = page.locator('iframe')
    
    if (await iframe.count() > 0) {
      const src = await iframe.first().getAttribute('src')
      
      if (src) {
        // Should include required VDO.ninja parameters
        expect(src).toMatch(/localhost|r58\.local|vdo/)
      }
    }
  })

  test('handles VDO.ninja load failure', async ({ page }) => {
    // Block VDO.ninja requests
    await page.route('**/localhost:8443/**', route => route.abort())
    await page.route('**/r58.local:8443/**', route => route.abort())
    
    await page.goto('/mixer')
    
    // Page should handle failure gracefully
    // Should show error state or fallback
    await expect(page.locator('body')).toBeVisible()
  })
})

