@echo off
setlocal
title Cloisonne2Creo - Restart
rem ============================================
rem  restart.bat - 重启服务 (V2.3.1)
rem  流程: stop -> wait -> start -> health
rem ============================================

cd /d "%~dp0"

echo [1/4] Stopping current service...
call stop.bat
if errorlevel 1 (
    echo [WARN] stop.bat returned error, continuing...
)

echo [2/4] Waiting 3s...
timeout /t 3 /nobreak >nul

echo [3/4] Starting service...
call start.bat
exit /b %errorlevel%
