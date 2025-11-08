@echo off
REM WSL2 VirtualMachinePlatform Crash Fixer - Improved Batch
REM For Windows 11 Pro (Build 26200), Intel/MSI/AMIBIOS
REM Created by: GitHub Copilot
REM Date: 2025-10-19

set LOGFILE=%TEMP%\WSL2_VirtualMachinePlatform_Fix.log

:: Step 1: BIOS/UEFI update and virtualization
cls
echo =============================================
echo WSL2 VirtualMachinePlatform Crash Fixer (Improved)
echo =============================================
echo.
echo [STEP 1] BIOS/UEFI & Virtualization
>> %LOGFILE% echo [STEP 1] BIOS/UEFI & Virtualization

echo - Ensure BIOS/UEFI is updated and virtualization is enabled (Intel VT-x, VT-d).
echo - Reboot and enter BIOS (DEL/F2/F10) and check virtualization settings.
echo - Update BIOS from MSI if available.
echo.
pause

:: Step 2: Windows Update & Drivers
cls
echo =============================================
echo [STEP 2] Windows Update & Drivers
>> %LOGFILE% echo [STEP 2] Windows Update & Drivers

echo - Install ALL Windows updates (including optional).
echo - Go to Settings > Windows Update > Advanced options > Optional updates.
echo - Download and install latest drivers from MSI and Intel.
echo.
pause

:: Step 3: Run PowerShell Fix Script (DISM, registry, MSI install)
cls
echo =============================================
echo [STEP 3] Automated Fix Script
>> %LOGFILE% echo [STEP 3] Automated Fix Script

echo - This will:
echo   * Run DISM and SFC health checks
>> %LOGFILE% echo   * Run DISM and SFC health checks

echo   * Disable/re-enable VirtualMachinePlatform and WSL features
>> %LOGFILE% echo   * Disable/re-enable VirtualMachinePlatform and WSL features

echo   * Clean registry keys (vmcompute, vmbus)
>> %LOGFILE% echo   * Clean registry keys (vmcompute, vmbus)

echo   * Download and install latest WSL2 MSI
>> %LOGFILE% echo   * Download and install latest WSL2 MSI

echo - The PowerShell window will stay open after completion so you can review all output.
echo - All actions are logged to: %LOGFILE%
echo.
pause

powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0scripts\WSL2_VirtualMachinePlatform_Fix.ps1"

:: Step 4: Final manual steps
cls
echo =============================================
echo [STEP 4] Final Manual Steps
>> %LOGFILE% echo [STEP 4] Final Manual Steps

echo - After script completes, verify BIOS virtualization settings again if issues persist.
echo - If system still crashes, boot into Safe Mode and run this batch file again.
echo - For integrated graphics, update GPU drivers and check UMA Frame Buffer Size in BIOS.
echo - Disable Core Isolation > Memory Integrity in Windows Security if enabled.
echo.
echo - After all steps, run:
echo     wsl --set-default-version 2
>> %LOGFILE% echo     wsl --set-default-version 2

echo     wsl --list --verbose
>> %LOGFILE% echo     wsl --list --verbose

echo     (to verify WSL2 is working)
echo.
pause
