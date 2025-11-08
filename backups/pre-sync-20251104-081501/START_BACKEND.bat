@echo off
REM AuraIA Backend Startup Script
REM Creator: Herman Swanepoel
REM Date: October 14, 2025

echo ========================================
echo  AuraIA Backend - Starting...
echo  Creator: Herman Swanepoel
echo ========================================
echo.

cd /d "%~dp0backend"

echo [1/3] Activating Python environment...
call ..\.venv_new\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Please ensure .venv_new exists
    pause
    exit /b 1
)

echo [2/3] Checking Ollama...
ollama list >nul 2>&1
if errorlevel 1 (
    echo WARNING: Ollama is not running or not installed
    echo.
    echo Please start Ollama:
    echo   Option 1: Run 'ollama serve' in another terminal
    echo   Option 2: Ensure Ollama service is running
    echo.
    echo Press any key to continue anyway...
    pause >nul
)

echo [3/3] Starting AuraIA Backend...
echo.
echo ========================================
echo  Backend will start on:
echo  http://localhost:8001
echo  
echo  API Docs:
echo  http://localhost:8001/docs
echo  
echo  Press CTRL+C to stop
echo ========================================
echo.

python run.py

pause
