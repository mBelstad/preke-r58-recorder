const puppeteer = require('puppeteer');
const path = require('path');

async function takeScreenshots() {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    const htmlPath = `file://${path.resolve(__dirname, 'src/static/switcher.html')}`;
    
    console.log('Loading:', htmlPath);
    await page.goto(htmlPath, { waitUntil: 'networkidle0', timeout: 30000 });

    // Wait for page to render
    await page.waitForSelector('.switcher-container', { timeout: 5000 });
    
    // Inject mock data for visual preview
    await page.evaluate(() => {
        // Mock some scene buttons
        const sceneGrid = document.getElementById('sceneGrid');
        if (sceneGrid) {
            sceneGrid.innerHTML = `
                <button class="scene-button-large program" data-scene-id="cam1">CAM 1 FULL</button>
                <button class="scene-button-large preview" data-scene-id="cam2">CAM 2 FULL</button>
                <button class="scene-button-large" data-scene-id="split">SIDE BY SIDE</button>
                <button class="scene-button-large" data-scene-id="quad">QUAD VIEW</button>
                <button class="scene-button-large" data-scene-id="pip">PIP CAM 2</button>
                <button class="scene-button-large" data-scene-id="interview">INTERVIEW</button>
            `;
        }
        
        // Mock input grid
        const inputGrid = document.getElementById('compactInputGrid');
        if (inputGrid) {
            inputGrid.innerHTML = `
                <div class="compact-input" data-source="cam0">
                    <div class="compact-signal-indicator signal-live"></div>
                    <div class="compact-input-label">CAM 1</div>
                </div>
                <div class="compact-input" data-source="cam1">
                    <div class="compact-signal-indicator signal-live"></div>
                    <div class="compact-input-label">CAM 2</div>
                </div>
                <div class="compact-input" data-source="cam2">
                    <div class="compact-signal-indicator signal-none"></div>
                    <div class="compact-input-label">CAM 3</div>
                </div>
                <div class="compact-input" data-source="cam3">
                    <div class="compact-signal-indicator signal-disabled"></div>
                    <div class="compact-input-label">CAM 4</div>
                </div>
            `;
        }
        
        // Update status indicators
        const statusDot = document.getElementById('statusDot');
        const statusText = document.getElementById('statusText');
        if (statusDot) statusDot.classList.add('active');
        if (statusText) statusText.textContent = 'PLAYING';
        
        const statusDotRight = document.getElementById('statusDotRight');
        const statusTextRight = document.getElementById('statusTextRight');
        if (statusDotRight) statusDotRight.classList.add('active');
        if (statusTextRight) statusTextRight.textContent = 'PLAYING';
        
        // Show local indicator
        const localIndicator = document.getElementById('localIndicator');
        if (localIndicator) localIndicator.style.display = 'block';
        
        // Hide program placeholder
        const programPlaceholder = document.getElementById('programPlaceholder');
        if (programPlaceholder) programPlaceholder.style.display = 'none';
        
        const previewPlaceholder = document.getElementById('previewPlaceholder');
        if (previewPlaceholder) previewPlaceholder.style.display = 'none';
    });

    // Screenshot 1: Dark theme (default)
    console.log('Taking dark theme screenshot...');
    await page.screenshot({ 
        path: 'mixer-dark-theme.png',
        fullPage: false
    });
    console.log('Saved: mixer-dark-theme.png');

    // Screenshot 2: Light theme
    console.log('Switching to light theme...');
    await page.evaluate(() => {
        document.documentElement.setAttribute('data-theme', 'light');
    });
    await new Promise(r => setTimeout(r, 500)); // Wait for transition
    
    await page.screenshot({ 
        path: 'mixer-light-theme.png',
        fullPage: false
    });
    console.log('Saved: mixer-light-theme.png');

    await browser.close();
    console.log('\n✅ Screenshots complete!');
}

takeScreenshots().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
