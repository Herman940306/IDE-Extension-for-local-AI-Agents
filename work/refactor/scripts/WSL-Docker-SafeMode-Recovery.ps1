# WSL + Docker Safe Mode Recovery Script
# Project Creator: Herman Swanepoel
# Version: 1.0-ENTERPRISE
# Date: 2025-10-19
#
# AURA-DEV GODMODE - DEVOPS MODE
# Safe mode recovery for systems experiencing crashes during Virtual Machine Platform enablement

#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Safe mode recovery script for WSL/Docker installation crashes
.DESCRIPTION
    Handles systems that crash when enabling Virtual Machine Platform.
    Provides gradual enablement with BIOS/UEFI validation and rollback capabilities.
.EXAMPLE
    .\WSL-Docker-SafeMode-Recovery.ps1 -Mode DiagnoseBIOS
.EXAMPLE
    .\WSL-Docker-SafeMode-Recovery.ps1 -Mode SafeEnable
.EXAMPLE
    .\WSL-Docker-SafeMode-Recovery.ps1 -Mode DisableAndRecover
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("DiagnoseBIOS", "SafeEnable", "DisableAndRecover", "CreateRestorePoint", "FullDiagnostics")]
    [string]$Mode = "FullDiagnostics",

    [Parameter(Mandatory=$false)]
    [string]$LogPath = "$env:TEMP\wsl-safemode-recovery.log"
)

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════

function Write-Log {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,

        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS", "CRITICAL")]
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"

    $color = switch ($Level) {
        "INFO"     { "Cyan" }
        "WARN"     { "Yellow" }
        "ERROR"    { "Red" }
        "SUCCESS"  { "Green" }
        "CRITICAL" { "Magenta" }
    }

    Write-Host $logEntry -ForegroundColor $color
    Add-Content -Path $LogPath -Value $logEntry
}

# ═══════════════════════════════════════════════════════════════════════════
# BIOS/UEFI DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

