@echo off
setlocal
title Cloisonne2Creo - Update Dependencies
rem ============================================
rem  update.bat - Install/update dependencies (V2.3.1)
rem  First run : creates .venv (Python 3.12) + installs requirements
rem  Later runs: pip install -r requirements.txt (idempotent)
rem ============================================

cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

echo.
echo ============================================
echo   Updating Cloisonne2Creo dependencies
echo ============================================
echo.

rem ---------- Find base Python (Python312 > py -3.12 > python) ----------
set "BASE_PY="
set "P312=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%P312%" (
    set "BASE_PY=%P312%"
    goto :base_found
)
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "BASE_PY=py -3.12"
    goto :base_found
)
python --version >nul 2>&1
if not errorlevel 1 (
    set "BASE_PY=python"
    goto :base_found
)
echo [ERROR] Python not found. Install Python 3.12 from python.org first.
pause
exit /b 1

:base_found
echo Base Python: %BASE_PY%

rem ---------- Create .venv on first run ----------
if not exist "%PROJECT_ROOT%.venv\Scripts\python.exe" (
    echo Creating virtual environment (.venv)...
    %BASE_PY% -m venv "%PROJECT_ROOT%.venv"
    if errorlevel 1 (
        echo [ERROR] venv creation failed.
        pause
        exit /b 1
    )
    echo .venv created.
)

set "VENV_PY=%PROJECT_ROOT%.venv\Scripts\python.exe"
echo Installing requirements into .venv...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Install failed.
    pause
    exit /b 1
)

echo.
echo Done. Dependencies updated.
echo Now run start.bat to launch.
pause
