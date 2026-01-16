import { test, expect } from '@playwright/test'

const BASE_URL = 'https://app.itagenten.no'

test.describe('Display Pages', () => {
  test('QR page loads and displays correctly', async ({ page }) => {
    const errors: string[] = []
    const warnings: string[] = []
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text())
      }
    })
    
    await page.goto(`${BASE_URL}/#/qr`, { waitUntil: 'networkidle' })
    
    // Wait for content to load
    await page.waitForSelector('.qr-view', { timeout: 10000 })
    
    // Wait for QR code to load
    await page.waitForSelector('.qr-view__qr-image', { timeout: 10000 })
    
    // Check for welcome text
    const welcomeTitle = page.locator('.qr-view__welcome-title')
    await expect(welcomeTitle).toBeVisible()
    await expect(welcomeTitle).toContainText('Welcome')
    
    // Check for QR code
    const qrImage = page.locator('.qr-view__qr-image')
    await expect(qrImage).toBeVisible()
    
    // Check if text is clipped - get bounding box
    const titleBox = await welcomeTitle.boundingBox()
    const viewport = page.viewportSize()
    
    if (titleBox && viewport) {
      console.log(`QR Title position: top=${titleBox.y}, viewport height=${viewport.height}`)
      if (titleBox.y < 0) {
        console.warn('⚠️ Title is clipped at top!')
      }
    }
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/qr-page.png', fullPage: true })
    
    // Wait a bit for any async errors
    await page.waitForTimeout(3000)
    
    console.log('QR Page Errors:', errors)
    console.log('QR Page Warnings:', warnings)
    expect(errors.length).toBe(0)
  })

  test('Podcast display page loads correctly', async ({ page }) => {
    const errors: string[] = []
    const warnings: string[] = []
    
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      } else if (msg.type() === 'warning') {
        warnings.push(msg.text())
      }
    })
    
    await page.goto(`${BASE_URL}/#/podcast`, { waitUntil: 'networkidle' })
    
    // Wait for content
    await page.waitForSelector('.studio-display', { timeout: 10000 })
    await page.waitForSelector('.display-header', { timeout: 10000 })
    
    // Check for header
    const header = page.locator('.display-header')
    await expect(header).toBeVisible()
    
    // Check for customer name
    const customerName = page.locator('text=Demo Session')
    await expect(customerName).toBeVisible()
    
    // Check for project name
    const projectName = page.locator('text=Demo Recording')
    await expect(projectName).toBeVisible()
    
    // Check that disk space is NOT shown (preview mode)
    const diskSpace = page.locator('text=/.*GB available.*/')
    await expect(diskSpace).not.toBeVisible()
    
    // Check for time remaining
    const timeRemaining = page.locator('text=/.*min left.*/')
    await expect(timeRemaining).toBeVisible()
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/podcast-page.png', fullPage: true })
    
    await page.waitForTimeout(3000)
    console.log('Podcast Page Errors:', errors)
    console.log('Podcast Page Warnings:', warnings)
  })

  test('Talking head display page loads correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/#/talking-head`)
    
    await page.waitForSelector('.studio-display', { timeout: 10000 })
    await page.screenshot({ path: 'test-results/talking-head-page.png', fullPage: true })
    
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    
    await page.waitForTimeout(2000)
    console.log('Talking Head Page Errors:', errors)
  })

  test('Course display page loads correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/#/course`)
    
    await page.waitForSelector('.studio-display', { timeout: 10000 })
    await page.screenshot({ path: 'test-results/course-page.png', fullPage: true })
    
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    
    await page.waitForTimeout(2000)
    console.log('Course Page Errors:', errors)
  })

  test('Webinar display page loads correctly', async ({ page }) => {
    await page.goto(`${BASE_URL}/#/webinar`)
    
    await page.waitForSelector('.studio-display', { timeout: 10000 })
    
    // Check that VDO.ninja offline message is NOT shown
    const vdoOffline = page.locator('text=/.*VDO.ninja Offline.*/')
    await expect(vdoOffline).not.toBeVisible()
    
    await page.screenshot({ path: 'test-results/webinar-page.png', fullPage: true })
    
    const errors: string[] = []
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })
    
    await page.waitForTimeout(2000)
    console.log('Webinar Page Errors:', errors)
  })
})
