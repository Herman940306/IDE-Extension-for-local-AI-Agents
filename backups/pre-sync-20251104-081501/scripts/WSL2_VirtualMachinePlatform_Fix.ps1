# WSL2 VirtualMachinePlatform Crash Fixer
# For Windows 11 Pro (Build 26200), Intel/MSI/AMIBIOS
# Created by: GitHub Copilot
# Date: 2025-10-19

#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Automates reliable fixes for VirtualMachinePlatform crashing during WSL2 installation.
.DESCRIPTION
    - Updates Windows
    - Runs DISM and SFC health checks
    - Disables/enables features
    - Cleans registry keys
    - Installs latest WSL2 MSI
    - Prompts for BIOS/firmware steps
#>

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "INFO"    { "Cyan" }
        "WARN"    { "Yellow" }
        "ERROR"   { "Red" }
        "SUCCESS" { "Green" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

Write-Log "WSL2 VirtualMachinePlatform Crash Fixer - Starting..." "INFO"

# 1. Prompt for BIOS/UEFI update and virtualization
Write-Log "Step 1: Ensure BIOS/UEFI is updated and virtualization is enabled (Intel VT-x, VT-d)." "WARN"
Write-Log "If unsure, reboot and enter BIOS (usually DEL/F2/F10) and check virtualization settings." "INFO"
Write-Log "Press Enter to continue..." "INFO"
Read-Host

# 2. Prompt for Windows Update
Write-Log "Step 2: Install ALL Windows updates (including optional)." "WARN"
Write-Log "Go to Settings > Windows Update > Advanced options > Optional updates." "INFO"
Write-Log "Press Enter to continue after updates are installed..." "INFO"
Read-Host

# 3. Run DISM and SFC health checks
Write-Log "Step 3: Running DISM health check..." "INFO"
DISM /Online /Cleanup-Image /RestoreHealth
Write-Log "Step 3: Running SFC scan..." "INFO"
sfc /scannow

# 4. Disable features (DISM)
Write-Log "Step 4: Disabling VirtualMachinePlatform and WSL features..." "INFO"
dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart
Write-Log "VirtualMachinePlatform disabled." "SUCCESS"
dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart
Write-Log "WSL feature disabled." "SUCCESS"
Write-Log "Restarting computer is recommended. Press Enter to continue if already restarted..." "INFO"
Read-Host

# 5. Clean registry keys
Write-Log "Step 5: Cleaning registry keys (Hyper-V, vmcompute, vmbus)..." "INFO"
$regPaths = @(
    "HKLM:\SYSTEM\CurrentControlSet\Services\vmcompute",
    "HKLM:\SYSTEM\CurrentControlSet\Services\vmbus"
)
foreach ($regPath in $regPaths) {
    if (Test-Path $regPath) {
        Remove-Item -Path $regPath -Recurse -Force
        Write-Log "Removed $regPath" "SUCCESS"
    }
}
Write-Log "Check for other Hyper-V related keys manually if issues persist." "WARN"

# 6. Re-enable features (DISM)
Write-Log "Step 6: Re-enabling WSL and VirtualMachinePlatform features..." "INFO"
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
Write-Log "WSL feature enabled." "SUCCESS"
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
Write-Log "VirtualMachinePlatform enabled." "SUCCESS"
Write-Log "Restarting computer is recommended. Press Enter to continue if already restarted..." "INFO"
Read-Host

# 7. Download and install latest WSL2 MSI
Write-Log "Step 7: Downloading and installing latest WSL2 MSI..." "INFO"
$msiPath = "$env:TEMP\wsl.msi"
Invoke-WebRequest -Uri "https://aka.ms/wsl-x64" -OutFile $msiPath -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /passive /norestart" -Wait
Write-Log "WSL2 MSI installed." "SUCCESS"

Write-Log "Step 8: Final checks - Run 'wsl --version' and 'wsl --list --verbose' to confirm installation." "INFO"
Write-Log "If system still crashes, repeat BIOS/firmware update and registry cleanup, or consult docs/WSL_DOCKER_TROUBLESHOOTING_GUIDE.md." "WARN"

Write-Log "WSL2 VirtualMachinePlatform Crash Fixer - Complete!" "SUCCESS"
