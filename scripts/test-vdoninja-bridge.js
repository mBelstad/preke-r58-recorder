#!/usr/bin/env node
/**
 * Test script for VDO.ninja Guest Bridge
 * Connects to an existing Chromium instance and tests the bridge flow
 */

const puppeteer = require('puppeteer-core');

const CHROMIUM_WS = 'ws://localhost:9222';
const BRIDGE_URL = 'https://r58-api.itagenten.no/static/vdoninja-guest-bridge.html';
const ROOM = process.argv[2] || 'testroom4';
const VDO_HOST = 'r58-vdo.itagenten.no';

async function main() {
    console.log(`\n=== VDO.ninja Bridge Test ===`);
    console.log(`Room: ${ROOM}`);
    
    try {
        // Connect to existing browser
        console.log('\n1. Connecting to Chromium...');
        const browser = await puppeteer.connect({
            browserWSEndpoint: `${CHROMIUM_WS}/devtools/browser/63464dac-23bc-4d01-bfb3-89d5d536adb3`,
        });
        console.log('   ✓ Connected to browser');
        
        // Get existing pages
        const pages = await browser.pages();
        console.log(`   Found ${pages.length} page(s)`);
        
        // Find or create bridge page
        let bridgePage = pages.find(p => p.url().includes('vdoninja-guest-bridge'));
        
        if (!bridgePage) {
            console.log('\n2. Opening bridge page...');
            bridgePage = await browser.newPage();
            await bridgePage.goto(`${BRIDGE_URL}?room=${ROOM}&autostart`, { waitUntil: 'networkidle0', timeout: 30000 });
        } else {
            console.log('\n2. Using existing bridge page');
        }
        console.log(`   URL: ${bridgePage.url()}`);
        
        // Wait for WHEP to connect
        console.log('\n3. Checking WHEP status...');
        await bridgePage.waitForFunction(
            () => document.getElementById('whepStatus')?.textContent?.includes('Connected'),
            { timeout: 15000 }
        ).catch(() => console.log('   ⚠ WHEP not connected yet'));
        
        const whepStatus = await bridgePage.evaluate(() => document.getElementById('whepStatus')?.textContent);
        console.log(`   WHEP Status: ${whepStatus}`);
        
        // Check if video is being received
        const videoStats = await bridgePage.evaluate(() => {
            const video = document.getElementById('inputVideo');
            if (video) {
                return {
                    width: video.videoWidth,
                    height: video.videoHeight,
                    playing: !video.paused
                };
            }
            return null;
        });
        console.log(`   Video: ${videoStats ? `${videoStats.width}x${videoStats.height}` : 'No video'}`);
        
        // Now open a new tab to join the room with screenshare
        console.log('\n4. Opening VDO.ninja screenshare tab...');
        const screensharePage = await browser.newPage();
        
        // Navigate to screenshare URL
        const screenshareUrl = `https://${VDO_HOST}/?push=hdmicam&room=${ROOM}&screenshare&label=HDMI-Camera`;
        await screensharePage.goto(screenshareUrl, { waitUntil: 'networkidle0', timeout: 30000 });
        console.log(`   URL: ${screensharePage.url()}`);
        
        // Wait for page to load
        await new Promise(r => setTimeout(r, 3000));
        
        // Try to click the "SELECT SCREEN TO SHARE" button
        console.log('\n5. Looking for screen share button...');
        const buttonFound = await screensharePage.evaluate(() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const shareBtn = buttons.find(b => b.textContent.includes('SELECT SCREEN'));
            if (shareBtn) {
                shareBtn.click();
                return true;
            }
            return false;
        });
        
        if (buttonFound) {
            console.log('   ✓ Clicked screen share button');
            console.log('   ⚠ Browser will show native screen picker dialog');
            console.log('   (This requires user interaction or special Chromium flags)');
        } else {
            console.log('   ✗ Screen share button not found');
        }
        
        // Open director to monitor
        console.log('\n6. Opening Director page...');
        const directorPage = await browser.newPage();
        await directorPage.goto(`https://${VDO_HOST}/?director=${ROOM}`, { waitUntil: 'networkidle0', timeout: 30000 });
        
        // Check for guests
        await new Promise(r => setTimeout(r, 3000));
        const guestCount = await directorPage.evaluate(() => {
            const guests = document.querySelectorAll('[class*="guest"]');
            return guests.length;
        });
        console.log(`   Director page loaded, guest elements: ${guestCount}`);
        
        // Take a screenshot of the director
        console.log('\n7. Taking screenshot of director...');
        await directorPage.screenshot({ path: '/tmp/director-screenshot.png', fullPage: true });
        console.log('   Saved to /tmp/director-screenshot.png');
        
        console.log('\n=== Test Complete ===');
        console.log('Check the director page to see if the camera appears as a guest');
        console.log(`Director URL: https://${VDO_HOST}/?director=${ROOM}`);
        
    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

main();

