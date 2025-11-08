@echo off
REM WSL2 VirtualMachinePlatform Crash Fixer - Automated Batch
REM For Windows 11 Pro (Build 26200), Intel/MSI/AMIBIOS
REM Created by: GitHub Copilot
REM Date: 2025-10-19

:: Step 1: Prompt for BIOS/UEFI update and virtualization
cls
echo =============================================
echo WSL2 VirtualMachinePlatform Crash Fixer
echo =============================================
echo.
echo [1] Ensure BIOS/UEFI is updated and virtualization is enabled (Intel VT-x, VT-d).
echo     - Reboot and enter BIOS (DEL/F2/F10) and check virtualization settings.
echo     - Update BIOS from MSI if available.
echo.
pause

:: Step 2: Prompt for Windows Update
cls
echo =============================================
echo [2] Install ALL Windows updates (including optional).
echo     - Go to Settings > Windows Update > Advanced options > Optional updates.
echo     - Download and install latest drivers from MSI and Intel.
echo.
pause

:: Step 3: Run PowerShell Fix Script (automates DISM, registry, MSI install)
powershell -Command "Start-Process pwsh -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-File', '%~dp0scripts\WSL2_VirtualMachinePlatform_Fix.ps1' -Verb RunAs"

:: Step 4: Final manual steps
echo =============================================
echo [3] After script completes, verify BIOS virtualization settings again if issues persist.
echo [4] If system still crashes, boot into Safe Mode and run this batch file again.
echo [5] For integrated graphics, update GPU drivers and check UMA Frame Buffer Size in BIOS.
echo [6] Disable Core Isolation > Memory Integrity in Windows Security if enabled.
echo.
echo [7] After all steps, run:
echo     wsl --set-default-version 2
echo     wsl --list --verbose
echo     (to verify WSL2 is working)
echo.
pause
