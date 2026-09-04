@echo off
setlocal
title Cloisonne2Creo - Health Check
rem ============================================
rem  healthcheck.bat - 检查服务状态 (V2.3.1)
rem ============================================

echo Checking http://127.0.0.1:8765/api/health ...
echo.

for /f "delims=" %%i in ('powershell -NoProfile -Command "try{ $h=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 3; Write-Host ('OK|' + $h.service + '|' + $h.version + '|' + $h.pid + '|' + $h.port) }catch{ Write-Host 'DOWN|||0|0' }"') do set "RESULT=%%i"

for /f "tokens=1-5 delims=|" %%a in ("%RESULT%") do (
    set "STATE=%%a"
    set "SERVICE=%%b"
    set "VERSION=%%c"
    set "PID=%%d"
    set "PORT=%%e"
)

if "%STATE%"=="OK" (
    echo Service: OK
    echo Service: %SERVICE%
    echo Version: %VERSION%
    echo PID:     %PID%
    echo Port:    %PORT%
    exit /b 0
)

echo Service: NOT RUNNING
echo.
echo Cloisonne2Creo is not running.
echo Possible causes:
echo   - Python runtime unavailable
echo   - dependency error
echo   - port 8765 occupied
echo   - startup exception
echo.
echo See: logs\startup.log
exit /b 1
