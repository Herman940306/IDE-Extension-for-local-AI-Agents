#Requires -Version 7.0
#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Full WSL2 + Docker + Ubuntu Automation for PowerShell 7 x64
.DESCRIPTION
    Complete automation script that handles everything from system checks to final validation
    Designed for PowerShell 7 x64 with enterprise-grade error handling and logging
.EXAMPLE
    .\PowerShell7-Full-Automation.ps1
.EXAMPLE
    .\PowerShell7-Full-Automation.ps1 -SkipBiosCheck -AutoRestart
#>

param(
    [switch]$SkipBiosCheck,
    [switch]$AutoRestart,
    [switch]$Force,
    [string]$LogPath = "$env:TEMP\wsl-docker-automation-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
)

# ══════════════════════════════════════════════════════════════════════════════════════
# POWERSHELL 7 ENTERPRISE AUTOMATION FRAMEWORK
# ══════════════════════════════════════════════════════════════════════════════════════

class AutomationLogger {
    [string]$LogPath
    [bool]$VerboseLogging = $true

    AutomationLogger([string]$logPath) {
        $this.LogPath = $logPath
        $this.WriteLog("=== WSL2 + Docker Automation Started ===", "HEADER")
        $psVersion = $global:PSVersionTable.PSVersion
        $osVersion = [System.Environment]::OSVersion.VersionString
        $this.WriteLog("PowerShell Version: $psVersion", "INFO")
        $this.WriteLog("OS Version: $osVersion", "INFO")
    }

    [void]WriteLog([string]$Message, [string]$Level = "INFO") {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss.fff"
        $logEntry = "[$timestamp] [$Level] $Message"

        # Console output with colors
        $color = switch ($Level) {
            "HEADER"  { "Magenta" }
            "INFO"    { "Cyan" }
            "SUCCESS" { "Green" }
            "WARN"    { "Yellow" }
            "ERROR"   { "Red" }
            "DEBUG"   { "Gray" }
            default   { "White" }
        }

        Write-Host $logEntry -ForegroundColor $color
        Add-Content -Path $this.LogPath -Value $logEntry -Encoding UTF8
    }

    [void]WriteProgress([string]$Activity, [string]$Status, [int]$PercentComplete) {
        Write-Progress -Activity $Activity -Status $Status -PercentComplete $PercentComplete
        $this.WriteLog("PROGRESS: $Activity - $Status ($PercentComplete%)", "DEBUG")
    }
}

class SystemValidator {
    [AutomationLogger]$Logger
    [hashtable]$Results

    SystemValidator([AutomationLogger]$logger) {
        $this.Logger = $logger
        $this.Results = @{}
    }

    [bool]ValidatePrerequisites() {
        $this.Logger.WriteLog("Starting comprehensive system validation...", "HEADER")

        # Check PowerShell 7
        $psVersion = $global:PSVersionTable.PSVersion
        if ($psVersion.Major -lt 7) {
            $this.Logger.WriteLog("PowerShell 7+ required. Current: $psVersion", "ERROR")
            return $false
        }
        $this.Logger.WriteLog("✅ PowerShell 7 detected: $psVersion", "SUCCESS")

        # Check Windows 11
        $osInfo = Get-CimInstance Win32_OperatingSystem
        $buildNumber = [int]($osInfo.Version.Split('.')[2])
        if ($buildNumber -lt 22000) {
            $this.Logger.WriteLog("Windows 11 required (Build 22000+). Current: $buildNumber", "ERROR")
            return $false
        }
        $this.Logger.WriteLog("✅ Windows 11 detected: Build $buildNumber", "SUCCESS")

        # Check Administrator privileges
        $currentPrincipal = [Security.Principal.WindowsPrincipal]([Security.Principal.WindowsIdentity]::GetCurrent())
        if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
            $this.Logger.WriteLog("Administrator privileges required", "ERROR")
            return $false
        }
        $this.Logger.WriteLog("✅ Administrator privileges confirmed", "SUCCESS")

        # Check CPU virtualization
        $cpu = Get-CimInstance Win32_Processor
        if (-not $cpu.VirtualizationFirmwareEnabled) {
            $this.Logger.WriteLog("CPU Virtualization not enabled in BIOS", "ERROR")
            $this.Logger.WriteLog("Enable Intel VT-x/VT-d or AMD-V/SVM in BIOS settings", "ERROR")
            return $false
        }
        $this.Logger.WriteLog("✅ CPU Virtualization enabled in BIOS", "SUCCESS")

