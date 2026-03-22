@echo off
title IceCat Show Companion v3.0
cd /d "%~dp0"

echo.
echo  =============================================
echo   IceCat Show Companion v3.0
echo   The Chill With IceCat  -  prankcast.com/icecat
echo  =============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found.
    echo  Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)

echo  Checking dependencies...
pip install -r requirements.txt --quiet --disable-pip-version-check

echo  Launching...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo  IceCat Companion exited with an error.
    echo  Check logs at: %USERPROFILE%\IceCatCompanion\logs\icecat.log
    pause
)
