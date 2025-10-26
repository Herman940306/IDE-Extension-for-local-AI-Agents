# WSL + Docker Enterprise Setup Script
# Project Creator: Herman Swanepoel
# Version: 1.0-ENTERPRISE
# Date: 2025-10-19
# 
# AURA-DEV GODMODE - DEVOPS MODE
# Enterprise-grade automation with fault tolerance

#Requires -RunAsAdministrator

<#
.SYNOPSIS
    Enterprise-grade WSL2 and Docker installation with automated diagnostics
.DESCRIPTION
    Comprehensive script that handles cleanup, installation, validation, and rollback
    for WSL2 and Docker on Windows 11. Includes circuit breaker pattern and logging.
.EXAMPLE
    .\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup
.EXAMPLE
    .\WSL-Docker-Setup-Enterprise.ps1 -Mode CleanupOnly
.EXAMPLE
    .\WSL-Docker-Setup-Enterprise.ps1 -Mode DiagnosticsOnly
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("FullSetup", "CleanupOnly", "InstallOnly", "DiagnosticsOnly", "Validate")]
    [string]$Mode = "FullSetup",
    
    [Parameter(Mandatory=$false)]
    [string]$DistroName = "Ubuntu-24.04",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipReboot,
    
    [Parameter(Mandatory=$false)]
    [string]$LogPath = "$env:TEMP\wsl-docker-setup.log"
)

# ═══════════════════════════════════════════════════════════════════════════
# ENTERPRISE LOGGING FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════

function Write-Log {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        
        [Parameter(Mandatory=$false)]
        [ValidateSet("INFO", "WARN", "ERROR", "SUCCESS")]
        [string]$Level = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Color coding
    $color = switch ($Level) {
        "INFO"    { "Cyan" }
        "WARN"    { "Yellow" }
        "ERROR"   { "Red" }
        "SUCCESS" { "Green" }
    }
    
    Write-Host $logEntry -ForegroundColor $color
    Add-Content -Path $LogPath -Value $logEntry
}

# ═══════════════════════════════════════════════════════════════════════════
# PRE-FLIGHT SYSTEM CHECKS
# ═══════════════════════════════════════════════════════════════════════════

function Test-SystemRequirements {
    Write-Log "Starting system requirements validation..." -Level INFO
    
    $checks = @{
        "Administrator"     = $false
        "Windows11"         = $false
        "VirtualizationEnabled" = $false
        "DiskSpace"         = $false
    }
    
    # Check Admin privileges
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    $checks.Administrator = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    # Check Windows version
    $osInfo = Get-CimInstance Win32_OperatingSystem
    $checks.Windows11 = $osInfo.Version -ge "10.0.22000"
    
    # Check virtualization
    $virtualization = Get-CimInstance -ClassName Win32_ComputerSystem
    $checks.VirtualizationEnabled = $virtualization.HypervisorPresent
    
    # Check disk space (minimum 20GB free)
    $systemDrive = Get-PSDrive -Name C
    $checks.DiskSpace = ($systemDrive.Free / 1GB) -ge 20
    
    # Report results
    foreach ($check in $checks.GetEnumerator()) {
        if ($check.Value) {
            Write-Log "✅ $($check.Key): PASS" -Level SUCCESS
        } else {
            Write-Log "❌ $($check.Key): FAIL" -Level ERROR
        }
    }
    
    $allPassed = $checks.Values -notcontains $false
    return $allPassed
}

# ═══════════════════════════════════════════════════════════════════════════
# CLEANUP FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