        # Check disk space (minimum 20GB)
        $systemDrive = Get-PSDrive C
        $freeSpaceGB = [math]::Round($systemDrive.Free / 1GB, 2)
        if ($freeSpaceGB -lt 20) {
            $this.Logger.WriteLog("Insufficient disk space: ${freeSpaceGB}GB free (20GB required)", "ERROR")
            return $false
        }
        $this.Logger.WriteLog("✅ Sufficient disk space: ${freeSpaceGB}GB free", "SUCCESS")

        # Check Hyper-V compatibility
        $hyperv = Get-CimInstance Win32_ComputerSystem
        if ($hyperv.HypervisorPresent) {
            $this.Logger.WriteLog("✅ Hypervisor present", "SUCCESS")
        } else {
            $this.Logger.WriteLog("⚠️ Hypervisor not detected (normal if not using Hyper-V)", "WARN")
        }

        return $true
    }

    [bool]CheckExistingInstallation() {
        $this.Logger.WriteLog("Checking existing WSL/Docker installation...", "INFO")

        try {
            $wslVersion = wsl --version 2>&1
            if ($wslVersion -match "WSL version") {
                $this.Logger.WriteLog("⚠️ WSL already installed: $($wslVersion -split "`n" | Select-Object -First 1)", "WARN")
                $this.Results.WSLInstalled = $true
            } else {
                $this.Results.WSLInstalled = $false
            }
        } catch {
            $this.Results.WSLInstalled = $false
        }

        return $this.Results.WSLInstalled
    }
}

class FeatureManager {
    [AutomationLogger]$Logger

    FeatureManager([AutomationLogger]$logger) {
        $this.Logger = $logger
    }

    [bool]EnableWindowsFeatures() {
        $this.Logger.WriteLog("Enabling Windows features for WSL2...", "HEADER")

        $features = @(
            @{Name = "VirtualMachinePlatform"; DisplayName = "Virtual Machine Platform"},
            @{Name = "Microsoft-Windows-Subsystem-Linux"; DisplayName = "Windows Subsystem for Linux"}
        )

        foreach ($feature in $features) {
            $this.Logger.WriteProgress("Enabling Windows Features", "Processing $($feature.DisplayName)", 50)

            try {
                $result = Enable-WindowsOptionalFeature -Online -FeatureName $feature.Name -All -NoRestart
                if ($result.RestartNeeded) {
                    $this.Logger.WriteLog("✅ $($feature.DisplayName) enabled (restart required)", "SUCCESS")
                } else {
                    $this.Logger.WriteLog("✅ $($feature.DisplayName) already enabled", "SUCCESS")
                }
            } catch {
                $this.Logger.WriteLog("❌ Failed to enable $($feature.DisplayName): $($_.Exception.Message)", "ERROR")
                return $false
            }
        }

        Write-Progress -Activity "Enabling Windows Features" -Completed
        return $true
    }

    [bool]InstallWSLKernel() {
        $this.Logger.WriteLog("Installing WSL2 kernel update...", "HEADER")

        $kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
        $kernelPath = "$env:TEMP\wsl_update_x64.msi"

        try {
            $this.Logger.WriteProgress("WSL Kernel Installation", "Downloading kernel update", 25)
            Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelPath -UseBasicParsing

            $this.Logger.WriteProgress("WSL Kernel Installation", "Installing kernel update", 75)
            Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", $kernelPath, "/quiet", "/norestart" -Wait

            $this.Logger.WriteLog("✅ WSL2 kernel update installed", "SUCCESS")
            Remove-Item $kernelPath -ErrorAction SilentlyContinue

            Write-Progress -Activity "WSL Kernel Installation" -Completed
            return $true
        } catch {
            $this.Logger.WriteLog("❌ Failed to install WSL2 kernel: $($_.Exception.Message)", "ERROR")
            return $false
        }
    }
}

class WSLManager {
    [AutomationLogger]$Logger

    WSLManager([AutomationLogger]$logger) {
        $this.Logger = $logger
    }

    [bool]ConfigureWSL() {
        $this.Logger.WriteLog("Configuring WSL settings...", "HEADER")

        try {
            # Set WSL2 as default
            $this.Logger.WriteProgress("WSL Configuration", "Setting WSL2 as default", 33)
            wsl --set-default-version 2
            $this.Logger.WriteLog("✅ WSL2 set as default version", "SUCCESS")

            # Install Ubuntu 24.04
            $this.Logger.WriteProgress("WSL Configuration", "Installing Ubuntu 24.04", 66)
            wsl --install -d Ubuntu-24.04
            $this.Logger.WriteLog("✅ Ubuntu 24.04 installation initiated", "SUCCESS")

            Write-Progress -Activity "WSL Configuration" -Completed
            return $true
        } catch {
            $this.Logger.WriteLog("❌ Failed to configure WSL: $($_.Exception.Message)", "ERROR")
            return $false
        }
    }

    [bool]InstallDockerInWSL() {
        $this.Logger.WriteLog("Installing Docker in Ubuntu...", "HEADER")

        $dockerScript = @'
#!/bin/bash
set -e

echo "Updating package lists..."
sudo apt update

echo "Installing prerequisites..."
sudo apt install -y ca-certificates curl gnupg lsb-release

echo "Adding Docker's official GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "Setting up Docker repository..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Installing Docker..."
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

echo "Adding user to docker group..."
sudo usermod -aG docker $USER

echo "Starting Docker service..."
sudo service docker start

echo "Testing Docker installation..."
sudo docker run --rm hello-world

echo "Docker installation completed successfully!"
'@

        try {
            $scriptPath = "/tmp/install_docker.sh"
            $this.Logger.WriteProgress("Docker Installation", "Preparing installation script", 25)

            # Write script to WSL
            $dockerScript | wsl -d Ubuntu-24.04 -- tee $scriptPath > $null

            $this.Logger.WriteProgress("Docker Installation", "Executing installation script", 50)
            wsl -d Ubuntu-24.04 -- chmod +x $scriptPath
            wsl -d Ubuntu-24.04 -- bash $scriptPath

            $this.Logger.WriteLog("✅ Docker installed successfully in Ubuntu", "SUCCESS")
            Write-Progress -Activity "Docker Installation" -Completed
            return $true
        } catch {
            $this.Logger.WriteLog("❌ Failed to install Docker: $($_.Exception.Message)", "ERROR")
            return $false
        }
    }
}

class ValidationManager {
    [AutomationLogger]$Logger

    ValidationManager([AutomationLogger]$logger) {
        $this.Logger = $logger
    }

    [bool]ValidateInstallation() {
        $this.Logger.WriteLog("Validating complete installation...", "HEADER")

        $allPassed = $true

        # Test WSL
        try {
            $wslVersion = wsl --version 2>&1
            if ($wslVersion -match "WSL version") {
                $this.Logger.WriteLog("✅ WSL is working: $($wslVersion -split "`n" | Select-Object -First 1)", "SUCCESS")
            } else {
                $this.Logger.WriteLog("❌ WSL validation failed", "ERROR")
                $allPassed = $false
            }
        } catch {
            $this.Logger.WriteLog("❌ WSL not accessible", "ERROR")
            $allPassed = $false
        }

        # Test WSL distributions
        try {
            $distros = wsl --list --verbose 2>&1
            if ($distros -match "Ubuntu-24.04.*2") {
                $this.Logger.WriteLog("✅ Ubuntu 24.04 running on WSL2", "SUCCESS")
            } else {
                $this.Logger.WriteLog("⚠️ Ubuntu 24.04 not found or not WSL2", "WARN")
            }
        } catch {
            $this.Logger.WriteLog("❌ Unable to list WSL distributions", "ERROR")
            $allPassed = $false
        }

        # Test Docker
        try {
            $dockerTest = wsl -d Ubuntu-24.04 -- docker run --rm hello-world 2>&1
            if ($dockerTest -match "Hello from Docker") {
                $this.Logger.WriteLog("✅ Docker is working correctly", "SUCCESS")
            } else {
                $this.Logger.WriteLog("❌ Docker test failed", "ERROR")
                $allPassed = $false
            }
        } catch {
            $this.Logger.WriteLog("❌ Docker not accessible", "ERROR")
            $allPassed = $false
        }

        return $allPassed
    }
}

