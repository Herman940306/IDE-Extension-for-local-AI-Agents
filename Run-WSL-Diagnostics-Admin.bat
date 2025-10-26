@echo off
REM WSL Docker Setup - Admin Launcher
REM This batch file launches PowerShell as Administrator and runs diagnostics

echo ========================================
echo WSL + Docker Setup - Admin Launcher
echo ========================================
echo.
echo This will launch PowerShell as Administrator
echo and run full system diagnostics.
echo.
echo Press any key to continue...
pause >nul

cd /d "%~dp0"
powershell -Command "Start-Process pwsh -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', '%~dp0scripts\WSL-Docker-SafeMode-Recovery.ps1', '-Mode', 'FullDiagnostics' -Verb RunAs"
