@echo off
setlocal enabledelayedexpansion
title Cloisonne2Creo V2.3.1
rem ============================================
rem  Cloisonne2Creo - Windows 启动脚本 (V2.3.1)
rem  开发/调试模式: 前台运行 + 自动打开浏览器
rem  关闭服务窗口即停止服务
rem ============================================

cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

rem ---------- 日志 ----------
if not exist "%PROJECT_ROOT%logs" mkdir "%PROJECT_ROOT%logs"
set "STARTUP_LOG=%PROJECT_ROOT%logs\startup.log"
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value ^| find "="') do set "TS=%%i"
set "TS=%TS:~0,4%-%TS:~4,2%-%TS:~6,2% %TS:~8,2%:%TS:~10,2%:%TS:~12,2%"

echo.
echo ============================================
echo   Cloisonne2Creo V2.3.1 - Windows Launcher
echo ============================================
echo.

rem ---------- 1. 确定 Python (优先级: .venv > Python312 > py -3.12 > python) ----------
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
echo Please install Python 3.12: https://www.python.org/downloads/
echo [%TS%] BAT_ERROR Python not found >> "%STARTUP_LOG%"
goto :fail

:py_found
echo [1/4] Python: %PYTHON_CMD%
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python launcher failed: %PYTHON_CMD%
    echo [%TS%] BAT_ERROR Python launcher failed >> "%STARTUP_LOG%"
    goto :fail
)
echo [%TS%] BAT_START Python selected >> "%STARTUP_LOG%"

rem ---------- 2. 检查依赖 ----------
echo [2/4] Checking dependencies...
%PYTHON_CMD% -c "import fastapi, uvicorn, cv2, numpy, skimage, skan, shapely, vtracer, svgpathtools, ezdxf" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Dependencies missing. Run update.bat to install, then retry.
    echo [%TS%] BAT_ERROR Dependencies missing >> "%STARTUP_LOG%"
    goto :fail
)
echo       Dependencies OK.

rem ---------- 3. 单实例检查 ----------
echo [3/4] Checking if already running...
set "HEALTH="
for /f %%i in ('powershell -NoProfile -Command "try{ (Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2).status }catch{ 'down' }"') do set "HEALTH=%%i"
if "%HEALTH%"=="ok" (
    echo       Cloisonne2Creo already running.
    echo       Opening browser...
    echo [%TS%] BAT_ALREADY_RUNNING health=ok >> "%STARTUP_LOG%"
    start "" "http://127.0.0.1:8765"
    exit /b 0
)

rem ---------- 4. 启动服务 (新窗口, 关闭窗口即停止) ----------
echo [4/4] Starting server on http://127.0.0.1:8765 ...
start "Cloisonne2Creo Server" /min cmd /k ""%PYTHON_CMD%" main.py"

rem ---------- 健康检查轮询 (最多15秒) ----------
echo       Waiting for server health (max 15s)...
set /a attempts=0
:wait_health
set /a attempts+=1
if %attempts% GTR 15 (
    echo.
    echo [ERROR] Server failed to start within 15s.
    echo         See logs\startup.log
    goto :fail
)
timeout /t 1 /nobreak >nul
set "HEALTH="
for /f %%i in ('powershell -NoProfile -Command "try{ (Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2).status }catch{ 'down' }"') do set "HEALTH=%%i"
if not "%HEALTH%"=="ok" goto :wait_health

echo       Health OK. Opening browser...
echo [%TS%] BAT_STARTED health=ok after %attempts%s >> "%STARTUP_LOG%"
start "" "http://127.0.0.1:8765"
echo.
echo ============================================
echo   Cloisonne2Creo is running: http://127.0.0.1:8765
echo   Close the "Cloisonne2Creo Server" window to stop.
echo ============================================
exit /b 0

:fail
echo.
echo =====================================
echo Cloisonne2Creo failed to start.
echo See logs\startup.log
echo =====================================
pause
exit /b 1