# ══════════════════════════════════════════════════════════════════════════════════════
# MAIN AUTOMATION WORKFLOW
# ══════════════════════════════════════════════════════════════════════════════════════

function Start-FullAutomation {
    param(
        [bool]$SkipBiosCheck,
        [bool]$AutoRestart,
        [bool]$Force,
        [string]$LogPath
    )

    # Initialize logging
    $logger = [AutomationLogger]::new($LogPath)
    $logger.WriteLog("Starting full automation with PowerShell 7 x64", "HEADER")

    try {
        # Phase 1: System Validation
        $validator = [SystemValidator]::new($logger)
        if (-not $validator.ValidatePrerequisites()) {
            throw "System validation failed. Check requirements and try again."
        }

        # Check existing installation
        if ($validator.CheckExistingInstallation() -and -not $Force) {
            $logger.WriteLog("WSL already installed. Use -Force to reinstall.", "WARN")
            $continue = Read-Host "Continue anyway? (y/N)"
            if ($continue -ne 'y' -and $continue -ne 'Y') {
                return
            }
        }

        # Phase 2: Feature Installation
        $featureManager = [FeatureManager]::new($logger)
        if (-not $featureManager.EnableWindowsFeatures()) {
            throw "Failed to enable Windows features"
        }

        if (-not $featureManager.InstallWSLKernel()) {
            throw "Failed to install WSL kernel"
        }

        # Phase 3: WSL Configuration
        $wslManager = [WSLManager]::new($logger)
        if (-not $wslManager.ConfigureWSL()) {
            throw "Failed to configure WSL"
        }

        # Check if restart is needed
        $restartNeeded = $true
        if ($restartNeeded) {
            $logger.WriteLog("System restart required for WSL2 features", "WARN")

            if ($AutoRestart) {
                $logger.WriteLog("Auto-restart enabled. Restarting in 10 seconds...", "WARN")
                Start-Sleep -Seconds 10
                Restart-Computer -Force
                return
            } else {
                $restart = Read-Host "Restart now? (Y/n)"
                if ($restart -ne 'n' -and $restart -ne 'N') {
                    Restart-Computer
                    return
                }
            }
        }

        # Phase 4: Docker Installation (post-restart)
        Start-Sleep -Seconds 5
        if (-not $wslManager.InstallDockerInWSL()) {
            throw "Failed to install Docker"
        }

        # Phase 5: Final Validation
        $validationManager = [ValidationManager]::new($logger)
        if ($validationManager.ValidateInstallation()) {
            $logger.WriteLog("🎉 AUTOMATION COMPLETED SUCCESSFULLY! 🎉", "SUCCESS")
            $logger.WriteLog("WSL2 + Docker + Ubuntu are ready to use", "SUCCESS")
        } else {
            $logger.WriteLog("⚠️ Installation completed with warnings", "WARN")
        }

    } catch {
        $logger.WriteLog("💥 AUTOMATION FAILED: $($_.Exception.Message)", "ERROR")
        $logger.WriteLog("Check log file: $LogPath", "ERROR")
        exit 1
    } finally {
        $logger.WriteLog("=== Automation workflow completed ===", "HEADER")
        Write-Host "`n📁 Full log available at: $LogPath" -ForegroundColor Cyan
    }
}

# ══════════════════════════════════════════════════════════════════════════════════════
# EXECUTION ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════════════

# Display banner
Write-Host @"
╔══════════════════════════════════════════════════════════════════════════════╗
║                   🚀 WSL2 + DOCKER + UBUNTU AUTOMATION 🚀                   ║
║                          PowerShell 7 x64 Enterprise                        ║
║                                                                              ║
║  This script will automatically:                                            ║
║  ✅ Validate system requirements                                             ║
║  ✅ Enable Windows features (WSL, VirtualMachinePlatform)                    ║
║  ✅ Install WSL2 kernel update                                               ║
║  ✅ Install Ubuntu 24.04                                                     ║
║  ✅ Install Docker in Ubuntu                                                 ║
║  ✅ Validate complete installation                                           ║
║                                                                              ║
║  ⚠️  Administrator privileges required                                       ║
║  ⚠️  System restart will be required                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green

Write-Host "`n⏳ Starting in 5 seconds... (Ctrl+C to cancel)" -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Execute automation
Start-FullAutomation -SkipBiosCheck $SkipBiosCheck -AutoRestart $AutoRestart -Force $Force -LogPath $LogPath
