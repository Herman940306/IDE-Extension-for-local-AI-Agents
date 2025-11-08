@echo off
REM WSL Docker Recovery - Admin Launcher (Safe Mode)
REM Use this if system crashed during installation

echo ========================================
echo WSL + Docker Recovery - Safe Mode
echo ========================================
echo.
echo WARNING: Use this only if your system crashed
echo during Virtual Machine Platform enablement.
echo.
echo This will:
echo  - Disable Virtual Machine Platform
echo  - Disable WSL features
echo  - Allow system to boot normally
echo.
echo Run this from SAFE MODE if Windows won't boot normally.
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul

cd /d "%~dp0"
powershell -Command "Start-Process pwsh -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', '%~dp0scripts\WSL-Docker-SafeMode-Recovery.ps1', '-Mode', 'DisableAndRecover' -Verb RunAs"
