@echo off
REM PowerShell 7 WSL+Docker Automation Launcher
REM Ensures admin privileges and PowerShell 7 execution

echo ========================================
echo PowerShell 7 WSL+Docker Automation
echo ========================================
echo.
echo Checking PowerShell 7 installation...

REM Check if PowerShell 7 is installed
if exist "C:\Program Files\PowerShell\7\pwsh.exe" (
    echo PowerShell 7 found at: C:\Program Files\PowerShell\7\pwsh.exe
) else (
    echo.
    echo ERROR: PowerShell 7 is not installed or not in PATH
    echo.
    echo Please install PowerShell 7 first:
    echo 1. Download from: https://github.com/PowerShell/PowerShell/releases
    echo 2. Or use winget: winget install Microsoft.PowerShell
    echo.
    pause
    exit /b 1
)

echo PowerShell 7 found at: C:\Program Files\PowerShell\7\pwsh.exe
echo.
echo This will run the full automation:
echo  * System validation
echo  * Windows features enablement
echo  * WSL2 + Ubuntu 24.04 installation
echo  * Docker installation
echo  * Complete validation
echo.
echo Your system will restart automatically when needed.
echo.
echo Press any key to start automation or Ctrl+C to cancel...
pause >nul

echo.
echo Launching PowerShell 7 automation as Administrator...
echo.

REM Launch PowerShell 7 with admin privileges using full path
"C:\Program Files\PowerShell\7\pwsh.exe" -Command "Start-Process 'C:\Program Files\PowerShell\7\pwsh.exe' -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0PowerShell7-Full-Automation.ps1\"' -Verb RunAs"

echo.
echo If a PowerShell 7 window opened with UAC prompt, the automation is running.
echo This command prompt window can be closed.
echo.
pause