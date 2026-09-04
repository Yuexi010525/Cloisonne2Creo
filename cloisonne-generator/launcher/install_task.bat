@echo off
setlocal
title Install Cloisonne2Creo autostart task
rem ============================================
rem  install_task.bat - Install Task Scheduler autostart (V2.3.1)
rem  Registers: run at logon + auto-restart on failure (1min x 5)
rem  Uninstall : launcher\uninstall_task.bat
rem ============================================

rem ---------- Auto-elevate (Task Scheduler needs admin) ----------
net session >nul 2>&1
if errorlevel 1 (
    echo Requesting administrator privileges...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

cd /d "%~dp0"
cd ..
set "PROJECT_ROOT=%CD%"

rem ---------- Pick Python (priority: .venv > Python312) ----------
set "PYTHON_EXE="
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
    goto :py_found
)
set "P312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%P312%" (
    set "PYTHON_EXE=%P312%"
    goto :py_found
)
echo [ERROR] Python not found. Run start.bat once or install Python 3.12 first.
pause
exit /b 1

:py_found
echo Python: %PYTHON_EXE%
echo WorkingDir: %PROJECT_ROOT%
echo.

echo Creating scheduled task "Cloisonne2Creo"...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$exe='%PYTHON_EXE%'; $wd='%PROJECT_ROOT%'; " ^
  "$action=New-ScheduledTaskAction -Execute $exe -Argument 'main.py' -WorkingDirectory $wd; " ^
  "$trigger=New-ScheduledTaskTrigger -AtLogOn; " ^
  "$settings=New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; " ^
  "Register-ScheduledTask -TaskName 'Cloisonne2Creo' -Action $action -Trigger $trigger -Settings $settings -Description 'Cloisonne2Creo server autostart at logon' -Force"

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to register task.
    echo   If this was denied, right-click this .bat and select "Run as administrator".
    echo   Or run: schtasks /create /tn "Cloisonne2Creo" /xml "task.xml" /f
    pause
    exit /b 1
)

echo.
echo Done. Task "Cloisonne2Creo" installed.
echo   Trigger : At log on
echo   Action  : %PYTHON_EXE% main.py (in %PROJECT_ROOT%)
echo   Restart : 1min x 5 on failure (Windows min interval)
echo.
echo The server will auto-start next time you log in.
echo To verify: schtasks /query /tn "Cloisonne2Creo"
echo To remove: launcher\uninstall_task.bat
pause