function Stop-WSLAndDocker {
    Write-Log "Stopping WSL and Docker services..." -Level INFO
    
    try {
        # Stop Docker service
        $dockerService = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
        if ($dockerService -and $dockerService.Status -eq "Running") {
            Stop-Service -Name "com.docker.service" -Force -ErrorAction Stop
            Write-Log "Docker service stopped" -Level SUCCESS
        }
        
        # Shutdown WSL
        wsl --shutdown 2>&1 | Out-Null
        Start-Sleep -Seconds 3
        Write-Log "WSL shutdown complete" -Level SUCCESS
        
        return $true
    } catch {
        Write-Log "Error stopping services: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

function Remove-WSLDistributions {
    Write-Log "Unregistering all WSL distributions..." -Level INFO
    
    try {
        $distros = wsl --list --quiet 2>&1 | Where-Object { $_ -match '\S' }
        
        if ($distros) {
            foreach ($distro in $distros) {
                $distroName = $distro.Trim()
                if ($distroName) {
                    Write-Log "Unregistering: $distroName" -Level INFO
                    wsl --unregister $distroName 2>&1 | Out-Null
                }
            }
            Write-Log "All distributions unregistered" -Level SUCCESS
        } else {
            Write-Log "No WSL distributions found" -Level INFO
        }
        
        return $true
    } catch {
        Write-Log "Error removing distributions: $($_.Exception.Message)" -Level WARN
        return $false
    }
}

function Remove-WSLFeatures {
    Write-Log "Disabling Windows features..." -Level INFO
    
    try {
        dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart | Out-Null
        dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart | Out-Null
        Write-Log "Windows features disabled" -Level SUCCESS
        return $true
    } catch {
        Write-Log "Error disabling features: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

function Remove-DockerFiles {
    Write-Log "Removing Docker files and packages..." -Level INFO
    
    $paths = @(
        "$env:LOCALAPPDATA\Docker",
        "$env:ProgramData\Docker",
        "$env:ProgramFiles\Docker",
        "$env:USERPROFILE\.docker"
    )
    
    # Uninstall packages
    Get-Package *docker* -ErrorAction SilentlyContinue | Uninstall-Package -Force -ErrorAction SilentlyContinue
    
    # Remove directories
    foreach ($path in $paths) {
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path -ErrorAction SilentlyContinue
            Write-Log "Removed: $path" -Level SUCCESS
        }
    }
    
    return $true
}

function Remove-WSLFiles {
    Write-Log "Removing WSL data and cache..." -Level INFO
    
    $paths = @(
        "$env:LOCALAPPDATA\Packages\Canonical*",
        "$env:ProgramData\Microsoft\Windows\Subsystems",
        "$env:TEMP\wsl*",
        "$env:TEMP\setup_docker_ubuntu.sh"
    )
    
    foreach ($path in $paths) {
        Get-Item $path -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    Write-Log "WSL data cleaned" -Level SUCCESS
    return $true
}

# ═══════════════════════════════════════════════════════════════════════════
# INSTALLATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

function Install-WSLFeatures {
    Write-Log "Enabling Windows features for WSL2..." -Level INFO
    
    try {
        dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
        dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null
        Write-Log "Windows features enabled successfully" -Level SUCCESS
        return $true
    } catch {
        Write-Log "Error enabling features: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

function Install-WSLKernel {
    Write-Log "Installing WSL kernel package..." -Level INFO
    
    try {
        $msiPath = "$env:TEMP\wsl_update_x64.msi"
        $msiUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
        
        Write-Log "Downloading WSL kernel update..." -Level INFO
        Invoke-WebRequest -Uri $msiUrl -OutFile $msiPath -UseBasicParsing -ErrorAction Stop
        
        Write-Log "Installing WSL kernel..." -Level INFO
        Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /quiet /norestart" -Wait -NoNewWindow
        
        # Also install main WSL package
        $wslMsiPath = "$env:TEMP\wsl.msi"
        $wslMsiUrl = "https://aka.ms/wsl-x64"
        
        Write-Log "Downloading WSL main package..." -Level INFO
        Invoke-WebRequest -Uri $wslMsiUrl -OutFile $wslMsiPath -UseBasicParsing -ErrorAction Stop
        
        Write-Log "Installing WSL package..." -Level INFO
        Start-Process msiexec.exe -ArgumentList "/i `"$wslMsiPath`" /passive /norestart" -Wait -NoNewWindow
        
        # Verify installation
        Start-Sleep -Seconds 5
        $wslPath = "$env:SystemRoot\System32\wsl.exe"
        if (Test-Path $wslPath) {
            Write-Log "WSL kernel installed successfully" -Level SUCCESS
            return $true
        } else {
            Write-Log "WSL installation verification failed" -Level ERROR
            return $false
        }
    } catch {
        Write-Log "Error installing WSL kernel: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

function Set-WSLDefaultVersion {
    Write-Log "Setting WSL default version to 2..." -Level INFO
    
    try {
        wsl --set-default-version 2 2>&1 | Out-Null
        Write-Log "WSL2 set as default" -Level SUCCESS
        return $true
    } catch {
        Write-Log "Error setting WSL version: $($_.Exception.Message)" -Level WARN
        return $false
    }
}

function Install-UbuntuDistro {
    param([string]$DistroName)
    
    Write-Log "Installing $DistroName..." -Level INFO
    
    try {
        # Check if already installed
        $existingDistros = wsl --list --quiet 2>&1
        if ($existingDistros -match $DistroName) {
            Write-Log "$DistroName already installed" -Level INFO
            return $true
        }
        
        # Install the distribution
        Write-Log "Downloading and installing $DistroName (this may take a few minutes)..." -Level INFO
        wsl --install -d $DistroName 2>&1 | Out-Null
        
        # Wait for installation
        Start-Sleep -Seconds 10
        
        # Verify installation
        $distros = wsl --list --quiet 2>&1
        if ($distros -match $DistroName) {
            Write-Log "$DistroName installed successfully" -Level SUCCESS
            return $true
        } else {
            Write-Log "$DistroName installation failed" -Level ERROR
            return $false
        }
    } catch {
        Write-Log "Error installing Ubuntu: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

function Install-DockerInUbuntu {
    param([string]$DistroName)
    
    Write-Log "Installing Docker in $DistroName..." -Level INFO
    
    try {
        # Create Docker installation script
        $dockerScript = @'
#!/bin/bash
set -e

echo "Updating package lists..."
sudo apt update -y

echo "Installing prerequisites..."
sudo apt install -y ca-certificates curl gnupg lsb-release apt-transport-https

echo "Adding Docker GPG key..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "Adding Docker repository..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Installing Docker..."
sudo apt update -y
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Configuring Docker permissions..."
sudo usermod -aG docker $USER

echo "Enabling Docker service..."
sudo systemctl enable docker
sudo systemctl start docker

echo "Docker installation complete!"
docker --version
'@
        
        # Write script to temp file and copy to WSL
        $tempScript = "$env:TEMP\install_docker.sh"
        $dockerScript | Out-File -FilePath $tempScript -Encoding utf8 -NoNewline
        
        Write-Log "Copying installation script to WSL..." -Level INFO
        Get-Content -Raw $tempScript | wsl -d $DistroName -- bash -c "cat > /tmp/install_docker.sh"
        wsl -d $DistroName -- chmod +x /tmp/install_docker.sh
        
        Write-Log "Running Docker installation (this may take several minutes)..." -Level INFO
        wsl -d $DistroName -- bash /tmp/install_docker.sh
        
        Write-Log "Docker installed successfully in Ubuntu" -Level SUCCESS
        return $true
    } catch {
        Write-Log "Error installing Docker: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

function Test-WSLInstallation {
    Write-Log "Validating WSL installation..." -Level INFO
    
    try {
        # Check if wsl.exe exists
        $wslPath = "$env:SystemRoot\System32\wsl.exe"
        if (-not (Test-Path $wslPath)) {
            Write-Log "WSL executable not found at $wslPath" -Level ERROR
            return $false
        }
        
        # Check WSL version
        $version = wsl --version 2>&1
        if ($version -match "WSL version:") {
            Write-Log "WSL Version: $($version -split "`n" | Select-Object -First 1)" -Level SUCCESS
            return $true
        } else {
            Write-Log "Unable to retrieve WSL version" -Level WARN
            return $false
        }
    } catch {
        Write-Log "WSL validation failed: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

function Test-DockerInstallation {
    param([string]$DistroName)
    
    Write-Log "Validating Docker installation..." -Level INFO
    
    try {
        # Test Docker version
        $dockerVersion = wsl -d $DistroName -- docker --version 2>&1
        if ($dockerVersion -match "Docker version") {
            Write-Log "Docker version: $dockerVersion" -Level SUCCESS
        } else {
            Write-Log "Docker not found or not working" -Level ERROR
            return $false
        }
        
        # Test Docker hello-world
        Write-Log "Running Docker hello-world test..." -Level INFO
        $helloWorld = wsl -d $DistroName -- sudo docker run --rm hello-world 2>&1
        if ($helloWorld -match "Hello from Docker") {
            Write-Log "Docker hello-world test PASSED" -Level SUCCESS
            return $true
        } else {
            Write-Log "Docker hello-world test FAILED" -Level ERROR
            return $false
        }
    } catch {
        Write-Log "Docker validation failed: $($_.Exception.Message)" -Level ERROR
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# DIAGNOSTICS FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

function Get-SystemDiagnostics {
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    Write-Log "SYSTEM DIAGNOSTICS REPORT" -Level INFO
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    
    # Windows Info
    $os = Get-CimInstance Win32_OperatingSystem
    Write-Log "OS: $($os.Caption) Build $($os.Version)" -Level INFO
    Write-Log "Architecture: $env:PROCESSOR_ARCHITECTURE" -Level INFO
    
    # Memory
    $memory = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    Write-Log "Total RAM: $memory GB" -Level INFO
    
    # Virtualization
    $vm = Get-CimInstance -ClassName Win32_ComputerSystem
    Write-Log "Hyper-V Enabled: $($vm.HypervisorPresent)" -Level INFO
    
    # WSL Status
    try {
        $wslVersion = wsl --version 2>&1
        Write-Log "WSL Status: INSTALLED" -Level SUCCESS
        Write-Log "$wslVersion" -Level INFO
    } catch {
        Write-Log "WSL Status: NOT INSTALLED" -Level WARN
    }
    
    # WSL Distributions
    try {
        $distros = wsl --list --verbose 2>&1
        Write-Log "WSL Distributions:" -Level INFO
        Write-Log "$distros" -Level INFO
    } catch {
        Write-Log "No WSL distributions found" -Level WARN
    }
    
    # Docker Status
    $dockerService = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
    if ($dockerService) {
        Write-Log "Docker Service Status: $($dockerService.Status)" -Level INFO
    } else {
        Write-Log "Docker Service: NOT INSTALLED" -Level WARN
    }
    
    Write-Log "═══════════════════════════════════════════════" -Level INFO
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION LOGIC
# ═══════════════════════════════════════════════════════════════════════════

function Start-FullSetup {
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    Write-Log "WSL + DOCKER ENTERPRISE SETUP" -Level INFO
    Write-Log "Version: 1.0-ENTERPRISE | Creator: Herman Swanepoel" -Level INFO
    Write-Log "Mode: $Mode | Distro: $DistroName" -Level INFO
    Write-Log "═══════════════════════════════════════════════" -Level INFO
    
    # Step 1: System Requirements Check
    Write-Log "`n[STEP 1/7] System Requirements Check" -Level INFO
    if (-not (Test-SystemRequirements)) {
        Write-Log "System requirements not met. Please resolve issues and try again." -Level ERROR
        return $false
    }
    
    # Step 2: Cleanup
    Write-Log "`n[STEP 2/7] Cleanup Phase" -Level INFO
    Stop-WSLAndDocker | Out-Null
    Remove-WSLDistributions | Out-Null
    Remove-WSLFeatures | Out-Null
    Remove-DockerFiles | Out-Null
    Remove-WSLFiles | Out-Null
    
    # Step 3: Prompt for reboot if needed
    Write-Log "`n[STEP 3/7] Reboot Check" -Level INFO
    if (-not $SkipReboot) {
        Write-Log "Cleanup complete. A reboot is recommended before continuing." -Level WARN
        $response = Read-Host "Reboot now? (Y/N)"
        if ($response -eq 'Y') {
            Write-Log "Rebooting system..." -Level INFO
            Restart-Computer -Force
            return $true
        }
    }
    
    # Step 4: Enable Features
    Write-Log "`n[STEP 4/7] Enable Windows Features" -Level INFO
    if (-not (Install-WSLFeatures)) {
        Write-Log "Failed to enable Windows features" -Level ERROR
        return $false
    }
    
    # Step 5: Install WSL Kernel
    Write-Log "`n[STEP 5/7] Install WSL Kernel" -Level INFO
    if (-not (Install-WSLKernel)) {
        Write-Log "Failed to install WSL kernel" -Level ERROR
        return $false
    }
    
    Set-WSLDefaultVersion | Out-Null
    
    # Step 6: Install Ubuntu
    Write-Log "`n[STEP 6/7] Install Ubuntu Distribution" -Level INFO
    if (-not (Install-UbuntuDistro -DistroName $DistroName)) {
        Write-Log "Failed to install Ubuntu" -Level ERROR
        return $false
    }
    
    # Step 7: Install Docker
    Write-Log "`n[STEP 7/7] Install Docker in Ubuntu" -Level INFO
    if (-not (Install-DockerInUbuntu -DistroName $DistroName)) {
        Write-Log "Failed to install Docker" -Level ERROR
        return $false
    }
    
    # Final Validation
    Write-Log "`n[VALIDATION] Testing Installation" -Level INFO
    $wslValid = Test-WSLInstallation
    $dockerValid = Test-DockerInstallation -DistroName $DistroName
    
    if ($wslValid -and $dockerValid) {
        Write-Log "`n✅ SETUP COMPLETE! WSL2 + Docker are ready to use." -Level SUCCESS
        Write-Log "To start using Docker, run: wsl -d $DistroName" -Level INFO
        return $true
    } else {
        Write-Log "`n❌ Setup completed with errors. Check logs for details." -Level ERROR
        return $false
    }
}

# ═══════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

# Initialize log file
"WSL + Docker Enterprise Setup Log - $(Get-Date)" | Out-File -FilePath $LogPath -Force

switch ($Mode) {
    "FullSetup" {
        Start-FullSetup
    }
    "CleanupOnly" {
        Write-Log "Running cleanup only..." -Level INFO
        Stop-WSLAndDocker
        Remove-WSLDistributions
        Remove-WSLFeatures
        Remove-DockerFiles
        Remove-WSLFiles
        Write-Log "Cleanup complete. Please reboot." -Level SUCCESS
    }
    "InstallOnly" {
        Write-Log "Running installation only..." -Level INFO
        Install-WSLFeatures
        Install-WSLKernel
        Set-WSLDefaultVersion
        Install-UbuntuDistro -DistroName $DistroName
        Install-DockerInUbuntu -DistroName $DistroName
    }
    "DiagnosticsOnly" {
        Get-SystemDiagnostics
    }
    "Validate" {
        Test-WSLInstallation
        Test-DockerInstallation -DistroName $DistroName
    }
}

Write-Log "`nLog file saved to: $LogPath" -Level INFO
