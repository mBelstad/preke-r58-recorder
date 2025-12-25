# VDO.ninja Service Fix Script for Windows
# Copy and paste this entire script into Windows PowerShell or Windows Terminal

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "R58 VDO.ninja Service Recovery Script (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Try to find R58 on network
Write-Host "Step 1: Finding R58 device..." -ForegroundColor Yellow
Write-Host ""

$R58_IP = $null
$testIPs = @("192.168.1.24", "192.168.1.25", "192.168.68.55", "10.58.0.1")

foreach ($ip in $testIPs) {
    Write-Host "  Testing $ip... " -NoNewline
    $ping = Test-Connection -ComputerName $ip -Count 1 -Quiet -TimeoutSeconds 2
    if ($ping) {
        Write-Host "FOUND!" -ForegroundColor Green
        $R58_IP = $ip
        break
    } else {
        Write-Host "No response" -ForegroundColor Red
    }
}

if (-not $R58_IP) {
    Write-Host ""
    Write-Host "ERROR: Could not find R58 device" -ForegroundColor Red
    Write-Host "Please check:" -ForegroundColor Yellow
    Write-Host "  1. R58 is powered on"
    Write-Host "  2. Network cable is connected"
    Write-Host "  3. This PC is on the same network"
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "R58 found at: $R58_IP" -ForegroundColor Green
Write-Host ""

# Create the SSH commands to execute on R58
$sshCommands = @"
echo '=================================================='
echo 'Connected to R58!'
echo '=================================================='
echo ''
echo 'Step 3: Checking service status...'
echo ''
echo 'VDO.ninja signaling server:'
systemctl is-active vdo-ninja && echo '  Active' || echo '  Inactive'
echo ''
echo 'Camera publishers:'
systemctl is-active ninja-publish-cam1 && echo '  CAM1: Active' || echo '  CAM1: Inactive'
systemctl is-active ninja-publish-cam2 && echo '  CAM2: Active' || echo '  CAM2: Inactive'
systemctl is-active ninja-publish-cam3 && echo '  CAM3: Active' || echo '  CAM3: Inactive'
echo ''
echo '=================================================='
echo 'Step 4: Restarting VDO.ninja services...'
echo '=================================================='
echo ''
echo 'Stopping preke-recorder (to free video devices)...'
sudo systemctl stop preke-recorder 2>/dev/null || true
sleep 2
echo 'Restarting VDO.ninja signaling server...'
sudo systemctl restart vdo-ninja
sleep 3
echo 'Restarting camera publishers...'
sudo systemctl restart ninja-publish-cam1
sudo systemctl restart ninja-publish-cam2
sudo systemctl restart ninja-publish-cam3
sleep 5
echo ''
echo '=================================================='
echo 'Step 5: Verifying services...'
echo '=================================================='
echo ''
echo 'VDO.ninja server:' `$(systemctl is-active vdo-ninja)
echo 'Camera 1 publisher:' `$(systemctl is-active ninja-publish-cam1)
echo 'Camera 2 publisher:' `$(systemctl is-active ninja-publish-cam2)
echo 'Camera 3 publisher:' `$(systemctl is-active ninja-publish-cam3)
echo ''
echo 'Recent publisher logs:'
echo '--- CAM1 (last 5 lines) ---'
sudo journalctl -u ninja-publish-cam1 -n 5 --no-pager | tail -5
echo ''
echo '--- CAM2 (last 5 lines) ---'
sudo journalctl -u ninja-publish-cam2 -n 5 --no-pager | tail -5
echo ''
echo '--- CAM3 (last 5 lines) ---'
sudo journalctl -u ninja-publish-cam3 -n 5 --no-pager | tail -5
echo ''
echo '=================================================='
echo 'Step 6: Checking port 8443...'
echo '=================================================='
netstat -tln | grep 8443 && echo 'Port 8443 is listening' || echo 'Port 8443 not available'
echo ''
echo '=================================================='
echo 'SERVICE RESTART COMPLETE!'
echo '=================================================='
echo ''
echo 'Access URLs:'
echo ''
echo 'Test Page:'
echo '  https://$R58_IP:8443/test_r58.html'
echo ''
echo 'Director View:'
echo '  https://$R58_IP:8443/?director=r58studio&wss=$R58_IP:8443'
echo ''
echo 'Mixer:'
echo '  https://$R58_IP:8443/mixer?push=MIXOUT&room=r58studio&wss=$R58_IP:8443'
echo ''
echo 'Individual Cameras:'
echo '  https://$R58_IP:8443/?view=r58-cam1&room=r58studio&wss=$R58_IP:8443'
echo '  https://$R58_IP:8443/?view=r58-cam2&room=r58studio&wss=$R58_IP:8443'
echo '  https://$R58_IP:8443/?view=r58-cam3&room=r58studio&wss=$R58_IP:8443'
echo ''
echo 'NOTE: Accept the self-signed certificate warning in your browser'
echo ''
"@

Write-Host "Step 2: Connecting to R58 via SSH..." -ForegroundColor Yellow
Write-Host ""
Write-Host "When prompted, enter password: linaro" -ForegroundColor Yellow
Write-Host ""

# Execute SSH command
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 linaro@$R58_IP $sshCommands

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "DONE! Services restarted on R58" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open a browser on this PC"
Write-Host "2. Go to: https://$R58_IP:8443/test_r58.html"
Write-Host "3. Accept the security warning (self-signed certificate)"
Write-Host "4. You should see the camera test page"
Write-Host ""

