@echo off
setlocal
title Uninstall Cloisonne2Creo autostart task
rem ============================================
rem  uninstall_task.bat - Remove scheduled task (V2.3.1)
rem  Only removes the task; project files are untouched
rem ============================================

rem ---------- Auto-elevate (Task Scheduler needs admin) ----------
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

echo Removing scheduled task "Cloisonne2Creo"...
schtasks /end /tn "Cloisonne2Creo" >nul 2>&1
schtasks /delete /tn "Cloisonne2Creo" /f >nul 2>&1
if errorlevel 1 (
    echo [WARN] Task not found or already removed.
) else (
    echo Task removed.
)

echo.
echo Project files are untouched.
pause
