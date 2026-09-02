@echo off
title 掐丝珐琅图片转Creo曲线生成器 V2.0
echo ============================================
echo   掐丝珐琅图片转 Creo 曲线生成器 V2.0
echo ============================================
echo.

cd /d "%~dp0"

rem 定位Python: 优先完整路径Python 3.12(依赖都装在那里)
set "PYTHON_CMD="
set "P312=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe"

if exist "%P312%" (
    set "PYTHON_CMD=%P312%"
    goto :python_found
)

py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    goto :python_found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_found
)

echo [错误] 未找到Python，请先安装Python 3.9+
pause
exit /b 1

:python_found
echo [1/3] 使用Python: %PYTHON_CMD%
%PYTHON_CMD% --version

echo [2/3] 检查依赖...
%PYTHON_CMD% -c "import fastapi, uvicorn, cv2, numpy" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    %PYTHON_CMD% -m pip install -r requirements.txt
)

echo [3/3] 启动服务器...
echo.
echo 服务器地址: http://127.0.0.1:8765
echo 浏览器将自动打开，如未打开请手动访问
echo 按 Ctrl+C 停止服务器
echo.

start "" "http://127.0.0.1:8765"

%PYTHON_CMD% main.py

pause