function Test-VirtualizationSupport {
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    Write-Log "VIRTUALIZATION DIAGNOSTICS" -Level INFO
    Write-Log "═══════════════════════════════════════════════" -Level INFO

    $issues = @()

    # Check processor virtualization capability
    try {
        $cpu = Get-CimInstance -ClassName Win32_Processor
        $vmCapable = $cpu.VirtualizationFirmwareEnabled

        if ($vmCapable) {
            Write-Log "✅ CPU Virtualization: ENABLED in BIOS" -Level SUCCESS
        } else {
            Write-Log "❌ CPU Virtualization: DISABLED in BIOS" -Level ERROR
            $issues += "CPU virtualization is disabled in BIOS/UEFI"
        }
    } catch {
        Write-Log "⚠️ Unable to detect CPU virtualization status" -Level WARN
    }

    # Check Hyper-V status
    try {
        $hyperv = Get-CimInstance -ClassName Win32_ComputerSystem
        if ($hyperv.HypervisorPresent) {
            Write-Log "✅ Hyper-V: Present and running" -Level SUCCESS
        } else {
            Write-Log "⚠️ Hyper-V: Not detected" -Level WARN
            $issues += "Hyper-V hypervisor not present"
        }
    } catch {
        Write-Log "⚠️ Unable to detect Hyper-V status" -Level WARN
    }

    # Check Windows version
    $os = Get-CimInstance Win32_OperatingSystem
    $build = [int]$os.BuildNumber

    if ($build -ge 19041) {
        Write-Log "✅ Windows Build: $build (WSL2 compatible)" -Level SUCCESS
    } else {
        Write-Log "❌ Windows Build: $build (requires 19041 or higher)" -Level ERROR
        $issues += "Windows version too old for WSL2"
    }

    # Check SLAT (Second Level Address Translation)
    try {
        $slat = (Get-CimInstance -ClassName Win32_Processor).SecondLevelAddressTranslationExtensions
        if ($slat) {
            Write-Log "✅ SLAT (Second Level Address Translation): Supported" -Level SUCCESS
        } else {
            Write-Log "❌ SLAT: Not supported by CPU" -Level ERROR
            $issues += "SLAT not supported (required for Hyper-V)"
        }
    } catch {
        Write-Log "⚠️ Unable to detect SLAT support" -Level WARN
    }

    # Check Data Execution Prevention (DEP)
    try {
        $dep = (Get-CimInstance -ClassName Win32_OperatingSystem).DataExecutionPrevention_Available
        if ($dep) {
            Write-Log "✅ DEP (Data Execution Prevention): Available" -Level SUCCESS
        } else {
            Write-Log "❌ DEP: Not available" -Level ERROR
            $issues += "DEP not available"
        }
    } catch {
        Write-Log "⚠️ Unable to detect DEP status" -Level WARN
    }

    # Check if running in VM
    $manufacturer = (Get-CimInstance -ClassName Win32_ComputerSystem).Manufacturer
    if ($manufacturer -match "VMware|Virtual|QEMU|Xen") {
        Write-Log "⚠️ Running in Virtual Machine: $manufacturer" -Level WARN
        Write-Log "   Nested virtualization may not be supported" -Level WARN
        $issues += "Running inside a virtual machine (nested virtualization required)"
    } else {
        Write-Log "✅ Physical Hardware: $manufacturer" -Level SUCCESS
    }

    # Check BIOS info
    try {
        $bios = Get-CimInstance -ClassName Win32_BIOS
        Write-Log "BIOS Version: $($bios.SMBIOSBIOSVersion)" -Level INFO
        Write-Log "BIOS Date: $($bios.ReleaseDate)" -Level INFO
    } catch {
        Write-Log "⚠️ Unable to retrieve BIOS information" -Level WARN
    }

    Write-Log "═══════════════════════════════════════════════" -Level INFO

    if ($issues.Count -gt 0) {
        Write-Log "`n⚠️ ISSUES DETECTED:" -Level WARN
        foreach ($issue in $issues) {
            Write-Log "  • $issue" -Level WARN
        }
        return $false
    } else {
        Write-Log "`n✅ All virtualization checks passed!" -Level SUCCESS
        return $true
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS FEATURES DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

function Get-WindowsFeatureStatus {
    Write-Log "`nChecking Windows Features status..." -Level INFO

    $features = @(
        "Microsoft-Windows-Subsystem-Linux",
        "VirtualMachinePlatform",
        "Microsoft-Hyper-V",
        "Microsoft-Hyper-V-All",
        "HypervisorPlatform"
    )

    foreach ($feature in $features) {
        try {
            $state = dism.exe /online /Get-FeatureInfo /FeatureName:$feature 2>&1

            if ($state -match "State : Enabled") {
                Write-Log "✅ ${feature}: ENABLED" -Level SUCCESS
            } elseif ($state -match "State : Disabled") {
                Write-Log "⚠️ ${feature}: DISABLED" -Level WARN
            } else {
                Write-Log "❓ ${feature}: UNKNOWN or NOT AVAILABLE" -Level INFO
            }
        } catch {
            Write-Log "❓ ${feature}: Unable to check status" -Level INFO
        }
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# SAFE ENABLEMENT WITH ROLLBACK
# ═══════════════════════════════════════════════════════════════════════════

function Enable-SafeVirtualization {
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    Write-Log "SAFE VIRTUALIZATION ENABLEMENT" -Level INFO
    Write-Log "═══════════════════════════════════════════════" -Level INFO

    # Step 1: Create system restore point
    Write-Log "`n[STEP 1] Creating System Restore Point..." -Level INFO
    try {
        Enable-ComputerRestore -Drive "C:\"
        Checkpoint-Computer -Description "Pre-WSL2-Installation" -RestorePointType "MODIFY_SETTINGS"
        Write-Log "✅ Restore point created successfully" -Level SUCCESS
    } catch {
        Write-Log "⚠️ Failed to create restore point: $($_.Exception.Message)" -Level WARN
        $continue = Read-Host "Continue without restore point? (Y/N)"
        if ($continue -ne 'Y') {
            return $false
        }
    }

    # Step 2: Update Windows first
    Write-Log "`n[STEP 2] Checking Windows Updates..." -Level INFO
    Write-Log "Please ensure Windows is fully updated before proceeding." -Level WARN
    Write-Log "Run: Settings > Windows Update > Check for updates" -Level INFO
    $updated = Read-Host "Have you installed all Windows updates? (Y/N)"
    if ($updated -ne 'Y') {
        Write-Log "Please update Windows first, then run this script again." -Level ERROR
        return $false
    }

    # Step 3: Update drivers
    Write-Log "`n[STEP 3] Driver Update Check..." -Level INFO
    Write-Log "Ensure chipset and virtualization drivers are up to date." -Level WARN
    Write-Log "Visit your PC manufacturer's website to download latest drivers." -Level INFO
    $driversUpdated = Read-Host "Have you updated all drivers? (Y/N)"
    if ($driversUpdated -ne 'Y') {
        Write-Log "⚠️ Proceeding without driver update confirmation..." -Level WARN
    }

    # Step 4: Enable WSL feature first (less likely to cause crash)
    Write-Log "`n[STEP 4] Enabling WSL feature (safe)..." -Level INFO
    try {
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
        Write-Log "✅ WSL feature enabled" -Level SUCCESS
    } catch {
        Write-Log "❌ Failed to enable WSL feature" -Level ERROR
        return $false
    }

    # Step 5: Enable Virtual Machine Platform (potential crash point)
    Write-Log "`n[STEP 5] Enabling Virtual Machine Platform..." -Level WARN
    Write-Log "⚠️ CRITICAL: This step may cause system to crash on incompatible systems" -Level CRITICAL
    Write-Log "If system crashes:" -Level WARN
    Write-Log "  1. Boot into Safe Mode (Shift + Restart)" -Level INFO
    Write-Log "  2. Run this script with -Mode DisableAndRecover" -Level INFO
    Write-Log "  3. Check BIOS settings for virtualization" -Level INFO

    $proceed = Read-Host "`nProceed with Virtual Machine Platform enablement? (Y/N)"
    if ($proceed -ne 'Y') {
        Write-Log "Operation cancelled by user" -Level INFO
        return $false
    }

    try {
        Write-Log "Enabling Virtual Machine Platform..." -Level INFO
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
        Write-Log "✅ Virtual Machine Platform enabled successfully" -Level SUCCESS

        Write-Log "`n⚠️ IMPORTANT: System restart required" -Level WARN
        Write-Log "During restart, Windows will configure the feature." -Level INFO
        Write-Log "If system hangs or shows black screen:" -Level WARN
        Write-Log "  • Wait 5 minutes for automatic recovery" -Level INFO
        Write-Log "  • If no recovery, force power off and boot to Safe Mode" -Level INFO

        $restart = Read-Host "`nRestart now? (Y/N)"
        if ($restart -eq 'Y') {
            Write-Log "Restarting system in 10 seconds..." -Level INFO
            Start-Sleep -Seconds 10
            Restart-Computer -Force
        } else {
            Write-Log "Please restart manually to complete installation" -Level INFO
        }

        return $true
    } catch {
        Write-Log "❌ Failed to enable Virtual Machine Platform: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# RECOVERY MODE
# ═══════════════════════════════════════════════════════════════════════════

function Disable-VirtualizationFeatures {
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    Write-Log "RECOVERY MODE - DISABLING VIRTUALIZATION FEATURES" -Level WARN
    Write-Log "═══════════════════════════════════════════════" -Level INFO

    # Stop any running WSL instances
    Write-Log "Shutting down WSL..." -Level INFO
    wsl --shutdown 2>&1 | Out-Null

    # Disable Virtual Machine Platform
    Write-Log "Disabling Virtual Machine Platform..." -Level INFO
    try {
        dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart
        Write-Log "✅ Virtual Machine Platform disabled" -Level SUCCESS
    } catch {
        Write-Log "❌ Failed to disable Virtual Machine Platform" -Level ERROR
    }

    # Disable WSL
    Write-Log "Disabling WSL..." -Level INFO
    try {
        dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart
        Write-Log "✅ WSL disabled" -Level SUCCESS
    } catch {
        Write-Log "❌ Failed to disable WSL" -Level ERROR
    }

    Write-Log "`n✅ Features disabled. System should be stable now." -Level SUCCESS
    Write-Log "Next steps:" -Level INFO
    Write-Log "  1. Restart your computer" -Level INFO
    Write-Log "  2. Update BIOS/UEFI firmware from manufacturer" -Level INFO
    Write-Log "  3. Enable CPU virtualization in BIOS settings" -Level INFO
    Write-Log "  4. Update all Windows updates" -Level INFO
    Write-Log "  5. Update chipset drivers" -Level INFO
    Write-Log "  6. Try enabling features again" -Level INFO

    $restart = Read-Host "`nRestart now? (Y/N)"
    if ($restart -eq 'Y') {
        Restart-Computer -Force
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# BIOS CONFIGURATION GUIDE
# ═══════════════════════════════════════════════════════════════════════════

function Show-BIOSConfigurationGuide {
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    Write-Log "BIOS/UEFI CONFIGURATION GUIDE" -Level INFO
    Write-Log "═══════════════════════════════════════════════" -Level INFO

    $manufacturer = (Get-CimInstance -ClassName Win32_ComputerSystem).Manufacturer
    $model = (Get-CimInstance -ClassName Win32_ComputerSystem).Model

    Write-Log "`nSystem: $manufacturer $model" -Level INFO

    Write-Log "`n📋 REQUIRED BIOS SETTINGS:" -Level INFO
    Write-Log "  1. Intel VT-x / AMD-V (Virtualization Technology)" -Level INFO
    Write-Log "  2. VT-d / AMD IOMMU (if available)" -Level INFO
    Write-Log "  3. Secure Boot (may need to be disabled)" -Level INFO

    Write-Log "`n🔧 HOW TO ACCESS BIOS:" -Level INFO
    Write-Log "  1. Restart your computer" -Level INFO
    Write-Log "  2. Press the BIOS key repeatedly during boot" -Level INFO
    Write-Log "     Common keys: F2, F10, F12, Del, Esc" -Level INFO
    Write-Log "     Your system: Check boot screen for prompt" -Level INFO

    Write-Log "`n⚙️ COMMON BIOS PATHS:" -Level INFO

    if ($manufacturer -match "Dell") {
        Write-Log "  Dell Systems:" -Level INFO
        Write-Log "    Advanced > Virtualization > Enable Intel Virtualization Technology" -Level INFO
        Write-Log "    Advanced > Virtualization > Enable VT for Direct I/O" -Level INFO
    } elseif ($manufacturer -match "HP|Hewlett") {
        Write-Log "  HP Systems:" -Level INFO
        Write-Log "    Advanced > System Options > Virtualization Technology > Enabled" -Level INFO
        Write-Log "    Security > Secure Boot Configuration > Disable (if needed)" -Level INFO
    } elseif ($manufacturer -match "Lenovo") {
        Write-Log "  Lenovo Systems:" -Level INFO
        Write-Log "    Configuration > Intel Virtual Technology > Enabled" -Level INFO
        Write-Log "    Security > Secure Boot > Disabled (if needed)" -Level INFO
    } elseif ($manufacturer -match "ASUS") {
        Write-Log "  ASUS Systems:" -Level INFO
        Write-Log "    Advanced > CPU Configuration > Intel Virtualization Technology > Enabled" -Level INFO
        Write-Log "    Advanced > CPU Configuration > SVM Mode > Enabled (AMD)" -Level INFO
    } elseif ($manufacturer -match "MSI") {
        Write-Log "  MSI Systems:" -Level INFO
        Write-Log "    OC > CPU Features > Intel Virtualization Tech > Enabled" -Level INFO
        Write-Log "    OC > CPU Features > SVM Mode > Enabled (AMD)" -Level INFO
    } else {
        Write-Log "  Generic Path (varies by manufacturer):" -Level INFO
        Write-Log "    Advanced > Processor/CPU Configuration > Virtualization" -Level INFO
        Write-Log "    or Security > Virtualization" -Level INFO
        Write-Log "    or System Configuration > Virtualization Technology" -Level INFO
    }

    Write-Log "`n⚠️ IMPORTANT WARNINGS:" -Level WARN
    Write-Log "  • Backup important data before modifying BIOS settings" -Level WARN
    Write-Log "  • Write down current settings before making changes" -Level WARN
    Write-Log "  • Do not interrupt BIOS update process" -Level WARN
    Write-Log "  • Contact manufacturer support if uncertain" -Level WARN

    Write-Log "`n🔄 AFTER BIOS CHANGES:" -Level INFO
    Write-Log "  1. Save and Exit BIOS (usually F10)" -Level INFO
    Write-Log "  2. Allow system to restart" -Level INFO
    Write-Log "  3. Boot into Windows normally" -Level INFO
    Write-Log "  4. Run diagnostics: .\WSL-Docker-SafeMode-Recovery.ps1 -Mode FullDiagnostics" -Level INFO
    Write-Log "  5. If passed, run: .\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup" -Level INFO

    Write-Log "═══════════════════════════════════════════════" -Level INFO
}

# ═══════════════════════════════════════════════════════════════════════════
# FULL DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════

function Start-FullDiagnostics {
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    Write-Log "FULL SYSTEM DIAGNOSTICS FOR WSL2/DOCKER" -Level INFO
    Write-Log "═══════════════════════════════════════════════" -Level INFO

    # System info
    $os = Get-CimInstance Win32_OperatingSystem
    Write-Log "`n📊 SYSTEM INFORMATION:" -Level INFO
    Write-Log "  OS: $($os.Caption)" -Level INFO
    Write-Log "  Build: $($os.BuildNumber)" -Level INFO
    Write-Log "  Architecture: $env:PROCESSOR_ARCHITECTURE" -Level INFO
    Write-Log "  RAM: $([math]::Round($os.TotalVisibleMemorySize / 1MB, 2)) GB" -Level INFO

    # Run virtualization tests
    Write-Log "`n" -Level INFO
    $virtOk = Test-VirtualizationSupport

    # Check Windows features
    Write-Log "`n" -Level INFO
    Get-WindowsFeatureStatus

    # BIOS guide
    Write-Log "`n" -Level INFO
    Show-BIOSConfigurationGuide

    # Final recommendation
    Write-Log "`n═══════════════════════════════════════════════" -Level INFO
    Write-Log "RECOMMENDATIONS:" -Level INFO
    Write-Log "═══════════════════════════════════════════════" -Level INFO

    if ($virtOk) {
        Write-Log "✅ System appears ready for WSL2/Docker installation" -Level SUCCESS
        Write-Log "Next step: Run .\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup" -Level INFO
    } else {
        Write-Log "⚠️ System requires configuration before WSL2/Docker" -Level WARN
        Write-Log "Next steps:" -Level INFO
        Write-Log "  1. Follow BIOS configuration guide above" -Level INFO
        Write-Log "  2. Enable virtualization in BIOS" -Level INFO
        Write-Log "  3. Update Windows and drivers" -Level INFO
        Write-Log "  4. Run diagnostics again to verify" -Level INFO
        Write-Log "  5. Then proceed with installation" -Level INFO
    }

    Write-Log "═══════════════════════════════════════════════" -Level INFO
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

"WSL Docker Safe Mode Recovery Log - $(Get-Date)" | Out-File -FilePath $LogPath -Force

switch ($Mode) {
    "FullDiagnostics" {
        Start-FullDiagnostics
    }
    "DiagnoseBIOS" {
        Test-VirtualizationSupport
        Show-BIOSConfigurationGuide
    }
    "SafeEnable" {
        Enable-SafeVirtualization
    }
    "DisableAndRecover" {
        Disable-VirtualizationFeatures
    }
    "CreateRestorePoint" {
        Write-Log "Creating system restore point..." -Level INFO
        Enable-ComputerRestore -Drive "C:\"
        Checkpoint-Computer -Description "WSL2-Docker-SafePoint" -RestorePointType "MODIFY_SETTINGS"
        Write-Log "✅ Restore point created" -Level SUCCESS
    }
}

Write-Log "`nLog saved to: $LogPath" -Level INFO
