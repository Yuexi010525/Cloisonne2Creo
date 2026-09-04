@echo off
setlocal
title Cloisonne2Creo - Stop
rem ============================================
rem  stop.bat - 精准停止服务 (V2.3.1)
rem  根据 PID + commandline 停止监听 8765 的 python 进程
rem  禁止 taskkill /f /im python.exe (会误杀其他 Python)
rem ============================================

echo Stopping Cloisonne2Creo (port 8765)...

set "FOUND="
for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do (
    set "FOUND=%%p"
)

if "%FOUND%"=="" (
    echo No Cloisonne2Creo process listening on 8765.
    exit /b 0
)

echo Found PID: %FOUND%
set "IS_PY="
for /f "delims=" %%c in ('powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=%FOUND%' | Select-Object -ExpandProperty CommandLine"') do set "IS_PY=%%c"
echo CommandLine: %IS_PY%

echo %IS_PY% | findstr /i "main.py" >nul
if errorlevel 1 (
    echo [WARN] PID %FOUND% does not look like Cloisonne2Creo. Refusing to kill.
    exit /b 1
)

taskkill /pid %FOUND% /f >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to stop PID %FOUND%.
    exit /b 1
)

echo Stopped PID %FOUND%.
exit /b 0
