@echo off
REM WSL Docker Full Setup - Admin Launcher
REM This batch file launches PowerShell as Administrator and runs full installation

echo ========================================
echo WSL + Docker Full Setup - Admin Launcher
echo ========================================
echo.
echo This will:
echo  1. Clean previous installations
echo  2. Enable Windows features
echo  3. Install WSL2 + Ubuntu 24.04
echo  4. Install Docker in Ubuntu
echo  5. Validate installation
echo.
echo Your system will restart after feature enablement.
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

cd /d "%~dp0"
REM Use robust PowerShell launcher that self-elevates and logs output
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0scripts\Launch-WSL-Install-Elevated.ps1' -Mode 'FullSetup'"

echo.
echo If an elevated PowerShell window opened, follow its prompts. This window will remain here.
echo Press any key to exit this launcher.
pause >nul
