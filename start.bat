@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title WSH Quiz Game

cd /d "%~dp0"

echo.
echo  ============================================
echo    WSH Quiz Game  --  Starting server
echo  ============================================
echo.

:: ---------------------------------------------
:: 1. Check Python
:: ---------------------------------------------
echo  [1/3]  Checking Python...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Python not found!
    echo.
    echo  Please install Python 3.8+ from: https://python.org/downloads
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v

for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)

if !PY_MAJOR! LSS 3 goto :bad_version
if !PY_MAJOR! EQU 3 if !PY_MINOR! LSS 8 goto :bad_version
goto :good_version

:bad_version
echo.
echo  [ERROR] Python 3.8 or newer is required.
echo  Found: !PYVER!
echo.
pause
exit /b 1

:good_version
echo         OK  (Python !PYVER!)
echo.

:: ---------------------------------------------
:: 2. Upgrade pip + install requirements
:: ---------------------------------------------
echo  [2/3]  Installing / updating dependencies...
echo.

python -m pip install --upgrade pip -q 2>nul
python -m pip install -r requirements.txt --upgrade -q
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Failed to install dependencies.
    echo  Try manually: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo         OK  (all packages up to date)
echo.

:: ---------------------------------------------
:: 3. Detect local network IP
:: ---------------------------------------------
echo  [3/3]  Detecting network address...

set LOCAL_IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set CANDIDATE=%%a
    set CANDIDATE=!CANDIDATE: =!
    if not "!CANDIDATE:~0,3!"=="127" (
        if not "!CANDIDATE:~0,3!"=="169" (
            if "!LOCAL_IP!"=="" set LOCAL_IP=!CANDIDATE!
        )
    )
)

if "!LOCAL_IP!"=="" set LOCAL_IP=unknown

echo         OK  (!LOCAL_IP!)
echo.

:: ---------------------------------------------
:: Launch
:: ---------------------------------------------
echo  ============================================
echo.
echo    Server is starting on port 8000
echo.
echo    Host (this PC):    http://localhost:8000
echo    Players (phones):  http://!LOCAL_IP!:8000
echo.
echo    Press Ctrl+C to stop the server
echo.
echo  ============================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo  Server stopped.
echo.
pause
