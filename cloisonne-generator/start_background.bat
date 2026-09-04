@echo off
setlocal
title Cloisonne2Creo - Start (Background)
rem ============================================
rem  start_background.bat - 可选后台启动 (V2.3.1)
rem  说明: 正式常驻请使用 launcher\install_task.bat (Task Scheduler)
rem  本脚本只做"最小化后台启动 + 健康检查", 不做自制 PID 守护
rem ============================================

cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

set "PYTHON_CMD="
if exist "%PROJECT_ROOT%.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%PROJECT_ROOT%.venv\Scripts\python.exe"
    goto :py_found
)
set "P312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%P312%" (
    set "PYTHON_CMD=%P312%"
    goto :py_found
)
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    goto :py_found
)
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :py_found
)
echo [ERROR] Python not found.
pause
exit /b 1

:py_found
rem 单实例检查
set "HEALTH="
for /f %%i in ('powershell -NoProfile -Command "try{ (Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2).status }catch{ 'down' }"') do set "HEALTH=%%i"
if "%HEALTH%"=="ok" (
    echo Cloisonne2Creo already running.
    start "" "http://127.0.0.1:8765"
    exit /b 0
)

echo Starting Cloisonne2Creo in background (minimized window)...
start "Cloisonne2Creo Server" /min cmd /k ""%PYTHON_CMD%" main.py"

echo Waiting for health (max 15s)...
set /a attempts=0
:wait
set /a attempts+=1
if %attempts% GTR 15 (
    echo [ERROR] Server failed to start. See logs\startup.log
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
set "HEALTH="
for /f %%i in ('powershell -NoProfile -Command "try{ (Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2).status }catch{ 'down' }"') do set "HEALTH=%%i"
if not "%HEALTH%"=="ok" goto :wait

echo Health OK. Opening browser...
start "" "http://127.0.0.1:8765"
exit /b 0
