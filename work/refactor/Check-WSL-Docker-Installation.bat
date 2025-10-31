@echo off
REM WSL2 & Docker Installation Validator - Batch Launcher
REM Checks if everything is installed correctly

echo =============================================
echo WSL2 ^& Docker Installation Validator
echo =============================================
echo.
echo This will check if WSL2 and Docker are installed correctly:
echo  - WSL installation and version
echo  - WSL distributions (Ubuntu, etc.)
echo  - VirtualMachinePlatform feature
echo  - Windows Subsystem for Linux feature
echo  - Hypervisor status
echo  - Docker in WSL
echo  - CPU virtualization in BIOS
echo.
echo Press any key to start validation...
pause >nul

cd /d "%~dp0"
powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0scripts\Validate-WSL-Docker-Installation.ps1"
