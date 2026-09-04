@echo off
title Cloisonne2Creo V2.2
echo ============================================
echo   Cloisonne2Creo - V2.2 Line Art Engineering
echo ============================================
echo.

cd /d "%~dp0"

set "PYTHON_CMD="

rem Try Python 3.12 full path first (deps installed here)
set "P312=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"
if exist "%P312%" (
    set "PYTHON_CMD=%P312%"
    goto :python_found
)

rem Try py launcher
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    goto :python_found
)

rem Try default python
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_found
)

echo [ERROR] Python not found. Please install Python 3.9+
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:python_found
echo [1/3] Python: %PYTHON_CMD%
%PYTHON_CMD% --version

echo [2/3] Checking dependencies...
%PYTHON_CMD% -c "import fastapi, uvicorn, cv2, numpy, skimage, skan, shapely" >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies, first run may take a few minutes...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency install failed. Check your network.
        pause
        exit /b 1
    )
) else (
    echo Dependencies OK.
)

echo [3/3] Starting server...
echo.
echo ============================================
echo   URL: http://127.0.0.1:8765
echo   Browser will open automatically.
echo   Press Ctrl+C to stop.
echo ============================================
echo.

start "" "http://127.0.0.1:8765"

%PYTHON_CMD% main.py

echo.
echo Server stopped.
pause
