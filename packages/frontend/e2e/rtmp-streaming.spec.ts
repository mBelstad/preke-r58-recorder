import { test, expect } from '@playwright/test'

const BASE_URL = 'https://app.itagenten.no'

test.describe('RTMP Streaming from Mixer', () => {
  test('Check mixer RTMP streaming status and configuration', async ({ page }) => {
    const errors: string[] = []
    const logs: string[] = []
    
    page.on('console', msg => {
      const text = msg.text()
      if (msg.type() === 'error') {
        errors.push(text)
      }
      logs.push(`[${msg.type()}] ${text}`)
    })
    
    // Navigate to mixer
    await page.goto(`${BASE_URL}/#/mixer`, { waitUntil: 'networkidle' })
    
    // Wait for mixer to load
    await page.waitForSelector('.mixer-view, iframe', { timeout: 15000 })
    
    // Wait a bit for everything to initialize
    await page.waitForTimeout(5000)
    
    // Check for streaming control panel
    const streamingPanel = page.locator('text=/.*Streaming.*|.*RTMP.*|.*Go Live.*/i')
    const hasStreamingPanel = await streamingPanel.count() > 0
    console.log('Streaming panel found:', hasStreamingPanel)
    
    // Check for "Start Streaming" button
    const startStreamingButton = page.locator('button:has-text("Start Streaming"), button:has-text("Stop")')
    const startButtonCount = await startStreamingButton.count()
    console.log('Start Streaming button found:', startButtonCount > 0)
    
    // Check for Scene Output button (needed to push to MediaMTX)
    const sceneOutputButton = page.locator('button:has-text("Scene Output")')
    const sceneOutputCount = await sceneOutputButton.count()
    console.log('Scene Output button found:', sceneOutputCount > 0)
    
    // Check API status for RTMP configuration
    const statusResponse = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/streaming/status')
        return await response.json()
      } catch (e) {
        return { error: e.message }
      }
    })
    
    console.log('Streaming status:', JSON.stringify(statusResponse, null, 2))
    
    // Check if mixer_program path exists in MediaMTX
    const mediamtxStatus = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/streaming/status')
        const data = await response.json()
        return {
          mixer_program_exists: data.paths?.mixer_program !== undefined,
          mixer_program_ready: data.paths?.mixer_program?.ready || false,
          rtmp_relay_configured: data.rtmp_relay_configured || false,
          run_on_ready: data.run_on_ready || null
        }
      } catch (e) {
        return { error: e.message }
      }
    })
    
    console.log('MediaMTX status:', JSON.stringify(mediamtxStatus, null, 2))
    
    // Check ProgramOutput component status
    const programOutputStatus = page.locator('[data-testid="program-output-status"]')
    const hasProgramOutput = await programOutputStatus.count() > 0
    if (hasProgramOutput) {
      const statusText = await programOutputStatus.textContent()
      console.log('Program Output status:', statusText)
    }
    
    // Take screenshot
    await page.screenshot({ path: 'test-results/mixer-rtmp-test.png', fullPage: true })
    
    await page.waitForTimeout(3000)
    console.log('Mixer RTMP Test Errors:', errors)
    console.log('Recent logs:', logs.slice(-20))
  })
  
  test('Click Start Streaming and test full RTMP flow', async ({ page }) => {
    const errors: string[] = []
    const logs: string[] = []
    
    page.on('console', msg => {
      const text = msg.text()
      if (msg.type() === 'error') {
        errors.push(text)
      }
      logs.push(`[${msg.type()}] ${text}`)
    })
    
    await page.goto(`${BASE_URL}/#/mixer`, { waitUntil: 'networkidle' })
    await page.waitForSelector('.mixer-view, iframe', { timeout: 15000 })
    await page.waitForTimeout(5000)
    
    // First, configure RTMP destination
    console.log('Step 1: Configuring RTMP destination...')
    const startResult = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/streaming/rtmp/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            destinations: [{
              platform: 'youtube',
              enabled: true,
              rtmp_url: 'rtmp://a.rtmp.youtube.com/live2/',
              stream_key: 'test-key-12345'
            }]
          })
        })
        return await response.json()
      } catch (e) {
        return { error: e.message }
      }
    })
    
    console.log('RTMP Start Result:', JSON.stringify(startResult, null, 2))
    
    // Check status after configuring RTMP
    await page.waitForTimeout(2000)
    const statusAfterConfig = await page.evaluate(async () => {
      try {
        const response = await fetch('/api/streaming/status')
        return await response.json()
      } catch (e) {
        return { error: e.message }
      }
    })
    
    console.log('Status after RTMP config:', JSON.stringify(statusAfterConfig, null, 2))
    
    // Step 2: Click "Start Streaming" button
    console.log('Step 2: Clicking Start Streaming button...')
    const startStreamingButton = page.locator('button:has-text("Start Streaming")')
    const buttonCount = await startStreamingButton.count()
    console.log('Start Streaming button count:', buttonCount)
    
    if (buttonCount > 0) {
      await startStreamingButton.first().click()
      console.log('Clicked Start Streaming button')
      
      // Wait for state changes
      await page.waitForTimeout(3000)
      
      // Check if button text changed to "Stop"
      const stopButtonCheck = page.locator('button:has-text("Stop")')
      const isStopped = await stopButtonCheck.count() > 0
      console.log('Button changed to Stop:', isStopped)
      
      // Check ProgramOutput status
      const programOutputStatus = page.locator('[data-testid="program-output-status"]')
      if (await programOutputStatus.count() > 0) {
        const statusText = await programOutputStatus.textContent()
        console.log('Program Output status after click:', statusText)
      }
      
      // Check for iframe in ProgramOutput
      const programOutputIframe = page.locator('iframe[src*="whipout"]')
      const iframeCount = await programOutputIframe.count()
      console.log('ProgramOutput iframe count:', iframeCount)
      
      if (iframeCount > 0) {
        const iframeSrc = await programOutputIframe.first().getAttribute('src')
        console.log('ProgramOutput iframe src:', iframeSrc?.substring(0, 200))
      }
      
      // Monitor stream status over time
      console.log('Step 3: Monitoring stream status...')
      for (let i = 0; i < 10; i++) {
        await page.waitForTimeout(2000)
        const currentStatus = await page.evaluate(async () => {
          try {
            const response = await fetch('/api/streaming/status')
            return await response.json()
          } catch (e) {
            return { error: e.message }
          }
        })
        
        const isReady = currentStatus.mixer_program_active || currentStatus.stream_info?.ready
        console.log(`Check ${i + 1}/10: mixer_program ready = ${isReady}`)
        
        if (isReady) {
          console.log('Stream is ready!', JSON.stringify(currentStatus, null, 2))
          break
        }
      }
      
      // Final status check
      const finalStatus = await page.evaluate(async () => {
        try {
          const response = await fetch('/api/streaming/status')
          return await response.json()
        } catch (e) {
          return { error: e.message }
        }
      })
      
      console.log('Final status:', JSON.stringify(finalStatus, null, 2))
      
      // Take screenshot
      await page.screenshot({ path: 'test-results/mixer-after-start-streaming.png', fullPage: true })
      
      // Step 4: Check for FFmpeg process (via backend logs check)
      console.log('Step 4: Checking for FFmpeg process...')
      const hasFFmpeg = await page.evaluate(async () => {
        try {
          // We can't directly check processes, but we can check if runOnReady was triggered
          const response = await fetch('/api/streaming/status')
          const data = await response.json()
          return {
            rtmp_relay_configured: data.rtmp_relay_configured,
            run_on_ready: data.run_on_ready,
            stream_ready: data.mixer_program_active || data.stream_info?.ready
          }
        } catch (e) {
          return { error: e.message }
        }
      })
      
      console.log('FFmpeg/RTMP status:', JSON.stringify(hasFFmpeg, null, 2))
      
      // Step 5: Stop streaming
      console.log('Step 5: Stopping streaming...')
      const stopButton = page.locator('button:has-text("Stop")')
      if (await stopButton.count() > 0) {
        await stopButton.first().click()
        await page.waitForTimeout(2000)
        console.log('Clicked Stop button')
      }
      
      // Stop RTMP relay
      const stopResult = await page.evaluate(async () => {
        try {
          const response = await fetch('/api/streaming/rtmp/stop', {
            method: 'POST'
          })
          return await response.json()
        } catch (e) {
          return { error: e.message }
        }
      })
      
      console.log('RTMP Stop Result:', JSON.stringify(stopResult, null, 2))
    } else {
      console.error('Start Streaming button not found!')
    }
    
    await page.screenshot({ path: 'test-results/mixer-rtmp-full-test.png', fullPage: true })
    
    await page.waitForTimeout(2000)
    console.log('Full Flow Test Errors:', errors)
    console.log('Recent logs:', logs.slice(-20))
  })
})
