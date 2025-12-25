@echo off
REM VDO.ninja Service Fix Script for Windows
REM Save this as find_and_fix_r58.bat and run it on the remote PC

echo ==================================================
echo R58 Service Recovery Script
echo ==================================================
echo.

REM Find R58 on network
echo Step 1: Finding R58 device...
echo.

set R58_IP=

for %%i in (192.168.68.55 192.168.1.24 192.168.1.25 10.58.0.1) do (
    echo Testing %%i...
    ping -n 1 -w 1000 %%i >nul 2>&1
    if !errorlevel! equ 0 (
        echo FOUND R58 at %%i!
        set R58_IP=%%i
        goto :found
    )
)

:notfound
echo.
echo ERROR: Could not find R58 device
echo Please check:
echo   1. R58 is powered on
echo   2. Network cable is connected
echo   3. This PC is on the same network
echo.
pause
exit /b 1

:found
echo.
echo R58 found at: %R58_IP%
echo.

REM Connect via SSH and restart services
echo Step 2: Connecting to R58 and restarting services...
echo When prompted, enter password: linaro
echo.

ssh linaro@%R58_IP% "sudo systemctl stop preke-recorder && sudo systemctl restart vdo-ninja && sleep 3 && sudo systemctl restart ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3 && sleep 5 && echo '' && echo 'Services restarted!' && echo '' && systemctl is-active vdo-ninja ninja-publish-cam1 ninja-publish-cam2 ninja-publish-cam3"

echo.
echo ==================================================
echo DONE!
echo ==================================================
echo.
echo Open browser and go to: https://%R58_IP%:8443/test_r58.html
echo.
echo Accept the certificate warning, then you should see the cameras.
echo.
pause

