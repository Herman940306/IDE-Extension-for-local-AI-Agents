# WSL2 & Docker Installation Validator
# Checks if everything is installed correctly
# Created: 2025-10-19

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "WSL2 & Docker Installation Validator" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Check 1: WSL installed
Write-Host "[CHECK 1] WSL Installation..." -ForegroundColor Yellow
try {
    $wslVersion = wsl --version 2>&1
    if ($wslVersion -match "WSL version") {
        Write-Host "✅ WSL is installed" -ForegroundColor Green
        Write-Host $wslVersion -ForegroundColor Gray
    } else {
        Write-Host "❌ WSL is not installed or not in PATH" -ForegroundColor Red
        $allPassed = $false
    }
} catch {
    Write-Host "❌ WSL command not found" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 2: WSL distributions
Write-Host "[CHECK 2] WSL Distributions..." -ForegroundColor Yellow
try {
    $distros = wsl --list --verbose 2>&1
    if ($distros -match "Ubuntu" -or $distros -match "Debian" -or $distros -match "Alpine") {
        Write-Host "✅ WSL distributions found:" -ForegroundColor Green
        Write-Host $distros -ForegroundColor Gray
        
        # Check if any distro is version 2
        if ($distros -match "VERSION 2") {
            Write-Host "✅ WSL2 distro detected" -ForegroundColor Green
        } else {
            Write-Host "⚠️  No WSL2 distros found (all are WSL1)" -ForegroundColor Yellow
            Write-Host "   Run: wsl --set-default-version 2" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  No WSL distributions installed" -ForegroundColor Yellow
        Write-Host "   Run: wsl --install -d Ubuntu-24.04" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Unable to list distributions" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 3: VirtualMachinePlatform feature
Write-Host "[CHECK 3] VirtualMachinePlatform Feature..." -ForegroundColor Yellow
try {
    $vmPlatform = dism.exe /online /Get-FeatureInfo /FeatureName:VirtualMachinePlatform 2>&1
    if ($vmPlatform -match "State : Enabled") {
        Write-Host "✅ VirtualMachinePlatform is enabled" -ForegroundColor Green
    } else {
        Write-Host "❌ VirtualMachinePlatform is not enabled" -ForegroundColor Red
        Write-Host "   Enable it in: Turn Windows features on or off" -ForegroundColor Yellow
        $allPassed = $false
    }
} catch {
    Write-Host "❌ Unable to check VirtualMachinePlatform status" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 4: WSL feature
Write-Host "[CHECK 4] Windows Subsystem for Linux Feature..." -ForegroundColor Yellow
try {
    $wslFeature = dism.exe /online /Get-FeatureInfo /FeatureName:Microsoft-Windows-Subsystem-Linux 2>&1
    if ($wslFeature -match "State : Enabled") {
        Write-Host "✅ WSL feature is enabled" -ForegroundColor Green
    } else {
        Write-Host "❌ WSL feature is not enabled" -ForegroundColor Red
        Write-Host "   Enable it in: Turn Windows features on or off" -ForegroundColor Yellow
        $allPassed = $false
    }
} catch {
    Write-Host "❌ Unable to check WSL feature status" -ForegroundColor Red
    $allPassed = $false
}
Write-Host ""

# Check 5: Hypervisor
Write-Host "[CHECK 5] Hypervisor Status..." -ForegroundColor Yellow
try {
    $hyperv = Get-CimInstance -ClassName Win32_ComputerSystem
    if ($hyperv.HypervisorPresent) {
        Write-Host "✅ Hypervisor is present and running" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Hypervisor not detected (may be normal if not using Hyper-V)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Unable to check hypervisor status" -ForegroundColor Yellow
}
Write-Host ""

# Check 6: Docker in WSL (if distro exists)
Write-Host "[CHECK 6] Docker in WSL..." -ForegroundColor Yellow
try {
    $distroCheck = wsl --list --quiet 2>&1 | Select-Object -First 1
    if ($distroCheck -match '\S') {
        $distroName = ($distroCheck -split "`n")[0].Trim()
        Write-Host "   Checking Docker in: $distroName" -ForegroundColor Gray
        
        $dockerVersion = wsl -d $distroName -- docker --version 2>&1
        if ($dockerVersion -match "Docker version") {
            Write-Host "✅ Docker is installed in WSL: $dockerVersion" -ForegroundColor Green
            
            # Test Docker hello-world
            Write-Host "   Testing Docker with hello-world..." -ForegroundColor Gray
            $helloWorld = wsl -d $distroName -- sudo docker run --rm hello-world 2>&1
            if ($helloWorld -match "Hello from Docker") {
                Write-Host "✅ Docker hello-world test PASSED" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Docker hello-world test failed" -ForegroundColor Yellow
                Write-Host "   Output: $helloWorld" -ForegroundColor Gray
            }
        } else {
            Write-Host "⚠️  Docker is not installed in WSL" -ForegroundColor Yellow
            Write-Host "   Run the installation script to install Docker" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  No WSL distributions to check for Docker" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Unable to check Docker in WSL" -ForegroundColor Yellow
}
Write-Host ""

# Check 7: Virtualization in BIOS
Write-Host "[CHECK 7] CPU Virtualization..." -ForegroundColor Yellow
try {
    $cpu = Get-CimInstance -ClassName Win32_Processor
    if ($cpu.VirtualizationFirmwareEnabled) {
        Write-Host "✅ CPU Virtualization is enabled in BIOS" -ForegroundColor Green
    } else {
        Write-Host "❌ CPU Virtualization is disabled in BIOS" -ForegroundColor Red
        Write-Host "   Enable Intel VT-x/VT-d or AMD-V/SVM in BIOS settings" -ForegroundColor Yellow
        $allPassed = $false
    }
} catch {
    Write-Host "⚠️  Unable to detect CPU virtualization status" -ForegroundColor Yellow
}
Write-Host ""

# Final summary
Write-Host "===============================================" -ForegroundColor Cyan
if ($allPassed) {
    Write-Host "✅ ALL CRITICAL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "   Your WSL2 installation is ready to use." -ForegroundColor Green
} else {
    Write-Host "⚠️  SOME CHECKS FAILED" -ForegroundColor Yellow
    Write-Host "   Review the failures above and follow the suggested fixes." -ForegroundColor Yellow
}
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Quick command reference
Write-Host "Quick Command Reference:" -ForegroundColor Cyan
Write-Host "  - Check WSL version:        wsl --version" -ForegroundColor Gray
Write-Host "  - List distributions:       wsl --list --verbose" -ForegroundColor Gray
Write-Host "  - Set WSL2 as default:      wsl --set-default-version 2" -ForegroundColor Gray
Write-Host "  - Install Ubuntu:           wsl --install -d Ubuntu-24.04" -ForegroundColor Gray
Write-Host "  - Enter WSL:                wsl" -ForegroundColor Gray
Write-Host "  - Test Docker:              wsl -- docker run hello-world" -ForegroundColor Gray
Write-Host ""
